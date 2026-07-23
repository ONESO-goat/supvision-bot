from services.user_service import UserService
from fastapi_config import get_session, app
from fastapi import Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel

class UserSignup(BaseModel):
    username: str
    email: str | None
    password: str
    
class UserLogin(BaseModel):
    username: str
    email: str | None
    password: str
    
user_service = UserService()

@app.post("/user/signup")
def fetch_signup(user_input: UserSignup, session: Session = Depends(get_session)):
    user, mes = user_service.create_user(session=session, **user_input.model_dump())
    if not user:
        raise HTTPException(status_code=400, detail=mes)
    return user

@app.post("/user/login")
def fetch_login(user_input: UserLogin, session: Session = Depends(get_session)):
    user, mes = user_service.login(session=session, **user_input.model_dump())
    if not user:
        raise HTTPException(status_code=400, detail=mes)
    return user

