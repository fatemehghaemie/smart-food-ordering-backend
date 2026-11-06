# Smart Food Backend

یک API برای سفارش غذا با FastAPI و SQLAlchemy. نسخهٔ فعلی شامل احراز هویت، فهرست رستوران و غذا، سفارش، نظر مشتری، پیشنهاد محتوایی غذا و تحلیل اختیاری نظر با API مدل زبانی است.

## قابلیت‌های فعلی

- ثبت‌نام مشتری و ورود با JWT؛ ثبت‌نام عمومی همیشه نقش `CUSTOMER` می‌سازد.
- مشاهده و جست‌وجوی رستوران‌ها و غذاها، مشاهدهٔ منو و فیلتر موجودی و قیمت.
- ساخت رستوران و غذا فقط برای مدیر.
- ثبت سفارش با محاسبهٔ مبلغ در Backend، ادغام اقلام تکراری و نگهداری قیمت زمان سفارش.
- مشاهدهٔ سفارش‌ها؛ مشتری فقط سفارش‌های خودش را می‌بیند و مدیر همه را.
- تغییر وضعیت طبق جریان مجاز: `PENDING → CONFIRMED → PREPARING → READY → DELIVERED`. لغو از `PENDING` و `CONFIRMED` مجاز است؛ `DELIVERED` و `CANCELLED` نهایی‌اند.
- ثبت یک نظر برای هر غذا توسط مشتری‌ای که آن غذا را در سفارش تحویل‌شده داشته است.
- پیشنهاد غذا بر پایهٔ شباهت محتوا و سابقهٔ سفارش‌های تحویل‌شده.
- تحلیل اختیاری متن نظر با یک API سازگار با قالب Chat Completions؛ خروجی فقط پس از اعتبارسنجی ذخیره می‌شود.

## پیش‌نیازها

- Python 3.10 یا جدیدتر
- pip
- Windows PowerShell برای دستورهای زیر؛ فرمان‌های Uvicorn در سیستم‌عامل‌های دیگر نیز قابل اجرا هستند.

نسخهٔ MVP به‌طور پیش‌فرض از SQLite استفاده می‌کند. فایل دیتابیس `smartfood.db` هنگام اجرا ساخته می‌شود و در Git نادیده گرفته شده است.

## نصب و اجرا در Windows

از ریشهٔ پروژه اجرا کن:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

اگر `.env` از قبل وجود دارد، دستور بالا آن را حفظ می‌کند؛ همان فایل را طبق بخش بعد ویرایش کن. سپس داده‌های نمونه را وارد کن:

```powershell
python run_seed.py
```

اجرای API:

```powershell
python run_server.py
```

یا با Uvicorn:

```powershell
uvicorn app.main:app --reload
```

API به‌طور پیش‌فرض روی `http://127.0.0.1:8000` در دسترس است. مستندات تعاملی Swagger در `/docs` و مستندات ReDoc در `/redoc` قرار دارند. برای بررسی در دسترس‌بودن سرویس از `GET /health` استفاده کن.

اگر فعال‌سازی venv در PowerShell به‌دلیل Execution Policy مجاز نبود، می‌توانی بدون فعال‌سازی آن فرمان‌ها را با مسیر کامل اجرا کنی:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe run_seed.py
.\venv\Scripts\python.exe run_server.py
```

## تنظیم متغیرهای محیطی

برنامه مقادیر را از فایل `.env` در ریشهٔ پروژه می‌خواند. `.env` را commit نکن؛ این فایل در `.gitignore` آمده است.

| متغیر | کاربرد |
|---|---|
| `DATABASE_URL` | نشانی دیتابیس؛ مقدار پیش‌فرض `sqlite:///./smartfood.db` است. |
| `SECRET_KEY` | کلید امضای JWT؛ برای استفادهٔ محلی هم یک مقدار تصادفی و بلند انتخاب کن. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | مدت اعتبار توکن؛ پیش‌فرض ۶۰ دقیقه. |
| `ADMIN_EMAIL` | ایمیل مدیر نمونه که هنگام seed ساخته می‌شود. اختیاری است. |
| `ADMIN_PASSWORD` | رمز مدیر نمونه؛ همراه `ADMIN_EMAIL` تنظیم شود. اختیاری است. |
| `LLM_API_KEY` | کلید دسترسی به سرویس مدل زبانی. |
| `LLM_API_URL` | نشانی کامل endpoint سازگار با Chat Completions. |
| `LLM_MODEL` | نام مدلی که provider می‌شناسد. |

برای ساخت کلید تصادفی می‌توانی این فرمان را اجرا کنی و خروجی را در `.env` بگذاری:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

تنظیمات LLM برای اجرای API اصلی لازم نیست. اگر یکی از سه مقدار `LLM_API_KEY`، `LLM_API_URL` یا `LLM_MODEL` خالی باشد، درخواست تحلیل نظر با `503` پاسخ داده می‌شود. هنگام استفاده از LLM، نشانی باید endpoint کامل Chat Completions باشد؛ مثلاً قالبی مانند `https://provider.example/v1/chat/completions`. provider باید احراز هویت Bearer و گزینهٔ JSON response format را پشتیبانی کند.

## بارگذاری دادهٔ نمونه

`python run_seed.py` جداول را ایجاد می‌کند و داده‌ها را از این فایل‌ها می‌خواند:

- `data/restaurants.csv`
- `data/foods.csv`

بارگذاری داده‌ها idempotent است: رستوران‌ها با نام و غذاها با ترکیب رستوران و نام غذا شناسایی می‌شوند؛ اجرای دوبارهٔ seed رکورد تکراری با این کلیدها اضافه نمی‌کند. اگر `ADMIN_EMAIL` و `ADMIN_PASSWORD` تنظیم شده باشند، seed یک مدیر می‌سازد؛ در غیر این صورت حساب مدیر ساخته نمی‌شود. ثبت‌نام از API راهی برای انتخاب نقش مدیر ندارد.

## احراز هویت

ثبت‌نام با JSON انجام می‌شود:

```powershell
curl.exe -X POST http://127.0.0.1:8000/auth/register `
  -H "Content-Type: application/json" `
  -d '{"name":"Sara Ahmadi","email":"sara@example.com","password":"StrongPass123"}'
```

ورود از فرم `application/x-www-form-urlencoded` استفاده می‌کند. فیلد OAuth2 با نام `username` ایمیل کاربر را می‌گیرد:

```powershell
curl.exe -X POST http://127.0.0.1:8000/auth/login `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=sara@example.com&password=StrongPass123"
```

پاسخ شامل `access_token` و `token_type` است. برای endpointهای نیازمند ورود، توکن را در هدر بفرست:

```text
Authorization: Bearer <access_token>
```

`GET /auth/me` اطلاعات حساب واردشده را برمی‌گرداند.

## Endpointها

| روش | مسیر | دسترسی و کاربرد |
|---|---|---|
| `GET` | `/health` | سلامت سرویس |
| `POST` | `/auth/register` | ثبت‌نام مشتری |
| `POST` | `/auth/login` | ورود و دریافت JWT |
| `GET` | `/auth/me` | حساب کاربر واردشده |
| `GET` | `/restaurants` | فهرست؛ پارامترهای `search`, `skip`, `limit` |
| `GET` | `/restaurants/{restaurant_id}` | جزئیات رستوران |
| `GET` | `/restaurants/{restaurant_id}/menu` | منو؛ `only_available` پیش‌فرض `true` است |
| `POST` | `/restaurants` | ساخت رستوران؛ فقط مدیر |
| `GET` | `/foods` | جست‌وجو با `q`, `category`, `restaurant_id`, `min_price`, `max_price`, `only_available`, `skip`, `limit` |
| `GET` | `/foods/{food_id}` | جزئیات غذا |
| `POST` | `/foods` | ساخت غذا؛ فقط مدیر |
| `POST` | `/orders` | ثبت سفارش؛ نیازمند ورود |
| `GET` | `/orders` | سفارش‌های قابل‌مشاهده؛ فیلتر اختیاری `status`, `skip`, `limit` |
| `GET` | `/orders/{order_id}` | جزئیات سفارش؛ مشتری مالک یا مدیر |
| `PATCH` | `/orders/{order_id}/status` | تغییر وضعیت؛ مدیر جریان آشپزخانه را پیش می‌برد، مشتری فقط سفارش خودش را لغو می‌کند |
| `POST` | `/reviews` | ثبت نظر برای غذای سفارش تحویل‌شده؛ نیازمند ورود |
| `GET` | `/foods/{food_id}/reviews` | نظرهای یک غذا؛ `skip`, `limit` |
| `GET` | `/recommendations/{user_id}` | پیشنهادها؛ مشتری فقط برای خودش، مدیر برای هر کاربر؛ `limit` از ۱ تا ۱۰۰ |
| `POST` | `/ai/analyze-review` | تحلیل نظر ذخیره‌شده؛ نویسندهٔ نظر یا مدیر |

قیمت غذا و سفارش عدد صحیح به تومان است. صفحه‌بندی فهرست‌ها با `skip` و `limit` انجام می‌شود؛ `limit` حداکثر ۱۰۰ است.

## نمونهٔ ثبت سفارش

بعد از ورود، توکن را در `$env:TOKEN` قرار بده و شناسهٔ رستوران و غذا را از API کاتالوگ بردار:

```powershell
$env:TOKEN = "<access_token>"
curl.exe -X POST http://127.0.0.1:8000/orders `
  -H "Authorization: Bearer $env:TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"restaurant_id":1,"items":[{"food_id":1,"quantity":2}]}'
```

مبلغ از قیمت فعلی غذا در Backend محاسبه می‌شود و قیمت زمان سفارش در اقلام سفارش نگهداری می‌شود. نمونهٔ خلاصه‌شدهٔ پاسخ:

```json
{
  "id": 1,
  "customer_id": 2,
  "restaurant_id": 1,
  "status": "PENDING",
  "total_price": 640000,
  "estimated_delivery_minutes": null,
  "created_at": "2026-01-01T12:00:00Z",
  "items": [
    {"food_id": 1, "quantity": 2, "unit_price": 320000, "line_total": 640000}
  ]
}
```

برای تغییر وضعیت، بدنه نمونه `{"status":"CONFIRMED"}` است. پرش از مراحل مجاز نیست و وضعیت‌های `DELIVERED` و `CANCELLED` نهایی‌اند.

## پیشنهاد غذا

نمونهٔ درخواست:

```powershell
curl.exe http://127.0.0.1:8000/recommendations/2?limit=5 `
  -H "Authorization: Bearer $env:TOKEN"
```

پاسخ شامل `strategy` و فهرست غذاها با امتیاز شباهت است:

```json
{
  "user_id": 2,
  "strategy": "personalized",
  "recommendations": [
    {"food":{"id":8,"name":"چیزبرگر","description":"...","ingredients":"...","category":"برگر","price":310000,"is_available":true,"restaurant_id":2},"score":0.73}
  ]
}
```

مدل MVP یک Content-Based Filter ساده است: متن نام، دسته‌بندی، توضیحات و مواد اولیه با TF-IDF برداری می‌شود؛ قیمت هم مقیاس‌بندی و به بردار اضافه می‌شود؛ رتبه‌بندی با Cosine Similarity انجام می‌شود. پروفایل سلیقه از اقلام سفارش‌های تحویل‌شده ساخته می‌شود و غذاهایی که کاربر قبلاً سفارش داده، از نتایج کنار گذاشته می‌شوند.

برای کاربری که سابقهٔ تحویل‌شده ندارد، `strategy` برابر `popular` می‌شود و غذاها بر اساس تعداد فروش تحویل‌شدهٔ سراسری مرتب می‌شوند. اگر فروش تحویل‌شده‌ای برای هیچ غذایی ثبت نشده باشد یا گزینهٔ در دسترس دیگری باقی نمانده باشد، `strategy` برابر `empty` و فهرست خالی است.

این روش برای MVP و کاتالوگ کوچک مناسب است. معنای ویژگی‌ها و وزن قیمت ساده است؛ مدل از رفتار کاربران مشابه یاد نمی‌گیرد، مشکل cold-start را فقط با محبوبیت عمومی پاسخ می‌دهد، و برای کاتالوگ بزرگ هنوز بهینه‌سازی نشده است. این خروجی نباید به‌عنوان توصیه‌گر صنعتی یا ارزیابی‌شده روی دادهٔ واقعی معرفی شود.

## تحلیل هوشمند نظر

ابتدا مشتری نظر را با `POST /reviews` ثبت می‌کند. سپس شناسهٔ همان نظر را به endpoint تحلیل می‌دهد:

```powershell
curl.exe -X POST http://127.0.0.1:8000/ai/analyze-review `
  -H "Authorization: Bearer $env:TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"review_id":1}'
```

نمونهٔ پاسخ:

```json
{
  "sentiment": "mixed",
  "food_quality": "positive",
  "delivery": "negative",
  "packaging": "negative",
  "summary": "غذا کیفیت خوبی داشته اما تحویل و بسته‌بندی مشکل داشته است."
}
```

خروجی JSON مدل با Pydantic اعتبارسنجی می‌شود. برچسب sentiment یکی از `positive`, `negative`, `mixed`, `neutral` و برچسب هر جنبه یکی از `positive`, `negative`, `neutral`, `not_mentioned` است. در صورت خطای provider یا خروجی نامعتبر، تحلیل ذخیره نمی‌شود. تحلیل معتبر برای همان نظر دوباره از provider درخواست نمی‌شود و در پاسخ فهرست نظرهای آن غذا نیز قابل مشاهده است.

این پیاده‌سازی به endpoint کامل سازگار با Chat Completions نیاز دارد و درخواست را با Bearer API key، نام مدل، prompt و `response_format: json_object` می‌فرستد. نام دقیق مدل و سازگاری provider باید در تنظیمات خودت وارد شود. تا زمانی که مقادیر LLM در `.env` تنظیم نشوند، endpoint با `503` پاسخ می‌دهد. تست‌های خودکار از پاسخ mock استفاده می‌کنند و ارتباط زنده با provider را ارزیابی نمی‌کنند.

## اجرای تست‌ها

با venv فعال:

```powershell
python -m pytest -q
```

یا بدون فعال‌سازی:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

تست‌ها از SQLite درون‌حافظه‌ای استفاده می‌کنند. تست‌های تحلیل LLM mock هستند و به API key واقعی یا اینترنت نیاز ندارند.

## ساختار کد

```text
app/
  models/       SQLAlchemy entities
  schemas/      Pydantic request/response validation
  routers/      HTTP endpoints and status mapping
  services/     business rules and integrations
  database.py   SQLAlchemy engine and session dependency
data/           CSV seed data
tests/          API and business-rule tests
```

جداول با `Base.metadata.create_all` ساخته می‌شوند. این MVP هنوز migration دیتابیس ندارد. SQLite پیکربندی پیش‌فرض و مسیر آزموده‌شده است؛ استفاده از PostgreSQL به نصب driver مناسب و تنظیمات جداگانه نیاز دارد. Docker، تخمین زمان تحویل و endpoint گزارش مدیریتی در وضعیت فعلی پیاده‌سازی نشده‌اند و قابلیت‌های تکمیلی بعد از MVP محسوب می‌شوند.
