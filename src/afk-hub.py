#!/usr/bin/env python3
"""
Linux AFK Game Studio
Integrated single-window architecture and clean desktop design.
Zero visual noise, focused utility.
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
from gi.repository import Gtk, Gdk, GLib

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from ahk_engine import run_ahk

CONFIG_DIR = os.path.expanduser("~/.config/afk-hub")
MACROS_DIR = os.path.join(CONFIG_DIR, "macros")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DISPLAY_IPC_FILE = "/tmp/afk_gamescope_display.txt"

os.makedirs(MACROS_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "games": [
        {"name": "Roblox (Sober)", "cmd": "flatpak run org.vinegarhq.Sober", "grab": True},
        {"name": "Minecraft Bedrock", "cmd": "flatpak run io.mrarm.mcpelauncher", "grab": True},
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
        "location": "Current",
        "x": 0,
        "y": 0
    }
}

RESOLUTIONS = ["800x450", "960x540", "1280x720", "1600x900", "1920x1080"]
FPS_CHOICES = ["10", "15", "20", "30", "60"]

CSS_DATA = b"""
/* Strict clean desktop palette - no decorative noise */
window {
    background-color: #16181d;
    color: #d8dbe2;
    font-family: system-ui, sans-serif;
    font-size: 12px;
}

.top-bar {
    background-color: #1b1e25;
    border-bottom: 1px solid #282c37;
    padding: 8px 12px;
}

.title-text {
    font-weight: 700;
    font-size: 13px;
    color: #ffffff;
    letter-spacing: -0.01em;
}

.badge {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
.badge-idle {
    background: #232732;
    color: #7d8597;
}
.badge-running {
    background: #19382b;
    color: #4ade80;
}
.badge-recording {
    background: #3e1e24;
    color: #f87171;
}

.panel-card {
    background-color: #1b1e25;
    border: 1px solid #282c37;
    border-radius: 6px;
    padding: 12px;
}

.panel-title {
    font-size: 11px;
    font-weight: 700;
    color: #7d8597;
    margin-bottom: 8px;
}

/* Button semantics */
button {
    background: #232732;
    color: #d8dbe2;
    border: 1px solid #333846;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 600;
}
button:hover {
    background: #2c313f;
    border-color: #404759;
}
button:active {
    background: #1c202a;
}
button:disabled {
    opacity: 0.4;
}

.btn-accent {
    background: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
}
.btn-accent:hover {
    background: #1d4ed8;
}

.btn-stop {
    background: #b91c1c;
    color: #ffffff;
    border: 1px solid #dc2626;
}
.btn-stop:hover {
    background: #991b1b;
}

.btn-action {
    background: #15803d;
    color: #ffffff;
    border: 1px solid #16a34a;
}
.btn-action:hover {
    background: #166534;
}

entry, spinbutton {
    background: #121418;
    color: #d8dbe2;
    border: 1px solid #282c37;
    border-radius: 4px;
    padding: 5px 8px;
}
entry:focus, spinbutton:focus {
    border-color: #3b82f6;
}

combobox button {
    background: #121418;
    border: 1px solid #282c37;
    color: #d8dbe2;
    padding: 4px 8px;
}

/* Tab strip clean styling */
stackswitcher button {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: #7d8597;
    padding: 8px 14px;
    font-weight: 600;
}
stackswitcher button:checked {
    background: transparent;
    color: #3b82f6;
    border-bottom: 2px solid #3b82f6;
}

.telemetry-strip {
    background: #121418;
    border-top: 1px solid #222630;
    padding: 6px 12px;
    font-size: 11px;
    color: #7d8597;
}
"""

class AFKStudioApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="AFK Game Studio")
        self.set_default_size(680, 580)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(0)

        self.load_config()

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

        # Apply clean CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_DATA)
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

        # 1. Header Bar
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        top_bar.get_style_context().add_class("top-bar")

        title = Gtk.Label(label="AFK Game Studio")
        title.get_style_context().add_class("title-text")
        top_bar.pack_start(title, False, False, 0)

        hotkey_hint = Gtk.Label(label="F8: Record | F9: Play | F10: Clicker | Super+G: Grab")
        hotkey_hint.set_margin_start(16)
        hotkey_hint.get_style_context().add_class("badge-idle")
        top_bar.pack_start(hotkey_hint, False, False, 0)

        self.badge_status = Gtk.Label(label="IDLE")
        self.badge_status.get_style_context().add_class("badge")
        self.badge_status.get_style_context().add_class("badge-idle")
        top_bar.pack_end(self.badge_status, False, False, 0)

        root.pack_start(top_bar, False, False, 0)

        # 2. Main Workspace
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_margin_top(10)
        body.set_margin_bottom(10)
        body.set_margin_start(12)
        body.set_margin_end(12)
        root.pack_start(body, True, True, 0)

        # Sandbox Launcher Card
        launcher_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        launcher_card.get_style_context().add_class("panel-card")

        l_title = Gtk.Label(label="INSTANCE SETTINGS")
        l_title.get_style_context().add_class("panel-title")
        l_title.set_halign(Gtk.Align.START)
        launcher_card.pack_start(l_title, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(6)

        # Target Game
        lbl_game = Gtk.Label(label="Game:")
        lbl_game.set_halign(Gtk.Align.START)
        grid.attach(lbl_game, 0, 0, 1, 1)

        self.cmb_game = Gtk.ComboBoxText()
        for g in self.config["games"]:
            self.cmb_game.append_text(g["name"])
        self.cmb_game.append_text("Custom Command...")
        self.cmb_game.set_active(min(self.config.get("selected_game", 0), len(self.config["games"])))
        self.cmb_game.connect("changed", self.on_game_changed)
        grid.attach(self.cmb_game, 1, 0, 1, 1)

        # Resolution
        lbl_res = Gtk.Label(label="Resolution:")
        lbl_res.set_halign(Gtk.Align.START)
        grid.attach(lbl_res, 2, 0, 1, 1)

        self.cmb_res = Gtk.ComboBoxText()
        for r in RESOLUTIONS:
            self.cmb_res.append_text(r)
        curr_res = self.config.get("resolution", "960x540")
        self.cmb_res.set_active(RESOLUTIONS.index(curr_res) if curr_res in RESOLUTIONS else 1)
        grid.attach(self.cmb_res, 3, 0, 1, 1)

        # FPS
        lbl_fps = Gtk.Label(label="FPS Cap:")
        lbl_fps.set_halign(Gtk.Align.START)
        grid.attach(lbl_fps, 0, 1, 1, 1)

        self.cmb_fps = Gtk.ComboBoxText()
        for f in FPS_CHOICES:
            self.cmb_fps.append_text(f + " FPS")
        curr_fps = str(self.config.get("fps", 15))
        self.cmb_fps.set_active(FPS_CHOICES.index(curr_fps) if curr_fps in FPS_CHOICES else 1)
        grid.attach(self.cmb_fps, 1, 1, 1, 1)

        # Camera Grab
        self.chk_grab = Gtk.CheckButton(label="3D Relative Camera Look")
        self.chk_grab.set_active(True)
        grid.attach(self.chk_grab, 2, 1, 2, 1)

        # Custom Entry (Hidden by default)
        self.ent_custom = Gtk.Entry()
        self.ent_custom.set_placeholder_text("Executable or command (e.g. wine /path/to/game.exe)")
        self.ent_custom.set_no_show_all(True)
        grid.attach(self.ent_custom, 0, 2, 4, 1)

        launcher_card.pack_start(grid, False, False, 0)

        # Launch Button
        self.btn_launch = Gtk.Button(label="Launch Sandbox Instance")
        self.btn_launch.get_style_context().add_class("btn-accent")
        self.btn_launch.connect("clicked", self.toggle_game_instance)
        launcher_card.pack_start(self.btn_launch, False, False, 4)

        body.pack_start(launcher_card, False, False, 0)

        # Automation Stack / Mode Switcher
        auto_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        auto_card.get_style_context().add_class("panel-card")

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.START)
        auto_card.pack_start(switcher, False, False, 0)

        # Tab 1: TinyTask
        tab_tinytask = self.build_tinytask_tab()
        self.stack.add_titled(tab_tinytask, "tinytask", "TinyTask Recorder")

        # Tab 2: AutoClicker
        tab_clicker = self.build_clicker_tab()
        self.stack.add_titled(tab_clicker, "clicker", "AutoClicker")

        # Tab 3: Script / AHK
        tab_script = self.build_script_tab()
        self.stack.add_titled(tab_script, "script", "Script & AHK")

        auto_card.pack_start(self.stack, True, True, 0)
        body.pack_start(auto_card, True, True, 0)

        # 3. Telemetry Status Bar
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        footer.get_style_context().add_class("telemetry-strip")

        self.lbl_time = Gtk.Label(label="AFK Duration: 00:00:00")
        footer.pack_start(self.lbl_time, False, False, 0)

        self.lbl_loops = Gtk.Label(label=" | Loops: 0")
        footer.pack_start(self.lbl_loops, False, False, 0)

        self.lbl_disp = Gtk.Label(label=f" | Display: {self.target_display}")
        footer.pack_start(self.lbl_disp, False, False, 0)

        self.lbl_msg = Gtk.Label(label="Ready")
        self.lbl_msg.set_halign(Gtk.Align.END)
        footer.pack_end(self.lbl_msg, True, True, 0)

        root.pack_end(footer, False, False, 0)

    # ----------------- TABS -----------------

    def build_tinytask_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(6)

        row_prof = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_p = Gtk.Label(label="Profile:")
        row_prof.pack_start(lbl_p, False, False, 0)

        self.cmb_profile = Gtk.ComboBoxText()
        self.refresh_profiles()
        self.cmb_profile.connect("changed", self.on_profile_changed)
        row_prof.pack_start(self.cmb_profile, True, True, 0)

        btn_new = Gtk.Button(label="New Profile")
        btn_new.connect("clicked", self.create_profile_dialog)
        row_prof.pack_start(btn_new, False, False, 0)
        box.pack_start(row_prof, False, False, 0)

        # Actions
        row_act = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_act.set_homogeneous(True)

        self.btn_rec = Gtk.Button(label="Record (F8)")
        self.btn_rec.connect("clicked", self.toggle_record)
        row_act.pack_start(self.btn_rec, True, True, 0)

        self.btn_play = Gtk.Button(label="Play (F9)")
        self.btn_play.get_style_context().add_class("btn-action")
        self.btn_play.connect("clicked", self.toggle_play)
        row_act.pack_start(self.btn_play, True, True, 0)

        box.pack_start(row_act, False, False, 0)

        # Options
        row_opt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.chk_loop = Gtk.CheckButton(label="Continuous Loop")
        self.chk_loop.set_active(True)
        row_opt.pack_start(self.chk_loop, False, False, 0)

        lbl_s = Gtk.Label(label="Speed:")
        row_opt.pack_start(lbl_s, False, False, 0)

        self.cmb_speed = Gtk.ComboBoxText()
        for s in ["0.5x", "1x", "1.5x", "2x", "4x"]:
            self.cmb_speed.append_text(s)
        self.cmb_speed.set_active(1)
        row_opt.pack_start(self.cmb_speed, False, False, 0)

        box.pack_start(row_opt, False, False, 0)
        return box

    def build_clicker_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(6)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(6)

        lbl_i = Gtk.Label(label="Interval (ms):")
        lbl_i.set_halign(Gtk.Align.START)
        grid.attach(lbl_i, 0, 0, 1, 1)

        self.spn_interval = Gtk.SpinButton.new_with_range(1, 60000, 10)
        self.spn_interval.set_value(self.config["clicker"].get("interval_ms", 100))
        grid.attach(self.spn_interval, 1, 0, 1, 1)

        lbl_b = Gtk.Label(label="Button:")
        lbl_b.set_halign(Gtk.Align.START)
        grid.attach(lbl_b, 2, 0, 1, 1)

        self.cmb_click_btn = Gtk.ComboBoxText()
        for b in ["Left", "Right", "Middle"]:
            self.cmb_click_btn.append_text(b)
        self.cmb_click_btn.set_active(0)
        grid.attach(self.cmb_click_btn, 3, 0, 1, 1)

        lbl_t = Gtk.Label(label="Click Type:")
        lbl_t.set_halign(Gtk.Align.START)
        grid.attach(lbl_t, 0, 1, 1, 1)

        self.cmb_click_type = Gtk.ComboBoxText()
        for t in ["Single Click", "Double Click"]:
            self.cmb_click_type.append_text(t)
        self.cmb_click_type.set_active(0)
        grid.attach(self.cmb_click_type, 1, 1, 1, 1)

        lbl_l = Gtk.Label(label="Position:")
        lbl_l.set_halign(Gtk.Align.START)
        grid.attach(lbl_l, 2, 1, 1, 1)

        self.cmb_click_loc = Gtk.ComboBoxText()
        self.cmb_click_loc.append_text("Current Cursor Position")
        self.cmb_click_loc.append_text("Fixed Coordinates (X, Y)")
        self.cmb_click_loc.set_active(0)
        self.cmb_click_loc.connect("changed", self.on_click_loc_changed)
        grid.attach(self.cmb_click_loc, 3, 1, 1, 1)

        self.coord_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.spn_x = Gtk.SpinButton.new_with_range(0, 3840, 1)
        self.spn_y = Gtk.SpinButton.new_with_range(0, 2160, 1)
        self.coord_box.pack_start(Gtk.Label(label="X:"), False, False, 0)
        self.coord_box.pack_start(self.spn_x, False, False, 0)
        self.coord_box.pack_start(Gtk.Label(label="Y:"), False, False, 0)
        self.coord_box.pack_start(self.spn_y, False, False, 0)
        self.coord_box.set_no_show_all(True)
        grid.attach(self.coord_box, 2, 2, 2, 1)

        box.pack_start(grid, False, False, 0)

        self.btn_clicker = Gtk.Button(label="Start AutoClicker (F10)")
        self.btn_clicker.get_style_context().add_class("btn-action")
        self.btn_clicker.connect("clicked", self.toggle_autoclicker)
        box.pack_start(self.btn_clicker, False, False, 4)

        return box

    def build_script_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(6)

        row_tpl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row_tpl.pack_start(Gtk.Label(label="Template:"), False, False, 0)

        self.cmb_template = Gtk.ComboBoxText()
        self.cmb_template.append_text("Roblox: Anti-AFK Camera Jiggle (AHK)")
        self.cmb_template.append_text("Roblox: Forward Step & Space (AHK)")
        self.cmb_template.append_text("Mining: Click Loop (AHK)")
        self.cmb_template.append_text("Python: Custom Script")
        self.cmb_template.set_active(0)
        self.cmb_template.connect("changed", self.load_script_template)
        row_tpl.pack_start(self.cmb_template, True, True, 0)
        box.pack_start(row_tpl, False, False, 0)

        self.txt_script = Gtk.TextView()
        self.txt_script.set_monospace(True)
        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(-1, 120)
        scroll.add(self.txt_script)
        box.pack_start(scroll, True, True, 0)

        self.btn_script = Gtk.Button(label="Execute Script")
        self.btn_script.get_style_context().add_class("btn-accent")
        self.btn_script.connect("clicked", self.toggle_script)
        box.pack_start(self.btn_script, False, False, 0)

        self.load_script_template(self.cmb_template)
        return box

    # ----------------- EVENTS -----------------

    def on_game_changed(self, widget):
        idx = widget.get_active()
        is_custom = (idx == len(self.config["games"]))
        self.ent_custom.set_visible(is_custom)
        if not is_custom:
            self.chk_grab.set_active(self.config["games"][idx].get("grab", True))

    def on_click_loc_changed(self, widget):
        self.coord_box.set_visible(widget.get_active() == 1)

    def refresh_profiles(self):
        self.cmb_profile.remove_all()
        files = sorted([f for f in os.listdir(MACROS_DIR) if f.endswith(".rec")])
        if not files:
            p = os.path.join(MACROS_DIR, "default.rec")
            open(p, "a").close()
            files = ["default.rec"]
        for f in files:
            self.cmb_profile.append_text(f)
        active = self.config.get("active_macro", "default.rec")
        self.cmb_profile.set_active(files.index(active) if active in files else 0)

    def on_profile_changed(self, widget):
        name = widget.get_active_text()
        if name:
            self.config["active_macro"] = name

    def create_profile_dialog(self, widget):
        dlg = Gtk.Dialog(title="New Profile", parent=self, flags=Gtk.DialogFlags.MODAL)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Create", Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_placeholder_text("profile_name")
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        dlg.get_content_area().pack_start(entry, True, True, 0)
        dlg.show_all()
        res = dlg.run()
        name = entry.get_text().strip()
        dlg.destroy()

        if res == Gtk.ResponseType.OK and name:
            if not name.endswith(".rec"):
                name += ".rec"
            open(os.path.join(MACROS_DIR, name), "a").close()
            self.refresh_profiles()
            files = [f for f in os.listdir(MACROS_DIR) if f.endswith(".rec")]
            if name in files:
                self.cmb_profile.set_active(files.index(name))

    def load_script_template(self, widget):
        idx = widget.get_active()
        buf = self.txt_script.get_buffer()
        if idx == 0:
            code = """; Roblox Anti-AFK Camera Jiggle
Loop {
    Send, {Right}
    Sleep, 400
    Send, {Left}
    Sleep, 400
    Sleep, 8000
}
"""
        elif idx == 1:
            code = """; Roblox Step & Jump
Loop {
    Send, {Space}
    Sleep, 300
    Send, w
    Sleep, 200
    Send, s
    Sleep, 200
    Sleep, 12000
}
"""
        elif idx == 2:
            code = """; Mining Click Loop
Loop {
    Click
    Sleep, 100
}
"""
        else:
            code = """# Python automation
import time, subprocess
while True:
    subprocess.run(["xdotool", "key", "space"])
    time.sleep(10)
"""
        buf.set_text(code)

    def get_actual_display(self):
        if os.path.exists(DISPLAY_IPC_FILE):
            try:
                with open(DISPLAY_IPC_FILE, "r") as f:
                    v = f.read().strip()
                    if v.startswith(":"):
                        return v
            except Exception:
                pass
        return ":3"

    # ----------------- EXECUTION -----------------

    def toggle_game_instance(self, widget):
        if self.game_proc is None or self.game_proc.poll() is not None:
            idx = self.cmb_game.get_active()
            if idx == len(self.config["games"]):
                cmd = self.ent_custom.get_text().strip()
                if not cmd:
                    self.lbl_msg.set_text("Enter a custom command")
                    return
            else:
                cmd = self.config["games"][idx]["cmd"]

            res = self.cmb_res.get_active_text()
            w, h = map(int, res.split("x"))
            fps = self.cmb_fps.get_active_text().replace(" FPS", "")

            extra = ["--force-composition"]
            if self.chk_grab.get_active():
                extra.append("--force-grab-cursor")

            env = os.environ.copy()
            env["__GL_GSYNC_ALLOWED"] = "0"
            env["__GL_VRR_ALLOWED"] = "0"

            wrapped = f'echo "$DISPLAY" > {DISPLAY_IPC_FILE}; exec {cmd}'
            full_cmd = ["gamescope", "-W", str(w), "-H", str(h), "-r", str(fps)] + extra + ["--", "bash", "-c", wrapped]

            try:
                self.game_proc = subprocess.Popen(full_cmd, env=env)
                self.btn_launch.set_label("Stop Instance")
                self.btn_launch.get_style_context().remove_class("btn-accent")
                self.btn_launch.get_style_context().add_class("btn-stop")
                self.badge_status.set_text("RUNNING")
                self.badge_status.get_style_context().remove_class("badge-idle")
                self.badge_status.get_style_context().add_class("badge-running")

                self.afk_start_time = time.time()
                self.loop_count = 0
                self.lbl_msg.set_text(f"Sandbox active ({res} @ {fps}fps)")
            except Exception as e:
                self.lbl_msg.set_text(f"Launch failed: {e}")
        else:
            if self.game_proc:
                self.game_proc.terminate()
                self.game_proc = None
            self.reset_game_ui()

    def reset_game_ui(self):
        self.btn_launch.set_label("Launch Sandbox Instance")
        self.btn_launch.get_style_context().remove_class("btn-stop")
        self.btn_launch.get_style_context().add_class("btn-accent")
        self.badge_status.set_text("IDLE")
        self.badge_status.get_style_context().remove_class("badge-running")
        self.badge_status.get_style_context().add_class("badge-idle")
        self.lbl_msg.set_text("Instance stopped")

    def toggle_record(self, widget=None):
        prof = self.config.get("active_macro", "default.rec")
        path = os.path.join(MACROS_DIR, prof)

        if not self.is_recording:
            self.is_recording = True
            self.btn_rec.set_label("Stop Rec (F8)")
            self.btn_rec.get_style_context().add_class("btn-stop")
            self.btn_play.set_sensitive(False)
            self.badge_status.set_text("RECORDING")
            self.badge_status.get_style_context().remove_class("badge-idle")
            self.badge_status.get_style_context().add_class("badge-recording")
            self.lbl_msg.set_text("Recording events...")

            rec_bin = os.path.join(APP_DIR, "tinytask-rec.py")
            if not os.path.exists(rec_bin):
                rec_bin = os.path.expanduser("~/.local/bin/tinytask-rec")
            self.rec_proc = subprocess.Popen([rec_bin, path])
        else:
            self.is_recording = False
            self.btn_rec.set_label("Record (F8)")
            self.btn_rec.get_style_context().remove_class("btn-stop")
            self.btn_play.set_sensitive(True)
            self.badge_status.set_text("RUNNING" if self.game_proc else "IDLE")
            self.badge_status.get_style_context().remove_class("badge-recording")
            self.badge_status.get_style_context().add_class("badge-running" if self.game_proc else "badge-idle")

            if self.rec_proc:
                self.rec_proc.send_signal(signal.SIGINT)
                self.rec_proc.wait()
                self.rec_proc = None

            count = sum(1 for _ in open(path, "r")) if os.path.exists(path) else 0
            self.lbl_msg.set_text(f"Recorded {count} actions to {prof}")

    def toggle_play(self, widget=None):
        prof = self.config.get("active_macro", "default.rec")
        path = os.path.join(MACROS_DIR, prof)

        if not self.is_playing:
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                self.lbl_msg.set_text(f"Profile {prof} is empty")
                return

            self.target_display = self.get_actual_display()
            self.is_playing = True
            self.btn_play.set_label("Stop Play (F9)")
            self.btn_play.get_style_context().remove_class("btn-action")
            self.btn_play.get_style_context().add_class("btn-stop")
            self.btn_rec.set_sensitive(False)

            speed = self.cmb_speed.get_active_text().replace("x", "")
            loop = self.chk_loop.get_active()

            self.play_thread = threading.Thread(target=self._play_worker, args=(path, speed, loop), daemon=True)
            self.play_thread.start()
        else:
            self.is_playing = False
            self.lbl_msg.set_text("Stopping playback...")

    def _play_worker(self, path, speed, loop):
        play_bin = os.path.join(APP_DIR, "tinytask-play")
        if not os.path.exists(play_bin):
            play_bin = os.path.expanduser("~/.local/bin/tinytask-play")
        env = os.environ.copy()
        env["DISPLAY"] = self.target_display

        while self.is_playing:
            self.loop_count += 1
            GLib.idle_add(self.lbl_loops.set_text, f" | Loops: {self.loop_count}")
            GLib.idle_add(self.lbl_msg.set_text, f"Loop #{self.loop_count} ({speed}x) on {self.target_display}")

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
        self.btn_play.set_label("Play (F9)")
        self.btn_play.get_style_context().remove_class("btn-stop")
        self.btn_play.get_style_context().add_class("btn-action")
        self.btn_rec.set_sensitive(True)
        self.lbl_msg.set_text("Playback idle")

    def toggle_autoclicker(self, widget=None):
        if not self.is_clicker_running:
            self.target_display = self.get_actual_display()
            self.is_clicker_running = True
            self.btn_clicker.set_label("Stop AutoClicker (F10)")
            self.btn_clicker.get_style_context().remove_class("btn-action")
            self.btn_clicker.get_style_context().add_class("btn-stop")

            interval = max(0.001, self.spn_interval.get_value() / 1000.0)
            btn = ["1", "3", "2"][self.cmb_click_btn.get_active()]
            is_dbl = (self.cmb_click_type.get_active() == 1)
            is_fix = (self.cmb_click_loc.get_active() == 1)
            fx, fy = int(self.spn_x.get_value()), int(self.spn_y.get_value())

            self.clicker_thread = threading.Thread(
                target=self._clicker_worker,
                args=(interval, btn, is_dbl, is_fix, fx, fy),
                daemon=True
            )
            self.clicker_thread.start()
        else:
            self.is_clicker_running = False
            self.btn_clicker.set_label("Start AutoClicker (F10)")
            self.btn_clicker.get_style_context().remove_class("btn-stop")
            self.btn_clicker.get_style_context().add_class("btn-action")
            self.lbl_msg.set_text("AutoClicker stopped")

    def _clicker_worker(self, interval, btn, is_dbl, is_fix, fx, fy):
        env = os.environ.copy()
        env["DISPLAY"] = self.target_display
        GLib.idle_add(self.lbl_msg.set_text, f"AutoClicker active ({interval*1000:.0f}ms)")

        while self.is_clicker_running:
            cmd = ["xdotool"]
            if is_fix:
                cmd += ["mousemove", str(fx), str(fy)]
            cmd += ["click"]
            if is_dbl:
                cmd += ["--repeat", "2", "--delay", "50"]
            cmd += [btn]

            subprocess.run(cmd, env=env)
            time.sleep(interval)

    def toggle_script(self, widget=None):
        if not self.is_script_running:
            buf = self.txt_script.get_buffer()
            code = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
            if not code.strip():
                self.lbl_msg.set_text("Script editor is empty")
                return

            self.target_display = self.get_actual_display()
            self.is_script_running = True
            self.btn_script.set_label("Stop Script")
            self.btn_script.get_style_context().remove_class("btn-accent")
            self.btn_script.get_style_context().add_class("btn-stop")

            self.script_thread = threading.Thread(target=self._script_worker, args=(code,), daemon=True)
            self.script_thread.start()
        else:
            self.is_script_running = False
            self.btn_script.set_label("Execute Script")
            self.btn_script.get_style_context().remove_class("btn-stop")
            self.btn_script.get_style_context().add_class("btn-accent")
            self.lbl_msg.set_text("Script stopped")

    def _script_worker(self, code):
        GLib.idle_add(self.lbl_msg.set_text, "Script running...")
        try:
            if code.strip().startswith("# Python"):
                env = os.environ.copy()
                env["DISPLAY"] = self.target_display
                proc = subprocess.Popen([sys.executable, "-c", code], env=env)
                while self.is_script_running and proc.poll() is None:
                    time.sleep(0.1)
                if proc.poll() is None:
                    proc.terminate()
            else:
                run_ahk(code, self.target_display, stop_check=lambda: not self.is_script_running)
        except Exception as e:
            GLib.idle_add(self.lbl_msg.set_text, f"Script error: {e}")
        finally:
            self.is_script_running = False
            GLib.idle_add(self._reset_script_ui)

    def _reset_script_ui(self):
        self.btn_script.set_label("Execute Script")
        self.btn_script.get_style_context().remove_class("btn-stop")
        self.btn_script.get_style_context().add_class("btn-accent")
        self.lbl_msg.set_text("Script finished")

    # ----------------- DAEMON WATCHERS -----------------

    def start_background_watcher(self):
        def watcher():
            while True:
                time.sleep(1.0)
                disp = self.get_actual_display()
                if disp != self.target_display:
                    self.target_display = disp
                    GLib.idle_add(self.lbl_disp.set_text, f" | Display: {disp}")

                if self.game_proc and self.game_proc.poll() is None and self.afk_start_time:
                    elapsed = int(time.time() - self.afk_start_time)
                    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
                    GLib.idle_add(self.lbl_time.set_text, f"AFK Duration: {h:02d}:{m:02d}:{s:02d}")
                elif self.game_proc and self.game_proc.poll() is not None:
                    self.game_proc = None
                    GLib.idle_add(self.reset_game_ui)

        t = threading.Thread(target=watcher, daemon=True)
        t.start()

    def start_hotkey_listener(self):
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
                            if ev.type == evdev.ecodes.EV_KEY and ev.value == 1:
                                if ev.code == evdev.ecodes.KEY_F8:
                                    GLib.idle_add(self.toggle_record)
                                elif ev.code == evdev.ecodes.KEY_F9:
                                    GLib.idle_add(self.toggle_play)
                                elif ev.code == evdev.ecodes.KEY_F10:
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
