
"""Launch GeoGraphixLoading."""

import json
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QShortcut, QKeySequence

from app.loading_screen import WelcomeScreen
from app.weather import WeatherFetch


# -------------------------
# Project Files
# -------------------------

ROOT = Path(__file__).resolve().parent


def load_json(relative_path):

    with (ROOT / relative_path).open(encoding='utf-8') as file:
        return json.load(file)


# -------------------------
# Main Application
# -------------------------

def main():

    # -------------------------
    # Settings
    # -------------------------

    settings = load_json('config/settings.json')

    region = settings['default_region']

    facts_path = (
        ROOT / 'data' / 'facts' / f'{region.lower()}.json'
    )

    if facts_path.exists():

        facts = json.loads(
            facts_path.read_text(encoding='utf-8')
        ).get('facts', [])

    else:

        facts = []

    # -------------------------
    # Location
    # -------------------------

    locations = load_json('config/locations.json')

    city = settings.get('default_city', 'Columbus')

    region_info = locations.get(region, {})

    city_info = region_info.get('cities', {}).get(city, {})

    city_timezone = city_info.get(
        'timezone',
        region_info.get('timezone')
    )

    latitude, longitude = city_info.get(
        'center',
        region_info.get('center', [39.9612, -82.9988])
    )

    # -------------------------
    # Application Window
    # -------------------------

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle('GeoGraphixLoading')

    # -------------------------
    # Welcome Screen
    # -------------------------

    welcome = WelcomeScreen(
        region,
        facts,
        settings.get('fact_interval_seconds', 120),
        settings.get('welcome_weather', 'sunny'),
        timezone=city_timezone
    )

    welcome.speed = float(
        settings.get('welcome_scroll_pixels_per_second', 12)
    )

    window.setCentralWidget(welcome)

    def quit_application():
        print("K pressed. Closing GeoGraphixLoading...", flush=True)
        app.quit()
        
    exit_shortcut = QShortcut(QKeySequence('k'), window)
    exit_shortcut.activated.connect(app.quit)
    # -------------------------
    # Weather Updates
    # -------------------------

    workers = []

    def refresh_weather():

        if workers:
            return

        worker = WeatherFetch(
            latitude,
            longitude,
            window
        )

        workers.append(worker)

        worker.succeeded.connect(
            welcome.set_weather_details
        )

        worker.failed.connect(
            lambda message: print(
                'Weather update failed:',
                message
            )
        )

        worker.finished.connect(
            lambda: workers.remove(worker)
        )

        worker.finished.connect(worker.deleteLater)

        worker.start()

    weather_timer = QTimer(window)

    weather_timer.timeout.connect(refresh_weather)

    weather_timer.start(15 * 60 * 1000)

    refresh_weather()

    # -------------------------
    # Start Application
    # -------------------------

    window.showFullScreen()

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
