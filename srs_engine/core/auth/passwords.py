from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit — truncate to avoid ValueError
    return _pwd_context.hash(password[:72])

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain[:72], hashed)