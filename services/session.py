from models.models import Guardian, User
from models.guardian_session import GuardianSession
from guardian_services import GuardianServices
from sqlmodel import Session, select
from agent.bot import Agent
from datetime import datetime

guardian_services = GuardianServices()


class YTGSessionService:

    def get_YTGSession(self, session:Session, session_id:str)->tuple[GuardianSession|None, str]:
        if not session or not session_id:
            return None, "Session and ID are required"
        sess = session.get(GuardianSession, session_id)
        if not sess:
            return None, f"No session under the id '{session_id}'"
        return sess, "success"
    
    def get_or_create(self, session: Session, user: 'User', guardian: 'Guardian') -> GuardianSession:
        existing = session.exec(
            select(GuardianSession).where(
                GuardianSession.user_id == user.id,
                GuardianSession.guardian_id == guardian.id,
            )
        ).first()
        if existing:
            return existing

        row = GuardianSession(user_id=user.id, guardian_id=guardian.id)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def process_scan(
        self,
        session: Session,
        agent: 'Agent',
        session_row: GuardianSession,
        image_bytes: bytes,
    ) -> dict:
        stuff, mes = guardian_services.get_guardian_data(
            session=session, 
            guardian_id=session_row.guardian_id
            )
        
        guardian:Guardian|None = stuff.get("guardian")
        if not guardian:
            raise ValueError("Guardian does not exist during session process")

        if stuff.get("settings"):
            settings = stuff.get("settings")
        if stuff.get("restrictions"):
            restrictions = stuff.get("restrictions")
            
            
        classification = agent.engine._classify_image(image_bytes=image_bytes)
        overview = agent.overview(
            image_overview=classification.get("summary", ""),
            guardian_settings=settings or None,
            guardian_restrictions=restrictions or [])
        
        overview["image_summary"] = classification

        was_already_warning = session_row.warning_active

        user = session.get(User, session_row.user_id)
        if overview["flagged"]:
            session_row.warning_active = True
            session_row.tracking_start_at = None
            
            if not was_already_warning:
                is_family_account = guardian.guardian_type == "family"
                # If it's a family account, include the name of the person in this alert. 
                # If its individual, skip the name.
                # This is for parents or caregivers to know who is facing the issue,
                # while individual people dont have to see their name spammed through out
                    
                breakdown = agent._breakdown_overview(
                    user=user, 
                    classification_result=overview, 
                    include_name=is_family_account)
                
                session_row.events.append(breakdown)
                session.commit()
                
        elif was_already_warning:
            session_row.tracking_start_at = datetime.utcnow()
            session_row.target_duration_seconds = 180

        completed = agent.stopwatch.update_and_check_timer(session_row)

        session.add(session_row)
        session.commit()

        return {
            "flagged": overview["flagged"],
            "description": overview.get("description"),
            "warning_active": session_row.warning_active,
            "points_awarded": completed,
        }
        
    def delete_session(self, session:Session, session_id:str):
        """_summary_

        Session auto delete after cycles. GuardianSessions are the connection between the user and the 
        agent. This is called when the user logs out, away for some time, etc.
        
        Args:
            session (Session): the session
            session_id (str): GuardianSession id
        """
        sess, mes = self.get_YTGSession(session=session, session_id=session_id)
        if not sess:
            return None, mes
        session.delete(sess)
        session.commit()
        