# MicroPython driver for HD44780-compatible 20x4 LCDs over I2C (PCF8574 backpack)
# Class name: LCD2004
#
# Notes
# - Works with common backpacks where:
#     P7..P4 -> D7..D4, P3 -> Backlight, P2 -> E, P1 -> RW (unused, tied low), P0 -> RS
# - Defaults to 20x4 addressing. Also works for 16x2/16x4 if cols/rows are set accordingly.
# - Efficient batched I2C writes; flush() is called automatically unless auto_flush=False.
# - Safer backlight() implementation that never clocks E (doesn’t send spurious commands).

import time

class LCD2004:
    """HD44780 LCD via PCF8574 I2C expander (4-bit mode)."""

    # Command constants
    _CMD_CLEAR            = 0x01
    _CMD_HOME             = 0x02
    _CMD_ENTRY_MODE_SET   = 0x04
    _CMD_DISPLAY_CTRL     = 0x08
    _CMD_SHIFT            = 0x10
    _CMD_FUNCTION_SET     = 0x20
    _CMD_SET_CGRAM_ADDR   = 0x40
    _CMD_SET_DDRAM_ADDR   = 0x80

    # Entry mode flags
    _ENTRY_INC            = 0x02
    _ENTRY_SHIFT          = 0x01

    # Display control flags
    _DISP_ON              = 0x04
    _CURSOR_ON            = 0x02
    _BLINK_ON             = 0x01

    # Function set flags
    _FUNC_8BIT            = 0x10
    _FUNC_2LINE           = 0x08
    _FUNC_5x10            = 0x04  # (rarely used; most 20x4 use 5x8)

    # PCF8574 bit masks (typical wiring)
    _MASK_RS              = 0x01
    _MASK_RW              = 0x02  # unused; we always write
    _MASK_E               = 0x04
    _MASK_BL              = 0x08

    def __init__(self, i2c, addr=None, cols=20, rows=4, backlight=True, auto_flush=True):
        """
        i2c: machine.I2C or SoftI2C instance
        addr: I2C address; if None, first scanned address is used
        cols, rows: LCD geometry
        backlight: initial backlight state
        auto_flush: True -> flush after each high-level operation
        """
        self.i2c = i2c
        self.addr = addr if addr is not None else self._detect_address(i2c)
        self.cols = int(cols)
        self.rows = int(rows)
        self.auto_flush = bool(auto_flush)

        # Row DDRAM offsets (controller is internally 2x40; 4-line modules interleave)
        if self.rows >= 4:
            if self.cols >= 20:
                self._row_ofs = (0x00, 0x40, 0x14, 0x54)  # common 20x4 map
            else:
                self._row_ofs = (0x00, 0x40, 0x10, 0x50)  # common 16x4 map
        else:
            self._row_ofs = (0x00, 0x40, 0x00, 0x40)     # 1/2 line modules

        self._bl = self._MASK_BL if backlight else 0x00
        self._buf = bytearray()

        # Initialize LCD in 4-bit mode (per datasheet power-up sequence)
        time.sleep_ms(50)                         # wait > 40ms after VCC rises
        self._write4(0x30, rs=0) ; time.sleep_ms(5)
        self._write4(0x30, rs=0) ; time.sleep_us(150)
        self._write4(0x30, rs=0) ; time.sleep_us(150)
        self._write4(0x20, rs=0)                  # 4-bit mode
        self.flush()

        # Function set: 4-bit, 2 line, 5x8 dots
        self._command(self._CMD_FUNCTION_SET | self._FUNC_2LINE)
        # Display off
        self._command(self._CMD_DISPLAY_CTRL)
        # Clear display (slow)
        self.clear()
        # Entry mode: increment, no shift
        self._command(self._CMD_ENTRY_MODE_SET | self._ENTRY_INC)
        # Display on, no cursor, no blink
        self.display(on=True, cursor=False, blink=False)

        # Ensure backlight state is applied without strobing E
        self._apply_backlight_only()

    # ---------- Public API ----------

    def clear(self):
        self._command(self._CMD_CLEAR)
        self.flush()
        time.sleep_ms(2)  # datasheet: clear/home need >1.52ms

    def home(self):
        self._command(self._CMD_HOME)
        self.flush()
        time.sleep_ms(2)

    def backlight(self, on: bool):
        """Turn backlight LED on/off without clocking E."""
        self._bl = self._MASK_BL if on else 0x00
        self._apply_backlight_only()

    def display(self, on=True, cursor=False, blink=False):
        """Set display on/off, cursor visibility, and blink."""
        ctrl = (self._CMD_DISPLAY_CTRL |
                (self._DISP_ON if on else 0) |
                (self._CURSOR_ON if cursor else 0) |
                (self._BLINK_ON if blink else 0))
        self._command(ctrl)
        if self.auto_flush:
            self.flush()

    def set_cursor(self, col: int, row: int):
        """Set cursor to (col,row) with bounds clamped."""
        if row < 0: row = 0
        if row >= self.rows: row = self.rows - 1
        if col < 0: col = 0
        if col >= self.cols: col = self.cols - 1
        addr = self._row_ofs[row] + col
        self._command(self._CMD_SET_DDRAM_ADDR | addr)
        if self.auto_flush:
            self.flush()

    def write(self, s):
        """Write text at current cursor. Accepts str, bytes, or bytearray."""
        if isinstance(s, str):
            for ch in s:
                self._data(ord(ch) & 0xFF)
        else:
            for b in s:
                self._data(b & 0xFF)
        if self.auto_flush:
            self.flush()

    def write_at(self, row: int, col: int, s, *, truncate=True, fill_to_eol=False):
        """Convenience: set cursor then write; optional truncate/fill to EOL."""
        self.set_cursor(col, row)
        if isinstance(s, (bytes, bytearray)):
            text = bytes(s)
        else:
            text = str(s)
        if truncate and len(text) > (self.cols - col):
            text = text[: self.cols - col]
        self.write(text)
        if fill_to_eol:
            remaining = self.cols - (col + len(text))
            if remaining > 0:
                self.write(" " * remaining)
        if self.auto_flush:
            self.flush()

    def clear_line(self, row: int):
        """Clear a whole line."""
        self.write_at(row, 0, " " * self.cols, truncate=False, fill_to_eol=False)

    def scroll_left(self):
        self._command(self._CMD_SHIFT | 0x08)  # display shift, left
        if self.auto_flush:
            self.flush()

    def scroll_right(self):
        self._command(self._CMD_SHIFT | 0x0C)  # display shift, right
        if self.auto_flush:
            self.flush()

    def create_char(self, index: int, bitmap):
        """
        Define a custom 5x8 char.
        index: 0..7
        bitmap: iterable of 8 bytes (only low 5 bits used per row)
        """
        idx = index & 0x07
        self._command(self._CMD_SET_CGRAM_ADDR | (idx << 3))
        for i in range(8):
            self._data((bitmap[i] if i < len(bitmap) else 0) & 0x1F)
        if self.auto_flush:
            self.flush()

    def flush(self):
        """Write buffered bytes to the PCF8574."""
        if self._buf:
            try:
                # _buf is already a bytearray, so writeto accepts it directly.
                self.i2c.writeto(self.addr, self._buf)
            finally:
                # Reuse the same object to avoid reallocs
                self._buf[:] = b""

    # ---------- Internals ----------

    def _detect_address(self, i2c):
        scan = i2c.scan()
        if not scan:
            raise OSError("No I2C devices found for LCD2004.")
        # Heuristic: prefer common 0x27/0x3F if present
        if 0x27 in scan: return 0x27
        if 0x3F in scan: return 0x3F
        return scan[0]

    def _apply_backlight_only(self):
        """Update backlight LED without toggling E or sending a nibble."""
        # Send a single byte with E=0,RW=0,RS=0 and BL per state.
        self.i2c.writeto(self.addr, bytes([self._bl]))


    def _write4(self, byte, rs):
        """Queue one 4-bit transfer (upper nibble of 'byte') with optional RS."""
        data = (byte & 0xF0) | self._bl | (self._MASK_RS if rs else 0)
        # E high then E low
        # Old (CPython-friendly but not MicroPython-safe):
        # self._buf.extend((data | self._MASK_E, data))
        # MicroPython-safe:
        self._buf.append(data | self._MASK_E)
        self._buf.append(data)

    def _send(self, byte, rs):
        """Queue full 8-bit transfer (two 4-bit cycles)."""
        hb = byte & 0xF0
        lb = (byte << 4) & 0xF0
        self._write4(hb, rs)
        self._write4(lb, rs)


    def _command(self, cmd):
        self._send(cmd & 0xFF, rs=0)
        # Only clear/home require extra time; others are fine at I2C pace
        if cmd in (self._CMD_CLEAR, self._CMD_HOME):
            self.flush()
            time.sleep_ms(2)

    def _data(self, val):
        self._send(val & 0xFF, rs=1)
