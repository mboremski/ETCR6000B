#!/usr/bin/env python3
"""Passively listen on /dev/ttyUSB0, stepping through baud rates, hex-dump raw bytes."""
import sys, time, serial

PORT = "/dev/ttyUSB0"
BAUDS = [9600, 19200, 38400, 57600, 115200, 4800, 2400]
DWELL = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0

def dump(b):
    for i in range(0, len(b), 16):
        chunk = b[i:i+16]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        print(f"    {i:04x}  {hexs:<47}  {asc}")

for baud in BAUDS:
    try:
        with serial.Serial(PORT, baud, timeout=0.2) as s:
            s.reset_input_buffer()
            buf = bytearray()
            t0 = time.time()
            while time.time() - t0 < DWELL:
                buf += s.read(4096)
            if buf:
                print(f"[{baud}] {len(buf)} Bytes empfangen:")
                dump(bytes(buf[:512]))
            else:
                print(f"[{baud}] still (0 Bytes in {DWELL:.0f}s)")
    except Exception as e:
        print(f"[{baud}] Fehler: {e}")
