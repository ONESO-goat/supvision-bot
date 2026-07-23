from agent.bot import Agent
from sqlmodel import Session, select, func
from models.models import User, Guardian, GuardianSettings, GuardianRestrictions

class YTGSession:
    def  __init__(self) -> None:
        pass
    
    def link(self, 
             session:Session, 
             user: 'User',
             guardian: "Guardian",
             guardian_settings: "GuardianSettings",
             guardian_restrictions: "GuardianRestrictions"):
        agent = Agent(
            guadian=guardian,
            guardian_settings=guardian_settings,
            guardian_restrictions=guardian_restrictions.restrictions)
        
        return agent
    
    def run(self):
        pass
    