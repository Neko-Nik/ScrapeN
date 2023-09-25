from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status, Response
from firebase_admin import auth, credentials, initialize_app
from src.utils.user.handler import User

credentials = credentials.Certificate("src/utils/user/firebase.json")

initialize_app(credentials)

def get_user_token(res: Response, credential: HTTPAuthorizationCredentials=Depends(HTTPBearer(auto_error=False))):
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is needed",
            headers={'WWW-Authenticate': 'Bearer realm="auth_required"'},
        )
    try:
        decoded_token = auth.verify_id_token(credential.credentials)
        # if user name is not in database, add it same as the email without @
        if not "name" in decoded_token:
            # This also means that user is using password login
            decoded_token["name"] = decoded_token["email"].split("@")[0]

    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication from Firebase. {err}",
            headers={'WWW-Authenticate': 'Bearer error="invalid_token"'},
        )
    res.headers['WWW-Authenticate'] = 'Bearer realm="auth_required"'
    return decoded_token

