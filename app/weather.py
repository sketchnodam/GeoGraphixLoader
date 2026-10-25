"""Fetch current weather for the configured city without blocking the GUI."""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from PySide6.QtCore import QThread, Signal


def weather_from_code(code):
    code = int(code)
    if code in (95, 96, 99): return 'thunder'
    if code in (71, 73, 75, 77, 85, 86): return 'snowy'
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82): return 'rainy'
    if code in (1, 2, 3, 45, 48): return 'cloudy'
    if code == 0: return 'sunny'
    return 'cloudy'


class WeatherFetch(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, latitude, longitude, parent=None):
        super().__init__(parent)
        self.latitude = latitude
        self.longitude = longitude

    def run(self):
        params = urlencode({'latitude': self.latitude, 'longitude': self.longitude,
                            'current': 'weather_code,temperature_2m', 'temperature_unit': 'fahrenheit', 'timezone': 'auto'})
        url = 'https://api.open-meteo.com/v1/forecast?' + params
        try:
            request = Request(url, headers={'User-Agent': 'GeoSplore/0.1'})
            with urlopen(request, timeout=12) as response:
                data = json.load(response)
            code = data['current']['weather_code']
            self.succeeded.emit({'weather': weather_from_code(code), 'temperature': data['current'].get('temperature_2m'), 'unit': data.get('current_units', {}).get('temperature_2m', '°F')})
        except Exception as exc:
            self.failed.emit(str(exc))
