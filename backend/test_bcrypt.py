from passlib.context import CryptContext

try:
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    hash = pwd_context.hash("password")
    print(f"Hash success: {hash}")
    verify = pwd_context.verify("password", hash)
    print(f"Verify success: {verify}")
except Exception as e:
    print(f"Error: {e}")
