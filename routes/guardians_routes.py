from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from fastapi_config import get_session
from models.models import GuardianType, UserType
from services.guardian_services import GuardianServices
from services.user_service import UserService

router = APIRouter(prefix="/guardians", tags=["Guardians"])
guardian_service = GuardianServices()
user_service = UserService()


# ------------------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------------------
class CreateGuardianRequest(BaseModel):
    owner_id: str
    name: str = Field(..., min_length=1, max_length=120)
    guardian_type: GuardianType = GuardianType.PERSONAL


class AddConnectionRequest(BaseModel):
    user_id: str
    connection_type: UserType


class ChangeCodeRequest(BaseModel):
    code: int


class UpdateGuardianSettingsRequest(BaseModel):
    warning_message: str | None = None
    applause_message: str | None = None
    strictness: str | None = None
    language: str | None = None


# ------------------------------------------------------------------------------
# Guardian Management Endpoints
# ------------------------------------------------------------------------------
@router.get("/")
def get_all_guardians(session: Session = Depends(get_session)):
    return guardian_service.get_all_guardians(session)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_guardian(
    payload: CreateGuardianRequest, 
    session: Session = Depends(get_session)
):
    user = user_service.get_user_by_id(session, user_id=payload.owner_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User '{payload.owner_id}' not found"
        )

    guardian, msg = guardian_service.create_guardian(
        session=session,
        user=user,
        name=payload.name,
        guardian_type=payload.guardian_type,
    )

    if not guardian:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return guardian


@router.get("/{guardian_id}")
def get_guardian(guardian_id: str, session: Session = Depends(get_session)):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )
    return guardian


@router.get("/owner/{user_id}")
def get_guardian_by_owner(user_id: str, session: Session = Depends(get_session)):
    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User '{user_id}' not found"
        )

    guardian = guardian_service.get_guardian_by_owner(session, user=user)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Guardian found for owner '{user_id}'",
        )
    return guardian


@router.delete("/{guardian_id}")
def delete_guardian(guardian_id: str, session: Session = Depends(get_session)):
    success, msg = guardian_service.delete_guardian(
        session=session, guardian_id=guardian_id
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {"message": f"Guardian '{guardian_id}' successfully deleted"}


# ------------------------------------------------------------------------------
# Connections Endpoints
# ------------------------------------------------------------------------------
@router.get("/{guardian_id}/connections")
def get_guardian_connections(
    guardian_id: str, 
    session: Session = Depends(get_session)
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    return guardian_service.get_all_connections(session, guardian=guardian)


@router.post("/{guardian_id}/connections", status_code=status.HTTP_201_CREATED)
def add_connection(
    guardian_id: str,
    payload: AddConnectionRequest,
    session: Session = Depends(get_session),
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    user = user_service.get_user_by_id(session, user_id=payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{payload.user_id}' does not exist",
        )

    connection, msg = guardian_service.add_connection(
        session=session,
        guardian=guardian,
        user=user,
        connection_type=payload.connection_type,
    )
    if not connection:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return connection


@router.delete("/{guardian_id}/connections/{user_id}")
def remove_connection(
    guardian_id: str, 
    user_id: str, 
    session: Session = Depends(get_session)
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    user = user_service.get_user_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' does not exist",
        )

    success, msg = guardian_service.remove_connection(
        session=session, guardian=guardian, user=user
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {"message": f"Connection between Guardian '{guardian_id}' and user '{user_id}' removed"}


# ------------------------------------------------------------------------------
# Settings & Security Endpoints
# ------------------------------------------------------------------------------
@router.put("/{guardian_id}/code")
def change_guardian_code(
    guardian_id: str,
    payload: ChangeCodeRequest,
    session: Session = Depends(get_session),
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    updated_guardian, msg = guardian_service.change_code(
        session=session, guardian=guardian, code=payload.code
    )
    if not updated_guardian:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return updated_guardian


@router.get("/{guardian_id}/settings")
def get_guardian_settings(
    guardian_id: str, 
    session: Session = Depends(get_session)
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    settings, msg = guardian_service.get_guardian_settings(
        session=session, guardian=guardian
    )
    if not settings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return settings


@router.patch("/{guardian_id}/settings")
def update_guardian_settings(
    guardian_id: str,
    payload: UpdateGuardianSettingsRequest,
    session: Session = Depends(get_session),
):
    guardian = guardian_service.get_guardian_by_id(session, guardian_id=guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guardian '{guardian_id}' does not exist",
        )

    settings, msg = guardian_service.update_guardian_settings(
        session=session,
        guardian=guardian,
        warning_message=payload.warning_message,
        applause_message=payload.applause_message,
        strictness=payload.strictness,
        language=payload.language,
    )
    if not settings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return settings