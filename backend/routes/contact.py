from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from schemas.contact import ContactReceipt, ContactSessionStatus, ContactSubmission
from services.contact_service import contact_service

router = APIRouter(prefix="/contact", tags=["contact demo"])
bearer = HTTPBearer(auto_error=False)


def session_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "contact_session_required")
    return credentials.credentials


@router.get("/profile")
def public_contact():
    # Explicitly authorized public contact; not indexed in RAG or inferred by the model.
    return {
        "name": "Jeyker Salinas",
        "phone": "+34 624 179 342",
        "email": "jeyker.salinas13@gmail.com",
        "github": "https://github.com/JeykerSalinas",
    }


@router.post("/sessions")
def create_session(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"token": contact_service.create_session(), "used": False}


@router.get("/session", response_model=ContactSessionStatus)
def get_session(response: Response, token: str = Depends(session_token)):
    response.headers["Cache-Control"] = "no-store"
    return contact_service.status(token)


@router.post("/submit", response_model=ContactReceipt)
def submit_contact(submission: ContactSubmission, response: Response, token: str = Depends(session_token)):
    response.headers["Cache-Control"] = "no-store"
    return contact_service.submit(token, submission)
