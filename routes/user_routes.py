from services.user_service import UserService
from fastapi_config import get_session, app
from fastapi import Depends, HTTPException
from sqlmodel import Session


user_service = UserService()


