# pylint: disable=E0401

import time
import threading
import sounddevice as sd
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont

from utils.gpio import setup_spi, close_spi, read_adc
from utils.calculations import adc_to_freq, adc_to_amp, adc_to_base, adc_to_decay
from sutils.ound_engine import audio_callback

# OLED setup
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)
oled_width, oled_height = device.size
font = ImageFont.load_default()
device.clear()

# Globals
_smoothed_freq = 440.0
_smoothed_amp = 0.2
_smoothed_base = 1.0
_smoothed_decay = 2.0
_running = True
FREQ_MIN = 100.0
FREQ_MAX = 2000.0
AMP_MAX = 0.8

def adc_poller():
    global _smoothed_freq, _smoothed_amp, _smoothed_base, _smoothed_decay, _running
    _running = True  # Ensure _running is assigned
    while _running:
        raw_a = read_adc(0)  # Channel 0 for amplitude
        raw_f = read_adc(1)  # Channel 1 for frequency
        raw_b = read_adc(2)  # Channel 2 for base
        # Channels 3 and 4 are unused for now

        _smoothed_amp = adc_to_amp(raw_a)
        _smoothed_freq = adc_to_freq(raw_f)
        _smoothed_base = adc_to_base(raw_b)
        time.sleep(0.01)

def show_wave_on_oled(freq, _, base):  # Remove unused 'amp' argument
    image = Image.new("1", (oled_width, oled_height))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), f"Freq: {int(freq)} Hz", font=font, fill=255)
    draw.text((0, 10), f"Base: {base:.2f}", font=font, fill=255)
    device.display(image)

def main():
    setup_spi()
    poller = threading.Thread(target=adc_poller, daemon=True)
    poller.start()
    params = {
        'freq': _smoothed_freq,
        'amp': _smoothed_amp,
        'base': _smoothed_base,
        'decay': _smoothed_decay
    }
    with sd.OutputStream(channels=1, samplerate=44100, blocksize=512, dtype='float32',
                         callback=lambda outdata, frames, time_info, status: audio_callback(outdata, frames, time_info, status, params)):
        while True:
            time.sleep(0.2)
            show_wave_on_oled(_smoothed_freq, _smoothed_amp, _smoothed_base)
    close_spi()

if __name__ == "__main__":
    main()


