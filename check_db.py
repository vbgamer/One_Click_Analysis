from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend import models

try:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./backend/clean.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    users = db.query(models.User).all()
    print(f"Total Users: {len(users)}")
    for user in users:
        print(f"ID: {user.id}, Email: {user.email}, Name: {user.name}")

    db.close()
    print("Database check complete.")
except Exception as e:
    print(f"Error checking DB: {e}")
