import json

import httpx
import pytest
from sqlalchemy import func, select

from app.models import Review, ReviewAnalysis, User, UserRole
from app.security import hash_password
from app.services import review_ai_service

VALID_ANALYSIS = {
    "sentiment": "mixed",
    "food_quality": "positive",
    "delivery": "negative",
    "packaging": "negative",
    "summary": "غذا خوب بود اما تحویل و بسته‌بندی مشکل داشت.",
}


def create_review(db_session, menu_data, email="review-owner@example.com", text="نظر مشتری"):
    user = User(
        name="Review Owner",
        email=email,
        hashed_password=hash_password("secret1234"),
        role=UserRole.CUSTOMER,
    )
    db_session.add(user)
    db_session.flush()
    review = Review(user_id=user.id, food_id=menu_data["pizza"], rating=4, text=text)
    db_session.add(review)
    db_session.commit()
    return user, review


def auth_header(client, email):
    response = client.post(
        "/auth/login", data={"username": email, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def configure_llm(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_api_url", "https://llm.example.test/v1/chat/completions")
    monkeypatch.setattr(settings, "llm_model", "test-model")


def test_provider_request_uses_configured_chat_completions_contract(monkeypatch):
    configure_llm(monkeypatch)
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": []}

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr(review_ai_service.httpx, "Client", lambda timeout: Client())

    review_ai_service._request_completion("نظر آزمایشی")

    assert captured["url"] == "https://llm.example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["messages"][1]["content"] == "نظر آزمایشی"


def test_http_transport_error_is_converted_to_provider_error(monkeypatch):
    configure_llm(monkeypatch)

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, **kwargs):
            raise httpx.TimeoutException("simulated timeout")

    monkeypatch.setattr(review_ai_service.httpx, "Client", lambda timeout: Client())

    with pytest.raises(review_ai_service.ReviewAIProviderError):
        review_ai_service._request_completion("نظر آزمایشی")


def test_analysis_is_validated_persisted_and_returned(client, db_session, menu_data, monkeypatch):
    configure_llm(monkeypatch)
    _, review = create_review(db_session, menu_data)

    def fake_completion(review_text):
        assert review_text == review.text
        return {"choices": [{"message": {"content": json.dumps(VALID_ANALYSIS, ensure_ascii=False)}}]}

    monkeypatch.setattr(review_ai_service, "_request_completion", fake_completion)
    response = client.post(
        "/ai/analyze-review",
        json={"review_id": review.id},
        headers=auth_header(client, "review-owner@example.com"),
    )

    assert response.status_code == 200
    assert response.json() == VALID_ANALYSIS
    assert db_session.scalar(select(func.count()).select_from(ReviewAnalysis)) == 1
    listed_review = client.get(f"/foods/{menu_data['pizza']}/reviews").json()[0]
    assert listed_review["analysis"] == VALID_ANALYSIS


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        json.dumps({**VALID_ANALYSIS, "delivery": "excellent"}),
        json.dumps({**VALID_ANALYSIS, "extra": "not allowed"}),
        json.dumps({**VALID_ANALYSIS, "summary": "   "}),
    ],
)
def test_invalid_model_output_is_not_saved(
    client, db_session, menu_data, monkeypatch, content
):
    configure_llm(monkeypatch)
    _, review = create_review(db_session, menu_data)
    monkeypatch.setattr(
        review_ai_service,
        "_request_completion",
        lambda review_text: {"choices": [{"message": {"content": content}}]},
    )

    response = client.post(
        "/ai/analyze-review",
        json={"review_id": review.id},
        headers=auth_header(client, "review-owner@example.com"),
    )

    assert response.status_code == 502
    assert db_session.scalar(select(func.count()).select_from(ReviewAnalysis)) == 0


def test_provider_error_does_not_save_analysis(client, db_session, menu_data, monkeypatch):
    configure_llm(monkeypatch)
    _, review = create_review(db_session, menu_data)

    def fail_request(review_text):
        raise review_ai_service.ReviewAIProviderError("simulated timeout")

    monkeypatch.setattr(review_ai_service, "_request_completion", fail_request)
    response = client.post(
        "/ai/analyze-review",
        json={"review_id": review.id},
        headers=auth_header(client, "review-owner@example.com"),
    )

    assert response.status_code == 502
    assert db_session.scalar(select(func.count()).select_from(ReviewAnalysis)) == 0


def test_missing_llm_configuration_returns_503_without_saving(
    client, db_session, menu_data, monkeypatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "")
    _, review = create_review(db_session, menu_data)

    response = client.post(
        "/ai/analyze-review",
        json={"review_id": review.id},
        headers=auth_header(client, "review-owner@example.com"),
    )

    assert response.status_code == 503
    assert db_session.scalar(select(func.count()).select_from(ReviewAnalysis)) == 0


def test_existing_analysis_is_returned_without_calling_provider(
    client, db_session, menu_data, monkeypatch
):
    _, review = create_review(db_session, menu_data)
    analysis = ReviewAnalysis(review_id=review.id, **VALID_ANALYSIS)
    db_session.add(analysis)
    db_session.commit()
    monkeypatch.setattr(
        review_ai_service,
        "_request_completion",
        lambda review_text: pytest.fail("provider should not be called"),
    )

    response = client.post(
        "/ai/analyze-review",
        json={"review_id": review.id},
        headers=auth_header(client, "review-owner@example.com"),
    )

    assert response.status_code == 200
    assert response.json() == VALID_ANALYSIS


def test_only_review_owner_or_admin_can_request_analysis(
    client, db_session, menu_data, login_as
):
    _, review = create_review(db_session, menu_data)

    response = client.post(
        "/ai/analyze-review",
        json={"review_id": review.id},
        headers=login_as(),
    )

    assert response.status_code == 403


def test_empty_review_text_is_rejected_without_calling_provider(
    client, db_session, menu_data, monkeypatch
):
    _, review = create_review(db_session, menu_data, text="  ")
    monkeypatch.setattr(
        review_ai_service,
        "_request_completion",
        lambda review_text: pytest.fail("provider should not be called"),
    )

    response = client.post(
        "/ai/analyze-review",
        json={"review_id": review.id},
        headers=auth_header(client, "review-owner@example.com"),
    )

    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(ReviewAnalysis)) == 0
