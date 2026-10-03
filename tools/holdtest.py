#!/usr/bin/env python3
"""Log 0x23 responses and flag changes of the STATUS byte (HOLD investigation)."""
import sys, time, serial
dur = float(sys.argv[1]) if len(sys.argv) > 1 else 60
with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.3) as s:
    time.sleep(0.2)
    t0 = time.time(); last_status = None; last_val = None; frozen = 0
    while time.time() - t0 < dur:
        s.reset_input_buffer(); s.write(b'\x23'); s.flush()
        time.sleep(0.12)
        r = s.read(8)
        t = time.time() - t0
        if len(r) < 3:
            print(f"{t:5.1f}s  (keine Antwort)", flush=True); time.sleep(0.2); continue
        val = (r[0] << 8) | r[1]; st = r[2]
        marks = []
        if last_status is not None and st != last_status:
            marks.append(f"*** STATUS {last_status:#04x} -> {st:#04x} ***")
        if last_val is not None and val == last_val:
            frozen += 1
        else:
            if frozen >= 5: marks.append(f"(war {frozen}x konstant)")
            frozen = 0
        print(f"{t:5.1f}s  {r.hex(' ')}  {val:5d} mA  st={st:#04x}  "
              + "  ".join(marks), flush=True)
        last_status, last_val = st, val
        time.sleep(0.2)
