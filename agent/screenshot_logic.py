import mss
import mss.tools
from PIL import Image, ImageChops
import io


class ScreenshotLogic:

    def __init__(self):
        # Keeps track of the last captured frame
        self.previous_image_file = "images/previous_image.jpeg"
        self.previous_screenshot = None
        self.times_on_the_same_page = 0

    def get_previous_image(self, path:str="images/previous_image.jpeg"):
        return self.previous_screenshot

    def _is_different(self, difference: float) -> bool:
        """Determine if the difference between two screenshots is significant

        enough.
        """
        # Adjusted to 0.005 (0.5% screen difference) to catch standard UI updates
        threshold = 0.005
        return difference > threshold

    def difference(self, img1: Image.Image, img2: Image.Image) -> float:
        """Calculate the difference between two images as a ratio between 0.0

        and 1.0.
        """
        
        if img1.size != img2.size:
            return 1.0
        
        diff = ImageChops.difference(img1, img2)
        hist = diff.histogram()
        num_bands = len(hist) // 256

        total_diff_intensity = 0
        for band in range(num_bands):
            band_hist = hist[band * 256 : (band + 1) * 256]
            for intensity, pixel_count in enumerate(band_hist):
                total_diff_intensity += intensity * pixel_count

        max_possible_intensity = img1.size[0] * img1.size[1] * num_bands * 255
        return total_diff_intensity / max_possible_intensity


    def capture_screenshot(self) -> bytes:
        """Captures a screenshot of the primary monitor and returns it as PNG

        bytes.
        """
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)

                return mss.tools.to_png(screenshot.rgb, screenshot.size)
        except Exception as ex:
            print(
                f"⚠️ [ScreenshotLogic.capture_screenshot] Error capturing screenshot: {ex}"
            )
            return b""

    def check_for_updates(self) -> bool:
        """Captures a new screenshot, compares it to the previous one, and

        updates state.

        Returns True if the screen changed significantly.
        """
        png_bytes = self.capture_screenshot()
        if not png_bytes:
            return False

        # Convert raw PNG bytes into a PIL Image
        current_img = Image.open(io.BytesIO(png_bytes))

        # Handle the initial run when no previous image exists
        if self.previous_screenshot is None:
            self.previous_screenshot = current_img
            return False

        # Compute difference ratio
        diff_ratio = self.difference(self.previous_screenshot, current_img)

        # Evaluate if the change crosses our threshold
        has_changed = self._is_different(diff_ratio)
        if has_changed:
            self.times_on_the_same_page = 0
        else:
            self.times_on_the_same_page += 1

        # Always update state so we compare against the most recent frame
        self.previous_screenshot = current_img

        return has_changed
