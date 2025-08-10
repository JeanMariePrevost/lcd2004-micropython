# Save your class in lcd2004.py (from the previous message), then run this.
# Adjust I2C pins to your board. For Raspberry Pi Pico: I2C0 on GP0/GP1 is common.

import time
from machine import I2C, Pin
from lcd2004 import LCD2004

def demo():
    # --- I2C setup (change pins as needed) ---
    i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)

    # --- LCD init ---
    lcd = LCD2004(i2c, cols=20, rows=4, backlight=True, auto_flush=True)

    # 1) Basic hello world + titles
    lcd.clear()
    lcd.write_at(0, 0, "LCD2004 sanity demo", truncate=True, fill_to_eol=True)
    lcd.write_at(1, 0, "Hello, world!", fill_to_eol=True)
    time.sleep(1.0)

    # 2) Cursor + blink states
    lcd.display(on=True, cursor=True, blink=False)
    lcd.write_at(2, 0, "Cursor ON, blink OFF", truncate=True)
    time.sleep(1.0)
    lcd.display(on=True, cursor=True, blink=True)
    lcd.write_at(3, 0, "Cursor+Blink ON     ", truncate=True)
    time.sleep(1.0)
    lcd.display(on=True, cursor=False, blink=False)

    # 3) set_cursor + write
    lcd.set_cursor(0, 1)  # col 0, row 1
    lcd.write("Hello again -> ")
    time.sleep(0.6)

    # 4) create a custom char (index 0) and print it
    # Simple 5x8 smiley (only low 5 bits used per row)
    SMILE = [
        0b00000,
        0b01010,
        0b01010,
        0b00000,
        0b00000,
        0b10001,
        0b01110,
        0b00000,
    ]
    lcd.create_char(0, SMILE)
    lcd.write(chr(0))
    time.sleep(0.8)

    # 5) clear_line + write_at with fill to EOL
    lcd.clear_line(2)
    lcd.write_at(2, 0, "Line 2 cleared      ", truncate=True, fill_to_eol=True)
    time.sleep(0.6)

    # 6) Truncation demo (intentionally too long)
    long_text = "This line will be truncated at column 5"
    lcd.write_at(2, 5, long_text, truncate=True)
    time.sleep(0.8)

    # 7) Scroll demo
    lcd.write_at(3, 0, "Scrolling left -->  ", fill_to_eol=True)
    for _ in range(6):
        lcd.scroll_left()
        time.sleep(0.25)
    for _ in range(6):
        lcd.scroll_right()
        time.sleep(0.25)

    # 8) Home + small overwrite
    lcd.home()
    lcd.write("Home() OK")
    time.sleep(0.8)

    # 9) Display off/on
    lcd.display(on=False)
    time.sleep(0.5)
    lcd.display(on=True)
    time.sleep(0.5)

    # 10) Backlight toggle
    lcd.backlight(False)
    time.sleep(0.5)
    lcd.backlight(True)
    time.sleep(0.5)

    # Final screen
    lcd.clear()
    lcd.write_at(0, 0, "Demo complete.", fill_to_eol=True)
    lcd.write_at(1, 0, "Custom char: ", fill_to_eol=False)
    lcd.write(chr(0))
    lcd.write_at(2, 0, "Cursor/scroll OK.", fill_to_eol=True)
    lcd.write_at(3, 0, "Backlight OK.", fill_to_eol=True)

if __name__ == "__main__":
    demo()
