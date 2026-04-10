import jwt
import json
from cryptography.hazmat.primitives import serialization
from passlib.context import CryptContext
from datetime import datetime, timedelta


ACCESS_TOKEN_EXPIRE_MINUTES = 30
PRIVATE_PEM_LOCATION = "app/private.pem"


with open(PRIVATE_PEM_LOCATION, "rb") as f:
    _private_key = serialization.load_pem_private_key(
        f.read(),
        password=None
    )

_public_key_pem = _private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_public_key_pem():
    return _public_key_pem


def create_access_token(user_id: str):
    payload = {
        "sub": str(user_id),
        "exp": int((datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())
    }

    token = jwt.encode(payload, _private_key, algorithm="RS256")

    return token


def decode_token(token: str, public_key_pem: str = None):
    if public_key_pem is None:
        public_key_pem = get_public_key_pem()

    try:
        signed_token = jwt.decode(token, public_key_pem, algorithms=["RS256"])
    except Exception as e:
        print("Error decoding JWT: e")
        return None

    return signed_token


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)