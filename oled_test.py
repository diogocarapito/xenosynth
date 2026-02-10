import time
from luma.core.interface.serial import spi
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
from controls.gpio import setup_spi, close_spi  # your SPI helper

def main():
    setup_spi()  # Initialize SPI (your function)

    # SPI interface
    serial = spi(port=1, device=0x3C)  # adjust bus/device if needed
    device = sh1106(serial)

    # Get screen size
    width, height = device.size

    # Load default font
    font = ImageFont.load_default()

    # Clear screen
    device.clear()

    try:
        for i in range(10):  # test loop 10 times
            # Create image buffer
            image = Image.new("1", (width, height))
            draw = ImageDraw.Draw(image)

            # Draw text
            draw.text((0, 0), f"Test {i+1}", font=font, fill=255)
            draw.text((0, 10), "OLED SPI OK", font=font, fill=255)

            # Display image
            device.display(image)

            time.sleep(1)  # wait 1 second between updates

    finally:
        device.clear()  # clear screen on exit
        close_spi()     # close SPI (your helper)

if __name__ == "__main__":
    main()