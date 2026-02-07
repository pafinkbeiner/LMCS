from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from PIL import Image
import os
import time
import argparse
from wled import WLEDMatrix

# Matrix Größe
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 16

# Default refresh interval in seconds
DEFAULT_REFRESH_INTERVAL = 1.0


def get_chrome_options():
    """Get Chrome options configured for headless operation."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Use Chromium if available (Docker environment)
    chrome_bin = os.environ.get('CHROME_BIN')
    if chrome_bin:
        options.binary_location = chrome_bin
    
    return options


def get_chrome_service():
    """Get Chrome service with driver path if specified."""
    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
    if chromedriver_path:
        return Service(executable_path=chromedriver_path)
    return None


class MatrixDisplay:
    """Manages the browser and matrix display with support for continuous updates."""
    
    def __init__(self):
        self.driver = None
        self.matrix = None
        self.screenshot_path = "screenshot.png"
        self.html_url = None
        
    def setup(self):
        """Initialize the browser and matrix."""
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
        self.html_url = f'file:///{html_path}'
        
        options = get_chrome_options()
        service = get_chrome_service()
        
        if service:
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            self.driver = webdriver.Chrome(options=options)
            
        self.driver.get(self.html_url)
        self.driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": 400,
                "height": 100,
                "deviceScaleFactor": 1,
                "mobile": False
            }
        )
        
        self.matrix = WLEDMatrix()
        print("Matrix display initialized")
        
    def take_screenshot(self):
        """Take a screenshot of the current page state."""
        self.driver.save_screenshot(self.screenshot_path)
        return self.screenshot_path
    
    def refresh_page(self):
        """Refresh the page to update dynamic content."""
        self.driver.refresh()
        
    def update_display(self):
        """Take screenshot and send to matrix."""
        screenshot_path = self.take_screenshot()
        
        # Bild laden
        img = Image.open(screenshot_path)
        
        # In RGB konvertieren (falls RGBA oder anderes Format)
        img = img.convert('RGB')
        
        # Auf Matrix-Größe skalieren (64x16)
        img_resized = img.resize((MATRIX_WIDTH, MATRIX_HEIGHT), Image.Resampling.NEAREST)
        
        # Framebuffer leeren
        self.matrix.clear(True)
        
        # Pixel übertragen
        for y in range(MATRIX_HEIGHT):
            for x in range(MATRIX_WIDTH):
                r, g, b = img_resized.getpixel((x, y))
                self.matrix.set_pixel(x, y, r, g, b)
        
        # An WLED senden
        self.matrix.show()
        
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
            print("Browser closed")
            
    def run_loop(self, interval: float = DEFAULT_REFRESH_INTERVAL):
        """
        Run the display update in a loop.
        
        Args:
            interval: Time between updates in seconds
        """
        print(f"Starting display loop (refresh every {interval}s). Press Ctrl+C to stop.")
        try:
            while True:
                self.update_display()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopping display loop...")
        finally:
            self.cleanup()


def take_screenshot():
    """Legacy function for single screenshot (kept for compatibility)."""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    html_url = f'file:///{html_path}'

    options = get_chrome_options()
    service = get_chrome_service()

    if service:
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)

    try:
        driver.get(html_url)
        driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": 400,
                "height": 100,
                "deviceScaleFactor": 1,
                "mobile": False
            }
        )

        screenshot_path = "screenshot.png"
        driver.save_screenshot(screenshot_path)

        img = Image.open(screenshot_path)
        print("Final image size:", img.size)

        return screenshot_path

    finally:
        driver.quit()


def image_to_matrix(image_path: str, matrix: WLEDMatrix):
    """
    Lädt ein Bild, skaliert es auf Matrix-Größe und überträgt es.
    
    Args:
        image_path: Pfad zum Bild
        matrix: WLEDMatrix Objekt
    """
    # Bild laden
    img = Image.open(image_path)
    
    # In RGB konvertieren (falls RGBA oder anderes Format)
    img = img.convert('RGB')
    
    # Auf Matrix-Größe skalieren (64x16)
    img_resized = img.resize((MATRIX_WIDTH, MATRIX_HEIGHT), Image.Resampling.NEAREST)
    
    # Framebuffer leeren
    matrix.clear(True)
    
    # Pixel übertragen
    for y in range(MATRIX_HEIGHT):
        for x in range(MATRIX_WIDTH):
            r, g, b = img_resized.getpixel((x, y))
            matrix.set_pixel(x, y, r, g, b)
    
    # An WLED senden
    matrix.show()
    
    print(f"Bild ({img.size}) auf Matrix ({MATRIX_WIDTH}x{MATRIX_HEIGHT}) übertragen")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display website content on WLED matrix')
    parser.add_argument('-l', '--loop', action='store_true',  help='Run in continuous loop mode')
    parser.add_argument('-i', '--interval', type=float, default=DEFAULT_REFRESH_INTERVAL, help=f'Refresh interval in seconds (default: {DEFAULT_REFRESH_INTERVAL})')
    parser.add_argument('-o', '--once', action='store_true', help='Run once (default behavior without --loop)')
    
    args = parser.parse_args()
    
    if args.loop:
        # Loop mode - continuously update the display
        display = MatrixDisplay()
        display.setup()
        display.run_loop(interval=args.interval)
    else:
        # Single run mode (original behavior)
        screenshot_path = take_screenshot()
        matrix = WLEDMatrix()
        image_to_matrix(screenshot_path, matrix)