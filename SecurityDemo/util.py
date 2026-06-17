# JWT helpers for the auth server lab: generate a token (with scopes) and validate one.
#   python util.py        # generates a token and writes it to .env as TOKEN=...
#
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
import datetime
 
# Secret key used to sign the JWT (HS256 - symmetric, for the lab only)
secret_key = 'your-secret-key'
 
def generate_token():
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }
    # the user info, its claims and expiry time
    payload = {
        "sub": "1234567890",                # Subject (user ID)
        "name": "User Userson",             # Custom claim
        "admin": True,                      # Custom claim
        "iat": datetime.datetime.utcnow(),  # Issued at
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),  # Expiry
        "scopes": ["Admin.Write", "User.Read"]  # Custom claim for scopes/permissions
    }
 
    # encode it
    encoded_jwt = jwt.encode(payload, secret_key, algorithm="HS256", headers=header)
    print("Encoded JWT:", encoded_jwt)
    return encoded_jwt
 
def validate_token(token: str) -> str | None:
    try:
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        return decoded
    except ExpiredSignatureError:
        print("[FAIL] Token has expired.")
    except InvalidTokenError as e:
        print(f"[FAIL] Invalid token: {e}")
    return None
 
if __name__ == "__main__":
    token = generate_token()
    # write to .env file
    with open(".env", "w") as f:
        f.write(f"TOKEN={token}")
    print(token)
