from models.models import AvailableLanguages, User, Guardian, UserType, UserSettings
from sqlmodel import Session, select, func
from helpers import validate_password, hash_password, verify_password
from datetime import datetime
from pydantic import ValidationError

class UserService:
    def __init__(self)->None:
        pass
    
    def get_all_users(self, session:Session):
        statement = select(User)
        return session.exec(statement).all()
    
    def get_user_by_email(self, session, email:str):
        if not email:
            raise ValueError("Email is required")
        return session.exec(
            select(User).where(User.email == email)
        ).first()
        
    def get_user_by_username(self, session, username:str):
        if not username:
            raise ValueError("Username is required")
        return session.exec(
            select(User).where(User.username == username)
        ).first()
        
    def get_user_by_id(self, session, user_id:str):
        if not user_id:
            raise ValueError("User ID is required")
        return session.get(User, user_id)
    
    def create_user(self, session, username:str, name:str, email:str, password:str, user_type:UserType=UserType.INDIVIDUAL):
        if not username or not name or not email or not password:
            raise ValueError("Username, name, email, and password are required")
        
        if session.exec(
            select(User).where(func.lower(User.username) == username.lower())
        ).first():
            raise ValueError(f"User with username '{username}' already exists")
        
        if session.exec(
            select(User).where(func.lower(User.email) == email.lower())
        ).first():
            raise ValueError(f"User with email '{email}' already exists")
        
        if not validate_password(password)[0]:
            raise ValueError("Password does not meet security requirements")
        hashed_password = hash_password(password)
        user = User(
            username=username,
            name=name,
            email=email,
            password=hashed_password,  
            user_type=user_type
        )
        settings = UserSettings(
            user=user,
            language=AvailableLanguages.ENGLISH.value
        )
        session.add_all([user, settings])
        session.commit()
        session.refresh(user)
        return user
    
    def delete_user(self, session, user:User):
        if not user:
            raise ValueError("User is required")
        guardian = session.exec(
            select(Guardian).where(Guardian.owner_id == user.id)
        ).first()

        session.delete(guardian)
            
        session.delete(user)
        session.commit()
        return True
    
    def login(self, session:Session, password:str, username:str='', email:str=''):
        if not email and not username:
            raise ValueError("Username or email are required")
        
        if not password:
            raise ValueError("Password is required")
        
        if username:
            user = session.exec(
                select(User).where(User.username == username)
            ).first()
        else:
            user = session.exec(
                select(User).where(User.email == email)
            ).first()
        

        if not user or not verify_password(password, user.password):
            raise ValueError("Username or password are incorrect")
        
        return user
    
    def change_name(self, session:Session, user:User, new_name:str):
        if not user:
            raise ValueError("User is required")
        
        if not new_name:
            raise ValueError("New name is required")
        
        user.name = new_name
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    
    def change_password(self, session:Session, user:User, new_password:str):
        if not user:
            raise ValueError("User is required")
        
        if not new_password or not validate_password(new_password)[0]:
            raise ValueError("New password does not meet the requirements")
        
        hashed_password = hash_password(new_password)
        user.password = hashed_password
        session.add(user)
        session.commit()
        session.refresh(user)
        return user