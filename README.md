# Pico Barograph

A fork of [pico-pressure-graph](../pico-pressure-graph) that reworks the
250x122 e-Paper panel into a barograph console modeled on the piRadar 7-inch
layout: barometer dial, large digital readout, 3-hour trend, 48-hour trace,
and a 30-day daily min/max whisker chart.

## Display layout

The left dial panel is always shown; the right panel alternates between the
48-hour trace and the 30-day min/max chart on successive refreshes.

```
+-----------------+-----------------------------+
|  barometer arc  |  LAST 48 HOURS               |
|  28 .. 31 inHg  |  full-height pressure trace  |
|                 |                              |
|     29.87       |   -- alternates each         |
|     INHG        |      refresh with --         |
|                 |                              |
|   ^ RISING      |  30-DAY MIN/MAX              |
|   +0.08/3H      |  daily min/max whisker bars  |
|                 |  -48h / -30d             now |
+-----------------+-----------------------------+
```

Differences from the 7-inch version, imposed by the hardware:

- The Pico has no RTC and no network, so all time markers are relative
  (`-48h`, `-30d`, `now`) and the 30-day high/low lines carry no dates.
- The dial shows tick marks and numerals only; the RAIN/CHANGE/FAIR wording
  does not fit at this size.
- The 3-hour trend uses `STEADY` / `RISING` / `FALLING` / `RAPID RISE` /
  `RAPID FALL` (0.02 and 0.06 inHg/3h thresholds) since the full wording
  is too wide for the panel.
- Range labels on both plots are drawn inside the plot corners and can
  overlap the oldest data.

## Data and persistence

- A sample is taken every `SAMPLE_INTERVAL_SECONDS` (15 minutes).
- The last `RECENT_SAMPLES` (192 = 48 hours) feed the trace.
- Every `SAMPLES_PER_DAY` (96 = 24 hours) the day's min/max is pushed onto a
  30-entry ring that feeds the whisker chart. "Days" are 96-sample buckets,
  not calendar days.
- State is written to `history.dat` on the Pico's flash on each day rollover
  and every 6 hours (under 5 writes/day), so the charts survive power loss.
  Delete the file to start fresh; a corrupt or missing file is ignored.

## Hardware

Identical to pico-pressure-graph: Freenove Pico 2 W, GY-BMP280-3.3 on
GP4/GP5 (I2C `0x76`), Waveshare 2.13-inch e-Paper HAT V4 on the SPI pins in
`config.py`. See the wiring table in the
[pico-pressure-graph README](../pico-pressure-graph/README.md). Set
`GROUND_ELEVATION_M` to your elevation so the sea-level (QNH) conversion is
correct.

## Case

[case/](case/) holds the STLs for the 3D-printed enclosure: `baroBodyV3.stl`
(the body) and `baroFaceV3.stl` (the face plate).

## Run

Copy `config.py`, `graph.py`, `bmp280.py`, `epd2in13_v4.py`, and `main.py`
to the Pico (for example with
`py -m mpremote connect COMx fs cp file.py :file.py`). `main.py` samples the
BMP280, updates the history file, redraws the console, and refreshes the
display (partial refresh each cycle, full refresh every 30th).
`epd2in13_v4.py` is Waveshare's official
[Pico V4 driver](https://github.com/waveshareteam/Pico_ePaper_Code/blob/main/python/Pico_ePaper-2.13_V4.py),
modified only to use the SPI and pin settings in `config.py`.
