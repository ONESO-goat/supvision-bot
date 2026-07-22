from models.models import (AccountConnection, 
                           User, 
                           Account, 
                           UserType, 
                           AccountSettings, 
                           AccountRestrictions, 
                           AccountType,
                           AvailableLanguages
                           )

from sqlmodel import Session, select, func
from datetime import datetime
from pydantic import ValidationError
from helpers import validate_password, hash_password, verify_password
import traceback

class AccountServices:
    
    def get_all_accounts(self, session:Session):
        statement = select(Account)
        return session.exec(statement).all()
    
    def get_all_connections(self, session:Session, account:Account):
        if not account:
            raise ValueError("Account is required")
        return session.exec(
            select(AccountConnection).where(AccountConnection.account_id == account.id)
        ).all()
        
    def validate_connection(self, session:Session, account:Account, user:User):
        if not account or not user:
            raise ValueError("Account and user are required")
        return session.exec(
            select(AccountConnection).where(
                AccountConnection.account_id == account.id,
                AccountConnection.user_id == user.id
            )
        ).first()

    def get_account_by_user(self, session:Session, user:User):
        if not user:
            return None
        return session.exec(
            select(Account).where(Account.owner_id == user.id)
        ).first()
        
    def get_account_by_id(self, session:Session, account_id:str):
        if not account_id:
            return None
        return session.get(Account, account_id)
    
    def create_account(self, session:Session, user:User, name:str, account_type:AccountType=AccountType.PERSONAL):
        if not user:
            raise ValueError("User is required")
        
        if not name or not account_type:
            raise ValueError("Account name and type are required")

        account = Account(
            name=name,
            owner_id=user.id,
            account_type=account_type

        )
        settings = AccountSettings(account_id=account.id)
        restrictions = AccountRestrictions(account_id=account.id)
        
        account.account_settings = settings
        account.restrictions = restrictions
        
        session.add_all([account, settings, restrictions])
        session.commit()
        session.refresh(account)
        return account
    
    def delete_account(self, session:Session, account_id:str):
        try:
            account = self.get_account_by_id(session=session, account_id=account_id)
            if not account:
                raise ValueError(f"Account {account_id} does not exist")
            all_connections = session.exec(
                select(AccountConnection).where(AccountConnection.account_id == account.id)
            ).all()
            for connection in all_connections:
                session.delete(connection)
            settings = session.exec(
                select(AccountSettings).where(AccountSettings.account_id == account.id)
            ).first()
            if settings:
                session.delete(settings)
            restrictions = session.exec(
                select(AccountRestrictions).where(AccountRestrictions.account_id == account.id)
            ).first()
            if restrictions:
                session.delete(restrictions)

            session.delete(account)
            session.commit()
            return True
        except Exception as ex:
            session.rollback()
            raise ex
    
    def add_connection(self, session:Session, account:Account, user:User, connection_type:UserType):
        if not account or not user:
            raise ValueError("Account and user are required")
        
        if len(self.get_all_connections(session=session, account=account)) >= 7:
            raise ValueError("Maximum number of connections reached for this account")
        
        if connection_type not in UserType:
            raise ValueError(f"Invalid connection type: {connection_type}")
        
        if session.exec(
            select(AccountConnection).where(
                AccountConnection.account_id == account.id,
                AccountConnection.user_id == user.id
            )
        ).first():
            raise ValueError(f"Connection already exists between account {account.id} and user {user.id}")
        
        connection = AccountConnection(
            account_id=account.id,
            user_id=user.id,
            connection_type=connection_type
        )
        session.add(connection)
        session.commit()
        session.refresh(connection)
        return connection
    
    def remove_connection(self, session:Session, account:Account, user:User):
        if not account or not user:
            raise ValueError("Account and user are required")
        
        connection = session.exec(
            select(AccountConnection).where(
                AccountConnection.account_id == account.id,
                AccountConnection.user_id == user.id
            )
        ).first()
        
        if not connection:
            raise ValueError(f"No connection exists between account {account.id} and user {user.id}")
        
        session.delete(connection)
        session.commit()
        return True
    
    
    def change_password(self, session:Session, account:Account, new_password:str):
        if not account:
            raise ValueError("Account is required")
        
        if not new_password or not validate_password(new_password):
            raise ValueError("New password does not meet the requirements")
        
        hashed_password = hash_password(new_password)
        account.password = hashed_password
        session.add(account)
        session.commit()
        session.refresh(account)
        return account
    
    def get_account_settings(self, session:Session, account:Account):
        if not account:
            raise ValueError("Account is required")
        
        settings = session.exec(
            select(AccountSettings).where(AccountSettings.account_id == account.id)
        ).first()
        
        if not settings:
            settings = AccountSettings(account_id=account.id)
            session.add(settings)
            session.commit()
            session.refresh(settings)
        
        return settings
    
    def update_account_settings(self, session:Session, account:Account, strictness:str=None, language:str=None):
        if not account:
            raise ValueError("Account is required")
        
        settings = self.get_account_settings(session=session, account=account)
        
        if strictness:
            settings.strictness = strictness
        if language:
            settings.language = language
        
        session.add(settings)
        session.commit()
        session.refresh(settings)
        return settings
    
    