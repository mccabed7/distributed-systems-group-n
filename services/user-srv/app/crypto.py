from jwcrypto import jwt, jwk
import json
from passlib.context import CryptContext
from datetime import datetime, timedelta


ACCESS_TOKEN_EXPIRE_MINUTES = 30


with open("private.pem", "rb") as f:
    private_key = jwk.JWK.from_pem(f.read())
    private_key.kid = "key0"

_jwks = jwk.JWKSet()
_jwks["keys"].add(private_key)

public_jwks = _jwks.export(private_keys=False, as_dict=True)

print(_jwks, public_jwks)


def create_access_token(user_id: str):
    header = {"alg": "RS256", "typ": "JWT", "kid": private_key.kid}
    payload = {
        "sub": str(user_id),
        "exp": int((datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp())
    }
    token = jwt.JWT(header=header, claims=payload)
    token.make_signed_token(private_key)
    return token.serialize()


def check_token_valid(token: str, jwks: str = None):
    if jwks is None:
        jwks = json.dumps(public_jwks)

    jwks = jwk.JWKSet.from_json(jwks)

    try:
        signed_token = jwt.JWT(jwt=token, key=jwks)
    except jwt.JWTMissingKey:
        return False

    print("validating token, claims:", signed_token.claims)
    return True





pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)