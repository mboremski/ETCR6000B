#!/usr/bin/env python3
"""Measure how long the meter stays responsive after power-on.

Waits until the meter is silent (off), then starts timing at the first response,
so the zero point is exactly the moment it was switched on.

Usage:
    ./lifetime.py          reference run (0x23 only)
    ./lifetime.py 0x41     also send this byte before every poll (keepalive test)
"""
import sys, time, serial

keep = int(sys.argv[1], 16) if len(sys.argv) > 1 else None
POLL = 2.0

def alive(s):
    s.reset_input_buffer(); s.write(b'\x23'); s.flush(); time.sleep(0.1)
    return len(s.read(8)) >= 3

with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.25) as s:
    time.sleep(0.1)
    label = f"Keepalive 0x{keep:02x}" if keep is not None else "Referenz (nur 0x23)"
    print(f"=== {label} ===", flush=True)

    print("1) warte darauf, dass die Zange AUS ist ...", flush=True)
    t = time.time()
    while alive(s):
        if time.time() - t > 120:
            sys.exit("Zange ist nach 120 s immer noch an - bitte ausschalten.")
        time.sleep(0.5)
    print("   Zange ist aus.", flush=True)

    print("2) jetzt EINSCHALTEN - warte auf die erste Antwort ...", flush=True)
    t = time.time()
    while not alive(s):
        if time.time() - t > 180:
            sys.exit("In 180 s nicht eingeschaltet worden - Abbruch.")
        time.sleep(0.3)

    t0 = time.time()
    print(f"   eingeschaltet um {time.strftime('%H:%M:%S')} - Messung laeuft\n", flush=True)

    last_ok, miss, nextmark = 0.0, 0, 30
    while time.time() - t0 < 500:
        if keep is not None:
            s.reset_input_buffer(); s.write(bytes([keep])); s.flush()
            time.sleep(0.1); s.read(64)
        ok = alive(s)
        el = time.time() - t0
        if ok:
            last_ok = el; miss = 0
            if el >= nextmark:
                print(f"  {el:6.1f}s  laeuft noch", flush=True); nextmark += 30
        else:
            miss += 1
            print(f"  {el:6.1f}s  keine Antwort ({miss}/5)", flush=True)
            if miss >= 5:
                print(f"\n>>> ABGESCHALTET nach {last_ok:.1f}s "
                      f"= {last_ok/60:.2f} Minuten ab Einschalten", flush=True)
                break
        time.sleep(POLL)
    else:
        print(f"\n>>> lief 500 s durch, letzte Antwort {last_ok:.1f}s", flush=True)
