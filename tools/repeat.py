#!/usr/bin/env python3
"""Send the responding bytes repeatedly to check whether answers are reproducible."""
import time, serial, collections
with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.2) as s:
    s.dtr=True; s.rts=True; time.sleep(0.2)
    for b in [0x05, 0x0f, 0x19, 0x23]:
        seen = collections.Counter()
        for _ in range(10):
            s.reset_input_buffer(); s.write(bytes([b])); s.flush()
            time.sleep(0.1)
            seen[s.read(128).hex(' ')] += 1
        print(f"0x{b:02x}:")
        for resp, n in seen.most_common():
            print(f"    {n:2d}x  {resp or '(leer)'}")
