import time
from utils.math import adc_to_freq, adc_to_amp, adc_to_base
from controls.gpio import read_adc


def adc_poller(
    _smoothed_freq, _smoothed_amp, _smoothed_base, _smoothed_decay, _running
):
    _smoothed_decay = 2.0  # Assign _smoothed_decay explicitly
    _running = True  # Ensure _running is assigned
    while _running:
        raw_a = read_adc(0)  # Channel 0 for amplitude
        raw_f = read_adc(1)  # Channel 1 for frequency
        raw_b = read_adc(2)  # Channel 2 for base
        # Channels 3 and 4 are unused for now

        _smoothed_amp = adc_to_amp(raw_a)
        _smoothed_freq = adc_to_freq(raw_f)  # Re-enable frequency updates
        _smoothed_base = adc_to_base(raw_b)

        print(
            f"Freq: {_smoothed_freq:.2f} Hz, Amp: {_smoothed_amp:.2f}, Base: {_smoothed_base:.2f}"
        )
        time.sleep(0.01)
