#!/usr/bin/env python3
"""Listen on /dev/ttyUSB0 at 9600 8N1 and hex-dump whatever arrives."""
import sys, time, serial
port, baud, dur = "/dev/ttyUSB0", 9600, float(sys.argv[1]) if len(sys.argv)>1 else 10
with serial.Serial(port, baud, timeout=0.2) as s:
    s.reset_input_buffer()
    buf = bytearray(); t0 = time.time()
    while time.time()-t0 < dur:
        buf += s.read(4096)
print(f"{len(buf)} Bytes in {dur:.0f}s @ {baud} 8N1")
b = bytes(buf)
for i in range(0, min(len(b), 640), 16):
    c = b[i:i+16]
    print(f"  {i:04x}  {' '.join(f'{x:02x}' for x in c):<47}  "
          + "".join(chr(x) if 32<=x<127 else '.' for x in c))
