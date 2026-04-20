from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.db import engine, get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, CreateResponse, LoginResponse
from app.crypto import hash_password, verify_password, create_access_token, get_public_key_pem, decode_token


User.metadata.create_all(bind=engine) # intialise tables

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register")
def register(data: UserCreate, db: Session = Depends(get_db)) -> CreateResponse:
    """
    Given username and password information, create a user account.
    """
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return CreateResponse(id=user.id, username=user.username)


@app.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)) -> LoginResponse:
    """
    Given username and password information, generate a JWT for the user to prove authentication and stay logged in.
    """
    user = db.query(User).filter(User.username == data.username).first()

    if not user:
        print(f"Login request fail: invalid user {data.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        print(f"Login request fail: invalid password for {data.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return LoginResponse(id=user.id, username=user.username, token=create_access_token(user.id))


@app.delete("/users/me")
def delete_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> dict:
    """
    Delete the currently authenticated user.
    Expects: Authorization: Bearer <token>
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    token = authorization.split(" ")[1]

    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"detail": "User deleted successfully"}


@app.get("/public_key")
def get_public_key() -> dict:
    """
    Retreive the public key that can be used by other services for checking token validity
    """
    return {"public_key": get_public_key_pem()}


@app.get("/validate")
def validate_token(authorization: str = Header(...)):
    """
    Check token validity. Not to be used by other services for checking token validity.
    Expects: Authorization: Bearer <token>
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    token = authorization.split(" ")[1]
    claims = decode_token(token)

    if not claims:
        raise HTTPException(status_code=401)
    return {"status": "ok"}
    