# ETCR6000B / EITAI 6000B — Serial Protocol

Reverse-engineered USB protocol of the **EITAI 6000B** (identical to the
**ETCR6000B**), a DC/AC leakage current clamp meter (0 mA – 60 A, 1 mA
resolution).

The meter ships with Windows software but no protocol documentation whatsoever.
This repository contains the fully reconstructed protocol, a Python driver, and
the measurements that back every claim made here.

## Quick start

```bash
./etcr6000b.py                 # single reading
./etcr6000b.py -f              # continuous
./etcr6000b.py -f -c log.csv   # continuous, also written to CSV
./etcr6000b.py --dump          # read the meter's stored measurements
```

## The protocol in brief

**9600 8N1**, strict request/response over a CH340 USB bridge (USB ID
`1a86:7523`). The meter never sends anything on its own.

| Request | Response | Meaning |
|---------|----------|---------|
| `0x23` | `[HI] [LO] [STATUS]` | current reading |
| `0x0f` | `05 05 NN` | `NN` = number of stored records |
| `0x19` | `N × [HI] [LO] [STATUS]` | full memory dump |
| `0x05` | `d5 55 55` | unknown |

Decoding — **not a uint16, but base 100**:

```
counts = HI × 100 + LO          (LO always stays below 100)
value  = sign × counts × factor
```

| STATUS | Mode | Factor | Sign |
|--------|------|--------|------|
| `0x0b` | AC | 1 mA | none |
| `0x05` | AC | 10 mA | none |
| `0x15` | DC | 1 mA | + |
| `0x16` | DC | 10 mA | + |
| `0x17` | DC | 1 mA | − |
| `0x18` | DC | 10 mA | − |

Stored records use the **exact same 3-byte format** as live readings, including
range and sign — one decoder covers both.

Every statement above is backed by measurement; see "Evidence" below.

## Important limitations of the meter

**HOLD freezes the value on the serial link too — with no indication whatsoever.**
The status byte does not change. Software therefore cannot distinguish a held
value from a real one. While logging, an accidental HOLD press will record a
stale value indefinitely with nothing in the data to reveal it.

**The meter powers off after 5 min 39 s, and this cannot be prevented.**
Measured and cross-checked: neither continuous polling nor any of the 256
possible command bytes resets the timer (338.9 s in both runs, difference 0.0 s).
The meter runs on a 9 V block battery, not on USB power. It has no POWER button,
only a slide switch OFF/DC/AC; the sole button is HOLD, and every press stores a
record.

**Consequence:** over USB this is a query device, not a data logger. It is useful
for spot readings, for short runs under five minutes, and above all for
collecting measurements stored on the meter via HOLD.

**No remote control.** No single byte triggers any action on the meter; every
command found is read-only.

## Evidence

### Connection and hardware

- USB-to-serial bridge: QinHeng CH340 (USB ID `1a86:7523`) → `/dev/ttyUSB0`
- 9600 baud, 8 data bits, 1 stop bit, no parity (manual p. 4, confirmed)
- DTR/RTS have no effect; no hardware handshake required
- The meter never transmits unsolicited data — strict request/response
- It runs on a 9 V block battery, **not** on USB power
- **No POWER button.** Power is a slide switch OFF / DC / AC; the only button is
  HOLD. The manual repeatedly mentions a "POWER key" and entering data access
  mode via "HOLD+POWER" — that does not apply to this unit, presumably a
  different variant of the series.

### Commands

| Request | Response | Meaning |
|---------|----------|---------|
| `0x23` | `[HI] [LO] [STATUS]` | current reading |
| `0x0f` | `05 05 NN` | `NN` = number of stored records |
| `0x19` | `N × 3 bytes` | full memory dump |
| `0x05` | `d5 55 55` | constant, unknown |

All other bytes `0x00`–`0xFF` produce no response, as do the usual ASCII probes
(CR, LF, `*IDN?`, `READ`, `AT`).

### Reading decoding (command `0x23`)

```
counts = HI × 100 + LO
value  = sign × counts × factor
```

The two data bytes are **not** a uint16. The base-100 encoding is established by
two independent observations:

1. `LO` never exceeded 89 in any measurement across all runs.
2. Only base 100 keeps a measurement ramp continuous across the meter's
   automatic range switching. Read as uint16, the transitions produce absurd
   jumps — from 1551 to 82 in AC, and from 605 to 60 in DC.

#### Status byte

| Value | Bits | Mode | Factor | Sign | How it was verified |
|-------|------|------|--------|------|---------------------|
| `0x0b` | `0000 1011` | AC | 1 mA | none | ramp, continuous into `0x05` |
| `0x05` | `0000 0101` | AC | 10 mA | none | display 1.83 A == decoded 1.83 A |
| `0x15` | `0001 0101` | DC | 1 mA | + | range switch, continuous into `0x16` |
| `0x16` | `0001 0110` | DC | 10 mA | + | display jumped 600 mA → 0.6 A |
| `0x17` | `0001 0111` | DC | 1 mA | − | zero crossing and switch into `0x18` |
| `0x18` | `0001 1000` | DC | 10 mA | − | display −1.49 A, counts 149 |

Established structure: **bit 4 (`0x10`) is the DC flag** — set in all three DC
cases, clear in both AC cases.

The remainder does **not** decompose into a clean bit field and is therefore
documented as a table rather than a formula:

- AC ×1 is `0x0b` but DC ×1 is `0x15` — the low nibbles differ (`b` vs `5`), so
  there is no shared range code across modes.
- Bit 3 (`0x08`) is ruled out as a sign bit: it is set in `0x18` (negative) but
  also in `0x0b` (a positive AC ramp).

Within DC, however, a clean rule holds: **changing sign adds 2 to the code.**

```
0x15 (×1, +)  → 0x17 (×1, −)
0x16 (×10, +) → 0x18 (×10, −)
```

This was stated as a prediction while `0x17` had never been observed, and the
subsequent DC sweep confirmed it.

The rule applies to DC only. AC has no sign: during an AC sweep the count ran
down to exactly 0 and back up while the status byte stayed `0x0b` throughout,
and the display showed no minus sign either. **AC readings are magnitudes.**

#### Verification of scaling

Both range transitions are continuous — the physical current does not change at
the moment the meter switches range, so a correct decoding must not jump.

DC sweep, +1.05 A → −1.00 A, all three transitions continuous:

```
0x16 ×10:  54 →  540 mA   |  0x15 ×1 : 528 →  528 mA
0x15 ×1 :   8 →   +8 mA   |  0x17 ×1 :   0 →   -0 mA   (zero crossing)
0x17 ×1 : 588 →  588 mA   |  0x18 ×10:  64 →  640 mA
```

The reading is always a **magnitude**; the sign lives solely in the status byte.
It is not two's complement.

DC ramp 400 → 600 mA: counts 605 (`0x15`, ×1) → 60 (`0x16`, ×10), i.e. 605 mA →
600 mA, a ratio of exactly 10. Confirmed at the display: the reading flipped
from 600 mA to 0.6 A — a pure change of unit, same value.

AC sweep, both transitions confirming ×1 / ×10:

```
downward:   54 (0x05, ×10) = 540 mA  →  403 (0x0b, ×1) = 403 mA
upward:    622 (0x0b, ×1 ) = 622 mA  →   55 (0x05, ×10) = 550 mA
```

These are continuous but only to within about 10 %, whereas DC matched to a few
percent. The cause is open: either the knob moving during the 0.5 s sampling
interval, or slightly different calibration between the two AC ranges.

**Auto-range hysteresis (AC):** switching up happens around 620 counts, switching
back down only around 400–540. This prevents chattering at the boundary and
explains why the up and down paths do not switch at the same point.

### Known anomaly: stale status byte at range boundaries

In one of three transitions during the DC sweep, a frame appeared whose count had
already moved to the new range while the status byte still reported the old one:

```
62.1s  05 58 17   counts=588  st=0x17   -> ×1  = 588 mA
62.7s  00 3f 17   counts= 63  st=0x17   -> ×1  =  63 mA   <-- wrong
63.2s  00 40 18   counts= 64  st=0x18   -> ×10 = 640 mA
```

Taken literally the middle frame yields 63 mA instead of roughly 630 mA — a
factor-10 error. The other two transitions in the same run were synchronous.

Consequence for analysis: individual readings at a range boundary are not
reliable. When recording series, discard outliers where the value jumps by
roughly a factor of 10 without the status byte changing. The driver deliberately
does **not** filter this out; it prints the raw bytes so such cases stay visible.

### Reading the memory (command `0x19`)

`0x19` returns the entire memory as a sequence of 3-byte records. The record
format is **identical** to that of a live reading, sign and range included, so no
separate conversion is needed.

Verified against four values stored on the meter beforehand:

```
response: 02 5f 15  04 46 15  01 23 17  00 42 18

slot  raw         decoded   display
1     02 5f 15     295 mA    295 mA   exact
2     04 46 15     470 mA    470 mA   exact
3     01 23 17    -135 mA   -135 mA   exact
4     00 42 18    -660 mA   -0.66 A   exact
```

Slot 4 proves the range is stored as well: `0x18` is the 10 mA range with a
negative sign.

**Fill level:** `0x0f` returns `05 05 NN` where `NN` is the number of stored
records. The first two bytes were always `05 05`.

The memory is **non-volatile** — it survived switching the meter off and on.

#### No data access mode required

`0x19` and `0x0f` work in ordinary measuring mode. Checked immediately after
leaving data access mode, with the same four records stored:

```
0x0f -> 05 05 04                                        (4 records)
0x19 -> 02 5f 15 04 46 15 01 23 17 00 42 18   (12 bytes, identical)
0x23 -> 00 42 18                              (live reading)
```

So the memory can be collected fully automatically, with no button press on the
meter.

This also explains an earlier observation: before the memory was filled, `0x19`
constantly returned `00 00 17` and `0x0f` constantly returned `05 05 01`. That was
not a fixed response — it was exactly one stored record holding the value 0. The
commands always behaved identically; only the memory contents differed.

### The HOLD button and device modes

Derived from display observation plus bus capture.

| Press duration | Effect on the meter |
|----------------|---------------------|
| very short | no reaction |
| short (~1 s) | `DH` + slot number: the current reading is stored |
| long (~4 s) | data access mode: display blinks, slot number top right, no `DH` |
| short, in that mode | pages through the stored slots (01, 02, 03 …) |
| very long (~10 s), in that mode | `dEL`: memory erased, display then goes dark; the meter must be restarted via the slide switch |

Deviation from the manual: it describes entering data access mode with
HOLD+POWER. In practice a long HOLD press alone is sufficient — this unit has no
POWER button.

The number next to `DH` is the **slot number**, not a reading.

#### Effect on the protocol

- During a long button press the meter does not answer the bus **at all** for
  about 4 seconds (8 consecutive requests without a response). The firmware does
  not service the serial port while a key is held.
- The status byte never changed throughout. **There is no HOLD bit.**

#### WARNING: HOLD freezes the bus value too, with no indication

Verified: with HOLD active, the ZERO knob was turned from −500 mA to −203 mA. The
value returned by `0x23` stayed at 501 the entire time and only jumped to 203 when
HOLD was released:

```
30.2s  05 01 17  counts=501    <- HOLD active, knob already at -203
30.7s  05 01 17  counts=501
31.3s  02 03 17  counts=203    <- HOLD released, real value appears
```

What makes this conclusive is what is absent: across the whole run there is no
reading between 206 and 499. Turning the knob produced stepped ramps over many
samples in every other capture (e.g. 243-255-269-280-293-304-318-342). A jump
within a single sample cannot be produced by hand.

The status byte stayed `0x17` across all 101 readings.

**Consequence:** software polling `0x23` **cannot** tell whether the meter is in
HOLD. An accidental press means an arbitrarily long run of frozen values with
nothing in the data to indicate it.

A possible software mitigation is to flag an exactly constant value across many
samples as suspicious. This is only a heuristic, though — the meter also returns
byte-identical values for long stretches on genuinely quiet signals, observed
repeatedly. Reliable discrimination is not possible at the protocol level.

### Auto power-off cannot be prevented (tested)

**Does bus traffic keep the meter awake?** While the display was already blinking
its shutdown warning, `0x23` was polled continuously every ~0.15 s:

```
12.0s  OK  00 44 18     <- last response
12.4s  NO RESPONSE
...    silent for the rest of the test
```

The meter powered off after 12.4 s despite continuous polling. The timer runs
independently of interface activity.

**Measured shutdown time.** Reference run with power-on as the zero point and
polling only every 2 s:

```
last response at 338.9 s = 5 min 39 s
```

This matches the manual: 5 minutes of normal operation plus a 30 s blinking
warning equals 330 s; the difference is the detection threshold at power-on.

**Does any byte keep it awake?** All 256 bytes were sent cyclically throughout a
full run (372 transmissions, every byte sent at least once), interleaved with
`0x23` as a liveness check:

```
reference, no keepalive:  338.9 s
with all 256 bytes:       338.9 s     difference -0.0 s
```

Identical to a tenth of a second. The shutdown timer is deterministic and
unaffected by any single byte.

**Limit of this test:** a keepalive requiring a *multi-byte sequence* or rapid
repetition would not have been found. The result is "no single-byte keepalive",
not "none exists".

### No remote control via the interface (tested)

**Can HOLD be triggered over the serial link?** All 256 bytes were sent
individually, each followed by a check of the memory fill level via `0x0f`. A
triggered HOLD always stores a record on the meter, so the fill level would have
to rise.

```
fill level at start: 4
fill level at end:   4
triggering bytes:    NONE
```

No single byte causes a store. The meter is read-only over USB; all four known
commands merely retrieve data.

**Limits of this test:**

- A *multi-byte* command would not be found this way.
- A command that only holds *without storing* would also be invisible, since
  detection depends on the fill level.

It is strong evidence, not a formal proof.

Incidentally, the meter withstood being sent all 256 bytes without a single
dropout, and the memory contents were unchanged.

## Contents

| Path | Contents |
|------|----------|
| `etcr6000b.py` | driver and command-line tool |
| `tools/` | analysis scripts from the reverse engineering |

The capture files referenced in the evidence section are working material and are
not part of this repository. All measurements and derivations are reproduced in
the text above, so the documentation stands on its own.

## Still open

- Command `0x05` (`d5 55 55`) — meaning unknown
- Ranges above 10 mA per step — there must be at least one more to reach 60 A;
  testing it would require a real current above roughly 6 A
- Multi-byte commands — every test here covered single bytes only

## Manual

The manufacturer's manual is copyrighted and therefore not included here. It can
be downloaded from the manufacturer:
<https://www.eitaiinst.com/pages/downloads> (entry "EITAI6000_6000B").

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This protocol was reconstructed by observation, not documented by the
manufacturer. It describes one individual EITAI 6000B unit. Other devices in the
series may differ — the manual itself describes a POWER button this unit does not
have. Use at your own risk.
