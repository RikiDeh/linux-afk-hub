#!/usr/bin/env python3
"""
Linux AFK Game Studio & Automation Hub (Production-Grade & Anti-Slop)
Features:
- Gamescope sandbox manager (Dynamic display resolution, FPS limiting, NVIDIA composition fix)
- TinyTask Macro Engine (evdev precision recorder & XTest playback) with Profile Library
- OP AutoClicker Engine (ms precision, button selector, click type, fixed/dynamic coordinates)
- AutoHotkey (.ahk) & Scripting Engine with built-in templates
- Global Background Hotkeys (F8 Record, F9 Play, F10 AutoClick) via evdev
- Live Telemetry Dashboard & Active State Management
"""

import sys
import os
import re
import json
import time
import signal
import select
import threading
import subprocess

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

# Resolusi path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from ahk_engine import run_ahk

CONFIG_DIR = os.path.expanduser("~/.config/afk-hub")
MACROS_DIR = os.path.join(CONFIG_DIR, "macros")
SCRIPTS_DIR = os.path.join(CONFIG_DIR, "scripts")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DISPLAY_IPC_FILE = "/tmp/afk_gamescope_display.txt"

os.makedirs(MACROS_DIR, exist_ok=True)
os.makedirs(SCRIPTS_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "games": [
        {"name": "Roblox (Sober Flatpak)", "cmd": "flatpak run org.vinegarhq.Sober", "grab": True},
        {"name": "Minecraft Bedrock (Flatpak)", "cmd": "flatpak run io.mrarm.mcpelauncher", "grab": True},
        {"name": "Dawn Launcher", "cmd": "flatpak run gg.dawn.Launcher", "grab": False}
    ],
    "selected_game": 0,
    "resolution": "960x540",
    "fps": 15,
    "active_macro": "default.rec",
    "clicker": {
        "interval_ms": 100,
        "button": "Left",
        "click_type": "Single",
        "repeat_infinite": True,
        "repeat_count": 100,
        "location": "Current",
        "x": 0,
        "y": 0
    }
}

RESOLUTIONS = [
    ("800x450", "800x450 — Ultra Low (Hemat Daya Ekstrem)"),
    ("960x540", "960x540 — Balanced (Rekomendasi AFK)"),
    ("1280x720", "1280x720 — HD 720p (Standar)"),
    ("1600x900", "1600x900 — 900p (Detail)"),
    ("1920x1080", "1920x1080 — Full HD (Maksimal)")
]

FPS_OPTIONS = [
    (10, "10 FPS — Ultra Low (Laptop Dingin & Sunyi)"),
    (15, "15 FPS — AFK Rekomendasi"),
    (20, "20 FPS — Halus & Hemat"),
    (30, "30 FPS — Standar Gaming"),
    (60, "60 FPS — Normal")
]

CSS_THEME = b"""
/* Antislop Design Token: Deep Neutral Tone, Accessible Hierarchy, Restrained Accent */
window {
    background-color: #14161b;
    color: #e2e4ea;
    font-family: 'Inter', 'Adwaita Sans', system-ui, sans-serif;
    font-size: 13px;
}

/* Headerbar / App Shell */
.top-shell {
    background: #1a1d24;
    border-bottom: 1px solid #282c37;
    padding: 10px 16px;
}

.brand-title {
    font-weight: 700;
    font-size: 15px;
    color: #f0f2f7;
    letter-spacing: -0.01em;
}

.status-badge {
    padding: 3px 10px;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.02em;
}
.badge-idle { background: #232732; color: #8d94a5; }
.badge-active { background: #133a28; color: #4ade80; border: 1px solid #1f6844; }
.badge-record { background: #451a1a; color: #f87171; border: 1px solid #772b2b; }

/* Cards & Sections */
.studio-card {
    background: #1a1d24;
    border: 1px solid #282c37;
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 10px;
}

.section-title {
    font-size: 11px;
    font-weight: 700;
    
    letter-spacing: 0.06em;
    color: #8b92a2;
    margin-bottom: 10px;
}

/* Notebook / Tabs */
notebook {
    background: transparent;
    border: none;
}
notebook tab {
    padding: 8px 16px;
    font-weight: 600;
    color: #8b92a2;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
}
notebook tab:checked {
    color: #60a5fa;
    border-bottom: 2px solid #3b82f6;
}

/* Controls & Buttons */
button {
    background: #232732;
    color: #e2e4ea;
    border: 1px solid #323846;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    transition: all 120ms ease-out;
}
button:hover {
    background: #2b303d;
    border-color: #3e4555;
}
button:active {
    background: #1c202a;
}
button:disabled {
    opacity: 0.45;
}

.btn-primary {
    background: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
}
.btn-primary:hover {
    background: #1d4ed8;
}

.btn-danger {
    background: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
}
.btn-danger:hover {
    background: #b91c1c;
}

.btn-success {
    background: #16a34a;
    color: #ffffff;
    border: 1px solid #22c55e;
}
.btn-success:hover {
    background: #15803d;
}

/* Inputs & Comboboxes */
entry, spinbutton {
    background: #14161b;
    color: #e2e4ea;
    border: 1px solid #2d323e;
    border-radius: 6px;
    padding: 6px 10px;
}
entry:focus, spinbutton:focus {
    border-color: #3b82f6;
}

combobox button {
    background: #14161b;
    border: 1px solid #2d323e;
    color: #e2e4ea;
    padding: 4px 10px;
}

/* Telemetry Footer */
.telemetry-bar {
    background: #111317;
    border-top: 1px solid #20232c;
    padding: 8px 16px;
    font-size: 12px;
    color: #8b92a2;
}
"""

class AFKStudioApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Linux AFK Game Studio")
        self.set_default_size(720, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(0)

        self.load_config()

        # State runtime
        self.game_proc = None
        self.rec_proc = None
        self.play_thread = None
        self.clicker_thread = None
        self.script_thread = None
        
        self.is_recording = False
        self.is_playing = False
        self.is_clicker_running = False
        self.is_script_running = False

        self.target_display = ":3"
        self.afk_start_time = None
        self.loop_count = 0

        # Load Styling
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_THEME)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.build_ui()
        self.start_background_watcher()
        self.start_hotkey_listener()

    def load_config(self):
        self.config = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config.update(json.load(f))
            except Exception:
                pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)

        # 1. TOP SHELL (Header & Active Instance Badge)
        top_shell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        top_shell.get_style_context().add_class("top-shell")

        title_lbl = Gtk.Label(label="AFK Game Studio & Automation")
        title_lbl.get_style_context().add_class("brand-title")
        top_shell.pack_start(title_lbl, False, False, 0)

        # Global Hotkeys Helper Pill
        hotkeys_pill = Gtk.Label(label="Hotkeys: [F8] Rec | [F9] TinyTask | [F10] Clicker | [Super+G] Mouse Lock")
        hotkeys_pill.set_margin_start(16)
        hotkeys_pill.get_style_context().add_class("badge-idle")
        top_shell.pack_start(hotkeys_pill, False, False, 0)

        self.badge_status = Gtk.Label(label="SANDBOX IDLE")
        self.badge_status.get_style_context().add_class("status-badge")
        self.badge_status.get_style_context().add_class("badge-idle")
        top_shell.pack_end(self.badge_status, False, False, 0)

        root.pack_start(top_shell, False, False, 0)

        # SCROLLABLE CONTENT BODY
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_margin_top(12)
        body.set_margin_bottom(12)
        body.set_margin_start(16)
        body.set_margin_end(16)
        scroll.add(body)
        root.pack_start(scroll, True, True, 0)

        # 2. SECTION: GAME INSTANCE LAUNCHER
        card_launcher = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_launcher.get_style_context().add_class("studio-card")

        card_title = Gtk.Label(label="Game Sandbox & Hardware Optimizer")
        card_title.get_style_context().add_class("section-title")
        card_title.set_halign(Gtk.Align.START)
        card_launcher.pack_start(card_title, False, False, 0)

        grid_cfg = Gtk.Grid()
        grid_cfg.set_column_spacing(12)
        grid_cfg.set_row_spacing(8)

        # Game combo
        lbl_game = Gtk.Label(label="Target Game:")
        lbl_game.set_halign(Gtk.Align.START)
        grid_cfg.attach(lbl_game, 0, 0, 1, 1)

        self.cmb_game = Gtk.ComboBoxText()
        for g in self.config["games"]:
            self.cmb_game.append_text(g["name"])
        self.cmb_game.append_text("➕ Tambah Custom Command...")
        self.cmb_game.set_active(min(self.config.get("selected_game", 0), len(self.config["games"])))
        self.cmb_game.connect("changed", self.on_game_selection_changed)
        grid_cfg.attach(self.cmb_game, 1, 0, 1, 1)

        # Resolution combo
        lbl_res = Gtk.Label(label="Resolusi:")
        lbl_res.set_halign(Gtk.Align.START)
        grid_cfg.attach(lbl_res, 2, 0, 1, 1)

        self.cmb_res = Gtk.ComboBoxText()
        for key, text in RESOLUTIONS:
            self.cmb_res.append_text(text)
        current_res = self.config.get("resolution", "960x540")
        res_keys = [k for k, _ in RESOLUTIONS]
        self.cmb_res.set_active(res_keys.index(current_res) if current_res in res_keys else 1)
        grid_cfg.attach(self.cmb_res, 3, 0, 1, 1)

        # FPS combo
        lbl_fps = Gtk.Label(label="Frame Rate:")
        lbl_fps.set_halign(Gtk.Align.START)
        grid_cfg.attach(lbl_fps, 0, 1, 1, 1)

        self.cmb_fps = Gtk.ComboBoxText()
        for val, text in FPS_OPTIONS:
            self.cmb_fps.append_text(text)
        current_fps = self.config.get("fps", 15)
        fps_vals = [v for v, _ in FPS_OPTIONS]
        self.cmb_fps.set_active(fps_vals.index(current_fps) if current_fps in fps_vals else 1)
        grid_cfg.attach(self.cmb_fps, 1, 1, 1, 1)

        # Options check
        self.chk_grab = Gtk.CheckButton(label="Relative 3D Camera Look")
        self.chk_grab.set_active(True)
        grid_cfg.attach(self.chk_grab, 2, 1, 2, 1)

        # Custom Entry (hidden by default)
        self.ent_custom = Gtk.Entry()
        self.ent_custom.set_placeholder_text("Ketik executable path atau command (contoh: wine /path/to/game.exe)")
        self.ent_custom.set_no_show_all(True)
        grid_cfg.attach(self.ent_custom, 0, 2, 4, 1)

        card_launcher.pack_start(grid_cfg, False, False, 0)

        # Action Button Row
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_launch = Gtk.Button(label="⚡ Luncurkan Game Terisolasi")
        self.btn_launch.get_style_context().add_class("btn-primary")
        self.btn_launch.connect("clicked", self.toggle_game_instance)
        btn_box.pack_start(self.btn_launch, True, True, 0)

        card_launcher.pack_start(btn_box, False, False, 4)
        body.pack_start(card_launcher, False, False, 0)

        # 3. SECTION: NOTEBOOK AUTOMATION MODES
        card_modes = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_modes.get_style_context().add_class("studio-card")

        notebook = Gtk.Notebook()
        card_modes.pack_start(notebook, True, True, 0)

        # TAB 1: TinyTask Macro
        tab_tinytask = self.build_tinytask_tab()
        notebook.append_page(tab_tinytask, Gtk.Label(label="🔴 TinyTask Recorder"))

        # TAB 2: Dedicated AutoClicker
        tab_clicker = self.build_clicker_tab()
        notebook.append_page(tab_clicker, Gtk.Label(label="⚡ AutoClicker"))

        # TAB 3: Script & AHK Engine
        tab_script = self.build_script_tab()
        notebook.append_page(tab_script, Gtk.Label(label="📜 AutoHotkey & Script"))

        body.pack_start(card_modes, True, True, 0)

        # 4. TELEMETRY STATUS BAR (Footer)
        telemetry = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        telemetry.get_style_context().add_class("telemetry-bar")

        self.lbl_telemetry_time = Gtk.Label(label="AFK Duration: 00:00:00")
        telemetry.pack_start(self.lbl_telemetry_time, False, False, 0)

        self.lbl_telemetry_loops = Gtk.Label(label=" | Loops: 0")
        telemetry.pack_start(self.lbl_telemetry_loops, False, False, 0)

        self.lbl_telemetry_disp = Gtk.Label(label=f" | Active Display: {self.target_display}")
        telemetry.pack_start(self.lbl_telemetry_disp, False, False, 0)

        self.lbl_telemetry_msg = Gtk.Label(label="Siap. Luncurkan game untuk memulai.")
        self.lbl_telemetry_msg.set_halign(Gtk.Align.END)
        telemetry.pack_end(self.lbl_telemetry_msg, True, True, 0)

        root.pack_end(telemetry, False, False, 0)

    # ----------------- TAB BUILDERS -----------------

    def build_tinytask_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(8)

        # Profile selection
        prof_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        prof_lbl = Gtk.Label(label="Macro Profile:")
        prof_box.pack_start(prof_lbl, False, False, 0)

        self.cmb_profile = Gtk.ComboBoxText()
        self.refresh_macro_profiles()
        self.cmb_profile.connect("changed", self.on_macro_profile_changed)
        prof_box.pack_start(self.cmb_profile, True, True, 0)

        btn_new_prof = Gtk.Button(label="➕ New")
        btn_new_prof.connect("clicked", self.create_new_macro_profile)
        prof_box.pack_start(btn_new_prof, False, False, 0)
        box.pack_start(prof_box, False, False, 0)

        # Main Record & Play Actions
        act_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        act_box.set_homogeneous(True)

        self.btn_rec = Gtk.Button(label="🔴 Record Gerakan (F8)")
        self.btn_rec.connect("clicked", self.toggle_record)
        act_box.pack_start(self.btn_rec, True, True, 0)

        self.btn_play = Gtk.Button(label="▶ Play Macro (F9)")
        self.btn_play.get_style_context().add_class("btn-success")
        self.btn_play.connect("clicked", self.toggle_play)
        act_box.pack_start(self.btn_play, True, True, 0)

        box.pack_start(act_box, False, False, 0)

        # Playback Options
        opt_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.chk_loop = Gtk.CheckButton(label="Continuous Loop (AFK)")
        self.chk_loop.set_active(True)
        opt_box.pack_start(self.chk_loop, False, False, 0)

        spd_lbl = Gtk.Label(label="Kecepatan:")
        opt_box.pack_start(spd_lbl, False, False, 0)

        self.cmb_speed = Gtk.ComboBoxText()
        for s in ["0.5x", "1x", "1.5x", "2x", "4x"]:
            self.cmb_speed.append_text(s)
        self.cmb_speed.set_active(1)
        opt_box.pack_start(self.cmb_speed, False, False, 0)

        box.pack_start(opt_box, False, False, 0)
        return box

    def build_clicker_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(8)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(8)

        # Interval
        lbl_int = Gtk.Label(label="Click Interval (ms):")
        lbl_int.set_halign(Gtk.Align.START)
        grid.attach(lbl_int, 0, 0, 1, 1)

        self.spn_interval = Gtk.SpinButton.new_with_range(1, 100000, 10)
        self.spn_interval.set_value(self.config["clicker"].get("interval_ms", 100))
        grid.attach(self.spn_interval, 1, 0, 1, 1)

        # Button (Left, Right, Middle)
        lbl_btn = Gtk.Label(label="Mouse Button:")
        lbl_btn.set_halign(Gtk.Align.START)
        grid.attach(lbl_btn, 2, 0, 1, 1)

        self.cmb_click_btn = Gtk.ComboBoxText()
        for b in ["Left", "Right", "Middle"]:
            self.cmb_click_btn.append_text(b)
        self.cmb_click_btn.set_active(0)
        grid.attach(self.cmb_click_btn, 3, 0, 1, 1)

        # Click Type
        lbl_type = Gtk.Label(label="Click Type:")
        lbl_type.set_halign(Gtk.Align.START)
        grid.attach(lbl_type, 0, 1, 1, 1)

        self.cmb_click_type = Gtk.ComboBoxText()
        for t in ["Single Click", "Double Click"]:
            self.cmb_click_type.append_text(t)
        self.cmb_click_type.set_active(0)
        grid.attach(self.cmb_click_type, 1, 1, 1, 1)

        # Location Type
        lbl_loc = Gtk.Label(label="Location:")
        lbl_loc.set_halign(Gtk.Align.START)
        grid.attach(lbl_loc, 2, 1, 1, 1)

        self.cmb_click_loc = Gtk.ComboBoxText()
        self.cmb_click_loc.append_text("Current Cursor Position")
        self.cmb_click_loc.append_text("Fixed Coordinate (X, Y)")
        self.cmb_click_loc.set_active(0)
        self.cmb_click_loc.connect("changed", self.on_click_loc_changed)
        grid.attach(self.cmb_click_loc, 3, 1, 1, 1)

        # Fixed X, Y entries
        self.lbl_x = Gtk.Label(label="X:")
        self.spn_x = Gtk.SpinButton.new_with_range(0, 3840, 1)
        self.lbl_y = Gtk.Label(label="Y:")
        self.spn_y = Gtk.SpinButton.new_with_range(0, 2160, 1)

        coord_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        coord_box.pack_start(self.lbl_x, False, False, 0)
        coord_box.pack_start(self.spn_x, False, False, 0)
        coord_box.pack_start(self.lbl_y, False, False, 0)
        coord_box.pack_start(self.spn_y, False, False, 0)
        self.coord_box = coord_box
        self.coord_box.set_no_show_all(True)
        grid.attach(coord_box, 2, 2, 2, 1)

        box.pack_start(grid, False, False, 0)

        # Clicker toggle button
        self.btn_clicker = Gtk.Button(label="⚡ Start AutoClicker (F10)")
        self.btn_clicker.get_style_context().add_class("btn-success")
        self.btn_clicker.connect("clicked", self.toggle_autoclicker)
        box.pack_start(self.btn_clicker, False, False, 4)

        return box

    def build_script_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8)

        # Template presets
        tpl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tpl_lbl = Gtk.Label(label="Script Template:")
        tpl_box.pack_start(tpl_lbl, False, False, 0)

        self.cmb_template = Gtk.ComboBoxText()
        self.cmb_template.append_text("Roblox: Anti-AFK Camera Jiggle (AHK)")
        self.cmb_template.append_text("Roblox: Jump & Forward Step (AHK)")
        self.cmb_template.append_text("Roblox: Mining AutoClick Loop (AHK)")
        self.cmb_template.append_text("Python: Advanced Logic Script")
        self.cmb_template.set_active(0)
        self.cmb_template.connect("changed", self.load_script_template)
        tpl_box.pack_start(self.cmb_template, True, True, 0)

        box.pack_start(tpl_box, False, False, 0)

        # Script text editor
        self.txt_script = Gtk.TextView()
        self.txt_script.set_wrap_mode(Gtk.WrapMode.NONE)
        self.txt_script.set_monospace(True)
        scroll_txt = Gtk.ScrolledWindow()
        scroll_txt.set_size_request(-1, 140)
        scroll_txt.add(self.txt_script)
        box.pack_start(scroll_txt, True, True, 0)

        # Run button
        self.btn_run_script = Gtk.Button(label="▶ Jalankan Script / AHK")
        self.btn_run_script.get_style_context().add_class("btn-primary")
        self.btn_run_script.connect("clicked", self.toggle_script_run)
        box.pack_start(self.btn_run_script, False, False, 0)

        self.load_script_template(self.cmb_template)
        return box

    # ----------------- EVENT HANDLERS & LOGIC -----------------

    def on_game_selection_changed(self, widget):
        idx = widget.get_active()
        is_custom = (idx == len(self.config["games"]))
        self.ent_custom.set_visible(is_custom)
        if not is_custom:
            self.chk_grab.set_active(self.config["games"][idx].get("grab", True))

    def on_click_loc_changed(self, widget):
        is_fixed = (widget.get_active() == 1)
        self.coord_box.set_visible(is_fixed)

    def refresh_macro_profiles(self):
        self.cmb_profile.remove_all()
        files = sorted([f for f in os.listdir(MACROS_DIR) if f.endswith(".rec")])
        if not files:
            default_path = os.path.join(MACROS_DIR, "default.rec")
            open(default_path, "a").close()
            files = ["default.rec"]
        for f in files:
            self.cmb_profile.append_text(f)
        active = self.config.get("active_macro", "default.rec")
        if active in files:
            self.cmb_profile.set_active(files.index(active))
        else:
            self.cmb_profile.set_active(0)

    def on_macro_profile_changed(self, widget):
        txt = widget.get_active_text()
        if txt:
            self.config["active_macro"] = txt

    def create_new_macro_profile(self, widget):
        dialog = Gtk.Dialog(title="Nama Macro Profile Baru", parent=self, flags=Gtk.DialogFlags.MODAL)
        dialog.add_buttons("Batal", Gtk.ResponseType.CANCEL, "Simpan", Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_placeholder_text("misal: fishing_loop")
        entry.set_margin_start(16)
        entry.set_margin_end(16)
        entry.set_margin_top(16)
        entry.set_margin_bottom(16)
        dialog.get_content_area().pack_start(entry, True, True, 0)
        dialog.show_all()
        res = dialog.run()
        name = entry.get_text().strip()
        dialog.destroy()

        if res == Gtk.ResponseType.OK and name:
            if not name.endswith(".rec"):
                name += ".rec"
            p = os.path.join(MACROS_DIR, name)
            open(p, "a").close()
            self.refresh_macro_profiles()
            self.config["active_macro"] = name
            files = [f for f in os.listdir(MACROS_DIR) if f.endswith(".rec")]
            if name in files:
                self.cmb_profile.set_active(files.index(name))

    def load_script_template(self, widget):
        idx = widget.get_active()
        buf = self.txt_script.get_buffer()
        if idx == 0:
            template = """; Roblox Anti-AFK Camera Jiggle
Loop {
    Send, {Right}
    Sleep, 400
    Send, {Left}
    Sleep, 400
    Sleep, 8000
}
"""
        elif idx == 1:
            template = """; Roblox Jump & Forward Step
Loop {
    Send, {Space}
    Sleep, 500
    Send, w
    Sleep, 200
    Send, s
    Sleep, 200
    Sleep, 15000
}
"""
        elif idx == 2:
            template = """; AutoClicker Mining Loop
Loop {
    Click
    Sleep, 100
}
"""
        else:
            template = """# Python Script
import time, subprocess
print("Python AFK script running...")
while True:
    subprocess.run(["xdotool", "key", "space"])
    time.sleep(10)
"""
        buf.set_text(template)

    def get_actual_display(self):
        if os.path.exists(DISPLAY_IPC_FILE):
            try:
                with open(DISPLAY_IPC_FILE, "r") as f:
                    val = f.read().strip()
                    if val.startswith(":"):
                        return val
            except Exception:
                pass
        return ":3"

    # ----------------- GAME LAUNCHER -----------------

    def toggle_game_instance(self, widget):
        if self.game_proc is None or self.game_proc.poll() is not None:
            # Launch
            idx = self.cmb_game.get_active()
            if idx == len(self.config["games"]):
                cmd = self.ent_custom.get_text().strip()
                if not cmd:
                    self.lbl_telemetry_msg.set_text("⚠️ Isi custom command terlebih dahulu!")
                    return
            else:
                cmd = self.config["games"][idx]["cmd"]

            res_idx = self.cmb_res.get_active()
            res_val = RESOLUTIONS[res_idx][0]
            w, h = map(int, res_val.split("x"))

            fps_idx = self.cmb_fps.get_active()
            fps_val = FPS_OPTIONS[fps_idx][0]

            extra = ["--force-composition"]
            if self.chk_grab.get_active():
                extra.append("--force-grab-cursor")

            env = os.environ.copy()
            env["__GL_GSYNC_ALLOWED"] = "0"
            env["__GL_VRR_ALLOWED"] = "0"

            wrapped_cmd = f'echo "$DISPLAY" > {DISPLAY_IPC_FILE}; exec {cmd}'
            full_cmd = ["gamescope", "-W", str(w), "-H", str(h), "-r", str(fps_val)] + extra + ["--", "bash", "-c", wrapped_cmd]

            try:
                self.game_proc = subprocess.Popen(full_cmd, env=env)
                self.btn_launch.set_label("🛑 Hentikan Game Instance")
                self.btn_launch.get_style_context().remove_class("btn-primary")
                self.btn_launch.get_style_context().add_class("btn-danger")
                self.badge_status.set_text("SANDBOX RUNNING")
                self.badge_status.get_style_context().remove_class("badge-idle")
                self.badge_status.get_style_context().add_class("badge-active")

                self.afk_start_time = time.time()
                self.loop_count = 0
                self.lbl_telemetry_msg.set_text(f"Game aktif ({w}x{h} @ {fps_val}FPS). Laptop bebas dipakai!")
            except Exception as e:
                self.lbl_telemetry_msg.set_text(f"❌ Gagal membuka game: {e}")
        else:
            # Kill
            if self.game_proc:
                self.game_proc.terminate()
                self.game_proc = None
            self.reset_game_ui()

    def reset_game_ui(self):
        self.btn_launch.set_label("⚡ Luncurkan Game Terisolasi")
        self.btn_launch.get_style_context().remove_class("btn-danger")
        self.btn_launch.get_style_context().add_class("btn-primary")
        self.badge_status.set_text("SANDBOX IDLE")
        self.badge_status.get_style_context().remove_class("badge-active")
        self.badge_status.get_style_context().add_class("badge-idle")
        self.lbl_telemetry_msg.set_text("Game dihentikan.")

    # ----------------- TINYTASK REC / PLAY -----------------

    def toggle_record(self, widget=None):
        macro_name = self.config.get("active_macro", "default.rec")
        target_path = os.path.join(MACROS_DIR, macro_name)

        if not self.is_recording:
            self.is_recording = True
            self.btn_rec.set_label("⏹ Stop Rec (F8)")
            self.btn_rec.get_style_context().add_class("btn-danger")
            self.btn_play.set_sensitive(False)
            self.badge_status.set_text("RECORDING")
            self.badge_status.get_style_context().remove_class("badge-idle")
            self.badge_status.get_style_context().add_class("badge-record")
            self.lbl_telemetry_msg.set_text("🔴 Merekam input mouse & keyboard live...")

            rec_bin = os.path.join(APP_DIR, "tinytask-rec.py")
            if not os.path.exists(rec_bin):
                rec_bin = os.path.expanduser("~/.local/bin/tinytask-rec")
            self.rec_proc = subprocess.Popen([rec_bin, target_path])
        else:
            self.is_recording = False
            self.btn_rec.set_label("🔴 Record Gerakan (F8)")
            self.btn_rec.get_style_context().remove_class("btn-danger")
            self.btn_play.set_sensitive(True)
            self.badge_status.set_text("SANDBOX RUNNING" if self.game_proc else "SANDBOX IDLE")
            self.badge_status.get_style_context().remove_class("badge-record")
            self.badge_status.get_style_context().add_class("badge-active" if self.game_proc else "badge-idle")

            if self.rec_proc:
                self.rec_proc.send_signal(signal.SIGINT)
                self.rec_proc.wait()
                self.rec_proc = None

            count = 0
            if os.path.exists(target_path):
                with open(target_path, "r") as f:
                    count = sum(1 for _ in f)
            self.lbl_telemetry_msg.set_text(f"✅ Rekaman selesai ({count} aksi tersimpan di {macro_name}).")

    def toggle_play(self, widget=None):
        macro_name = self.config.get("active_macro", "default.rec")
        target_path = os.path.join(MACROS_DIR, macro_name)

        if not self.is_playing:
            if not os.path.exists(target_path) or os.path.getsize(target_path) == 0:
                self.lbl_telemetry_msg.set_text(f"⚠️ Profile {macro_name} masih kosong! Record dulu.")
                return

            self.target_display = self.get_actual_display()
            self.is_playing = True
            self.btn_play.set_label("⏹ Stop Macro (F9)")
            self.btn_play.get_style_context().remove_class("btn-success")
            self.btn_play.get_style_context().add_class("btn-danger")
            self.btn_rec.set_sensitive(False)

            speed = self.cmb_speed.get_active_text().replace("x", "")
            loop = self.chk_loop.get_active()

            self.play_thread = threading.Thread(target=self._play_worker, args=(target_path, speed, loop), daemon=True)
            self.play_thread.start()
        else:
            self.is_playing = False
            self.lbl_telemetry_msg.set_text("Menghentikan macro playback...")

    def _play_worker(self, path, speed, loop):
        play_bin = os.path.join(APP_DIR, "tinytask-play")
        if not os.path.exists(play_bin):
            play_bin = os.path.expanduser("~/.local/bin/tinytask-play")
        env = os.environ.copy()
        env["DISPLAY"] = self.target_display

        while self.is_playing:
            self.loop_count += 1
            GLib.idle_add(self.lbl_telemetry_loops.set_text, f" | Loops: {self.loop_count}")
            GLib.idle_add(self.lbl_telemetry_msg.set_text, f"▶ Playback loop #{self.loop_count} ({speed}x) di {self.target_display}")

            proc = subprocess.Popen([play_bin, path, str(speed)], env=env)
            while proc.poll() is None:
                if not self.is_playing:
                    proc.terminate()
                    break
                time.sleep(0.08)

            if not loop or not self.is_playing:
                break
            time.sleep(0.3)

        self.is_playing = False
        GLib.idle_add(self._reset_play_ui)

    def _reset_play_ui(self):
        self.btn_play.set_label("▶ Play Macro (F9)")
        self.btn_play.get_style_context().remove_class("btn-danger")
        self.btn_play.get_style_context().add_class("btn-success")
        self.btn_rec.set_sensitive(True)
        self.lbl_telemetry_msg.set_text("Playback selesai. Macro standby.")

    # ----------------- AUTOCLICKER -----------------

    def toggle_autoclicker(self, widget=None):
        if not self.is_clicker_running:
            self.target_display = self.get_actual_display()
            self.is_clicker_running = True
            self.btn_clicker.set_label("🛑 Stop AutoClicker (F10)")
            self.btn_clicker.get_style_context().remove_class("btn-success")
            self.btn_clicker.get_style_context().add_class("btn-danger")

            interval = max(0.001, self.spn_interval.get_value() / 1000.0)
            btn_idx = ["1", "3", "2"][self.cmb_click_btn.get_active()]
            is_double = (self.cmb_click_type.get_active() == 1)
            is_fixed = (self.cmb_click_loc.get_active() == 1)
            fx, fy = int(self.spn_x.get_value()), int(self.spn_y.get_value())

            self.clicker_thread = threading.Thread(
                target=self._clicker_worker,
                args=(interval, btn_idx, is_double, is_fixed, fx, fy),
                daemon=True
            )
            self.clicker_thread.start()
        else:
            self.is_clicker_running = False
            self.btn_clicker.set_label("⚡ Start AutoClicker (F10)")
            self.btn_clicker.get_style_context().remove_class("btn-danger")
            self.btn_clicker.get_style_context().add_class("btn-success")
            self.lbl_telemetry_msg.set_text("AutoClicker stopped.")

    def _clicker_worker(self, interval, btn, is_double, is_fixed, fx, fy):
        env = os.environ.copy()
        env["DISPLAY"] = self.target_display

        GLib.idle_add(self.lbl_telemetry_msg.set_text, f"⚡ AutoClicker aktif ({interval*1000:.0f}ms) di {self.target_display}")
        while self.is_clicker_running:
            cmd = ["xdotool"]
            if is_fixed:
                cmd += ["mousemove", str(fx), str(fy)]
            cmd += ["click"]
            if is_double:
                cmd += ["--repeat", "2", "--delay", "50"]
            cmd += [btn]

            subprocess.run(cmd, env=env)
            time.sleep(interval)

    # ----------------- SCRIPT ENGINE -----------------

    def toggle_script_run(self, widget=None):
        if not self.is_script_running:
            buf = self.txt_script.get_buffer()
            code = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
            if not code.strip():
                self.lbl_telemetry_msg.set_text("⚠️ Editor script kosong!")
                return

            self.target_display = self.get_actual_display()
            self.is_script_running = True
            self.btn_run_script.set_label("🛑 Hentikan Script")
            self.btn_run_script.get_style_context().remove_class("btn-primary")
            self.btn_run_script.get_style_context().add_class("btn-danger")

            self.script_thread = threading.Thread(target=self._script_worker, args=(code,), daemon=True)
            self.script_thread.start()
        else:
            self.is_script_running = False
            self.btn_run_script.set_label("▶ Jalankan Script / AHK")
            self.btn_run_script.get_style_context().remove_class("btn-danger")
            self.btn_run_script.get_style_context().add_class("btn-primary")
            self.lbl_telemetry_msg.set_text("Script dihentikan.")

    def _script_worker(self, code):
        GLib.idle_add(self.lbl_telemetry_msg.set_text, "📜 Script / AHK Runner aktif...")
        try:
            if code.strip().startswith("# Python"):
                # Run Python
                env = os.environ.copy()
                env["DISPLAY"] = self.target_display
                proc = subprocess.Popen([sys.executable, "-c", code], env=env)
                while proc.poll() is None:
                    if not self.is_script_running:
                        proc.terminate()
                        break
                    time.sleep(0.1)
            else:
                # Run AHK engine
                run_ahk(code, self.target_display, stop_check=lambda: not self.is_script_running)
        except Exception as e:
            GLib.idle_add(self.lbl_telemetry_msg.set_text, f"Script error: {e}")
        finally:
            self.is_script_running = False
            GLib.idle_add(self._reset_script_ui)

    def _reset_script_ui(self):
        self.btn_run_script.set_label("▶ Jalankan Script / AHK")
        self.btn_run_script.get_style_context().remove_class("btn-danger")
        self.btn_run_script.get_style_context().add_class("btn-primary")
        self.lbl_telemetry_msg.set_text("Script selesai.")

    # ----------------- BACKGROUND MONITOR & HOTKEYS -----------------

    def start_background_watcher(self):
        def watcher():
            while True:
                time.sleep(1.0)
                # Cek display
                disp = self.get_actual_display()
                if disp != self.target_display:
                    self.target_display = disp
                    GLib.idle_add(self.lbl_telemetry_disp.set_text, f" | Active Display: {disp}")

                # Update AFK duration
                if self.game_proc and self.game_proc.poll() is None and self.afk_start_time:
                    elapsed = int(time.time() - self.afk_start_time)
                    h = elapsed // 3600
                    m = (elapsed % 3600) // 60
                    s = elapsed % 60
                    GLib.idle_add(self.lbl_telemetry_time.set_text, f"AFK Duration: {h:02d}:{m:02d}:{s:02d}")
                elif self.game_proc and self.game_proc.poll() is not None:
                    self.game_proc = None
                    GLib.idle_add(self.reset_game_ui)

        t = threading.Thread(target=watcher, daemon=True)
        t.start()

    def start_hotkey_listener(self):
        """Global Hotkeys F8, F9, F10 via evdev kernel listener"""
        def hotkey_loop():
            import evdev
            devs = []
            for p in evdev.list_devices():
                try:
                    d = evdev.InputDevice(p)
                    if evdev.ecodes.EV_KEY in d.capabilities():
                        devs.append(d)
                except Exception:
                    pass
            if not devs:
                return

            dev_map = {d.fd: d for d in devs}
            while True:
                r, _, _ = select.select(dev_map.keys(), [], [], 0.2)
                for fd in r:
                    try:
                        for ev in dev_map[fd].read():
                            if ev.type == evdev.ecodes.EV_KEY and ev.value == 1: # Key down
                                if ev.code == evdev.ecodes.KEY_F8: # F8
                                    GLib.idle_add(self.toggle_record)
                                elif ev.code == evdev.ecodes.KEY_F9: # F9
                                    GLib.idle_add(self.toggle_play)
                                elif ev.code == evdev.ecodes.KEY_F10: # F10
                                    GLib.idle_add(self.toggle_autoclicker)
                    except Exception:
                        pass

        t = threading.Thread(target=hotkey_loop, daemon=True)
        t.start()

def main():
    app = AFKStudioApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
