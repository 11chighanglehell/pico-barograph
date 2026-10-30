# Your Barograph: An Owner's Briefing

## What this is

This is a **barograph** — a barometer that remembers. Inside the wooden case is a
small computer (a Raspberry Pi Pico) and a precision pressure sensor. Every 15
minutes it measures the atmospheric pressure, converts it to the sea-level
equivalent used in weather reports, and redraws the display. Over time it builds
up a record of how the pressure has been moving — and pressure movement, more
than pressure itself, is what tells you about the weather to come.

The display is e-ink (like an e-reader), so it's always readable, uses almost no
power, and only flickers briefly when it updates.

## How to read it

### The left panel (always there)

- **The dial** sweeps from 28 to 31 inches of mercury (inHg). The needle shows
  the pressure right now. The small stub mark on the dial shows where the
  pressure was **3 hours ago**, so the gap between needle and stub is the recent
  movement at a glance.
- **The big number** is the current sea-level pressure in inHg — the same number
  your weather app or the TV meteorologist quotes.
- **The trend line** below it (e.g. `▲ RISING +0.04/3H`) is the change over the
  last 3 hours. This is the most useful line on the whole display:

| Trend | What it usually means |
|---|---|
| STEADY | No change coming soon |
| RISING | Improving, clearing weather |
| RAPID RISE | Clearing, but often windy |
| FALLING | Weather on the way — clouds, precipitation |
| RAPID FALL | A storm system is moving in |

Rules of thumb: **high and rising** = fair weather; **low and falling** = grab
an umbrella; a **rapid fall** is worth taking seriously.

### The right panel (alternates every 15 minutes)

- **LAST 48 HOURS** — a continuous trace of the pressure over the past two
  days. Nice for spotting fronts moving through and the gentle twice-daily
  atmospheric "tide."
- **30-DAY MIN/MAX** — one vertical bar per day showing that day's pressure
  range. This is the long memory: stormy stretches show up as low, long bars;
  settled spells as high, short ones.

Don't worry if these charts look sparse at first — see below.

## Things that are normal

- **It starts out knowing nothing.** The history builds as it runs: the 48-hour
  chart fills in over its first two days, and the 30-day chart grows one bar per
  day for its first month.
- **The screen does a full blink every so often.** Most updates are quick and
  quiet, but a few times a day it does a full flashing refresh to keep the
  e-ink crisp. That's maintenance, not a malfunction.
- **It has no clock.** Time on the charts is relative ("48 hours ago → now"),
  counted in samples. If it loses power for a while, that gap simply doesn't
  appear in the charts — the trace stitches across it.

## Care and feeding

- **Power:** plug the USB cable into any standard USB power source. It draws a
  trivial amount of power; leave it on all the time — that's how it keeps its
  history.
- **Power cuts are fine.** It saves its history to internal memory several
  times a day, so after an outage it picks up roughly where it left off (it may
  lose a few hours of the most recent record).
- **Placement:** anywhere indoors is fine — pressure is the one weather
  variable that's the same inside and out. Avoid direct hot sun on the e-ink
  panel.
- **No maintenance required.** Nothing to calibrate, charge, connect, or
  update. It doesn't use Wi-Fi; everything it shows, it measured itself.

## For the curious (or the brave)

All of the code running inside is open source, written in MicroPython:

**https://github.com/11chighanglehell/pico-barograph**

If you ever feel like tweaking it — changing the dial range, the sample rate,
what the charts show — everything is there, and it's a surprisingly small
amount of code. No pressure. (Sorry.)

Enjoy the weather — you'll often see it coming on here before you see it out
the window.
