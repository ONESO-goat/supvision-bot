import mss
import mss.tools

class ScreenshotLogic:

    @staticmethod
    def capture_screenshot() -> bytes:
        """Captures a screenshot of the primary monitor and returns it as PNG

        bytes.
        """
        with mss.mss() as sct:
            # Index 1 targets the first/primary monitor
            monitor = sct.monitors[1]

            # Grab the screen region
            screenshot = sct.grab(monitor)

            # Convert to PNG raw bytes and return
            return mss.tools.to_png(screenshot.rgb, screenshot.size)
