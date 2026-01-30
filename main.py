# from audio.stream import start_audio
# from synth.engine import SynthEngine
# from controls.mapper import start_controls

# pylint: disable=E0401

import time
import threading
import sounddevice as sd

from controls.oled import oled_setup, show_wave_on_oled
from controls.gpio import setup_spi, close_spi
from controls.pots import adc_poller
from synth.engine import audio_callback

import yaml

with open("config/synth.yaml", "r", encoding="utf-8") as f:
    config_synth = yaml.safe_load(f)


# Globals
_smoothed_freq = config_synth["smoothed_freq"]
_smoothed_amp = config_synth["smoothed_amp"]
_smoothed_base = config_synth["smoothed_base"]
_smoothed_decay = config_synth["smoothed_decay"]
FREQ_MIN = config_synth["freq_min"]
FREQ_MAX = config_synth["freq_max"]
AMP_MAX = config_synth["max_amplitude"]
_running = True

oled_width, oled_height, font, device = oled_setup()


def main():
    setup_spi()
    poller = threading.Thread(
        target=adc_poller(
            _smoothed_freq, _smoothed_amp, _smoothed_base, _smoothed_decay, _running
        ),
        daemon=True,
    )
    poller.start()

    def dynamic_audio_callback(outdata, frames, time_info, status):
        params = {
            "freq": _smoothed_freq,  # Fetch latest frequency dynamically
            "amp": _smoothed_amp,  # Fetch latest amplitude dynamically
            "base": _smoothed_base,  # Fetch latest base dynamically
            "decay": _smoothed_decay,
        }
        audio_callback(outdata, frames, time_info, status, params)

    with sd.OutputStream(
        channels=1,
        samplerate=44100,
        blocksize=64,
        dtype="float32",
        callback=dynamic_audio_callback,
    ):
        while True:
            time.sleep(0.2)
            show_wave_on_oled(
                _smoothed_freq,
                _smoothed_amp,
                _smoothed_base,
                oled_width,
                oled_height,
                font,
                device,
            )
    close_spi()


if __name__ == "__main__":
    main()
