#!/usr/bin/env python3
"""Test whether any byte resets the auto-power-off timer.

Sends a set of bytes cyclically for the whole run and measures how long the
meter keeps answering. Compare against the reference of 338.9 s.

Usage:  ./keepalive_test.py [lo] [hi]     default: all 256 bytes
"""
import sys, time, serial

lo = int(sys.argv[1], 0) if len(sys.argv) > 2 else 0x00
hi = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0xFF
CAND = [b for b in range(lo, hi + 1)]
REF = 338.9

def alive(s):
    s.reset_input_buffer(); s.write(b'\x23'); s.flush(); time.sleep(0.1)
    return len(s.read(8)) >= 3

with serial.Serial("/dev/ttyUSB0", 9600, timeout=0.25) as s:
    time.sleep(0.1)
    print(f"=== Keepalive-Test, Bytes 0x{lo:02x}-0x{hi:02x} ({len(CAND)} Stueck) ===",
          flush=True)
    print(f"    Referenz ohne Keepalive: {REF:.1f}s\n", flush=True)

    print("1) warte darauf, dass die Zange AUS ist ...", flush=True)
    t = time.time()
    while alive(s):
        if time.time() - t > 120: sys.exit("Zange noch an - bitte ausschalten.")
        time.sleep(0.5)
    print("   aus.", flush=True)
    print("2) jetzt EINSCHALTEN ...", flush=True)
    t = time.time()
    while not alive(s):
        if time.time() - t > 180: sys.exit("nicht eingeschaltet - Abbruch.")
        time.sleep(0.3)

    t0 = time.time(); last_ok = 0.0; miss = 0; i = 0; mark = 60
    print(f"   laeuft ab {time.strftime('%H:%M:%S')}\n", flush=True)

    while time.time() - t0 < 600:
        b = CAND[i % len(CAND)]; i += 1
        s.reset_input_buffer(); s.write(bytes([b])); s.flush(); time.sleep(0.06)
        s.read(64)
        ok = alive(s); el = time.time() - t0
        if ok:
            last_ok = el; miss = 0
            if el >= mark:
                print(f"  {el:6.1f}s  laeuft ({i} Bytes gesendet)", flush=True); mark += 60
        else:
            miss += 1
            if miss >= 5:
                print(f"\n>>> ABGESCHALTET nach {last_ok:.1f}s "
                      f"(Referenz {REF:.1f}s, Differenz {last_ok-REF:+.1f}s)", flush=True)
                print(">>> KEIN Keepalive-Effekt" if last_ok < REF + 20
                      else ">>> LAENGER ALS REFERENZ - Keepalive moeglich!", flush=True)
                break
        time.sleep(0.25)
    else:
        print(f"\n>>> 600 s durchgelaufen - eindeutig Keepalive vorhanden!", flush=True)
