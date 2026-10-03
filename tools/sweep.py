#!/usr/bin/env python3
"""Send every byte 0x00-0xFF plus common ASCII commands, report what responds."""
import time, serial
hits=[]
with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.12) as s:
    s.dtr=True; s.rts=True; time.sleep(0.2)
    for b in range(256):
        s.reset_input_buffer(); s.write(bytes([b])); s.flush()
        r = s.read(128)
        if r:
            print(f"  0x{b:02x} -> {len(r)}B  {r.hex(' ')}  |{''.join(chr(x) if 32<=x<127 else '.' for x in r)}|")
            hits.append((b,r))
    for cmd in [b"\r", b"\n", b"\r\n", b"?\r\n", b"*IDN?\r\n", b"READ\r\n",
                b"AT\r\n", b"D\r\n", b"R\r\n", b"S\r\n", b"V\r\n"]:
        s.reset_input_buffer(); s.write(cmd); s.flush(); time.sleep(0.15)
        r = s.read(256)
        if r:
            print(f"  {cmd!r} -> {r.hex(' ')}")
            hits.append((cmd,r))
print(f"\n{len(hits)} Antwort(en)" if hits else "\nkeine Antwort auf irgendein Byte/Kommando")
