#!/usr/bin/env python3
"""Phase A: poll the known commands. Phase B: full byte sweep (memory investigation)."""
import time, serial

def ask(s, b, wait=0.12):
    s.reset_input_buffer(); s.write(bytes([b])); s.flush(); time.sleep(wait)
    return s.read(64)

with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.3) as s:
    time.sleep(0.2); t0 = time.time()

    print("### PHASE A: bekannte Kommandos, 25 s ###", flush=True)
    while time.time() - t0 < 25:
        row = []
        for b in (0x23, 0x19, 0x0f, 0x05):
            r = ask(s, b)
            row.append(f"0x{b:02x}={r.hex(' ') if r else '--':<11}")
        print(f"{time.time()-t0:5.1f}s  " + "  ".join(row), flush=True)
        time.sleep(0.2)

    print("\n### PHASE B: voller Sweep 0x00-0xFF ###", flush=True)
    found = []
    for b in range(256):
        r = ask(s, b, 0.1)
        if r:
            print(f"  0x{b:02x} -> {r.hex(' ')}", flush=True)
            found.append((b, r))
    print(f"\n{len(found)} antwortende Kommandos", flush=True)
