# JWT basics: create and validate a signed token.
#   python lab.py

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
import datetime
 
# Secret key used to sign the JWT (HS256 - symmetric, for the lab only)
secret_key = 'this is a demo secret key used for testing'
 
header = {
    "alg": "HS256",
    "typ": "JWT"
}
 
# The user info, its claims and expiry time
payload = {
    "sub": "1234567890",                # Subject (user ID)
    "name": "User Userson",             # Custom claim
    "admin": True,                      # Custom claim
    "iat": datetime.datetime.utcnow(),  # Issued at
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Expiry
}
 
# encode it
encoded_jwt = jwt.encode(payload, secret_key, algorithm="HS256", headers=header)
 
print("Encoded JWT:", encoded_jwt)
 
# validate a token
try:
    decoded = jwt.decode(encoded_jwt, secret_key, algorithms=["HS256"])
    print("[OK] Token is valid.")
    print("Decoded claims:")
    for key, value in decoded.items():
        print(f"  {key}: {value}")
except ExpiredSignatureError:
    print("[FAIL] Token has expired.")
except InvalidTokenError as e:
    print(f"[FAIL] Invalid token: {e}")
