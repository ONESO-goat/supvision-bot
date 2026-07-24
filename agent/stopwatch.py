import time
import random
from models.models import GuardianReport
from models.guardian_session import GuardianSession
from datetime import datetime

class GuardianStateManager:
    def __init__(self):
        pass

    def user_scrolled_away(self, target_duration:int=300, random_time_duration:bool=False):
        """Called when the agent confirms the harmful content is gone."""
        if self.warning_active and self.tracking_start_time is None:
            # Set a random target between 120 and 300 seconds (2-5 minutes)
            if random_time_duration:
                self.target_duration = random.randint(120,300)
            else:
                self.target_duration = target_duration
  
            self.tracking_start_time = time.perf_counter()
            print(f"[Stopwatch] Started on the side. User must stay away for {self.target_duration}s.")

    
    
if __name__ in "__main__":

   pass