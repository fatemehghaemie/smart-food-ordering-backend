from app.database import Base, SessionLocal, engine
from app.seed import seed_all

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        print(seed_all(session))