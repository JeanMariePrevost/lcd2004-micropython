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

    def __init__(self, *, sda: int, scl: int, i2c_id: int = 0, freq: int = 400_000, addr: int | None = None, orientation: str = "bottom", wrap: bool = True):
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
        self._buffer.clear()
        self.lcd.clear()
        for r in range(self.rows):
            self.lcd.set_cursor(0, r)
            self.lcd.write(" " * self.cols)
        self.lcd.flush()

    def log(self, text: str) -> None:
        text = str(text)
        # if not text:
        #     return

        # Split incoming text into wrapped lines
        for logical_line in text.split("\n"):
            if self.wrap:
                self._buffer.extend(self._wrap_line(logical_line))
            else:
                self._buffer.append(logical_line[: self.cols])
        # Trim history to something reasonable
        max_history = 256
        if len(self._buffer) > max_history:
            self._buffer = self._buffer[-max_history:]
        self._render()

    def _wrap_line(self, line: str) -> list[str]:
        """Wrap a single string into chunks <= self.cols."""
        line = str(line)
        # if not line:
        #     return [""]

        out = []
        while line:
            out.append(line[: self.cols])
            line = line[self.cols :]
        return out or [""]

    def _render(self) -> None:
        # Get last N or first N lines depending on orientation
        if self.orientation == "bottom":
            visible = self._buffer[-self.rows :]
        else:
            visible = self._buffer[: self.rows]

        for r, text in enumerate(visible):
            t = self._to_str(text)[: self.cols]
            t = self._pad_right(t, self.cols)  # manual padding (no str.ljust)
            self.lcd.set_cursor(0, r)
            self.lcd.write(t)
        self.lcd.flush()

    @staticmethod
    def _pad_right(s: str, width: int) -> str:
        n = width - len(s)
        return s + (" " * n if n > 0 else "")

    @staticmethod
    def _to_str(x) -> str:
        if isinstance(x, (bytes, bytearray)):
            try:
                return x.decode("utf-8")
            except Exception:
                return x.decode()  # fallback default codec
        return str(x)
