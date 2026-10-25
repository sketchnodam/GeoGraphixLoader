"""Geo Splore welcome screen wpathith scrolling pixel backgrounds and hover-only labels."""

import math
import random
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QWidget

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

ROOT = Path(__file__).resolve().parents[1]
WEATHERS = ('sunny', 'cloudy', 'rainy', 'snowy', 'thunder')
PHASES = ('morning', 'midday', 'evening', 'night', 'midnight')
CATEGORIES = ('Demographics', 'Transportation', 'Economics', 'Infrastructure', 'Housing')
WEATHER_NAMES = {
    'sunny': 'Sunny', 'cloudy': 'Cloudy', 'rainy': 'Rainy',
    'snowy': 'Snowy', 'thunder': 'Thunder'
}


class WelcomeScreen(QWidget):
    entered = Signal()
    category_selected = Signal(str)

    def __init__(self, region, facts, interval_seconds=120, weather='sunny', timezone=None, parent=None):
        super().__init__(parent)
        self.region = region
        self.facts = list(facts) or [f'Explore {region}, one layer at a time.']
        random.shuffle(self.facts)
        self.fact_index = 0
        self.fact_opacity = 1.0
        self.fading_out = False

        self.offset = 0.0
        self.speed = 12.0
        self.clock_phase = 0.0
        self.weather = {'clear': 'sunny', 'rain': 'rainy', 'snow': 'snowy', 'storm': 'thunder'}.get(weather, weather)
        if self.weather not in WEATHERS:
            self.weather = 'sunny'
        self.weather_details = None
        self.timezone = None
        if ZoneInfo and timezone:
            try:
                self.timezone = ZoneInfo(timezone)
            except (KeyError, ValueError):
                pass

        self.backgrounds = {}
        background_folder = ROOT / 'assets' / 'backgrounds'

        print('Project root:', ROOT)
        print('Background folder:', background_folder)
        print('Folder exists:', background_folder.exists())

        for weather_name in WEATHERS:
            for phase in PHASES[:-1]:
                path = background_folder / f'{weather_name}_{phase}.png'
                pixmap = QPixmap(str(path))
                self.backgrounds[(weather_name, phase)] = pixmap
                print(
                    path.name,
                    '| Exists:', path.exists(),
                    '| Loaded:', not pixmap.isNull()
                )
        midnight_path = background_folder / 'midnight.png'
        midnight_pixmap = QPixmap(str(midnight_path))
        self.backgrounds[('midnight', 'midnight')] = midnight_pixmap

        print(
            midnight_path.name,
            '| Exists:', midnight_path.exists(),
            '| Loaded:', not midnight_pixmap.isNull()
        )

        self.menu_open = False
        self.hover_left = False
        self.hover_right = False
        self.weather_menu_open = False
        self.hovered_weather = None
        self.manual_weather = None
        self.manual_phase = None
        self.selected_category = None

        self.flash = 0

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.motion_timer = QTimer(self)
        self.motion_timer.timeout.connect(self.advance_frame)
        self.motion_timer.start(33)

        self.fact_timer = QTimer(self)
        self.fact_timer.timeout.connect(self.begin_fact_change)
        self.fact_timer.start(max(5, int(interval_seconds)) * 1000)

        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.advance_fade)

        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self.lightning_tick)
        self.flash_timer.start(110)

    # -------------------------
    # Time and weather
    # -------------------------

    def current_time(self):
        return datetime.now(self.timezone) if self.timezone else datetime.now()

    def phase(self):
        if self.manual_phase is not None:
            return self.manual_phase
        hour = self.current_time().hour
        if 0 <= hour < 5:
            return 'midnight'
        if 5 <= hour < 11:
            return 'morning'
        if 11 <= hour < 17:
            return 'midday'
        if 17 <= hour < 20:
            return 'evening'
        return 'night'

    def set_weather(self, weather):
        if weather in WEATHERS:
            self.weather = weather
            self.update()

    def set_weather_details(self, details):
        self.weather_details = details
        if self.manual_weather is None:
            self.set_weather(details.get('weather', self.weather))

    def select_weather_preview(self, weather, phase):
        self.manual_weather = weather
        self.manual_phase = phase
        self.weather_menu_open = False
        self.hovered_weather = None
        self.update()

    def restore_automatic_weather(self):
        self.manual_weather = None
        self.manual_phase = None
        self.weather_menu_open = False
        self.hovered_weather = None
        if self.weather_details:
            self.set_weather(self.weather_details.get('weather', self.weather))
        self.update()

    def weather_menu_layout(self):
        row_height = 44
        top = self.height() / 2 - (5 * row_height) / 2
        right_x = self.width() - 320
        left_x = right_x - 175
        return top, row_height, right_x, left_x

    def accent_color(self):
        phase = self.phase()
        if phase in ('night', 'midnight'):
            return QColor('#caa8ff')
        if phase == 'midday':
            return QColor('#8bc0ff')
        return QColor('#ffc489')

    # -------------------------
    # Animation
    # -------------------------

    def advance_frame(self):
        self.offset += self.speed * .033
        self.clock_phase += .033
        self.update()

    def lightning_tick(self):
        if (self.manual_weather or self.weather) != 'thunder':
            self.flash = 0
            return
        if self.flash:
            self.flash -= 1
        elif random.random() < .02:
            self.flash = random.choice([2, 3, 5])
        if self.flash:
            self.update()

    def begin_fact_change(self):
        if len(self.facts) > 1:
            self.fading_out = True
            self.fade_timer.start(35)

    def advance_fade(self):
        self.fact_opacity += -.07 if self.fading_out else .07
        if self.fading_out and self.fact_opacity <= 0:
            self.fact_opacity = 0
            self.fact_index = (self.fact_index + 1) % len(self.facts)
            self.fading_out = False
        elif not self.fading_out and self.fact_opacity >= 1:
            self.fact_opacity = 1
            self.fade_timer.stop()
        self.update()

    # -------------------------
    # Hover and interaction
    # -------------------------

    def mouseMoveEvent(self, event):
        x, y = event.position().x(), event.position().y()
        self.hover_left = x < 100 and abs(y - self.height() / 2) < 125
        self.hover_right = x > self.width() - 100 and abs(y - self.height() / 2) < 125

        if self.weather_menu_open:
            top, row_height, right_x, left_x = self.weather_menu_layout()
            row = int((y - top) // row_height)
            if right_x <= x <= right_x + 175 and 0 <= row < len(WEATHERS):
                self.hovered_weather = WEATHERS[row]
            elif (self.hovered_weather is not None and
                  left_x <= x < right_x and
                  0 <= row < len(PHASES)):
                pass  # Keep the submenu open while the mouse enters it.
            else:
                self.hovered_weather = None
        self.update()

    def leaveEvent(self, event):
        self.hover_left = False
        self.hover_right = False
        self.hovered_weather = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        x, y = event.position().x(), event.position().y()

        # Left arrow: existing categories.
        if x < 100 and abs(y - self.height() / 2) < 125:
            self.menu_open = not self.menu_open
            self.weather_menu_open = False
            self.hovered_weather = None
            self.update()
            return

        # Right arrow: weather and time-of-day previews.
        if x > self.width() - 100 and abs(y - self.height() / 2) < 125:
            self.weather_menu_open = not self.weather_menu_open
            self.menu_open = False
            self.hovered_weather = None
            self.update()
            return

        if self.weather_menu_open:
            top, row_height, right_x, left_x = self.weather_menu_layout()
            row = int((y - top) // row_height)

            # Click a time from the submenu of the hovered weather.
            if (self.hovered_weather is not None and
                    left_x <= x < right_x and 0 <= row < len(PHASES)):
                self.select_weather_preview(self.hovered_weather, PHASES[row])
                return

            # Clicks outside the five weather rows close the menu.
            if not (right_x <= x <= right_x + 175 and 0 <= row < len(WEATHERS)):
                self.weather_menu_open = False
                self.hovered_weather = None
            self.update()
            return

        if self.menu_open and 100 < x < 430:
            start = self.height() / 2 - 135
            for i, name in enumerate(CATEGORIES):
                if start + i * 54 <= y < start + (i + 1) * 54:
                    self.selected_category = name
                    self.menu_open = False
                    self.category_selected.emit(name)
                    self.update()
                    return

    def keyPressEvent(self, event):
        if Qt.Key.Key_1 <= event.key() <= Qt.Key.Key_5:
            self.select_weather_preview(WEATHERS[event.key() - Qt.Key.Key_1], self.phase())
        elif event.key() == Qt.Key.Key_0:
            # Restore live conditions without an extra visible menu row.
            self.restore_automatic_weather()
        else:
            super().keyPressEvent(event)

    # -------------------------
    # Rendering helpers
    # -------------------------

    # -------------------------
    # Rendering
    # -------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#081424'))
        w, h = self.width(), self.height()
        if not w or not h:
            return

        phase = self.phase()
        display_weather = self.manual_weather or self.weather
        key = ('midnight', 'midnight') if phase == 'midnight' else (display_weather, phase)
        img = self.backgrounds.get(key)
        if img is not None and not img.isNull():
            tile_width = img.width() * h / img.height()
            x = self.offset % tile_width - tile_width
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            while x < w:
                p.drawPixmap(QRectF(x, 0, tile_width, h), img, QRectF(0, 0, img.width(), img.height()))
                x += tile_width

        if display_weather == 'thunder' and self.flash and self.flash % 2:
            p.fillRect(self.rect(), QColor(214, 218, 255, 85))
            p.setPen(QPen(QColor('#f7f2ff'), max(2, int(w / 550))))
            p.drawPolyline(QPolygonF([
                QPointF(w * .69, 0), QPointF(w * .67, h * .14), QPointF(w * .70, h * .16),
                QPointF(w * .66, h * .32), QPointF(w * .68, h * .34), QPointF(w * .64, h * .52)
            ]))

        details = self.weather_details or {}
        temperature = details.get('temperature')
        unit = details.get('unit') or '°F'
        temp_text = f'{round(temperature)}{unit}' if temperature is not None else '—°F'
        condition = WEATHER_NAMES.get(display_weather, display_weather.title())
        if temperature is not None:
            weather_text = f'{condition}  {round(temperature)}°F'
        else:
            weather_text = f'{condition}  —°F'

        # Fully disappear at the bottom of a smooth 12-second breathing cycle.
        # Exactly the same pulse and color are used by the clock below.
        pulse = 0.5 - 0.5 * math.cos(self.clock_phase * (2 * math.pi / 4))
        info_color = QColor('#ffc586')
        info_color.setAlphaF(pulse)

        p.setPen(info_color)
        p.setFont(QFont('Consolas', max(12, int(w / 125)), QFont.Weight.Bold))
        p.drawText(QRectF(w * .30, 12, w * .40, 42),
                   Qt.AlignmentFlag.AlignCenter, weather_text)

        # Facts in the center.
        p.setOpacity(self.fact_opacity)
        p.setPen(QColor('#f1daff'))
        p.setFont(QFont('Consolas', max(18, min(32, int(w / 48))), QFont.Weight.DemiBold))
        p.drawText(QRectF(w * .16, h * .40, w * .68, h * .20),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                   self.facts[self.fact_index])
        p.setOpacity(1)

        # Bottom-right clock: no towers, AM, or PM; same amber full fade.
        p.setPen(info_color)
        p.setFont(QFont('Consolas', max(16, int(w / 92)), QFont.Weight.Bold))
        p.drawText(QRectF(max(0, w - 240), max(0, h - 76), min(w, 212), 56),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   self.current_time().strftime('%H:%M'))

        if self.hover_left or self.menu_open:
            p.setPen(QColor('#edf0f3'))
            p.setFont(QFont('Consolas', 38, QFont.Weight.Bold))
            p.drawText(QRectF(12, h / 2 - 55, 75, 110), Qt.AlignmentFlag.AlignCenter, '‹')

        if self.menu_open:
            p.setPen(QColor('#edf0f3'))
            p.setFont(QFont('Consolas', max(15, int(w / 85)), QFont.Weight.Bold))
            start = h / 2 - 135
            for i, name in enumerate(CATEGORIES):
                p.drawText(QRectF(108, start + i * 54, 330, 50), Qt.AlignmentFlag.AlignVCenter, name.upper())
        # Right-side arrow and transparent weather menu.
        if self.hover_right or self.weather_menu_open:
            p.setPen(QColor('#edf0f3'))
            p.setFont(QFont('Consolas', 38, QFont.Weight.Bold))
            p.drawText(QRectF(w - 87, h / 2 - 55, 75, 110),
                       Qt.AlignmentFlag.AlignCenter, '›')

        if self.weather_menu_open:
            top, row_height, right_x, left_x = self.weather_menu_layout()
            entries = ('Sunny', 'Cloudy', 'Rainy', 'Snowy', 'Thunder')
            p.setFont(QFont('Consolas', max(15, int(w / 100)), QFont.Weight.Bold))
            for i, entry in enumerate(entries):
                active = (self.hovered_weather == WEATHERS[i])
                p.setPen(QColor('#d4b6ff') if active else QColor('#edf0f3'))
                p.drawText(QRectF(right_x, top + i * row_height, 175, row_height),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                           ('‹ ' if active else '  ') + entry)

            if self.hovered_weather is not None:
                p.setPen(QColor('#d4b6ff'))
                for i, label in enumerate(('Morning', 'Midday', 'Evening', 'Night', 'Midnight')):
                    p.drawText(QRectF(left_x, top + i * row_height, 165, row_height),
                               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                               label)
        p.end()
