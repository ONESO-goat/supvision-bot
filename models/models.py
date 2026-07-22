from sqlmodel import SQLModel, Field, Relationship, JSON
from helper import create_id
from enum import Enum
from typing import Optional
from decimal import Decimal

class AvailableLanguages(Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    
class StrictnessLevel(Enum):
    WEAK = "weak"
    NORMAL = "normal"
    HARSH = "harsh"
    
class UserType(Enum):
    PARENT = "parent"
    GUADIAN = "guardian"
    INDIVIDUAL = "individual"
    OFFSPRING = "offspring"
    
class AccountType(Enum):
    FAMILY = "family"
    PERSONAL = "personal"

class UserSettings(SQLModel, table=True):
    id: str = Field(default=create_id(), primary_key=True)
    
    language: str = Field(default="en")
    
    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional['User'] = Relationship(back_populates="settings")
    
class User(SQLModel, table=True):
    id: str = Field(default=create_id(), primary_key=True)

    username: str
    name: str
    email: str
    password: str 
    user_type: UserType = Field(default=UserType.INDIVIDUAL.value)
    
    currency: Decimal = Field(default=Decimal('0.0'))
    
    settings_id: str = Field(default=None, foreign_key="user_settings.id")
    settings: Optional['UserSettings'] = Relationship(back_populates="user")
    
    history_id: str = Field(default=None, foreign_key="history.id")
    history: Optional['UserHistory'] = Relationship(back_populates="history")
    
    connections: list['AccountConnection'] = Relationship(back_populates="user")
    


class UserHistory(SQLModel, table=True):
    id: str = Field(default=create_id(), primary_key=True)
    
        
    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional['User'] = Relationship(back_populates="history")

class Account(SQLModel, table=True):
    id: str = Field(default=create_id(), primary_key=True)
    
    name: str
    account_type: AccountType = Field(default=AccountType.PERSONAL.value)
    
    owner_id: str = Field(default=None, foreign_key="owner.id")
    owner: Optional['User'] = Relationship(back_populates="account")
    
    connections: list['AccountConnection'] = Relationship(back_populates="account")
    
    settings_id: str = Field(default=None, foreign_key="account_settings.id")
    account_settings: Optional['AccountSettings'] = Relationship(back_populates="settings")


    balance: Decimal = Field(default=Decimal('0.0'))
    
class AccountConnection(SQLModel, table=True):
    id: str = Field(default=create_id(), primary_key=True)
    
    account_id: str = Field(default=None, foreign_key="account.id")
    account: Optional['Account'] = Relationship(back_populates="connections")
    
    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional['User'] = Relationship(back_populates="connections")
    
    connection_type: UserType = Field(default=UserType.INDIVIDUAL.value)
    
class AccountSettings(SQLModel, table=True):
    id: str = Field(default=create_id(), primary_key=True)

    strictness: str = Field(default=StrictnessLevel.NORMAL.value)
    language: str = Field(default=AvailableLanguages.ENGLISH.value)

    account_id: str = Field(default=None, foreign_key="account.id")
    account: Optional['Account'] = Relationship(back_populates="settings")
    
    restrictions_id: str = Field(default=None, foreign_key="account_restrictions.id")
    restrictions: Optional['AccountRestrictions'] = Relationship(back_populates="account")
    
class AccountRestrictions(SQLModel, table=True):
    id: str = Field(default=create_id(), primary_key=True)
    
    account_id: str = Field(default=None, foreign_key="account.id")
    account: Optional['Account'] = Relationship(back_populates="restrictions")
    
    restrictions: list = Field(default_factory=list, sa_type=JSON)
    
class RecentActivity(SQLModel, table=True):
    id: str = Field(default=create_id(), primary_key=True)
    
    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional['User'] = Relationship(back_populates="recent_activity")
    
    activities: list = Field(default_factory=list, sa_type=JSON)
