<p align="center">
  <a href="https://github.com/echo-lalia/MicroHydra-Apps" alt="Apps">
    <img src="https://img.shields.io/badge/Apps-d66e28" /></a>
  &nbsp;&nbsp;
  <a href="https://github.com/echo-lalia/microhydra-frozen" alt="Firmware">
    <img src="https://img.shields.io/badge/Firmware-d66e28" /></a>
  &nbsp;&nbsp;
  <a href="https://github.com/echo-lalia/Cardputer-MicroHydra/wiki" alt="Wiki">
    <img src="https://img.shields.io/badge/Wiki-b63532" /></a>
  &nbsp;&nbsp;
  <a href="https://github.com/echo-lalia/Cardputer-MicroHydra?tab=GPL-3.0-1-ov-file" alt="License">
    <img src="https://img.shields.io/github/license/echo-lalia/Cardputer-MicroHydra?labelColor=47102a&color=8d1f52" /></a>
  &nbsp;&nbsp;
  <a href="https://github.com/echo-lalia/Cardputer-MicroHydra" alt="Stars">
    <img src="https://img.shields.io/github/stars/echo-lalia/Cardputer-MicroHydra?style=flat&labelColor=47102a&color=8d1f52" /></a>
  &nbsp;&nbsp;
  <a href="https://discord.gg/6e4KUDpgQC" alt="Discord">
    <img src="https://img.shields.io/discord/1279691612099973151?logo=discord&logoColor=c86744&label=Discord&labelColor=300f2d&color=621e5a" /></a>
  &nbsp;&nbsp;
  <a href="https://ko-fi.com/ethanlacasse" alt="Ko-Fi">
    <img src="https://img.shields.io/badge/Support_MicroHydra-4c1b52?logo=kofi&logoColor=b63532" /></a>
</p>

---

# ExtraHydra

> ⚡ **ExtraHydra** is a custom fork of [MicroHydra](https://github.com/echo-lalia/Cardputer-MicroHydra), enhanced with additional features, mods, and UI improvements. It retains full compatibility with MicroHydra apps while extending core functionality.

<p align="center">
  <img src="https://i.ibb.co/nNMRWBjj/Frame-2-1.png" alt="ExtraHydra Banner"/>
</p>

---

## 🚀 Overview

ExtraHydra is a lightweight app launcher built on MicroPython (v1.23) for the ESP32-S3. It acts as an "OS-lite" for Cardputer-style devices.

* 🔁 Switch between apps seamlessly
* 📂 Auto-loads from `/apps` on internal flash or SD
* ⚡ Supports both `.py` and compiled `.mpy` apps
* 🧩 Enhanced UI, mod system, and custom hooks
* 📱 Clean separation of launcher and app runtime

Python scripts can be dropped into the `/apps` folder on your device's flash or SD card. On startup, ExtraHydra scans both locations to build the app list.

Take a look at the [Wiki](https://github.com/echo-lalia/Cardputer-MicroHydra/wiki) for guides, and check [MicroHydra-Apps](https://github.com/echo-lalia/MicroHydra-Apps) for community apps.

---

## 🧠 How It Works

ExtraHydra runs only one app at a time. To ensure clean memory and prevent import conflicts, it uses:

* 🧠 RTC memory to store app path and optional args
* 🔄 Full MicroPython reboot on every app switch
* 🪝 `hydra.loader` module to set and fetch state

When the system reboots, `main.py` reads the stored path from RTC. If valid, the target app is loaded; otherwise, the launcher UI starts.

> Example: The Files app sets the target file and the editor path in RTC. When the system reboots, the editor reads those args to open the file immediately.

If ExtraHydra is frozen into the firmware or precompiled as `.mpy`, rebooting into apps is fast and memory-efficient.

---

## 📦 Installing Apps

To add apps:

* Place a `.py`, `.mpy`, or app folder with `__init__.py` into `/apps`
* Works on both internal flash and microSD
* Apps appear automatically in the launcher

Apps can be simple single-file scripts or complex folders. Both formats are supported.

Want examples? Check:

* [Community Apps](https://github.com/echo-lalia/MicroHydra-Apps)
* [App Format Docs](https://github.com/echo-lalia/MicroHydra/wiki/App-Format)

You can also use the built-in **GetApps** app to browse and install packages over serial or Wi-Fi.

---

## 🔧 Installation Options

### 1. 🧩 MicroPython-Based Installation

* Flash regular MicroPython to your device (via Thonny or esptool)
* Extract `DEVICENAME_compiled.zip` or `raw.zip`
* Upload contents to the device root

> ⚠️ Raw `.py` files are editable and ideal for dev, but more prone to memory issues. Use compiled `.mpy` when not debugging.

### 2. 💾 Flash ExtraHydra Firmware

* Download `DEVICENAME.bin` from Releases
* Flash with [M5Burner](https://shop.m5stack.com/pages/download) or Thonny
* Ensure the device is in bootloader mode (hold G0 while connecting)

> ✅ This is the fastest, cleanest install method — includes frozen ExtraHydra launcher and built-in apps

---

## 🛠 Developer Notes

ExtraHydra uses a modular build system. If you're building from source:

* The `src/` folder must be preprocessed for your hardware
* Use the [multi-platform wiki guide](https://github.com/echo-lalia/MicroHydra/wiki/multi-platform) to prepare builds
* Supports `.mpy` bytecode compilation, asset packing, and OTA patching (coming soon)

---

## 💬 Community & Support

* 🤝 [Join the Discord](https://discord.gg/6e4KUDpgQC) — feedback, support, and updates
* 📦 [Browse Community Apps](https://github.com/echo-lalia/MicroHydra-Apps)
* ☕ [Support the original author](https://ko-fi.com/ethanlacasse) of MicroHydra

---