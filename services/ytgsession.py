from agent.bot import Agent
from sqlmodel import Session, select, func
from models.models import User, Guardian

class YTGSession:
    def  __init__(self) -> None:
        pass
    
    def link(self, session:Session, user: 'User', guardian: "Guardian"):
        agent = Agent(guadian=guardian)
        
    def run(self):
        pass
    