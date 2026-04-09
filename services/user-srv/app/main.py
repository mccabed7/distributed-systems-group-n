from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.db import engine, get_db
from app.models import User
from app.schemas import UserCreate, UserLogin
from app.auth import register_user, login_user
from app.crypto import public_jwks, check_token_valid

User.metadata.create_all(bind=engine) # just intialise tables

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register")
def register(data: UserCreate, db: Session = Depends(get_db)):
    try:
        print(db, data, data.email, data.password, len(data.password))
        user = register_user(db, data.email, data.password)
        return {"id": str(user.id), "email": user.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        token = login_user(db, data.email, data.password)
        return {"access_token": token}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/.well-known/jwks.json")
def jwks_endpoint():
    return public_jwks

@app.get("/validate")
def validate_token(authorization: str = Header(...)):
    token = authorization.split(" ")[1]
    valid = check_token_valid(token)
    if not valid:
        return HTTPException(
            status_code=401
        )
    return {"status": "ok"}
    