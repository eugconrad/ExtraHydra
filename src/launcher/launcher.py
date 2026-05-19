# import math
import os
import time
# from array import array
from machine import Timer
from micropython import const

import machine

from font import vga2_16x32
from hydra import beeper, loader, ntp
from hydra.config import Config
from hydra.i18n import I18n
from lib.hydra.idle import IdleManager
from lib import battlevel, display, sdcard, userinput, wifi

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ _CONSTANTS: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
_MAX_WIFI_ATTEMPTS = const(1000)
_MAX_NTP_ATTEMPTS = const(10)
_MH_DISPLAY_BACKLIGHT = const(38)
_MAX_VISIBLE_APPS = const(4)

_TRANS = const("""[
    {"en": "Files", "zh": "文件", "ja": "ファイル", "ru": "Файлы", "uk": "Файли"},
    {"en": "Terminal", "zh": "终端", "ja": "端末", "ru": "Терминал", "uk": "Термінал"},
    {"en": "Reload Apps", "zh": "重新加载应用", "ja": "アプリ再読", "ru": "Перезагрузить приложения", "uk": "Перезавантажити додатки"},
    {"en": "Settings", "zh": "设置", "ja": "設定", "ru": "Настройки", "uk": "Налаштування"},
    {"en": "Get Apps", "zh": "应用商店", "ja": "アプリストア", "ru": "Приложения", "uk": "Додатки"},
    {"en": "Press ENT to find apps", "zh": "按ENT键查找应用", "ja": "ENTを押してアプリを検索", "ru": "Нажмите ENT для поиска", "uk": "Натисніть ENT для пошуку"}
]""")

# bump up our clock speed so the UI feels smoother
# (240mhz is the max officially supported, but the default is 160mhz)
machine.freq(240_000_000)


class BrightnessManager:
    def __init__(self):
        self._target = CONFIG["brightness"]
        self._current = CONFIG["brightness"]
        self._step = 0

    def update(self):
        if self._current != self._target:
            step = 1 if self._target > self._current else -1
            self._current += step
            DISPLAY.set_brightness(self._current)
            return True
        return False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ GLOBALS: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
APP_NAMES = None
APP_PATHS = None
FILTERED_APPS = None

CURRENT_INPUT = ""
SELECTED_INDEX = 0
SCROLL_OFFSET = 0
CACHE = dict()

SHOW_MENU = False
WALLPAPER = None

CONFIG = Config()
DISPLAY = display.Display(use_tiny_buf=True)
KB = userinput.UserInput()
SD = sdcard.SDCard()
WIFI = wifi.WiFiManager()
NTP = ntp.TimeSync()

BEEP = beeper.Beeper()

BATT = battlevel.Battery()
I18N = I18n(_TRANS)
IDLE = IdleManager()
BRIGHTNESS = BrightnessManager()


def update_cache():
    global CACHE

    CACHE = {
        "batt_pct": BATT.read_pct(),
        "wifi_is_connected": WIFI.is_connected(),
    }


def create_wallpaper(filepath):
    if not filepath:
        return None
    try:
        with open(filepath, "rb") as f:
            if f.read(4) != b"MHI0":
                return None
            w, h = int.from_bytes(f.read(2), "little"), int.from_bytes(f.read(2), "little")
            format_byte = f.read(1)[0]
            if format_byte != 0x10:
                return None
            f.seek(9)  # Skip header
            return {
                'buffer': bytearray(f.read()),
                'w': w, 'h': h, 'x': (DISPLAY.width - w) // 2, 'y': (DISPLAY.height - h) // 2
            }

    except Exception:
        return None


def scan_apps():
    global APP_NAMES, APP_PATHS
    SD.mount()
    main_directory = os.listdir("/")
    sd_directory = []

    if "sd" in main_directory:
        sd_directory = os.listdir("/sd")
    if "apps" not in main_directory:
        os.mkdir("/apps")
    if "apps" not in sd_directory and "sd" in main_directory:
        os.mkdir("/sd/apps")

    main_app_list = list(os.ilistdir("/apps"))
    sd_app_list = []
    if "sd" in main_directory:
        try:
            sd_app_list = list(os.ilistdir("/sd/apps"))
        except OSError:
            os.umount('/sd')

    app_names = []
    app_paths = {}
    for entry in main_app_list:
        this_name, this_path = get_app_paths(entry, "/apps/")
        if this_name:
            app_names.append(this_name.replace('.cli', ''))
            app_paths[this_name] = this_path
    for entry in sd_app_list:
        this_name, this_path = get_app_paths(entry, "/sd/apps/")
        if this_name:
            app_names.append(this_name.replace('.cli', ''))
            app_paths[this_name] = this_path

    app_names.sort(key=lambda x: x.lower())
    # app_names += ["Files", "Terminal", "Reload Apps", "UI Sound", "Settings", "Get Apps"]
    app_names += ["Files", "Terminal", "Reload Apps", "Settings", "Get Apps"]
    # add paths for built-in apps
    # mh_if frozen:
    # app_paths.update({
    #     "Files": ".frozen/launcher/files",
    #     "Terminal": ".frozen/launcher/terminal",
    #     "Settings": ".frozen/launcher/settings",
    #     "Get Apps": ".frozen/launcher/getapps",
    #     })
    # mh_else:
    app_paths.update({
        "Files": "/launcher/files",
        "Terminal": "/launcher/terminal",
        "Settings": "/launcher/settings",
        "Get Apps": "/launcher/getapps",
    })
    # mh_end_if
    APP_NAMES = app_names
    APP_PATHS = app_paths


def get_app_paths(ientry, current_dir):
    _DIR_FLAG = 16384
    _FILE_FLAG = 32768
    entry = ientry[0]
    is_dir = (ientry[1] == _DIR_FLAG)
    if entry.endswith(".py"):
        return entry[:-3], current_dir + entry
    if entry.endswith(".mpy"):
        return entry[:-4], current_dir + entry
    if is_dir:
        dir_content = os.listdir(current_dir + entry)
        if "__init__.py" in dir_content or "__init__.mpy" in dir_content:
            return entry, current_dir + entry
    return None, None


def launch_app(app_path):
    if app_path.endswith(".cli.py"):
        loader.launch_app(APP_PATHS['Terminal'], f"${app_path}")
    loader.launch_app(app_path)


def filter_apps(search_text):
    global FILTERED_APPS, SELECTED_INDEX, SHOW_MENU, SCROLL_OFFSET
    SHOW_MENU = True
    if not search_text:
        FILTERED_APPS = [app for app in APP_NAMES]
    else:
        search_lower = search_text.lower()
        FILTERED_APPS = [app for app in APP_NAMES if search_lower in app.lower()]
    SELECTED_INDEX = 0
    SCROLL_OFFSET = 0


def draw_wallpaper():
    if isinstance(WALLPAPER, dict):
        DISPLAY.blit_buffer(
            WALLPAPER['buffer'],
            WALLPAPER['x'], WALLPAPER['y'], WALLPAPER['w'], WALLPAPER['h'],
        )
    else:
        DISPLAY.fill(DISPLAY.palette[2])


def draw_desktop():
    # DISPLAY.text("(DEV MODE)", 6, 50, DISPLAY.palette[0])
    # DISPLAY.text("(DEV MODE)", 4, 48, DISPLAY.palette[7])

    if not SHOW_MENU:
        text = I18N["Press ENT to find apps"]
        DISPLAY.text(text, DISPLAY.width // 2 - DISPLAY.get_total_width(text) // 2, DISPLAY.height - 12,
                     DISPLAY.palette[4])


def draw_conky():
    yyyy, mm, dd, h, m = time.localtime()[:5]
    text = "{:02}:{:02}{:02}.{:02}.{:04}".format(h, m, dd, mm, yyyy)
    DISPLAY.text(text[:5], 6, 6, DISPLAY.palette[0], font=vga2_16x32)
    DISPLAY.text(text[:5], 4, 4, DISPLAY.palette[7], font=vga2_16x32)
    DISPLAY.text(text[5:], 6, 38, DISPLAY.palette[0])
    DISPLAY.text(text[5:], 4, 36, DISPLAY.palette[7])

    text = f"Bat: {CACHE.get('batt_pct')}%"
    DISPLAY.text(text, DISPLAY.width - 4 - DISPLAY.get_total_width(text), 4, DISPLAY.palette[7])

    text = f"WIFI: {CACHE.get('wifi_is_connected')}"
    DISPLAY.text(text, DISPLAY.width - 4 - DISPLAY.get_total_width(text), 16, DISPLAY.palette[7])


def draw_dmenu():
    global SCROLL_OFFSET

    if SELECTED_INDEX < SCROLL_OFFSET:
        SCROLL_OFFSET = SELECTED_INDEX
    elif SELECTED_INDEX >= SCROLL_OFFSET + _MAX_VISIBLE_APPS:
        SCROLL_OFFSET = SELECTED_INDEX - _MAX_VISIBLE_APPS + 1

    x, y = 10, 10
    w = DISPLAY.width - x * 2

    margin = 4
    row_h = 16
    input_height = 24
    font_offset_y = 3

    visible_apps = FILTERED_APPS[SCROLL_OFFSET:SCROLL_OFFSET + _MAX_VISIBLE_APPS]
    num_rows = max(len(visible_apps), _MAX_VISIBLE_APPS)
    total_height = input_height + margin + num_rows * row_h + margin

    DISPLAY.fill_rect(x, y, w, total_height, DISPLAY.palette[4])
    DISPLAY.rect(x, y, w, total_height, DISPLAY.palette[6])

    prompt = "run: "
    prompt_width = len(prompt) * 8
    max_text_width = w - margin * 2 - prompt_width
    max_chars = max_text_width // 8

    clipped_input = CURRENT_INPUT[-max_chars:]
    input_text = prompt + clipped_input
    DISPLAY.text(input_text, x + margin, y + margin, DISPLAY.palette[8])
    DISPLAY.hline(x + margin, y + input_height, w - margin * 2, DISPLAY.palette[6])

    total_items = len(FILTERED_APPS)

    for idx, app_name in enumerate(visible_apps):
        actual_idx = SCROLL_OFFSET + idx
        y_pos = y + input_height + margin + idx * row_h

        is_selected = (actual_idx == SELECTED_INDEX)
        bg_color = DISPLAY.palette[5] if is_selected else DISPLAY.palette[4]
        text_color = DISPLAY.palette[8] if is_selected else DISPLAY.palette[7]

        DISPLAY.fill_rect(
            x + margin, y_pos, w - margin * 2 - (6 if total_items > _MAX_VISIBLE_APPS else 0), row_h, bg_color
        )
        DISPLAY.text(I18N[app_name], x + margin * 2, y_pos + font_offset_y, text_color)

    if total_items > _MAX_VISIBLE_APPS:
        bar_x = x + w - margin - 4
        bar_y = y + input_height + margin
        bar_h = num_rows * row_h
        scrollbar_height = int(bar_h * (_MAX_VISIBLE_APPS / total_items))
        scrollbar_y = bar_y + int((bar_h - scrollbar_height) * (SCROLL_OFFSET / (total_items - _MAX_VISIBLE_APPS)))

        DISPLAY.fill_rect(bar_x, bar_y, 4, bar_h, DISPLAY.palette[3])
        DISPLAY.fill_rect(bar_x, scrollbar_y, 4, scrollbar_height, DISPLAY.palette[6])


def handle_input(new_keys):
    global CURRENT_INPUT, SELECTED_INDEX, SHOW_MENU

    for key in new_keys:
        if len(key) == 1 and key.lower() in 'abcdefghijklmnopqrstuvwxyz1234567890':
            BEEP.play("G3", time_ms=20)
            CURRENT_INPUT += key
            filter_apps(CURRENT_INPUT)

        elif key == "BSPC" and CURRENT_INPUT:
            BEEP.play("B3", time_ms=20)
            CURRENT_INPUT = CURRENT_INPUT[:-1]
            filter_apps(CURRENT_INPUT)

        elif key == "UP":
            BEEP.play(("B3", "D3"), time_ms=30)
            SELECTED_INDEX = max(0, SELECTED_INDEX - 1)

        elif key == "DOWN":
            BEEP.play(("G3", "B3"), time_ms=30)
            SELECTED_INDEX = min(len(FILTERED_APPS) - 1, SELECTED_INDEX + 1)

        elif key == "ENT" and not SHOW_MENU:
            BEEP.play(("G3", "B3", "D3"), time_ms=30)
            filter_apps("")

        elif key == "`" or key == "ESC":
            # BEEP.play((("C3", "E3", "D3"), "D4", "C4"), time_ms=100)
            CURRENT_INPUT = ""
            SELECTED_INDEX = 0
            SHOW_MENU = False

        elif key == "ENT" and FILTERED_APPS and SHOW_MENU:
            selected_app = FILTERED_APPS[SELECTED_INDEX]

            # special "settings" app options will have their own behaviour, otherwise launch the app
            if selected_app == "UI Sound":
                CONFIG['ui_sound'] = not CONFIG['ui_sound']

                if CONFIG['ui_sound'] == 0:  # currently muted, then unmute
                    BEEP.play(("C3", "E3", "G3", ("C4", "E4", "G4"), ("C4", "E4", "G4")), 80)

            elif selected_app == "Reload Apps":
                CURRENT_INPUT = ""
                SELECTED_INDEX = 0
                scan_apps()

                BEEP.play(('C4', 'E4', 'G4'), 80)

            else:  # ~~~~~~~~~~~~~~~~~~~ LAUNCH THE APP! ~~~~~~~~~~~~~~~~~~~~

                # save CONFIG if it has been changed:
                CONFIG.save()

                # shut off the display
                DISPLAY.fill(0)
                DISPLAY.sleep_mode(True)
                machine.Pin(_MH_DISPLAY_BACKLIGHT, machine.Pin.OUT).value(0)  # backlight off
                DISPLAY.spi.deinit()

                if SD is not None:
                    try:
                        SD.deinit()
                    except:
                        print("Tried to deinit SDCard, but failed.")

                launch_app(APP_PATHS[selected_app])


def preloader():
    global WALLPAPER

    from lib.hydra.simpleterminal import SimpleTerminal
    term = SimpleTerminal()

    try:
        # WIFI
        if not WIFI.is_connected():
            term.print("  Connecting to WiFi...")
            WIFI.connect()

        if WIFI.is_connected():
            term.print(f"+ Connected to {WIFI.config['wifi_ssid']}")
        else:
            term.print("! No connection")

        # SD card
        if "sd" not in os.listdir("/"):
            term.print("  Initializing storage...")
            SD.mount()

        if "sd" in os.listdir("/"):
            term.print("+ SD card mounted")
        else:
            term.print("! SD card not mounted")

        # Apps
        term.print("  Scanning applications...")
        scan_apps()
        term.print(f"+ Found {len(APP_NAMES)} apps")

        # Time
        term.print("  Synchronizing time...")
        if not (WIFI.is_connected() and time.localtime()[0] == 2000 and CONFIG['sync_clock']):
            term.print("~ Time sync skipped")
        else:
            try:
                NTP.safe_sync()
                y, m, d, hh, mm, *_ = time.localtime()
                term.print(f"+ {hh:02d}:{mm:02d} {d:02d}.{m:02d}.{y}")
            except Exception as e:
                term.print(f"! Time sync failed: {str(e)}")

        # Wallpaper
        term.print("  Loading wallpaper...")
        wallpaper_path = CONFIG.config.get("wp_image")
        if not wallpaper_path:
            term.print("~ Using default background")
        else:
            try:
                WALLPAPER = create_wallpaper(wallpaper_path)
                if WALLPAPER:
                    term.print(f"+ Loaded {wallpaper_path}")
                else:
                    term.print("! Invalid wallpaper")
            except Exception as e:
                term.print(f"! Wallpaper loading failed: {str(e)}")

        update_cache()

    except Exception as e:
        term.print(f"! Fatal error: {str(e)}")
        term.print("! System may not work properly")

    del term


def dim_screen(_):
    BRIGHTNESS._target = 1


def restore_brightness(_):
    BRIGHTNESS._target = CONFIG["brightness"]


def main_loop():
    preloader()

    update_timer = Timer(-1)
    update_timer.init(period=5000, mode=Timer.PERIODIC, callback=lambda _: update_cache())

    IDLE.add_handler(20_000, dim_screen, restore_brightness)

    while True:
        new_keys = KB.get_new_keys()
        KB.ext_dir_keys(new_keys)

        if new_keys:
            handle_input(new_keys)
            IDLE.reset()
        else:
            IDLE.update()

        draw_wallpaper()
        draw_desktop()
        draw_conky()

        if SHOW_MENU:
            draw_dmenu()

        BRIGHTNESS.update()
        DISPLAY.show()


main_loop()
