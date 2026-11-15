# Linux AFK Game Studio

An integrated automation environment and hardware-optimized sandbox for running background games (Roblox, Minecraft Bedrock, etc.) on Linux under X11 and Wayland (Hyprland, Sway, KDE, GNOME).

---

## Capabilities

1. **Hardware-Optimized Sandbox (Gamescope)**
   - Isolated X11 display session. The primary laptop cursor and keyboard remain completely free for typing, work, and browsing.
   - Configurable resolution presets (540p, 720p, 900p, 1080p) and frame rate caps (10, 15, 20, 30, 60 FPS) to minimize CPU/GPU draw and battery consumption during long AFK sessions.
   - Built-in NVIDIA explicit sync and composition workarounds to eliminate flickering.
   - Relative 3D camera look mode (`--force-grab-cursor`) toggleable via `Super + G`.

2. **TinyTask Macro Engine**
   - Direct kernel event recorder via Linux `evdev` supporting mouse movement, clicks, and keyboard strokes without XRecord limitations.
   - Sub-millisecond C playback engine (`tinytask-play`) using XTest.
   - Named profile management (`.rec` files) and configurable speed multipliers (0.5x, 1x, 1.5x, 2x, 4x).

3. **AutoClicker**
   - Millisecond-precision click intervals.
   - Button selection (Left, Right, Middle) and click type (Single, Double).
   - Dynamic location (current cursor position) or fixed target coordinates (X, Y).

4. **AutoHotkey (.ahk) & Scripting Engine**
   - Built-in line-by-line interpreter for common AHK v1/v2 commands (`Click`, `Sleep`, `Send`, `Loop`, `MouseMove`).
   - Integrated editor with preset anti-AFK templates (camera jiggle, jump-step, click loops).
   - Python scripting support with standard xdotool bindings.

5. **Global System Hotkeys**
   - `F8`: Toggle Macro Recording
   - `F9`: Toggle Macro Playback
   - `F10`: Toggle AutoClicker
   - `Super + G`: Toggle Mouse Lock / Release

---

## Dependencies

### Arch Linux / CachyOS / Manjaro
```bash
sudo pacman -S gamescope gcc python-gobject python-evdev libxtst libx11 xdotool
```

### Ubuntu / Debian / Pop!_OS
```bash
sudo apt update
sudo apt install gamescope gcc python3-gi python3-evdev libxtst-dev libx11-dev xdotool
```

### Fedora
```bash
sudo dnf install gamescope gcc python3-gobject python3-evdev libXtst-devel libX11-devel xdotool
```

> **Input Permissions (evdev):**  
> To record events without root privileges, ensure your user belongs to the `input` group:
> ```bash
> sudo usermod -aG input $USER
> ```
> Log out and log back in for changes to take effect.

---

## Installation

```bash
git clone https://github.com/RikiDeh/linux-afk-hub.git
cd linux-afk-hub
chmod +x install.sh
./install.sh
```

Launch the application:
```bash
afk-hub
```

---

## Project Structure

```text
linux-afk-hub/
├── install.sh             # Build and installation script
├── README.md              # Technical reference and usage documentation
├── assets/
│   └── afk-hub.desktop    # Desktop application entry
└── src/
    ├── afk-hub.py         # Main GTK3 interface and orchestration runtime
    ├── ahk_engine.py      # AutoHotkey parser and execution engine
    ├── tinytask-rec.py    # Linux evdev input recorder
    └── tinytask-play.c    # Low-overhead C playback binary
```
