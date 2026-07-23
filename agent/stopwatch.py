import time
import random
from models.models import GuardianRecapToOwner

class GuardianStateManager:
    def __init__(self):
        self.warning_active = False
        self.tracking_start_time = None
        self.target_duration = 0  # Dynamic 2-5 minute target
        self.give_user_points: bool = False
        self.amount_of_points_to_assign: int = 0
    
        self.events = []
        
    def wait_5_seconds(self):
        """Simulates a 5-second wait for demonstration purposes."""
        print("[Agent] Waiting for 5 seconds...")
        time.sleep(5)
        print("[Agent] Wait complete.")
        
    def trigger_warning(self):
        """Called when the agent detects harmful content."""
        print("[Agent] Harmful content detected! Warning the user...")
        self.warning_active = True
        # Reset the stopwatch—they failed to keep away
        self.tracking_start_time = None 

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

    def update_and_check_timer(self):
        """Runs silently inside your main loop to check the stopwatch status."""
        if not self.warning_active or self.tracking_start_time is None:
            return

        elapsed = time.perf_counter() - self.tracking_start_time
            
            # Check if they successfully stayed away for the required duration
        if elapsed >= self.target_duration:
                self.give_user_points = True
                self.amount_of_points_to_assign += 10
                print(f"\n[Success] User ignored the post! +10 points. Total points to push: {self.amount_of_points_to_assign}")
                # Reset state until the next harmful post is found
                self.warning_active = False
                self.tracking_start_time = None
    
    def add_event(self, content:str, time_duration:int=180):

        self.events.append({
            "content": content,
            "should_avoid": True,
            "time_to_wait":  time_duration
        })
    
    def flush_wipe_events(self, session, user):
        """If the user ignores the agents warning, it just wipes out the events"""
        if len(self.events) <= 0:
            return
        
        for event in self.events:
            recap = GuardianRecapToOwner(
                content=event['content']
            )
            session.add(recap)
            session.commit()
        
        self.events = []
        
    
    def empty_point_count(self):
        self.amount_of_points_to_assign = 0
          
if __name__ in "__main__":

    # --- How to integrate this into your main screen-watching loop ---
    agent = GuardianStateManager()

    print("Agent is active and watching screen...")
    # Simulating your main loop
    try:
        while True:
            # 1. YOUR SCREEN CAPTURE & ANALYSIS CODE GOES HERE
            # harmful_detected = capture_and_analyze_screen()
            # content_gone = check_if_scrolled_away()
            
            # Mock simulation for demonstration:
            harmful_detected = False 
            content_gone = True      

            # 2. Update agent states based on screen analysis
            if harmful_detected:
                agent.trigger_warning()
            elif content_gone:
                agent.user_scrolled_away()

            # 3. The stopwatch runs here on the side without blocking the loop
            agent.update_and_check_timer()

            # Small sleep to prevent 100% CPU usage in your loop
            time.sleep(1) 

    except KeyboardInterrupt:
        print("Agent stopped.")
