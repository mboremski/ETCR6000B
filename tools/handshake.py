#!/usr/bin/env python3
"""Try all DTR/RTS combinations and check whether the meter sends anything."""
import time, serial, itertools
for dtr, rts in itertools.product([False,True],[False,True]):
    with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.2,
                       dsrdtr=False, rtscts=False) as s:
        s.dtr = dtr; s.rts = rts
        time.sleep(0.3); s.reset_input_buffer()
        buf = bytearray(); t0=time.time()
        while time.time()-t0 < 3: buf += s.read(4096)
        print(f"DTR={int(dtr)} RTS={int(rts)}: {len(buf)} Bytes"
              + (f"  {bytes(buf[:32]).hex(' ')}" if buf else ""))
