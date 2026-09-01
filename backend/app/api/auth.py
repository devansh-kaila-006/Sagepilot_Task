import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    secret = os.getenv("SUPABASE_JWT_SECRET")
    
    if not secret:
        # If secret is not configured, we'll allow access but warn. This prevents the whole 
        # POC from crashing if someone forgets to set the env var during testing.
        # In a real production environment, this should raise a 500 error.
        print("WARNING: SUPABASE_JWT_SECRET not set. Bypassing auth.")
        return {"sub": "anonymous"}

    try:
        # Supabase uses HS256 for signing JWTs. We don't strictly verify the audience here 
        # as it can vary, but we verify the signature against the secret.
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
