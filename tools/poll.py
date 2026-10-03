#!/usr/bin/env python3
"""Poll command 0x23 over time and print candidate decodings of the two data bytes."""
import sys, time, serial
dur = float(sys.argv[1]) if len(sys.argv)>1 else 10
with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.3) as s:
    s.dtr=True; s.rts=True; time.sleep(0.2)
    t0=time.time()
    while time.time()-t0 < dur:
        s.reset_input_buffer(); s.write(b'\x23'); s.flush()
        time.sleep(0.12)
        r = s.read(128)
        if r:
            be = int.from_bytes(r[0:2],'big'); le = int.from_bytes(r[0:2],'little')
            print(f"{time.time()-t0:5.1f}s  {r.hex(' '):<20} BE16={be:5d}  LE16={le:5d}")
        else:
            print(f"{time.time()-t0:5.1f}s  (keine Antwort)")
        time.sleep(0.3)
