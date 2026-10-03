#!/usr/bin/env python3
"""Look for bytes that trigger an ACTION on the meter rather than returning data.

Detection via the memory fill level (0x0f): a triggered HOLD stores a record,
so the fill level would rise.
"""
import sys, time, serial

def count(s):
    s.reset_input_buffer(); s.write(b'\x0f'); s.flush(); time.sleep(0.1)
    r = s.read(16)
    return r[2] if len(r) >= 3 else None

SKIP = {0x0f, 0x19, 0x23}
hits, dead = [], []

with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.25) as s:
    time.sleep(0.2)
    print("warte auf die Zange (bitte einschalten) ...", flush=True)
    base = None
    t0 = time.time()
    while base is None and time.time() - t0 < 180:
        base = count(s)
        if base is None:
            time.sleep(0.5)
    if base is None:
        sys.exit("Zange hat sich in 180 s nicht gemeldet - Abbruch.")

    print(f"Zange da. Fuellstand zu Beginn: {base}", flush=True)
    print(f"Starte Sweep ({time.strftime('%H:%M:%S')}) ...", flush=True)

    for b in range(256):
        if b in SKIP:
            continue
        s.reset_input_buffer(); s.write(bytes([b])); s.flush()
        time.sleep(0.12)
        resp = s.read(64)
        now = count(s)
        if now is None:
            dead.append(b)
            print(f"  0x{b:02x}: keine Antwort mehr (Zange aus?)", flush=True)
            if len(dead) > 10:
                print("  >10x keine Antwort - Abbruch.", flush=True)
                break
            continue
        if now != base:
            print(f"  *** TREFFER 0x{b:02x}: Fuellstand {base} -> {now}"
                  + (f"  Antwort {resp.hex(' ')}" if resp else ""), flush=True)
            hits.append((b, base, now)); base = now
            if now >= 99:
                print("  Speicher voll - Abbruch.", flush=True); break

    print(f"\nFuellstand am Ende: {count(s)}", flush=True)

print("\n=== ERGEBNIS ===", flush=True)
print(f"  ausloesende Bytes: {[hex(b) for b,_,_ in hits] or 'KEINE'}", flush=True)
print(f"  stumme Stellen:    {[hex(b) for b in dead] or 'keine'}", flush=True)
