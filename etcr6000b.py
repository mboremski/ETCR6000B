#!/usr/bin/env python3
"""
Driver for the ETCR6000B / EITAI 6000B leakage current clamp meter.

Protocol (reverse engineered, see README.md):
    9600 8N1, strict request/response; the meter never sends unsolicited data.
    Request  0x23  ->  response  [HI] [LO] [STATUS]
    counts = HI * 100 + LO           (base 100, LO always stays below 100)
    value  = sign * counts * factor  (factor and sign come from STATUS)
    STATUS encodes mode, range and sign - see the table below.

Usage:
    ./etcr6000b.py                 single reading
    ./etcr6000b.py -f              continuous (Ctrl-C to stop)
    ./etcr6000b.py -f -c log.csv   continuous, also written to CSV
    ./etcr6000b.py --dump          read the meter's stored measurements
"""
import argparse, csv, sys, time
from datetime import datetime
import serial

CMD_MEASURE = b'\x23'
CMD_DUMP    = b'\x19'   # memory dump, N x 3 bytes
CMD_COUNT   = b'\x0f'   # response 05 05 NN, NN = number of stored records

# STATUS byte -> (mode, factor in mA per count, sign)
# Every entry verified by measurement.
STATUS = {
    0x0b: ("AC",  1, +1),
    0x05: ("AC", 10, +1),
    0x15: ("DC",  1, +1),
    0x16: ("DC", 10, +1),
    0x17: ("DC",  1, -1),
    0x18: ("DC", 10, -1),
}

class ETCR6000B:
    def __init__(self, port="/dev/ttyUSB0", timeout=0.3):
        self.ser = serial.Serial(port, 9600, timeout=timeout)
        time.sleep(0.2)

    def read(self):
        """One reading: (mA, mode, status_known, raw_bytes), or None."""
        self.ser.reset_input_buffer()
        self.ser.write(CMD_MEASURE)
        self.ser.flush()
        time.sleep(0.12)
        r = self.ser.read(8)
        if len(r) < 3:
            return None
        counts = r[0] * 100 + r[1]
        known = r[2] in STATUS
        mode, factor, sign = STATUS.get(r[2], (f"?0x{r[2]:02x}", 1, +1))
        return sign * counts * factor, mode, known, r

    def decode(self, r):
        """3 raw bytes -> (mA, mode, status_known)"""
        counts = r[0] * 100 + r[1]
        known = r[2] in STATUS
        mode, factor, sign = STATUS.get(r[2], (f"?0x{r[2]:02x}", 1, +1))
        return sign * counts * factor, mode, known

    def count(self):
        """Number of stored records, or None."""
        self.ser.reset_input_buffer(); self.ser.write(CMD_COUNT); self.ser.flush()
        time.sleep(0.12)
        r = self.ser.read(16)
        return r[2] if len(r) >= 3 else None

    def dump(self):
        """Stored records as [(slot, mA, mode, status_known, raw_bytes), ...]."""
        self.ser.reset_input_buffer(); self.ser.write(CMD_DUMP); self.ser.flush()
        time.sleep(0.4)
        raw = self.ser.read(512)
        out = []
        for i in range(0, len(raw) - 2, 3):
            rec = raw[i:i+3]
            ma, mode, known = self.decode(rec)
            out.append((i // 3 + 1, ma, mode, known, rec))
        return out

    def close(self):
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

def fmt(ma):
    return f"{ma/1000:.3f} A" if abs(ma) >= 1000 else f"{ma} mA"

def main():
    p = argparse.ArgumentParser(description="Read the ETCR6000B clamp meter")
    p.add_argument("-p", "--port", default="/dev/ttyUSB0")
    p.add_argument("-f", "--follow", action="store_true", help="measure continuously")
    p.add_argument("-i", "--interval", type=float, default=0.5, help="seconds between readings (default 0.5)")
    p.add_argument("-c", "--csv", help="also append readings to this CSV file")
    p.add_argument("-d", "--dump", action="store_true",
                   help="read the stored measurements instead of measuring live")
    a = p.parse_args()

    try:
        dev = ETCR6000B(a.port)
    except serial.SerialException as e:
        sys.exit(f"cannot use port {a.port}: {e}")

    if a.dump:
        with dev:
            n = dev.count()
            recs = dev.dump()
            print(f"records stored according to the meter: {n if n is not None else '?'}")
            if not recs:
                print("No memory contents received.")
                print("Is the meter switched on? It powers off 5 min 39 s after power-on.")
                
            for platz, ma, mode, known, rec in recs:
                warn = "" if known else "  (unknown STATUS byte!)"
                print(f"  slot {platz:2d}  {mode}  {fmt(ma):>10}   [{rec.hex(' ')}]{warn}")
        return

    writer = fh = None
    if a.csv:
        fh = open(a.csv, "a", newline="")
        writer = csv.writer(fh)
        if fh.tell() == 0:
            writer.writerow(["timestamp", "mA", "mode", "raw_hex"])

    with dev:
        try:
            while True:
                m = dev.read()
                if m is None:
                    print("no response - is the meter switched on? "
                          "(it powers off 5 min 39 s after power-on)", file=sys.stderr)
                else:
                    ma, mode, verified, raw = m
                    ts = datetime.now()
                    warn = "" if verified else "  (unknown STATUS byte - value unverified!)"
                    print(f"{ts:%H:%M:%S}  {mode}  {fmt(ma):>10}   [{raw.hex(' ')}]{warn}")
                    if writer:
                        writer.writerow([ts.isoformat(timespec="seconds"), ma, mode, raw.hex(' ')])
                        fh.flush()
                if not a.follow:
                    break
                time.sleep(a.interval)
        except KeyboardInterrupt:
            print("\nstopped.", file=sys.stderr)
        finally:
            if fh:
                fh.close()

if __name__ == "__main__":
    main()
