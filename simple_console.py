# simple_console.py
from lcd2004 import LCD2004


class SimpleConsole:
    """
    Simple scrolling console for a 20×4 LCD2004.

    - orientation = "bottom" → new lines appear at the bottom, older lines scroll up
    - orientation = "top"    → new lines appear at the top, older lines scroll down
    - wrap = True → long lines wrap to the next row
    - wrap = False → long lines are truncated
    """

    MAX_HISTORY = 4  # number of lines kept in buffer (4 meaning no history beyond visible lines)

    def __init__(self, *, sda: int, scl: int, i2c_id: int = 0, freq: int = 400_000, addr: int | None = None, orientation: str = "bottom", wrap: bool = True):
        """
        Initialize a SimpleConsole instance bound to an LCD2004 display.

        Args:
            sda (int): GPIO pin number for I2C data line (SDA)
            scl (int): GPIO pin number for I2C clock line (SCL)
            i2c_id (int, optional): I2C controller number (default 0, sometimes 1)
            freq (int, optional):  I2C bus frequency. 400kHz is standard, 100kHz if connection flaky
            addr (int | None, optional): I2C address of the PCF8574 backpack. Common values are 0x27 or 0x3F.
                  By default (addr=None), automatically scans and picks the first device found.
            orientation (str, optional): Scrolling orientation of the console.
                - "bottom": New lines appear at the bottom; older lines scroll up. ("bottom-up")
                - "top": New lines appear at the top; older lines scroll down. ("top-down")
                Default is "bottom".
            wrap (bool, optional): If True, text longer than the display width wraps
                onto the next row. If False, it is truncated to the display width.
                Default is True.
        """
        if orientation not in ("bottom", "top"):
            raise ValueError("orientation must be 'bottom' or 'top'")
        self.lcd = LCD2004(sda=sda, scl=scl, i2c_id=i2c_id, freq=freq, addr=addr, auto_flush=False)
        self.orientation = orientation
        self.wrap = wrap
        self.cols = self.lcd.COLS
        self.rows = self.lcd.ROWS
        self._buffer: list[str] = []
        self.clear()

    def clear(self) -> None:
        """Clear the console and the display."""
        self._buffer.clear()
        self.lcd.clear()
        for r in range(self.rows):
            self.lcd.set_cursor(0, r)
            self.lcd.write(" " * self.cols)
        self.lcd.flush()

    def log(self, text: str) -> None:
        """Log a message to the console."""
        text = str(text)

        # Split incoming text into wrapped lines
        for logical_line in text.split("\n"):
            if self.wrap:
                self._buffer.extend(self._wrap_line(logical_line))
            else:
                self._buffer.append(logical_line[: self.cols])
        # Trim history to something reasonable
        if len(self._buffer) > self.MAX_HISTORY:
            self._buffer = self._buffer[-self.MAX_HISTORY :]
        self._render()

    def _wrap_line(self, line: str) -> list[str]:
        """Wrap a single string into chunks <= self.cols."""
        line = str(line)

        out = []
        while line:
            out.append(line[: self.cols])
            line = line[self.cols :]
        return out or [""]

    def _render(self) -> None:
        """Render the console to the display. (basically the SimpleConsole "write + flush")"""
        # Get last N or first N lines depending on orientation
        if self.orientation == "bottom":
            visible = self._buffer[-self.rows :]
        else:
            visible = self._buffer[: self.rows]

        # If there are less than self.rows lines, pad with empty lines to fill the screen
        if len(visible) < self.rows:
            if self.orientation == "bottom":
                visible = [""] * (self.rows - len(visible)) + visible
            else:
                visible = visible + [""] * (self.rows - len(visible))

        # Pad/truncate to exactly rows
        # Padding is used to ensure the new lines clear existing characters
        for r, text in enumerate(visible):
            t = self._to_str(text)[: self.cols]
            t = self._pad_right(t, self.cols)  # manual padding (no str.ljust)
            self.lcd.set_cursor(0, r)
            self.lcd.write(t)
        self.lcd.flush()

    @staticmethod
    def _pad_right(s: str, width: int) -> str:
        """Pad a string with spaces to exactly width characters."""
        n = width - len(s)
        return s + (" " * n if n > 0 else "")

    @staticmethod
    def _to_str(x) -> str:
        """Convert bytes/bytearray to string, using UTF-8, or default codec as a fallback."""
        if isinstance(x, (bytes, bytearray)):
            try:
                return x.decode("utf-8")
            except Exception:
                return x.decode()  # fallback default codec
        return str(x)
