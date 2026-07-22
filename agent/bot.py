from engine import Engine
from stopwatch import GuardianStateManager
from screenshot_logic import ScreenshotLogic


class Agent:
    def __init__(self) -> None:
        self.engine = Engine()
        self.stopwatch = GuardianStateManager()
        self.screenshot_logic = ScreenshotLogic()