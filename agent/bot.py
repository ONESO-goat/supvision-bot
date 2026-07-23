from .engine import Engine
from .stopwatch import GuardianStateManager
from .screenshot_logic import ScreenshotLogic
from helpers.prompt import Prompts
import io
import time
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from models.models import Guardian, GuardianSettings, User

class Agent:
    def __init__(self, user: 'User', guadian: 'Guardian', guardian_settings: 'GuardianSettings', guardian_restrictions: list) -> None:
        if not guadian or not guardian_settings:
            raise ValueError("Guardian and GuardianSettings are required")
        
        self.engine = Engine()
        self.stopwatch = GuardianStateManager()
        self.screenshot_logic = ScreenshotLogic()
        self.prompts = Prompts()
        
        self.user: "User" = user
        self.guardian: "Guardian" = guadian
        self.guardian_settings: 'GuardianSettings' = guardian_settings
        self.guardian_restrictions = guardian_restrictions

    
    def _ignore_this_function_just_for_an_idea(self, user):
        while True:
            time.sleep(5)
            d = self.check() # The agent checks
            self.stopwatch.update_and_check_timer()
            if d is None:
                continue
            self.read_overview(user, d) # the agent reads the overview on what was seen
            # If flagged, tell user move on.
            # If they dont, create object that is then send to the summary page (family accounts) for the owner to see
            
        
    def check(self):
        """
        Main loop for the agent. Continuously captures the screen, classifies it, and manages warnings.
        Here the agent is just checking the screen
        """
        print("Agent is active and watching screen...")
        try:
                if not self.screenshot_logic.check_for_updates():
                    return None  # screen unchanged, skip classification entirely
                
                # Capture the current screen
                screenshot = self.screenshot_logic.get_previous_image()
                if not screenshot:
                    screenshot = self.screenshot_logic.capture_screenshot()
                else:
                    buf = io.BytesIO()
                    screenshot.save(buf, format="PNG")
                    screenshot = buf.getvalue()
                # Classify the screenshot
                classification_result = self.engine._classify_image(
                    image_bytes=screenshot,
                    system_prompt=self.prompts.image_classification_prompt(),
                    return_json=True
                )
                
                composed_description = (
            f"Summary: {classification_result.get('summary', '')}\n"
            f"Visible text: {classification_result.get('visible_text', '')}\n"
            f"Comments: {classification_result.get('comments', '')}\n"
            f"Details: {classification_result.get('detailed_description', '')}"
        )
                overview = self.overview(composed_description)
                overview['image_summary'] = classification_result

                return overview
        except Exception as ex:
            print(f"\nAgent faced an internal error: {ex}")
            raise ex
    

    
    def read_overview(self, user, classification_result: dict[str, Any]):
        """
        Sends a warning to the user based on the classification result.
        """
        
        if classification_result.get("flagged"):
            was_already_warning = self.stopwatch.warning_active
            self.stopwatch.trigger_warning()
            if not was_already_warning:
                classifi_summ = self._breakdown_overview(user=user, classification_result=classification_result)
                self.stopwatch.add_event(content=classifi_summ)
            print(f"\n[Warning] Harmful content detected! Category: {classification_result.get('category')}, Confidence: {classification_result.get('confidence')}")
            print(f"Description: {classification_result.get('description')}")
        
        elif self.stopwatch.warning_active:
        # content is gone AND we were previously warning -> start the clock
            self.stopwatch.user_scrolled_away()
        
        else:
            print("\n[Info] No harmful content detected.")
           
    def overview(self, image_overview:str)->dict[str, Any]:
        overview = self.engine._generate(
            text=image_overview,
            system_prompt=self.prompts.agent_purpose(
                restricted_categories=self.guardian_restrictions if self.guardian_restrictions else [],
                strictness=self.guardian_settings.strictness
            ),
            return_json=True
        )
        """
        returns {{
  "flagged": boolean,
  "category": string | null,
  "confidence": number,
  "description": string,
  "source_context": string | null
}}"""   

        if not overview:
            return {
            "flagged": False,
            "category": None,
            "confidence": 0.0,
            "description": "No content matching configured restrictions.",
            "source_context": None
        }
            
        if overview['flagged']:
            overview['send_warning'] = True
        else: 
            overview['send_warning'] = False
        return overview
    
    def is_the_same_image(self, image1: bytes, image2: bytes) -> bool:
        """
        Compares two images to determine if they are the same.
        """
        b = self.screenshot_logic.difference(image1, image2)
        return not self.screenshot_logic._is_different(b)
    
    def _breakdown_overview(self, user, classification_result: dict):
        img_summary = classification_result.get('image_summary', {})
        confidence = (
            classification_result.get('confidence', 0.0) * 0.5
            + img_summary.get('confidence', 0.0) * 0.5
        )
        return f"""
Dependent: ** {user.name} **

Category validated: ** {classification_result.get('category')} **

description: {classification_result.get('description')}
confidence: {confidence}

info:
    summary: {img_summary.get('summary')}
    visible text summarized: {img_summary.get('visible_text')}
    detailed description: {img_summary.get('detailed_description')}
"""
    def update_user(self, user:User):
        self.user = user