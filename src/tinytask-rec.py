#!/usr/bin/env python3
import sys
import os
import time
import signal
import select
import evdev

if len(sys.argv) < 2:
    print("Usage: tinytask-rec <output_file>")
    sys.exit(1)

out_file = sys.argv[1]

# Ambil keyboard dan mouse fisik dari evdev
devs = []
for p in evdev.list_devices():
    try:
        d = evdev.InputDevice(p)
        name = d.name.lower()
        if "ydotool" in name:
            continue
        caps = d.capabilities()
        if evdev.ecodes.EV_KEY in caps or evdev.ecodes.EV_REL in caps:
            devs.append(d)
    except Exception:
        pass

if not devs:
    print("Error: Tidak ada input device yang bisa dibaca! Pastikan user tergabung di grup input.")
    sys.exit(1)

dev_map = {d.fd: d for d in devs}
running = True

def sig_handler(sig, frame):
    global running
    running = False

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

start_time = time.time()
print(f"Perekaman dimulai pada {len(devs)} device -> {out_file}", flush=True)

with open(out_file, "w") as f:
    while running:
        r, _, _ = select.select(dev_map.keys(), [], [], 0.05)
        for fd in r:
            dev = dev_map[fd]
            try:
                for ev in dev.read():
                    now_ms = int((time.time() - start_time) * 1000)
                    if ev.type == evdev.ecodes.EV_KEY:
                        # ev.value: 1=down, 0=up
                        if ev.value in [0, 1]:
                            f.write(f"EV_KEY {ev.code} {ev.value} {now_ms}\n")
                            f.flush()
                    elif ev.type == evdev.ecodes.EV_REL:
                        # ev.code: 0=REL_X, 1=REL_Y, 8=REL_WHEEL
                        f.write(f"EV_REL {ev.code} {ev.value} {now_ms}\n")
                        f.flush()
            except Exception:
                pass

print("Perekaman selesai.", flush=True)
