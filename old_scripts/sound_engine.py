# pylint: disable=E0401
import numpy as np

SAMPLE_RATE = 44100
TABLE_SIZE = 4096
N_PARTIALS = 6

sine_table = np.sin(2.0 * np.pi * np.arange(TABLE_SIZE) / TABLE_SIZE).astype(np.float32)


def audio_callback(
    outdata, frames, _, __, params
):  # Removed unused 'time_info' and 'status'
    freq = params["freq"]
    amp = params["amp"]
    base = params["base"]
    decay = params["decay"]

    samples = np.zeros(frames, dtype=np.float32)
    phase = params.get("_phase", 0.0)  # Use phase from params

    for n in range(N_PARTIALS):
        partial_freq = freq * (base**n)
        partial_amp = amp / (decay**n)
        step = (partial_freq * TABLE_SIZE) / SAMPLE_RATE
        idxs = (phase + step * np.arange(frames)).astype(np.int64) % TABLE_SIZE
        samples += sine_table[idxs] * partial_amp

    outdata[:] = samples.reshape(-1, 1)
    params["_phase"] = (
        phase + (freq * TABLE_SIZE / SAMPLE_RATE) * frames
    ) % TABLE_SIZE  # Update phase in params
