from engine import Engine
from stopwatch import GuardianStateManager
from screenshot_logic import ScreenshotLogic
from helpers.prompt import Prompts
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from models.models import Guardian, GuardianSettings, GuardianRestrictions

class Agent:
    def __init__(self, guadian: Guardian, guardian_settings: GuardianSettings, guardian_restrictions: list) -> None:
        if not guadian or not guardian_settings:
            raise ValueError("Guardian and GuardianSettings are required")
        
        self.engine = Engine()
        self.stopwatch = GuardianStateManager()
        self.screenshot_logic = ScreenshotLogic()
        self.prompts = Prompts()
        
        self.guardian = guadian
        self.guardian_settings = guardian_settings
        self.guardian_restrictions = guardian_restrictions
        

        
    def check(self):
        """
        Main loop for the agent. Continuously captures the screen, classifies it, and manages warnings.
        Here the agent is just checking the screen
        """
        print("Agent is active and watching screen...")
        try:
            while True:
                # Capture the current screen
                screenshot = self.screenshot_logic.capture_screenshot()
       
                # Classify the screenshot
                classification_result = self.engine._classify_image(
                    image_bytes=screenshot,
                    system_prompt=self.prompts.image_classification_prompt(),
                    return_json=True
                )
                
                overview = self.overview(classification_result['content'])

                # Update and check the stopwatch timer
                self.stopwatch.update_and_check_timer()
                return overview
        except KeyboardInterrupt:
            print("\nAgent stopped by user.")
    

    def send_warning(self, classification_result: dict[str, Any]):
        """
        Sends a warning to the user based on the classification result.
        """
        if classification_result.get("flagged"):
            self.stopwatch.trigger_warning()
            self.stopwatch.add_event(content=classification_result.get('content'))
            print(f"\n[Warning] Harmful content detected! Category: {classification_result.get('category')}, Confidence: {classification_result.get('confidence')}")
            print(f"Description: {classification_result.get('description')}")
        else:
            print("\n[Info] No harmful content detected.")
           
    def overview(self, image_overview:str):
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