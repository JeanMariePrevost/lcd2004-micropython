"""
MicroPython driver for LCD2004 / HD44780-compatible character LCDs over I²C using a PCF8574 backpack.

- Backlight is binary (on/off), controlled in software. Ensure the backpack’s jumper is set correctly.
- RW is tied to GND (write-only): the busy flag cannot be read; fixed delays are used where required.
- Contrast is set by the small potentiometer on the backpack.
"""

import time

from machine import I2C, Pin


class LCD2004:
    """
    Driver for HD44780 LCD displays with PCF8574 I2C backpack.

    The display has 80 character positions (20 columns × 4 rows) numbered from (0,0) at the
    top-left to (19,3) at the bottom-right.
    """

    # --- HD44780 commands ---
    # These are the standard commands that control the LCD's behavior
    _CMD_CLEAR = 0x01  # Clear display and return cursor to home and resets display shift
    _CMD_HOME = 0x02  # Return cursor to home position (0,0) and resets display shift (no clear)
    _CMD_ENTRY_MODE = 0x04  # Set how cursor moves after writing
    _CMD_DISPLAY_CTRL = 0x08  # Control display, cursor, and blink
    _CMD_SHIFT = 0x10  # Shift display or cursor left/right
    _CMD_FUNCTION_SET = 0x20  # Set data width, lines, and font
    _CMD_SET_CGRAM = 0x40  # Set custom character memory address
    _CMD_SET_DDRAM = 0x80  # Set display memory address (cursor position)

    # Entry mode flags (cursor behavior after writing)
    _ENTRY_INC = 0x02  # Cursor moves right after writing (left-to-right)
    _ENTRY_SHIFT = 0x01  # Display shifts with cursor (not used here)

    # Display control flags (on/off toggles)
    _DISP_ON = 0x04  # Display content visible
    _CURSOR_ON = 0x02  # Cursor underline visible
    _BLINK_ON = 0x01  # Cursor position blinks

    # Function set flags
    _FUNC_8BIT = 0x10  # 8-bit data mode (not used - we use 4-bit)
    _FUNC_2LINE = 0x08  # 2-line display mode
    _FUNC_5x10 = 0x04  # 5x10 font (not used on 20x4, they use 5x8 characters)

    # PCF8574 bit masks (Control the I2C backpack pins)
    _MASK_RS = 0x01  # Register Select (0=command, 1=data)
    _MASK_RW = 0x02  # Read/Write (unused - always write mode)
    _MASK_E = 0x04  # Enable (strobe for data transfer)
    _MASK_BL = 0x08  # Backlight control

    # Fixed geometry/mapping for standard 20×4 modules
    COLS = 20  # Characters per row
    ROWS = 4  # Number of rows
    _ROW_OFFSETS = (0x00, 0x40, 0x14, 0x54)  # Starting memory addresses for each row

    def __init__(self, *, sda: int, scl: int, i2c_id: int = 0, freq: int = 400_000, addr: "int | None" = None, backlight: bool = True, auto_flush: bool = True) -> None:
        """
        Initialize the LCD display connection.

        Args:
            sda: GPIO pin number for I2C data line (SDA)
            scl: GPIO pin number for I2C clock line (SCL)
            i2c_id: I2C controller number (default 0, sometimes 1)
            freq: I2C bus frequency. 400kHz is standard, 100kHz if connection flaky
            addr: I2C address of the PCF8574 backpack. Common values are 0x27 or 0x3F.
                  By default (addr=None), automatically scans and picks the first device found.
            backlight: Default backlight on/off state (default True)
            auto_flush: If True, automatically sends buffered data after each write operation.
                       Set to False if you want to batch multiple operations and flush manually. (default True)

        Example:
            # Basic setup on Raspberry Pi Pico (I2C0, pins 0 and 1)
            lcd = LCD2004(sda=0, scl=1)

            # Custom setup with manual control
            lcd = LCD2004(sda=2, scl=3, freq=100_000, auto_flush=False)
        """
        self.i2c = I2C(i2c_id, sda=Pin(sda), scl=Pin(scl), freq=freq)
        self.address = addr if addr is not None else self._detect_address()
        self.auto_flush = bool(auto_flush)

        # Display state latches
        self._display_on = 1  # Display content is visible
        self._cursor_on = 0  # Cursor underline is hidden
        self._blink_on = 0  # Cursor position doesn't blink

        # Backlight latch and write buffer
        self._backlight_state = self._MASK_BL if backlight else 0x00
        self._write_buffer = bytearray()

        # --- HD44780 Power-On Initialization Sequence (4-bit mode) ---
        # 1. Wait >40ms after VCC reaches 4.5V for stable operation
        time.sleep_ms(60)  # (requires >40ms)

        # 2. Wake up sequence: Three attempts at 8-bit mode (0x30) to wake up controller
        self._write_nibble(0x30, rs=0)  # First 8-bit mode attempt
        time.sleep_ms(6)  # Wait >4.1ms
        self._write_nibble(0x30, rs=0)  # Second 8-bit mode attempt
        time.sleep_us(150)  # Wait >100μs
        self._write_nibble(0x30, rs=0)  # Third 8-bit mode attempt
        time.sleep_us(150)  # Wait >100μs

        # 3. Final switch to 4-bit mode (0x20)
        self._write_nibble(0x20, rs=0)  # Sets interface to 4-bit mode
        self.flush()

        # Configure the display for normal operation
        self._command(self._CMD_FUNCTION_SET | self._FUNC_2LINE)  # 4-bit, 2 lines, 5×8 font
        self._command(self._CMD_DISPLAY_CTRL)  # Turn display off temporarily
        self.clear()  # Clear any startup garbage
        self._command(self._CMD_ENTRY_MODE | self._ENTRY_INC)  # Cursor moves right after writing
        self._apply_display_state()  # Turn display on (no cursor/blink)
        self._apply_backlight_only()  # Set initial backlight state

    # ---------------- Public API ----------------

    def clear(self) -> None:
        """
        Clear the display and return cursor to top-left position (0,0).

        Takes about 2ms to complete.
        """
        self._command(self._CMD_CLEAR)

    def home(self) -> None:
        """
        Return cursor to the top-left position (0,0) without clearing the display.

        Takes about 2ms to complete.
        """
        self._command(self._CMD_HOME)

    def set_backlight(self, on: bool) -> None:
        """
        Turn the backlight LED on or off.

        Not to be confused with set_display(), which controls whether the LCD controller shows its output.
        """
        self._backlight_state = self._MASK_BL if on else 0x00
        self._apply_backlight_only()

    def set_display(self, on: bool) -> None:
        """
        Show or hide the LCD display content.

        When turned off, the display goes blank but the memory is preserved.
        When turned back on, content is restored.
        Can be used to create "blinking" effects or to save power.
        """
        self._display_on = 1 if on else 0
        self._apply_display_state()

    def set_cursor_visible(self, on: bool) -> None:
        """
        Show or hide the cursor underline.
        """
        self._cursor_on = 1 if on else 0
        self._apply_display_state()

    def set_blink(self, on: bool) -> None:
        """
        Turn on/off the blinking block at the cursor position.

        Note:
        - Independent of the underline cursor: you can enable blink, the cursor, both, or neither.
        - Blink overlays one character cell; display contents are unchanged.
        """
        self._blink_on = 1 if on else 0
        self._apply_display_state()

    def set_cursor(self, col: int, row: int) -> None:
        """
        Move the cursor to a specific position on the display.

        Args:
            col: Column position (0-19, left to right)
            row: Row position (0-3, top to bottom)

        Example:
            lcd.set_cursor(0, 0)    # Top-left
            lcd.set_cursor(19, 3)   # Bottom-right
            lcd.set_cursor(10, 2)   # Middle of third row
        """
        # Clamp coordinates to valid display bounds (0-19 columns, 0-3 rows)
        if row < 0:
            row = 0
        if row > 3:
            row = 3
        if col < 0:
            col = 0
        if col > 19:
            col = 19

        # Calculate the memory address for this position and move cursor
        addr = self._ROW_OFFSETS[row] + col
        self._command(self._CMD_SET_DDRAM | addr)
        if self.auto_flush:
            self.flush()

    def write(self, s: "str | bytes | bytearray") -> None:
        """
        Write characters at the current cursor position.

        Args:
            s: str, bytes, or bytearray. For strings, characters are encoded as ASCII (0-127).

        Note:
            Custom characters (slots 0–7) can be written using chr(slot).

        Example:
            lcd.write("Hello")               # String
            lcd.write(b"ABC")                 # Bytes
            lcd.write(bytearray([65, 66]))    # Bytearray ("AB")
        """
        if isinstance(s, str):
            for ch in s:
                self._data(ord(ch) & 0xFF)
        else:
            for b in s:
                self._data(b & 0xFF)
        if self.auto_flush:
            self.flush()

    def scroll_left(self) -> None:
        """
        Display shift left by one column (hardware).

        - Shifts the visible window left; DDRAM contents are unchanged.
        - Newly revealed rightmost column shows whatever is in DDRAM there (often spaces).
        - Affects the whole display, not a single line.
        - Cursor/DDRAM address counter is not changed by this operation.
        """
        self._command(self._CMD_SHIFT | 0x08)
        if self.auto_flush:
            self.flush()

    def scroll_right(self) -> None:
        """
        Display shift right by one column (hardware).

        - Shifts the visible window right; DDRAM contents are unchanged.
        - Newly revealed leftmost column shows whatever is in DDRAM there.
        - Affects the whole display, not a single line.
        - Cursor/DDRAM address counter is not changed by this operation.
        """
        self._command(self._CMD_SHIFT | 0x0C)
        if self.auto_flush:
            self.flush()

    def create_char(self, index: int, bitmap: "list[int]") -> None:
        """
        Define a custom 5×8 character to be used in write()

        Args:
            index: Character slot number (0–7). Up to 8 custom characters.
            bitmap: List of 8 integers; only the low 5 bits of each row are used (value 0–31).

        Example - Creating a "battery full" symbol in slot 0:
            BATTERY_FULL = [
                0b01110,  # ·███·
                0b11111,  # █████
                0b11111,  # █████
                0b11111,  # █████
                0b11111,  # █████
                0b11111,  # █████
                0b11111,  # █████
                0b00000   # ·····
            ]
            lcd.create_char(0, BATTERY_FULL)
            lcd.write(chr(0))  # Display the custom character
        """
        idx = index & 0x07
        self._command(self._CMD_SET_CGRAM | (idx << 3))
        for i in range(8):
            row = bitmap[i] if i < len(bitmap) else 0
            self._data(row & 0x1F)
        if self.auto_flush:
            self.flush()

    def flush(self) -> None:
        """
        Send write buffer to the display and clear the buffer.
        """
        buf = self._write_buffer
        if not buf:
            return
        try:
            # Chunk to reduce risk of NACK/EIO on some ports
            for i in range(0, len(buf), 8):
                self.i2c.writeto(self.address, buf[i : i + 8])
        finally:
            buf[:] = b""

    # ---------------- Internals ----------------

    def _detect_address(self) -> int:
        """
        Automatically find the I2C address of the PCF8574 backpack.

        Raises:
            OSError: If no I2C devices are found on the bus.
        """
        scan = self.i2c.scan()
        if not scan:
            raise OSError("No I2C devices found for LCD2004.")
        # Prefer common addresses if present
        if 0x27 in scan:
            return 0x27
        if 0x3F in scan:
            return 0x3F
        return scan[0]

    def _apply_backlight_only(self) -> None:
        """
        Apply the current backlight state to the display.
        """
        self.i2c.writeto(self.address, bytes([self._backlight_state]))

    def _apply_display_state(self) -> None:
        """
        Apply the current display state (on/off, cursor, blink) to the display.
        """
        ctrl = self._CMD_DISPLAY_CTRL | (self._DISP_ON if self._display_on else 0) | (self._CURSOR_ON if self._cursor_on else 0) | (self._BLINK_ON if self._blink_on else 0)
        self._command(ctrl)
        if self.auto_flush:
            self.flush()

    def _write_nibble(self, byte: int, rs: bool) -> None:
        """
        Queue one 4-bit transfer (upper nibble of 'byte') with optional RS.

        Args:
            byte: The 8 bits to send
            rs: Register Select - True for data, False for commands
        """
        data = (byte & 0xF0) | self._backlight_state | (self._MASK_RS if rs else 0)
        self._write_buffer.append(data | self._MASK_E)  # E=1
        self._write_buffer.append(data)  # E=0

    def _send_byte(self, byte: int, rs: bool) -> None:
        """
        Queue full 8-bit transfer (two 4-bit cycles) with optional RS.

        Args:
            byte: The full 8-bit byte to send
            rs: Register Select - True for data, False for commands

        This method breaks down an 8-bit transfer into two 4-bit operations.
        """
        self._write_nibble(byte & 0xF0, rs)
        self._write_nibble((byte << 4) & 0xF0, rs)

    def _command(self, cmd: int) -> None:
        """
        Send a command byte to the LCD controller (byte with RS=0)

        Args:
            cmd: The command byte to send

        Commands control the LCD's behavior - clearing the display, moving the cursor, changing display settings, etc.
        """
        self._send_byte(cmd & 0xFF, rs=0)
        if cmd in (self._CMD_CLEAR, self._CMD_HOME):
            # CLEAR and HOME require a blocking delay (~1.52 ms).
            # We flush pending bytes and wait ~2 ms as a safe margin.
            self.flush()
            time.sleep_ms(2)

    def _data(self, val: int) -> None:
        """
        Queue a data byte to be written to DDRAM (text) or CGRAM (custom characters) with RS=1.

        Args:
            val: The data byte to send (typically a character code).

        Data writes place a character at the current address counter position
        and advance the counter according to the entry mode settings.
        """
        self._send_byte(val & 0xFF, rs=1)
