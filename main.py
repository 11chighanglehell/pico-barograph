"""Pico barograph console entry point."""

import struct
import time

from config import (
    BMP280_I2C_ADDRESS,
    DAILY_DAYS,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    GROUND_ELEVATION_M,
    HISTORY_FILE,
    I2C_ID,
    I2C_SCL_PIN,
    I2C_SDA_PIN,
    RECENT_SAMPLES,
    SAMPLE_INTERVAL_SECONDS,
    SAMPLES_PER_DAY,
)

_MAGIC = b"BPH1"


def _load_history():
    """Return (samples, daily, day_min, day_max, day_count) from flash."""
    try:
        with open(HISTORY_FILE, "rb") as handle:
            raw = handle.read()
    except OSError:
        return [], [], 0.0, 0.0, 0
    try:
        if raw[:4] != _MAGIC:
            raise ValueError("bad magic")
        recent_count = struct.unpack_from("<H", raw, 4)[0]
        offset = 6
        samples = list(struct.unpack_from("<{}f".format(recent_count), raw, offset))
        offset += 4 * recent_count
        daily_count = raw[offset]
        offset += 1
        flat = struct.unpack_from("<{}f".format(daily_count * 2), raw, offset)
        offset += 8 * daily_count
        daily = [(flat[i * 2], flat[i * 2 + 1]) for i in range(daily_count)]
        day_min, day_max = struct.unpack_from("<2f", raw, offset)
        day_count = struct.unpack_from("<H", raw, offset + 8)[0]
        return samples, daily, day_min, day_max, day_count
    except Exception:
        return [], [], 0.0, 0.0, 0


def _save_history(samples, daily, day_min, day_max, day_count):
    try:
        body = struct.pack("<H{}f".format(len(samples)), len(samples), *samples)
        flat = []
        for low, high in daily:
            flat.append(low)
            flat.append(high)
        body += struct.pack("<B{}f".format(len(daily) * 2), len(daily), *flat)
        body += struct.pack("<2fH", day_min, day_max, day_count)
        with open(HISTORY_FILE, "wb") as handle:
            handle.write(_MAGIC + body)
    except OSError:
        pass


def main():
    import framebuf
    from machine import I2C, Pin

    from bmp280 import BMP280
    from epd2in13_v4 import EPD_2in13_V4_Landscape_Flipped
    from graph import render

    i2c = I2C(
        I2C_ID,
        sda=Pin(I2C_SDA_PIN),
        scl=Pin(I2C_SCL_PIN),
        freq=100_000,
    )
    addresses = i2c.scan()
    if BMP280_I2C_ADDRESS not in addresses:
        raise OSError(
            "BMP280 not found at 0x{:02x}; I2C devices found: {}".format(
                BMP280_I2C_ADDRESS, [hex(address) for address in addresses]
            )
        )
    sensor = BMP280(i2c, BMP280_I2C_ADDRESS)

    epd = EPD_2in13_V4_Landscape_Flipped()
    samples, daily, day_min, day_max, day_count = _load_history()
    refreshes = 0

    while True:
        _, pressure = sensor.read()
        samples.append(pressure)
        del samples[:-RECENT_SAMPLES]
        if day_count == 0:
            day_min = day_max = pressure
        else:
            day_min = min(day_min, pressure)
            day_max = max(day_max, pressure)
        day_count += 1
        print("Pressure: {:.2f} hPa".format(pressure))

        if day_count >= SAMPLES_PER_DAY:
            daily.append((day_min, day_max))
            del daily[:-DAILY_DAYS]
            day_count = 0
            _save_history(samples, daily, day_min, day_max, day_count)
        elif day_count % 24 == 1:
            # Save on the first sample and every 6 hours so a power cut
            # loses little; flash wear stays under ~5 writes/day.
            _save_history(samples, daily, day_min, day_max, day_count)

        pixels = render(
            samples,
            daily,
            day_count,
            SAMPLE_INTERVAL_SECONDS,
            DISPLAY_WIDTH,
            DISPLAY_HEIGHT,
            GROUND_ELEVATION_M,
            refreshes,
        )
        image = framebuf.FrameBuffer(
            pixels, DISPLAY_WIDTH, DISPLAY_HEIGHT, framebuf.MONO_HLSB
        )
        epd.fill(1)
        epd.blit(image, 0, 0)

        refreshes += 1
        if refreshes % 30 == 1:
            epd.init()
            epd.display(epd.buffer)
        else:
            epd.displayPartial(epd.buffer)
        time.sleep(SAMPLE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
