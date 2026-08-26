from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from schemas.contact import ContactReceipt, ContactSessionStatus, ContactSubmission
from services.contact_service import contact_service
from services.contact_delivery import public_delivery_config, real_contact_service

router = APIRouter(prefix="/contact", tags=["contact"])
bearer = HTTPBearer(auto_error=False)


def call_service(method, *args):
    service = real_contact_service() if public_delivery_config()["mode"] == "resend" else contact_service
    return getattr(service, method)(*args)


@router.get("/config")
def delivery_config(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return public_delivery_config()


def session_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "contact_session_required")
    return credentials.credentials


@router.post("/sessions")
def create_session(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"token": call_service("create_session"), "used": False}


@router.get("/session", response_model=ContactSessionStatus)
def get_session(response: Response, token: str = Depends(session_token)):
    response.headers["Cache-Control"] = "no-store"
    return call_service("status", token)


@router.post("/submit", response_model=ContactReceipt)
def submit_contact(submission: ContactSubmission, response: Response, token: str = Depends(session_token)):
    response.headers["Cache-Control"] = "no-store"
    return call_service("submit", token, submission)
