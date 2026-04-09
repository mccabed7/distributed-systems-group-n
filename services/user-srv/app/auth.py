from sqlalchemy.orm import Session
from app.models import User
from app.crypto import hash_password, verify_password, create_access_token

def register_user(db: Session, email: str, password: str):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise Exception("User already exists")

    user = User(
        email=email,
        password_hash=hash_password(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def login_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise Exception("Invalid credentials (user)")
    if not verify_password(password, user.password_hash):
        raise Exception("Invalid credentials (pass)")

    token = create_access_token(user.id)
    return token