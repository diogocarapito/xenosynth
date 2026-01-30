#!/usr/bin/env python3
"""
sine_test.py
Plays a continuous sine wave without using MCP3008 or GPIO.
Use this to check if audio crackles on your Pi.
"""

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 22050  # try 22050 if CPU issues
BLOCK_SIZE = 512  # adjust to reduce crackle
FREQ = 440.0  # A4 note
AMP = 0.3  # 0.0 .. 1.0 safe range <0.8

# Precompute sine lookup table
TABLE_SIZE = 4096
sine_table = np.sin(2 * np.pi * np.arange(TABLE_SIZE) / TABLE_SIZE).astype(np.float32)

phase = 0.0


def audio_callback(outdata, frames, time_info, status):
    step = (FREQ * TABLE_SIZE) / SAMPLE_RATE
    idxs = (phase + step * np.arange(frames)).astype(np.int64) % TABLE_SIZE
    samples = sine_table[idxs] * AMP
    outdata[:] = samples.reshape(-1, 1)
    phase = (phase + step * frames) % TABLE_SIZE


print(f"Playing {FREQ} Hz sine wave... Ctrl+C to stop")
with sd.OutputStream(
    channels=1,
    samplerate=SAMPLE_RATE,
    blocksize=BLOCK_SIZE,
    dtype="float32",
    callback=audio_callback,
):
    try:
        while True:
            pass  # idle loop
    except KeyboardInterrupt:
        print("\nStopped.")
