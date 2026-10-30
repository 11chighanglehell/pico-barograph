"""Render the barograph console into a 1-bit framebuffer.

Layout on the 250x122 panel, modeled on the piRadar 7-inch console:

+----------------------------------+---------------------------------------+
|      (flat barometer arc)        |  LAST 48 HOURS                        |
|                                  |  [full-height pressure trace]       |
|             29.87                |                                       |
|             INHG                 |      -- alternates each refresh --    |
|          ^ RISING                |  30-DAY MIN/MAX                       |
|          +0.08/3H                |  [full-height min/max whisker bars] |
|                                  |  -48h / -30d                     now  |
+----------------------------------+---------------------------------------+

The left dial panel is always shown; the right panel alternates between the
48-hour trace and the 30-day min/max chart on successive refreshes.

All timestamps are relative because the Pico has no RTC and no network.
"""

import math

import framebuf

from config import DAILY_DAYS, DIAL_MAX_INHG, DIAL_MIN_INHG

HPA_PER_INHG = 33.8638866667
_ATMOSPHERE_HEIGHT_M = 44330.77
_ATMOSPHERE_EXPONENT = 5.25588

PANEL_X = 104  # right panel left edge; divider sits just left of it

DIAL_CX = 50
DIAL_CY = 60
DIAL_R = 52
DIAL_START_DEG = 150.0  # dial minimum; sweeps clockwise to 30 degrees
DIAL_SWEEP_DEG = 120.0

RECENT_WINDOW_SECONDS = 48 * 3600

_FONT_5X7 = {
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
}


def station_to_sea_level_hpa(pressure_hpa, elevation_m):
    fraction = 1.0 - elevation_m / _ATMOSPHERE_HEIGHT_M
    return pressure_hpa / fraction**_ATMOSPHERE_EXPONENT


def _big_text_width(text, scale):
    width = 0
    for char in text:
        width += (4 if char == "." else 6) * scale
    return width - scale


def _big_text(image, x, y, text, scale=2):
    for char in text:
        glyph = _FONT_5X7.get(char)
        if glyph is None:
            x += 4 * scale
            continue
        columns = 3 if char == "." else 5
        for row, bits in enumerate(glyph):
            for col in range(columns):
                if bits & (1 << (4 - col)):
                    image.fill_rect(
                        x + col * scale, y + row * scale, scale, scale, 0
                    )
        x += (columns + 1) * scale


def _title_bar(image, x1, y1, x2, y2, text):
    image.fill_rect(x1, y1, x2 - x1 + 1, y2 - y1 + 1, 0)
    image.text(text, x1 + 4, y1 + 1, 1)


def _dial(image, value_inhg, trend_inhg=None):
    span = DIAL_MAX_INHG - DIAL_MIN_INHG

    def point(dial_value, radius):
        angle = math.radians(
            DIAL_START_DEG - DIAL_SWEEP_DEG * (dial_value - DIAL_MIN_INHG) / span
        )
        return (
            int(DIAL_CX + radius * math.cos(angle)),
            int(DIAL_CY - radius * math.sin(angle)),
        )

    previous = point(DIAL_MIN_INHG, DIAL_R)
    for segment in range(1, 49):
        value = DIAL_MIN_INHG + span * segment / 48
        current = point(value, DIAL_R)
        image.line(previous[0], previous[1], current[0], current[1], 0)
        previous = current

    for tenth in range(int(span * 10) + 1):
        value = DIAL_MIN_INHG + tenth / 10
        inner = DIAL_R - (7 if tenth % 5 == 0 else 4)
        x0, y0 = point(value, inner)
        x1, y1 = point(value, DIAL_R - 1)
        image.line(x0, y0, x1, y1, 0)

    for label, value in (("28", 28.0), ("29", 29.0), ("30", 30.0), ("31", 31.0)):
        tx, ty = point(value, DIAL_R - 16)
        image.text(label, tx - 8, ty - 4, 0)

    if trend_inhg is not None:
        trend = max(DIAL_MIN_INHG, min(DIAL_MAX_INHG, trend_inhg))
        x0, y0 = point(trend, DIAL_R - 9)
        x1, y1 = point(trend, DIAL_R - 1)
        image.line(x0, y0, x1, y1, 0)
        image.line(x0 + 1, y0, x1 + 1, y1, 0)

    clamped = max(DIAL_MIN_INHG, min(DIAL_MAX_INHG, value_inhg))
    base_x, base_y = point(clamped, DIAL_R - 12)
    tip_x, tip_y = point(clamped, DIAL_R - 2)
    image.line(base_x, base_y, tip_x, tip_y, 0)
    image.line(base_x + 1, base_y, tip_x + 1, tip_y, 0)
    image.line(base_x, base_y + 1, tip_x, tip_y + 1, 0)
    image.fill_rect(base_x - 1, base_y - 1, 4, 4, 0)


def _arrow(image, x, y, direction):
    if direction == 0:
        image.hline(x, y + 3, 8, 0)
        image.hline(x, y + 4, 8, 0)
        return
    for row in range(7):
        half = row // 2
        if direction > 0:
            image.hline(x + 3 - half, y + row, 2 * half + 1, 0)
        else:
            image.hline(x + 3 - half, y + 6 - row, 2 * half + 1, 0)


def _trend(delta_inhg_per_3h):
    if abs(delta_inhg_per_3h) < 0.02:
        return "STEADY", 0
    if delta_inhg_per_3h >= 0.06:
        return "RAPID RISE", 1
    if delta_inhg_per_3h <= -0.06:
        return "RAPID FALL", -1
    return ("RISING", 1) if delta_inhg_per_3h > 0 else ("FALLING", -1)


def _dotted_hline(image, x0, x1, y):
    for x in range(x0, x1, 3):
        image.pixel(x, y, 0)


def _range_labels(image, x0, y0, y1, low, high):
    image.fill_rect(x0 + 2, y0 + 2, 42, 9, 1)
    image.text("{:.2f}".format(high), x0 + 3, y0 + 3, 0)
    image.fill_rect(x0 + 2, y1 - 10, 42, 9, 1)
    image.text("{:.2f}".format(low), x0 + 3, y1 - 10, 0)


def _plot_recent(image, x0, y0, x1, y1, values_inhg, interval_seconds):
    image.rect(x0, y0, x1 - x0 + 1, y1 - y0 + 1, 0)
    if len(values_inhg) < 2:
        image.text("collecting", x0 + 8, y0 + 8, 0)
        return

    low = math.floor((min(values_inhg) - 0.02) * 20) / 20
    high = math.ceil((max(values_inhg) + 0.02) * 20) / 20
    if high - low < 0.1:
        high = low + 0.1
    plot_w = x1 - x0 - 2
    plot_h = y1 - y0 - 2

    for grid_tenth in range(math.ceil(low * 10), int(high * 10)):
        grid = grid_tenth / 10
        grid_y = y0 + 1 + int((high - grid) * plot_h / (high - low))
        _dotted_hline(image, x0 + 1, x1, grid_y)
    _range_labels(image, x0, y0, y1, low, high)

    count = len(values_inhg)
    previous = None
    for index, value in enumerate(values_inhg):
        age = (count - 1 - index) * interval_seconds
        x = x1 - 1 - int(age * plot_w / RECENT_WINDOW_SECONDS)
        if x < x0 + 1:
            continue
        clamped = max(low, min(high, value))
        y = y0 + 1 + int((high - clamped) * plot_h / (high - low))
        if previous is not None:
            image.line(previous[0], previous[1], x, y, 0)
            image.line(previous[0], previous[1] + 1, x, y + 1, 0)
        previous = (x, y)
    if previous is not None:
        image.fill_rect(previous[0] - 1, previous[1] - 1, 3, 3, 0)


def _plot_daily(image, x0, y0, x1, y1, days_inhg):
    image.rect(x0, y0, x1 - x0 + 1, y1 - y0 + 1, 0)
    if not days_inhg:
        image.text("collecting", x0 + 8, y0 + 8, 0)
        return

    low = math.floor((min(mn for mn, _ in days_inhg) - 0.02) * 20) / 20
    high = math.ceil((max(mx for _, mx in days_inhg) + 0.02) * 20) / 20
    if high - low < 0.2:
        high = low + 0.2
    plot_h = y1 - y0 - 2

    for grid_tenth in range(math.ceil(low * 10), int(high * 10), 2):
        grid = grid_tenth / 10
        grid_y = y0 + 1 + int((high - grid) * plot_h / (high - low))
        _dotted_hline(image, x0 + 1, x1, grid_y)
    _range_labels(image, x0, y0, y1, low, high)

    pitch = (x1 - x0 - 4) / DAILY_DAYS
    count = len(days_inhg)
    for index, (mn, mx) in enumerate(days_inhg):
        x = x1 - 3 - int((count - 1 - index) * pitch)
        y_top = y0 + 1 + int((high - mx) * plot_h / (high - low))
        y_bot = y0 + 1 + int((high - mn) * plot_h / (high - low))
        image.vline(x, y_top, y_bot - y_top + 1, 0)
        image.vline(x + 1, y_top, y_bot - y_top + 1, 0)
        image.hline(x - 1, y_top, 4, 0)
        image.hline(x - 1, y_bot, 4, 0)


def render(
    samples_hpa,
    daily,
    day_count,
    interval_seconds,
    width,
    height,
    elevation_m,
    page=0,
):
    """Return a 1-bit framebuffer.

    samples_hpa: recent station-pressure samples in hPa, oldest first.
    daily: list of (min, max) station-pressure pairs for completed days,
           oldest first, up to DAILY_DAYS entries.
    day_count: how many trailing samples belong to the current partial day.
    page: even shows the 48-hour trace, odd the 30-day min/max chart.
    """
    stride = (width + 7) // 8
    pixels = bytearray(stride * height)
    image = framebuf.FrameBuffer(pixels, width, height, framebuf.MONO_HLSB)
    image.fill(1)

    sea_inhg = [
        station_to_sea_level_hpa(p, elevation_m) / HPA_PER_INHG for p in samples_hpa
    ]
    days_inhg = [
        (
            station_to_sea_level_hpa(mn, elevation_m) / HPA_PER_INHG,
            station_to_sea_level_hpa(mx, elevation_m) / HPA_PER_INHG,
        )
        for mn, mx in daily
    ]
    if sea_inhg and day_count:
        current = sea_inhg[-min(day_count, len(sea_inhg)):]
        days_inhg = days_inhg + [(min(current), max(current))]

    # Left panel: dial, readout, trend.
    if sea_inhg:
        now = sea_inhg[-1]
        back = int(10800 / interval_seconds)
        trend_value = sea_inhg[-1 - back] if len(sea_inhg) > back else None
        _dial(image, now, trend_value)
        readout = "{:.2f}".format(now)
        _big_text(image, (PANEL_X - _big_text_width(readout, 3)) // 2, 52, readout, 3)
        image.text("INHG", (PANEL_X - 32) // 2, 77, 0)

        if len(sea_inhg) > back:
            delta = sea_inhg[-1] - sea_inhg[-1 - back]
            word, direction = _trend(delta)
            word_x = (PANEL_X - (11 + len(word) * 8)) // 2
            _arrow(image, word_x, 93, direction)
            image.text(word, word_x + 11, 93, 0)
            delta_text = "{:+.2f}/3H".format(delta)
            image.text(delta_text, (PANEL_X - len(delta_text) * 8) // 2, 105, 0)
    else:
        image.text("collecting", 10, 60, 0)

    image.vline(PANEL_X - 3, 2, height - 4, 0)

    # Right panel: full-height chart, alternating per refresh.
    plot_bottom = height - 14
    if page % 2 == 0:
        _title_bar(image, PANEL_X, 2, width - 1, 11, "LAST 48 HOURS")
        _plot_recent(
            image, PANEL_X, 13, width - 1, plot_bottom, sea_inhg, interval_seconds
        )
        image.text("-48h", PANEL_X, height - 11, 0)
    else:
        _title_bar(image, PANEL_X, 2, width - 1, 11, "30-DAY MIN/MAX")
        _plot_daily(image, PANEL_X, 13, width - 1, plot_bottom, days_inhg)
        image.text("-30d", PANEL_X, height - 11, 0)
    image.text("now", width - 25, height - 11, 0)

    return pixels
