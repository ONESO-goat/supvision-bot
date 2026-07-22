from models.models import (GuardianConnection, 
                           User, 
                           Guardian, 
                           UserType, 
                           GuardianSettings, 
                           GuardianRestrictions, 
                           GuardianType,
                           AvailableLanguages
                           )

from sqlmodel import Session, select, func
from datetime import datetime
from pydantic import ValidationError
from helpers import validate_password, hash_password, verify_password
import traceback

class GuardianServices:
    
    def get_all_guardians(self, session:Session):
        statement = select(Guardian)
        return session.exec(statement).all()
    
    def get_all_connections(self, session:Session, guardian:Guardian):
        if not guardian:
            raise ValueError("Guardian is required")
        return session.exec(
            select(GuardianConnection).where(GuardianConnection.guardian_id == guardian.id)
        ).all()
        
    def validate_connection(self, session:Session, guardian:Guardian, user:User):
        if not guardian or not user:
            raise ValueError("Guardian and user are required")
        return session.exec(
            select(GuardianConnection).where(
                GuardianConnection.guardian_id == guardian,
                GuardianConnection.user_id == user.id
            )
        ).first()

    def get_guardian_by_owner(self, session:Session, user:User):
        if not user:
            return None
        return session.exec(
            select(Guardian).where(Guardian.owner_id == user.id)
        ).first()
        
    def get_guardian_by_id(self, session:Session, guardian_id:str):
        if not guardian_id:
            return None
        return session.get(Guardian, guardian_id)
    
    def create_guardian(self, session:Session, user:User, name:str, guardian_type:GuardianType=GuardianType.PERSONAL):
        if not user:
            raise ValueError("User is required")
        
        if not name or not guardian_type:
            raise ValueError("Guardian name and type are required")

        if self.get_guardian_by_owner(session, user=user):
            raise ValueError("Already have an Guardian")

        guardian = Guardian(
            name=name,
            owner_id=user.id,
            guardian_type=guardian_type

        )
        session.add(guardian)
        session.flush()  # populates Guardian.id
        settings = GuardianSettings(guardian=guardian)
        restrictions = GuardianRestrictions(guardian=guardian)
        
        guardian.guardian_settings = settings
        guardian.restrictions = restrictions
        
        session.add_all([settings, restrictions])
        session.commit()
        session.refresh(guardian)
        return guardian
    
    def delete_guardian(self, session:Session, guardian_id:str):
        try:
            guardian = self.get_guardian_by_id(session=session, guardian_id=guardian_id)
            if not guardian:
                raise ValueError(f"Guardian {guardian_id} does not exist")
            all_connections = session.exec(
                select(GuardianConnection).where(GuardianConnection.guardian_id == guardian.id)
            ).all()
            for connection in all_connections:
                session.delete(connection)
            settings = session.exec(
                select(GuardianSettings).where(GuardianSettings.guardian_id == guardian.id)
            ).first()
            if settings:
                session.delete(settings)
            restrictions = session.exec(
                select(GuardianRestrictions).where(GuardianRestrictions.guardian_id == guardian.id)
            ).first()
            if restrictions:
                session.delete(restrictions)

            session.delete(guardian)
            session.commit()
            return True
        except Exception as ex:
            session.rollback()
            raise ex
    
    def add_connection(self, session:Session, guardian:Guardian, user:User, connection_type:UserType):
        if not guardian or not user:
            raise ValueError("Guardian and user are required")
        
        if len(self.get_all_connections(session=session, guardian=guardian)) >= 7:
            raise ValueError("Maximum number of connections reached for this Guardian")
        
        if connection_type not in UserType:
            raise ValueError(f"Invalid connection type: {connection_type}")
        
        if session.exec(
            select(GuardianConnection).where(
                GuardianConnection.guardian_id == guardian.id,
                GuardianConnection.user_id == user.id
            )
        ).first():
            raise ValueError(f"Connection already exists between Guardian {guardian.id} and user {user.id}")
        
        connection = GuardianConnection(
            guardian=guardian,
            user=user,
            connection_type=connection_type
        )
        session.add(connection)
        session.commit()
        session.refresh(connection)
        return connection
    
    def remove_connection(self, session:Session, guardian:Guardian, user:User):
        if not guardian or not user:
            raise ValueError("Guardian and user are required")
        
        connection = session.exec(
            select(GuardianConnection).where(
                GuardianConnection.guardian_id == guardian.id,
                GuardianConnection.user_id == user.id
            )
        ).first()
        
        if not connection:
            raise ValueError(f"No connection exists between Guardian {guardian.id} and user {user.id}")
        
        session.delete(connection)
        session.commit()
        return True
    
    
    def change_password(self, session:Session, guardian:Guardian, new_password:str):
        if not guardian:
            raise ValueError("Guardian is required")
        
        if not new_password or not validate_password(new_password)[0]:
            raise ValueError("New password does not meet the requirements")
        
        hashed_password = hash_password(new_password)
        guardian.password = hashed_password
        session.commit()

        return guardian
    
    def get_guardian_settings(self, session:Session, guardian:Guardian):
        if not guardian:
            raise ValueError("Guardian is required")
        
        settings = session.exec(
            select(GuardianSettings).where(GuardianSettings.guardian_id == guardian.id)
        ).first()
        
        if not settings:
            settings = GuardianSettings(guardian=guardian)
            session.add(settings)
            session.commit()
            session.refresh(settings)
        
        return settings
    
    def update_guardian_settings(self, 
                                session:Session, 
                                guardian:Guardian, 
                                warning_message:str|None=None,
                                applause_message:str|None=None,
                                strictness:str|None=None, 
                                language:str|None=None):
        if not guardian:
            raise ValueError("Guardian is required")
        
        settings = self.get_guardian_settings(session=session, guardian=guardian)
        
        if warning_message or applause_message:
            valid, mes = self._validate_applause_and_warning_message(warning_message=warning_message,applause=applause_message)
            if not valid:
                raise ValueError(mes)
            if warning_message:
                settings.custom_warning_messages['warning'] = warning_message
            if applause_message:
                settings.custom_warning_messages['applause'] = applause_message
            
        if strictness:
            settings.strictness = strictness
        if language:
            settings.language = language
        
        session.add(settings)
        session.commit()
        session.refresh(settings)
        return settings
    
    def _validate_applause_and_warning_message(self, 
                                               warning_message:str|None=None, 
                                               applause:str|None=None)->tuple[bool, str]:
        
        if not warning_message and not applause:
            return False, "Warning message or appluase are required"
        
        if warning_message is not None and not 12 <= len(warning_message) <= 120:
            return False, f"The warning message of length {len(warning_message)} falls outside the valid range. length requirement is between 12-120"
        
        if applause is not None and not 12 <= len(applause) <= 120:
            return False,  f"The appluase message of length {len(applause)} falls outside the valid range. length requirement is between 12-120"
        
        # TODO: AI AGENT detects if the messages are civil and make sense
        return True, "Messages are valid"
        
        
        
        