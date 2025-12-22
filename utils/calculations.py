FREQ_MIN = 100.0
FREQ_MAX = 2000.0
AMP_MAX = 0.8

def adc_to_freq(adc_val: int) -> float:
    return FREQ_MIN + (adc_val / 1023.0) * (FREQ_MAX - FREQ_MIN)

def adc_to_amp(adc_val: int) -> float:
    return (adc_val / 1023.0) * AMP_MAX

def adc_to_base(adc_val: int) -> float:
    return 1.0 + 3.0 * (adc_val / 1023.0)

def adc_to_decay(adc_val: int) -> float:
    return 1.2 + 2.8 * (adc_val / 1023.0)