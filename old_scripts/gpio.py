# pylint: disable=E0401
import spidev

spi = spidev.SpiDev()


def setup_spi():
    spi.open(0, 0)
    spi.max_speed_hz = 1350000


def close_spi():
    spi.close()


def read_adc(channel: int) -> int:
    if not 0 <= channel <= 7:
        return 0
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc[1] & 3) << 8) | adc[2]
