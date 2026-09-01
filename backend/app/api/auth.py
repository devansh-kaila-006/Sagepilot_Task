import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = credentials.credentials
    import httpx
    import logging

    try:
        supabase_url = os.getenv("SUPABASE_URL")
        anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not anon_key:
            logging.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY in env")
            raise Exception("Server configuration error")

        # Call Supabase to get the user
        response = httpx.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": anon_key
            }
        )

        if response.status_code != 200:
            logging.error(f"Supabase auth failed: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user_data = response.json()
        return {"sub": user_data.get("id"), "role": user_data.get("role"), "email": user_data.get("email")}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"JWT Verification Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Server Error",
            headers={"WWW-Authenticate": "Bearer"},
        )
