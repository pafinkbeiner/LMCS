import requests
import numpy as np


class WLEDMatrix:
    """
    Einfache Klasse zur Steuerung einer WLED LED-Matrix.
    4 Matrizen (8x32) im Block-Layout = 16x64 LEDs.
    
    Layout:
    [2][1]  (oben)
    [3][0]  (unten)
    """
    
    def __init__(self, ip: str = "10.0.0.221", timeout: int = 5):
        """
        Initialisiert die WLED Matrix Verbindung.
        
        Args:
            ip: IP-Adresse des WLED Controllers (ESP32)
            timeout: Timeout für HTTP-Requests in Sekunden
        """
        self.ip = ip
        self.base_url = f"http://{ip}"
        self.timeout = timeout
        
        # 4 Matrizen à 8x32 im 2x2 Block-Layout
        self.matrix_width = 32
        self.matrix_height = 8
        self.total_width = 64   # 2 Matrizen nebeneinander
        self.total_height = 16  # 2 Matrizen übereinander
        self.total_leds = 1024
        
        # Framebuffer für alle LEDs (RGB)
        self.framebuffer = np.zeros((self.total_height, self.total_width, 3), dtype=np.uint8)
    
    def _xy_to_index(self, x: int, y: int) -> int:
        """
        Konvertiert (x, y) Koordinaten zum LED-Index.
        
        Layout:
        [Matrix 2]  [Matrix 1]   (y=0-7)
        [Matrix 3]  [Matrix 0]   (y=8-15)
        
        Vertikale Serpentine-Verkabelung (spaltenweise).
        Matrix 0 & 3: LED 0 oben links, LED 255 oben rechts
        Matrix 1 & 2: LED 0 unten rechts, LED 255 unten links
        """
        is_top = y < 8
        is_left = x < 32
        
        # Matrix bestimmen
        if is_top and is_left:
            matrix_idx = 2
        elif is_top and not is_left:
            matrix_idx = 1
        elif not is_top and is_left:
            matrix_idx = 3
        else:
            matrix_idx = 0
        
        # Lokale Koordinaten innerhalb der Matrix (8 hoch, 32 breit)
        local_x = x % 32
        local_y = y % 8
        
        # Matrix 1 und 2 sind 180° gedreht
        if matrix_idx in [1, 2]:
            local_x = 31 - local_x
            local_y = 7 - local_y
        
        # Vertikale Serpentine: spaltenweise, ungerade Spalten gespiegelt
        if local_x % 2 == 1:
            local_y = 7 - local_y
        
        base_offset = matrix_idx * 256
        return base_offset + local_x * 8 + local_y
    
    def set_pixel(self, x: int, y: int, r: int, g: int, b: int):
        """
        Setzt die Farbe eines einzelnen Pixels im Framebuffer.
        
        Args:
            x: X-Koordinate (0-63)
            y: Y-Koordinate (0-15)
            r, g, b: Farbwerte (0-255)
        """
        if 0 <= x < self.total_width and 0 <= y < self.total_height:
            self.framebuffer[y, x] = [r, g, b]
    
    def clear(self, send: bool = False):
        """Löscht die Matrix (alle LEDs aus)."""
        self.framebuffer[:, :] = [0, 0, 0]
        if send:
            try:
                requests.post(f"{self.base_url}/json", json={"on": False}, timeout=self.timeout)
            except requests.RequestException:
                pass
    
    def show(self) -> bool:
        """
        Sendet den Framebuffer an den WLED Controller.
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        # Baue i-Array nur für nicht-schwarze Pixel: [index, "RRGGBB", ...]
        pixel_data = []
        for y in range(self.total_height):
            for x in range(self.total_width):
                r, g, b = self.framebuffer[y, x]
                if r > 0 or g > 0 or b > 0:
                    idx = self._xy_to_index(x, y)
                    hex_color = f"{int(r):02X}{int(g):02X}{int(b):02X}"
                    pixel_data.append(idx)
                    pixel_data.append(hex_color)
        
        payload = {
            "on": True,
            "seg": [{
                "id": 0,
                "i": pixel_data
            }]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/json",
                json=payload,
                timeout=self.timeout
            )
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Fehler beim Senden an WLED: {e}")
            return False


# Beispielverwendung
if __name__ == "__main__":
    matrix = WLEDMatrix(ip="10.0.0.221")
    
    # Test: Ecken markieren
    matrix.clear(send=True)  # Erst alles löschen
    matrix.set_pixel(0, 0, 255, 0, 0)     # Rot oben links
    matrix.set_pixel(63, 0, 0, 255, 0)    # Grün oben rechts
    matrix.set_pixel(0, 15, 0, 0, 255)    # Blau unten links
    matrix.set_pixel(63, 15, 255, 255, 0) # Gelb unten rechts
    matrix.show()

