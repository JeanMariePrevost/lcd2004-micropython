"""
Demo: LCD2004 SimpleConsole Wrapper

Demonstrates usage of the SimpleConsole class
- Initialization with default settings (wrap=True, recent_first=True)
- Printing this flags
- Sequential log entries
- Automatic line wrapping
- Multi-line support
- Clearing the display
"""

import time

from lcd2004.simple_console import SimpleConsole

# Init console
console = SimpleConsole(sda=0, scl=1)  # Change pins for your board / setup

# Demo output
console.log("SimpleConsole Demo")
time.sleep(2)

# Print wrap and recent_first flags
console.clear()
if console.recent_first:
    console.log("Recent first")
    console.log("Wrap enabled" if console.wrap else "Wrap disabled")
    console.log("Settings:")
else:
    console.log("Recent last")
    console.log("Wrap enabled" if console.wrap else "Wrap disabled")
    console.log("Settings:")
time.sleep(2)

# Basic logging
console.clear()
console.log("Basic logging:")
time.sleep(0.8)
console.log("Fake task 1: OK")
time.sleep(0.8)
console.log("Fake task 2: OK")
time.sleep(0.8)
console.log("Fake task 3: OK")
time.sleep(0.8)
console.log("Fake task 4: OK")
time.sleep(0.8)
console.log("Fake task 5: OK")
time.sleep(2)


# Demonstrate wrapping
console.log("This is a long line that will automatically wrap to the next row if wrap=True")
time.sleep(3)

# Demonstrate multiple lines at once
console.log("Line one\nLine two\nLine three\nLine four")
time.sleep(3)

console.clear()
time.sleep(1)

console.log("Demo completed")
