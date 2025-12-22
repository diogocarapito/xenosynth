#!/usr/bin/env python3
"""
synth.py

Monophonic sine synth controlled by two potentiometers via MCP3008:
 - Pot CH5 -> Frequency (100..2000 Hz)
 - Pot CH6 -> Amplitude (0..0.8)
Audio output via sounddevice (PortAudio). Uses a lookup table for efficiency.
OLED display for visual feedback.
    - SDA (GPIO 2)
    - SCL (GPIO 3)

"""

import time
import threading
import numpy as np

# Try imports and give a clear error if missing
try:
    import spidev
except Exception as e:
    raise SystemExit("spidev not installed or SPI not enabled. Install + enable SPI. "
                     "On Debian: sudo apt-get install python3-spidev ; enable SPI with sudo raspi-config.") from e

try:
    import sounddevice as sd
except Exception as e:
    raise SystemExit("sounddevice not installed or PortAudio missing. "
                     "Install PortAudio with: sudo apt-get install portaudio19-dev libportaudio2 libportaudiocpp0 ; "
                     "then pip3 install sounddevice") from e

from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont

# --- OLED setup for 128x64 on I2C (SCL/SDA) ---
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)  # or ssd1306(serial) for SSD1306 displays

oled_width, oled_height = device.size
font = ImageFont.load_default()

# Clear display
device.clear()

# -------------------- User parameters --------------------
SAMPLE_RATE = 44100           # audio sample rate
BLOCK_SIZE = 512              # audio block size (lower = more responsive, higher = less CPU)
TABLE_SIZE = 4096             # sine table size (bigger -> smoother)
POLL_HZ = 100                 # how often we read the pots (Hz)
FREQ_MIN = 100.0              # min frequency (Hz)
FREQ_MAX = 2000.0             # max frequency (Hz)
AMP_MAX  = 0.8                # maximum amplitude to avoid clipping
ADC_CHANNEL_FREQ = 4          # MCP3008 channel for frequency pot
ADC_CHANNEL_AMP  = 5          # MCP3008 channel for amplitude pot
ADC_CHANNEL_BASE = 6          # MCP3008 channel for partials base pot
ADC_CHANNEL_DECAY = 7         # MCP3008 channel for decay pot
# ---------------------------------------------------------

# --- Precompute sine table ---
sine_table = np.sin(2.0 * np.pi * np.arange(TABLE_SIZE) / TABLE_SIZE).astype(np.float32)

# --- Globals updated by ADC thread (smoothed) and read by audio callback ---
_smoothed_freq = 440.0
_smoothed_amp  = 0.2
_smoothed_base = 1.0  # initial base for partials
_smoothed_decay = 2.0  # initial decay
_running = True

# Smoothing parameters (try a higher value for amplitude)
SMOOTH_TAU = 0.2  # higher value = more smoothing
_alpha = None      # computed from POLL_HZ

# --- SPI (MCP3008) setup ---
spi = spidev.SpiDev()
try:
    spi.open(0, 0)               # bus 0, device CE0
    spi.max_speed_hz = 1350000
except FileNotFoundError as e:
    raise SystemExit("SPI device not found. Enable SPI (sudo raspi-config -> Interface Options -> SPI) and reboot.") from e


def read_adc(channel: int) -> int:
    """Read ADC channel 0..7 from MCP3008. Returns 0..1023."""
    if not 0 <= channel <= 7:
        return 0
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc[1] & 3) << 8) | adc[2]


def adc_to_freq(adc_val: int) -> float:
    """Map ADC 0..1023 to frequency FREQ_MIN..FREQ_MAX (log or linear). Linear here."""
    return FREQ_MIN + (adc_val / 1023.0) * (FREQ_MAX - FREQ_MIN)


def adc_to_amp(adc_val: int) -> float:
    """Map ADC 0..1023 to amplitude 0..AMP_MAX"""
    return (adc_val / 1023.0) * AMP_MAX


def adc_to_base(adc_val: int) -> float:
    """Map ADC 0..1023 to base 1.0..4.0"""
    return 1.0 + 3.0 * (adc_val / 1023.0)


def adc_to_decay(adc_val: int) -> float:
    # Map ADC 0..1023 to decay factor 1.2..4.0
    return 1.2 + 2.8 * (adc_val / 1023.0)


def adc_poller():
    """Background thread: polls ADC channels at POLL_HZ and updates smoothed globals."""
    global _smoothed_freq, _smoothed_amp, _smoothed_base, _smoothed_decay, _running, _alpha

    if _alpha is None:
        dt = 1.0 / POLL_HZ
        _alpha_freq = 1.0 - np.exp(-dt / SMOOTH_TAU)
        _alpha_amp  = 1.0 - np.exp(-dt / (SMOOTH_TAU * 2))
        _alpha_base = 1.0 - np.exp(-dt / (SMOOTH_TAU * 8))   # much slower for base
        _alpha_decay = 1.0 - np.exp(-dt / (SMOOTH_TAU * 8))  # much slower for decay

    while _running:
        try:
            raw_f = read_adc(ADC_CHANNEL_FREQ)
            raw_a = read_adc(ADC_CHANNEL_AMP)
            raw_b = read_adc(ADC_CHANNEL_BASE)
            raw_d = read_adc(ADC_CHANNEL_DECAY)
        except Exception:
            time.sleep(1.0 / POLL_HZ)
            continue

        target_f = adc_to_freq(raw_f)
        target_a = adc_to_amp(raw_a)
        target_b = adc_to_base(raw_b)
        target_d = adc_to_decay(raw_d)
        # Quantize base and decay to steps of 0.1 to avoid micro-crackles
        target_b = round(target_b * 10) / 10.0
        target_d = round(target_d * 10) / 10.0

        _smoothed_freq += _alpha_freq * (target_f - _smoothed_freq)
        _smoothed_amp  += _alpha_amp  * (target_a - _smoothed_amp)
        _smoothed_base += _alpha_base * (target_b - _smoothed_base)
        _smoothed_decay += _alpha_decay * (target_d - _smoothed_decay)

        time.sleep(1.0 / POLL_HZ)


# --- Audio callback: super lightweight, uses lookup table ---
_phase = 0.0  # fractional phase in table indices (float)

def audio_callback(outdata, frames, time_info, status):
    """
    outdata: (frames, channels) float32 numpy array provided by PortAudio.
    Keep this function extremely fast: no blocking, no I/O.
    """
    global _phase, _smoothed_freq, _smoothed_amp, _smoothed_base, _smoothed_decay

    freq = _smoothed_freq
    amp  = _smoothed_amp
    base = _smoothed_base
    decay = _smoothed_decay

    N_PARTIALS = 6  # Use 6 partials

    samples = np.zeros(frames, dtype=np.float32)
    for n in range(N_PARTIALS):
        partial_freq = freq * (base ** n)
        partial_amp = amp / (decay ** n)
        step = (partial_freq * TABLE_SIZE) / SAMPLE_RATE
        idxs = (_phase + step * np.arange(frames)).astype(np.int64) % TABLE_SIZE
        samples += sine_table[idxs] * partial_amp

    # Write into outdata (mono -> shape (-1,1))
    outdata[:] = samples.reshape(-1, 1)

    # advance phase
    _phase = (_phase + (freq * TABLE_SIZE / SAMPLE_RATE) * frames) % TABLE_SIZE


def show_wave_on_oled(freq, amp, base):
    """Display waveform graph and frequency value on OLED using luma."""
    image = Image.new("1", (oled_width, oled_height))
    draw = ImageDraw.Draw(image)

    # Draw frequency text
    draw.text((0, 0), f"Freq: {int(freq)} Hz", font=font, fill=255)
    draw.text((0, 10), f"Base: {base:.2f}", font=font, fill=255)

    # Waveform parameters
    wave_height = oled_height - 18  # leave space for text
    y_offset = 18
    center_y = y_offset + wave_height // 2

    # Generate waveform points
    points = []
    N_PARTIALS = 6  # Use 6 partials
    decay = _smoothed_decay
    for x in range(oled_width):
        # Map x to phase (0..2pi)
        phase = (x / oled_width) * 2 * np.pi
        val = 0
        for n in range(N_PARTIALS):
            partial_freq = freq * (base ** n)
            partial_amp = amp / (decay ** n)
            val += partial_amp * np.sin(phase * (base ** n))
        y = int(center_y - (wave_height // 2) * val)
        points.append((x, y))

    # Draw waveform
    for i in range(1, len(points)):
        draw.line([points[i-1], points[i]], fill=255)

    device.display(image)


def main():
    global _running

    print("Starting ADC poller thread...")
    poller = threading.Thread(target=adc_poller, daemon=True)
    poller.start()

    print("Opening audio stream (sample_rate={}, blocksize={})...".format(SAMPLE_RATE, BLOCK_SIZE))
    try:
        with sd.OutputStream(channels=1,
                             samplerate=SAMPLE_RATE,
                             blocksize=BLOCK_SIZE,
                             dtype='float32',
                             callback=audio_callback):
            print("Synth running. Pots: CH0=freq, CH1=amp. Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(0.2)  # main thread idle
                    show_wave_on_oled(_smoothed_freq, _smoothed_amp, _smoothed_base)
            except KeyboardInterrupt:
                print("\nStopping...")
    except Exception as e:
        print("Error opening audio stream or during playback:", e)
    finally:
        _running = False
        time.sleep(0.1)
        try:
            spi.close()
        except Exception:
            pass
        print("Exited cleanly.")


if __name__ == "__main__":
    main()