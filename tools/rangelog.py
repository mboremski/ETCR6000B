#!/usr/bin/env python3
"""Log 0x23 with base-100 decoding and flag every change of the STATUS byte."""
import sys, time, serial
dur = float(sys.argv[1]) if len(sys.argv) > 1 else 60
with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.3) as s:
    time.sleep(0.2); t0 = time.time(); last = None
    while time.time() - t0 < dur:
        s.reset_input_buffer(); s.write(b'\x23'); s.flush(); time.sleep(0.1)
        r = s.read(8); t = time.time() - t0
        if len(r) < 3:
            print(f"{t:5.1f}s  (keine Antwort)", flush=True); time.sleep(0.15); continue
        hi, lo, st = r[0], r[1], r[2]
        cnt = hi * 100 + lo
        mark = ""
        if last is not None and st != last:
            mark = f"   *** STATUS 0x{last:02x} ({last:08b}) -> 0x{st:02x} ({st:08b}) ***"
        print(f"{t:5.1f}s  {r.hex(' ')}  counts={cnt:5d}  st=0x{st:02x} {st:08b}{mark}", flush=True)
        last = st
        time.sleep(0.15)
