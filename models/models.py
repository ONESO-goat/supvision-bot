from sqlmodel import SQLModel, Field, Relationship, JSON
from helper import create_id, create_number_id
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class Messages(BaseModel):
    warning: str = "Avoid the upcoming content"
    applause: str = "Great work friend! We are all proud of you."


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
    CAREGIVER = "caregiver" 
    INDIVIDUAL = "individual"
    OFFSPRING = "offspring"


class GuardianType(Enum):
    FAMILY = "family"
    PERSONAL = "personal"


class RewardType(Enum):
    GIFT_CARD = "gift_card"


class Reward(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)
    name: str
    type: RewardType
    amount: int
    cost: int


class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"

    id: str = Field(default_factory=create_id, primary_key=True)

    language: str = Field(default=AvailableLanguages.ENGLISH.value)

    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="settings")


class User(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)

    username: str
    name: str
    email: str
    password: str
    user_type: UserType = Field(default=UserType.INDIVIDUAL)

    currency: int = Field(default=0)

    settings_id: str = Field(default=None, foreign_key="user_settings.id")
    settings: Optional["UserSettings"] = Relationship(back_populates="user")

    history_id: str = Field(default=None, foreign_key="user_history.id")
    history: Optional["UserHistory"] = Relationship(back_populates="user")

    connections: list["GuardianConnection"] = Relationship(back_populates="user")

    guardian: Optional["Guardian"] = Relationship(back_populates="owner")

    rewards: list["UserWonReward"] = Relationship(back_populates="user")

    recent_activity: Optional["RecentActivity"] = Relationship(back_populates="user")


class UserWonReward(SQLModel, table=True):
    id: str = Field(default_factory=create_id, primary_key=True)
    order_id: int = Field(default_factory=create_number_id, unique=True)

    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="rewards")

    reward_id: str = Field(default=None, foreign_key="reward.id")
    reward: Optional["Reward"] = Relationship()


class UserHistory(SQLModel, table=True):
    __tablename__ = "user_history"

    id: str = Field(default_factory=create_id, primary_key=True)

    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="history")


class Guardian(SQLModel, table=True):
    """
    The container that activates and configures the supervising agent.
    Not a financial account -- represents one "watch" setup: an owner
    (parent/caregiver) plus the settings/restrictions that control how
    the agent behaves, plus the offspring connected to it.
    """

    id: str = Field(default_factory=create_id, primary_key=True)

    name: str
    guardian_type: GuardianType = Field(default=GuardianType.PERSONAL)

    owner_id: str = Field(default=None, foreign_key="user.id")
    owner: Optional["User"] = Relationship(back_populates="guardian")

    connections: list["GuardianConnection"] = Relationship(back_populates="guardian")

    settings_id: str = Field(default=None, foreign_key="guardian_settings.id")
    guardian_settings: Optional["GuardianSettings"] = Relationship(back_populates="guardian")

    restrictions_id: str = Field(default=None, foreign_key="guardian_restrictions.id")
    restrictions: Optional["GuardianRestrictions"] = Relationship(back_populates="guardian")


class GuardianConnection(SQLModel, table=True):
    __tablename__ = "guardian_connection"

    id: str = Field(default_factory=create_id, primary_key=True)

    guardian_id: str = Field(default=None, foreign_key="guardian.id")
    guardian: Optional["Guardian"] = Relationship(back_populates="connections")

    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="connections")

    connection_type: UserType = Field(default=UserType.INDIVIDUAL)


class GuardianSettings(SQLModel, table=True):
    __tablename__ = "guardian_settings"

    id: str = Field(default_factory=create_id, primary_key=True)

    strictness: str = Field(default=StrictnessLevel.NORMAL.value)
    language: str = Field(default=AvailableLanguages.ENGLISH.value)
    custom_warning_messages: dict = Field(default_factory=lambda: Messages().model_dump(), sa_type=JSON)
    """
    example:
    {
        "warning": "Please avoid this type of content honey",
        "applause": "Good job Julius! I'm proud that you're not taking in this content"
    }
    """

    guardian_id: str = Field(default=None, foreign_key="guardian.id")
    guardian: Optional["Guardian"] = Relationship(back_populates="guardian_settings")


class GuardianRestrictions(SQLModel, table=True):
    __tablename__ = "guardian_restrictions"

    id: str = Field(default_factory=create_id, primary_key=True)

    guardian_id: str = Field(default=None, foreign_key="guardian.id")
    guardian: Optional["Guardian"] = Relationship(back_populates="restrictions")

    restrictions: list = Field(default_factory=list, sa_type=JSON)


class RecentActivity(SQLModel, table=True):
    __tablename__ = "recent_activity"

    id: str = Field(default_factory=create_id, primary_key=True)

    user_id: str = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="recent_activity")

    activities: list = Field(default_factory=list, sa_type=JSON)