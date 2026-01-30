from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont


def oled_setup():
    # OLED setup
    serial = i2c(port=1, address=0x3C)
    device = sh1106(serial)
    oled_width, oled_height = device.size
    font = ImageFont.load_default()
    device.clear()

    return oled_width, oled_height, font, device


def show_wave_on_oled(
    freq, _, base, oled_width, oled_height, font, device
):  # Remove unused 'amp' argument
    image = Image.new("1", (oled_width, oled_height))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), f"Freq: {int(freq)} Hz", font=font, fill=255)
    draw.text((0, 10), f"Base: {base:.2f}", font=font, fill=255)
    device.display(image)
