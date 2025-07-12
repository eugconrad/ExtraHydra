"""Common utilities for MicroHydra core modules."""
import time
import os


def clamp(x: float, minimum: float, maximum: float) -> int|float:
    """Clamp the given value to the range `minimum` - `maximum`.

    This function is faster than using `min(max(val, val), val)`
    (in my testing, at least), and a bit more readable, too.
    """
    if x < minimum:
        return minimum
    if x > maximum:
        return maximum
    return x


def get_instance(cls, *, allow_init: bool = True) -> object:
    """Get the active instance of the given class.

    If an instance doesn't exist and `allow_init` is `True`, one will be created and returned.
    Otherwise, if there is no instance, raises `AttributeError`.
    """
    if hasattr(cls, 'instance'):
        return cls.instance
    if allow_init:
        return cls()
    msg = f"{cls.__name__} has no instance. (You must initialize it first)"
    raise AttributeError(msg)


def save_screenshot(display):
    """Saves a screenshot from the given display object to the SD card.

    Supports both RGB565 and GS4_HMSB (4-bit grayscale) framebuffer formats.

    Args:
        display: An object with `fbuf`, `width`, `height`, and `use_tiny_buf` attributes.

    Raises:
        OSError: If framebuffer not available or SD card is inaccessible.
    """
    if not hasattr(display, "fbuf"):
        raise OSError("Framebuffer not available")

    # Check SD card access
    try:
        os.listdir('/sd')
    except OSError:
        from lib import sdcard
        sdcard.SDCard().mount()
        # raise OSError("SD card not accessible")

    # Create screenshots directory if needed
    s_dir = "/sd/Hydra/screenshots"
    try:
        os.stat(s_dir)
    except OSError:
        os.mkdir(s_dir)

    # Generate filename with timestamp
    filename = "/{:04}-{:02}-{:02}_{:02}-{:02}-{:02}.mhi".format(*time.localtime()[:6])

    with open(s_dir + filename, "wb") as f:
        buf = memoryview(display.fbuf)
        f.write(b"MHI0")
        f.write(display.width.to_bytes(2, "little"))
        f.write(display.height.to_bytes(2, "little"))
        f.write(bytes([
            0x10 if getattr(display, "use_tiny_buf", False) else 0x01  # 0x10 = GS4, 0x01 = RGB565
        ]))

        for i in range(0, len(buf), 128):
            f.write(buf[i:i + 128])
