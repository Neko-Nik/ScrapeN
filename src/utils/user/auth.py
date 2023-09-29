from src.utils.base.libraries import (
    auth,
    initialize_app,
    credentials,
    HTTPBearer,
    HTTPAuthorizationCredentials,
    HTTPException,
    status,
    Response,
    Depends
)

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
        # check revoked token is required to be True so that we allow only valid tokens
        decoded_token = auth.verify_id_token(credential.credentials, check_revoked=True)

    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication!",
            headers={'WWW-Authenticate': 'Bearer error="invalid_token"'},
        )
    res.headers['WWW-Authenticate'] = 'Bearer realm="auth_required"'
    return decoded_token

