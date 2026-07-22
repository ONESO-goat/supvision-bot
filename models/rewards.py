from sqlmodel import SQLModel, Field, Session
from helper import create_id
import time
from pydantic import BaseModel
from enum import Enum


class RewardType(Enum):
    GIFT_CARD = "gift_card"
    PASS = "pass"

class Reward(SQLModel, table=True):
    id: str = Field(default=create_id(), primary_key=True)
    name: str
    type: RewardType
    amount: int
    cost: int

def _add_rewards(session:Session):
    """Adding the test rewards for MVP"""

    if not session:
        raise ValueError("Session is required")
    
    try:
        titles = [
            ("dunkin gift card", RewardType.GIFT_CARD, 20, 2500), 
            ("fornite gift card", RewardType.GIFT_CARD, 10, 1000),
            ("get out of jail pass", RewardType.PASS, 0, 2000)
            ]
        for reward in titles:
            time.sleep(0.1)
            reward_name  = reward[0]
            reward_type = reward[1]
            reward_amount = reward[2]
            reward_cost = reward[3]

            session.add(
                Reward(
                    name=reward_name,
                    type=reward_type,
                    amount=reward_amount,
                    cost=reward_cost
                )
            )
        session.commit()
    except Exception as ex:
        session.rollback()
        raise ValueError(f"An error occured when adding rewards to system: {ex}")

def add_reward(session:Session, name:str, reward_type:str|RewardType, reward_amount:int, reward_cost:int):
    if not session:
        raise ValueError("Session is required")
    try:

        session.add(
                Reward(
                    name=name,
                    type=reward_type,
                    amount=reward_amount,
                    cost=reward_cost
                )
            )
        session.commit()
    except Exception as ex:
        session.rollback()
        raise ValueError(f"An error occured when adding rewards to system: {ex}")