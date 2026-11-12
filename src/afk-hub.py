#!/usr/bin/env python3
import sys
import os
import json
import signal
import subprocess
import threading
import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

CONFIG_DIR = os.path.expanduser("~/.config/afk-hub")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
MACRO_DIR = os.path.join(CONFIG_DIR, "macros")
DEFAULT_MACRO = os.path.join(MACRO_DIR, "last_recording.rec")
DISPLAY_IPC_FILE = "/tmp/afk_gamescope_display.txt"

os.makedirs(MACRO_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "games": [
        {
            "name": "Roblox (Sober Flatpak)",
            "command": "flatpak run org.vinegarhq.Sober",
            "needs_grab": True
        },
        {
            "name": "Minecraft Bedrock (Flatpak)",
            "command": "flatpak run io.mrarm.mcpelauncher",
            "needs_grab": True
        },
        {
            "name": "Dawn Launcher",
            "command": "flatpak run gg.dawn.Launcher",
            "needs_grab": False
        },
        {
            "name": "Custom Command...",
            "command": "",
            "needs_grab": False
        }
    ],
    "selected_game_idx": 0,
    "resolution": "960x540 (Hemat / Small)",
    "fps": "15 FPS (Ultra Hemat)"
}

RESOLUTIONS = {
    "800x450 (Super Tiny)": (800, 450),
    "960x540 (Hemat / Small)": (960, 540),
    "1280x720 (Standard HD)": (1280, 720),
    "1600x900 (Medium HD)": (1600, 900),
    "1920x1080 (Full HD)": (1920, 1080)
}

FPS_OPTIONS = {
    "10 FPS (Ekstrem Hemat)": 10,
    "15 FPS (Ultra Hemat)": 15,
    "20 FPS (Sangat Hemat)": 20,
    "30 FPS (Standar AFK)": 30,
    "60 FPS (Normal)": 60
}

class AFKHubApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Linux AFK Game Hub & Automation")
        self.set_default_size(580, 620)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(14)

        self.load_config()

        self.game_proc = None
        self.rec_proc = None
        self.is_recording = False
        self.is_playing = False
        self.play_thread = None
        self.target_display = ":3"

        css = b"""
        window { background-color: #1e1e2e; color: #cdd6f4; font-family: sans-serif; }
        label { color: #cdd6f4; }
        entry { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 6px; padding: 4px 8px; }
        combobox button { background-color: #313244; color: #cdd6f4; border-radius: 6px; }
        checkbutton check { background-color: #313244; border: 1px solid #45475a; }
        
        .card { background-color: #24273a; border-radius: 10px; padding: 12px; border: 1px solid #363a4f; margin-bottom: 8px; }
        .section-header { font-size: 13px; font-weight: bold; color: #89b4fa; margin-bottom: 6px; }
        
        .btn-launch { background: #89b4fa; color: #11111b; font-weight: bold; border-radius: 8px; padding: 10px; font-size: 14px; }
        .btn-launch:hover { background: #b4befe; }
        .btn-kill { background: #f38ba8; color: #11111b; font-weight: bold; border-radius: 8px; padding: 10px; font-size: 14px; }
        
        .btn-rec { background: #f38ba8; color: #11111b; font-weight: bold; border-radius: 6px; padding: 8px; }
        .btn-play { background: #a6e3a1; color: #11111b; font-weight: bold; border-radius: 6px; padding: 8px; }
        
        .status-box { background-color: #181825; border-radius: 6px; padding: 8px; font-size: 12px; }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_box)

        # Header Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_lbl = Gtk.Label(label="<b>🚀 Linux AFK Game Optimizer & Macro Hub</b>")
        title_lbl.set_use_markup(True)
        title_lbl.set_halign(Gtk.Align.START)
        title_box.pack_start(title_lbl, True, True, 0)
        main_box.pack_start(title_box, False, False, 0)

        # CARD 1: Game Selection
        card_game = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_game.get_style_context().add_class("card")
        
        lbl_c1 = Gtk.Label(label="1. PILIH GAME & INSTANCE")
        lbl_c1.get_style_context().add_class("section-header")
        lbl_c1.set_halign(Gtk.Align.START)
        card_game.pack_start(lbl_c1, False, False, 0)

        grid_game = Gtk.Grid()
        grid_game.set_column_spacing(10)
        grid_game.set_row_spacing(8)

        lbl_target = Gtk.Label(label="Target Game:")
        lbl_target.set_halign(Gtk.Align.START)
        grid_game.attach(lbl_target, 0, 0, 1, 1)

        self.cmb_game = Gtk.ComboBoxText()
        for g in self.config["games"]:
            self.cmb_game.append_text(g["name"])
        self.cmb_game.set_active(self.config.get("selected_game_idx", 0))
        self.cmb_game.connect("changed", self.on_game_changed)
        grid_game.attach(self.cmb_game, 1, 0, 1, 1)

        self.lbl_custom = Gtk.Label(label="Custom Cmd:")
        self.lbl_custom.set_halign(Gtk.Align.START)
        self.ent_custom = Gtk.Entry()
        self.ent_custom.set_placeholder_text("contoh: wine /path/to/game.exe")
        grid_game.attach(self.lbl_custom, 0, 1, 1, 1)
        grid_game.attach(self.ent_custom, 1, 1, 1, 1)

        card_game.pack_start(grid_game, False, False, 0)
        main_box.pack_start(card_game, False, False, 0)

        # CARD 2: Optimization Settings
        card_opt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_opt.get_style_context().add_class("card")

        lbl_c2 = Gtk.Label(label="2. OPTIMISASI RESOURCE (HEMAT CPU, GPU & BATERAI)")
        lbl_c2.get_style_context().add_class("section-header")
        lbl_c2.set_halign(Gtk.Align.START)
        card_opt.pack_start(lbl_c2, False, False, 0)

        grid_opt = Gtk.Grid()
        grid_opt.set_column_spacing(12)
        grid_opt.set_row_spacing(8)

        lbl_res = Gtk.Label(label="Resolusi Jendela:")
        lbl_res.set_halign(Gtk.Align.START)
        grid_opt.attach(lbl_res, 0, 0, 1, 1)

        self.cmb_res = Gtk.ComboBoxText()
        for r in RESOLUTIONS.keys():
            self.cmb_res.append_text(r)
        curr_res = self.config.get("resolution", "960x540 (Hemat / Small)")
        self.cmb_res.set_active(list(RESOLUTIONS.keys()).index(curr_res) if curr_res in RESOLUTIONS else 1)
        grid_opt.attach(self.cmb_res, 1, 0, 1, 1)

        lbl_fps = Gtk.Label(label="Batas FPS:")
        lbl_fps.set_halign(Gtk.Align.START)
        grid_opt.attach(lbl_fps, 0, 1, 1, 1)

        self.cmb_fps = Gtk.ComboBoxText()
        for f in FPS_OPTIONS.keys():
            self.cmb_fps.append_text(f)
        curr_fps = self.config.get("fps", "15 FPS (Ultra Hemat)")
        self.cmb_fps.set_active(list(FPS_OPTIONS.keys()).index(curr_fps) if curr_fps in FPS_OPTIONS else 1)
        grid_opt.attach(self.cmb_fps, 1, 1, 1, 1)

        self.chk_grab = Gtk.CheckButton(label="Enable 3D Camera Look (Relative Mouse / Toggle via Super+G)")
        self.chk_grab.set_active(True)
        grid_opt.attach(self.chk_grab, 0, 2, 2, 1)

        card_opt.pack_start(grid_opt, False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.btn_launch = Gtk.Button(label="⚡ Luncurkan Game Terisolasi")
        self.btn_launch.get_style_context().add_class("btn-launch")
        self.btn_launch.connect("clicked", self.toggle_game_instance)
        btn_box.pack_start(self.btn_launch, True, True, 0)

        card_opt.pack_start(btn_box, False, False, 4)
        main_box.pack_start(card_opt, False, False, 0)

        # CARD 3: Built-in TinyTask
        card_macro = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_macro.get_style_context().add_class("card")

        lbl_c3 = Gtk.Label(label="3. TINYTASK MACRO (RECORD & PLAYBACK)")
        lbl_c3.get_style_context().add_class("section-header")
        lbl_c3.set_halign(Gtk.Align.START)
        card_macro.pack_start(lbl_c3, False, False, 0)

        macro_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        macro_btn_box.set_homogeneous(True)

        self.btn_rec = Gtk.Button(label="🔴 Record Gerakan")
        self.btn_rec.get_style_context().add_class("btn-rec")
        self.btn_rec.connect("clicked", self.toggle_record)
        macro_btn_box.pack_start(self.btn_rec, True, True, 0)

        self.btn_play = Gtk.Button(label="▶ Play Macro")
        self.btn_play.get_style_context().add_class("btn-play")
        self.btn_play.connect("clicked", self.toggle_play)
        macro_btn_box.pack_start(self.btn_play, True, True, 0)

        card_macro.pack_start(macro_btn_box, False, False, 0)

        macro_opts = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.chk_loop = Gtk.CheckButton(label="Continuous Loop (AFK)")
        self.chk_loop.set_active(True)
        macro_opts.pack_start(self.chk_loop, True, True, 0)

        lbl_spd = Gtk.Label(label="Kecepatan:")
        macro_opts.pack_start(lbl_spd, False, False, 0)
        self.cmb_speed = Gtk.ComboBoxText()
        for s in ["1x", "1.5x", "2x", "0.5x"]:
            self.cmb_speed.append_text(s)
        self.cmb_speed.set_active(0)
        macro_opts.pack_start(self.cmb_speed, False, False, 0)

        card_macro.pack_start(macro_opts, False, False, 0)
        main_box.pack_start(card_macro, False, False, 0)

        # Status Footer
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        status_box.get_style_context().add_class("status-box")
        self.lbl_status = Gtk.Label(label="Status: Siap. Pilih game dan klik 'Luncurkan Game Terisolasi'.")
        self.lbl_status.set_line_wrap(True)
        self.lbl_status.set_halign(Gtk.Align.START)
        status_box.pack_start(self.lbl_status, True, True, 0)
        main_box.pack_start(status_box, True, True, 0)

        self.on_game_changed(self.cmb_game)

    def load_config(self):
        self.config = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config.update(json.load(f))
            except Exception:
                pass

    def save_config(self):
        self.config["selected_game_idx"] = self.cmb_game.get_active()
        self.config["resolution"] = self.cmb_res.get_active_text()
        self.config["fps"] = self.cmb_fps.get_active_text()
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def on_game_changed(self, widget):
        idx = widget.get_active()
        is_custom = (idx == len(self.config["games"]) - 1)
        self.lbl_custom.set_visible(is_custom)
        self.ent_custom.set_visible(is_custom)
        if not is_custom:
            game = self.config["games"][idx]
            self.chk_grab.set_active(game.get("needs_grab", False))

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

    def toggle_game_instance(self, widget):
        if self.game_proc is None or self.game_proc.poll() is not None:
            self.save_config()
            idx = self.cmb_game.get_active()
            if idx == len(self.config["games"]) - 1:
                cmd = self.ent_custom.get_text().strip()
                if not cmd:
                    self.lbl_status.set_text("⚠️ Isi custom command terlebih dahulu!")
                    return
            else:
                cmd = self.config["games"][idx]["command"]

            res_text = self.cmb_res.get_active_text()
            w, h = RESOLUTIONS.get(res_text, (960, 540))
            
            fps_text = self.cmb_fps.get_active_text()
            fps = FPS_OPTIONS.get(fps_text, 15)

            extra_flags = ["--force-composition"]
            if self.chk_grab.get_active():
                extra_flags.append("--force-grab-cursor")

            env = os.environ.copy()
            env["__GL_GSYNC_ALLOWED"] = "0"
            env["__GL_VRR_ALLOWED"] = "0"

            # Bungkus command untuk mencatat $DISPLAY aktual ke IPC file
            wrapped_cmd = f'echo "$DISPLAY" > {DISPLAY_IPC_FILE}; exec {cmd}'

            full_cmd = ["gamescope", "-W", str(w), "-H", str(h), "-r", str(fps)] + extra_flags + ["--", "bash", "-c", wrapped_cmd]
            
            try:
                self.game_proc = subprocess.Popen(full_cmd, env=env)
                self.btn_launch.set_label("🛑 Hentikan Game (Kill Instance)")
                self.btn_launch.get_style_context().remove_class("btn-launch")
                self.btn_launch.get_style_context().add_class("btn-kill")
                self.lbl_status.set_text(f"🚀 Game berjalan! Resolusi: {w}x{h} | Limit: {fps} FPS.\nKursor laptop bebas. Gunakan [Super+G] untuk lepas/kunci kamera game.")
            except Exception as e:
                self.lbl_status.set_text(f"❌ Gagal meluncurkan game: {e}")
        else:
            if self.game_proc:
                self.game_proc.terminate()
                self.game_proc = None
            self.btn_launch.set_label("⚡ Luncurkan Game Terisolasi")
            self.btn_launch.get_style_context().remove_class("btn-kill")
            self.btn_launch.get_style_context().add_class("btn-launch")
            self.lbl_status.set_text("Game dihentikan.")

    def toggle_record(self, widget):
        if not self.is_recording:
            self.is_recording = True
            self.btn_rec.set_label("⏹ Stop Rec")
            self.btn_play.set_sensitive(False)
            self.lbl_status.set_text("🔴 MEREKAM SEMUA GERAKAN (Keyboard & Mouse)...\nLakukan aksi di game sekarang. Setelah selesai, klik Stop Rec.")

            rec_bin = os.path.expanduser("~/.local/bin/tinytask-rec")
            self.rec_proc = subprocess.Popen([rec_bin, DEFAULT_MACRO])
        else:
            self.is_recording = False
            self.btn_rec.set_label("🔴 Record Gerakan")
            self.btn_play.set_sensitive(True)
            if self.rec_proc:
                self.rec_proc.send_signal(signal.SIGINT)
                self.rec_proc.wait()
                self.rec_proc = None
            
            # Cek hasil file rekaman
            count = 0
            if os.path.exists(DEFAULT_MACRO):
                with open(DEFAULT_MACRO, "r") as f:
                    count = sum(1 for _ in f)
            self.lbl_status.set_text(f"✅ Rekaman selesai! ({count} aksi tersimpan).\nKlik ▶ Play Macro untuk menjalankan putaran AFK.")

    def toggle_play(self, widget):
        if not self.is_playing:
            if not os.path.exists(DEFAULT_MACRO) or os.path.getsize(DEFAULT_MACRO) == 0:
                self.lbl_status.set_text("⚠️ Belum ada aksi terekam! Klik 'Record Gerakan' dulu.")
                return

            self.target_display = self.get_actual_display()
            self.is_playing = True
            self.btn_play.set_label("⏹ Stop Macro")
            self.btn_rec.set_sensitive(False)

            speed = self.cmb_speed.get_active_text().replace("x", "")
            loop = self.chk_loop.get_active()

            self.play_thread = threading.Thread(target=self._play_worker, args=(speed, loop), daemon=True)
            self.play_thread.start()
        else:
            self.is_playing = False
            self.lbl_status.set_text("Menghentikan macro...")

    def _play_worker(self, speed, loop):
        play_bin = os.path.expanduser("~/.local/bin/tinytask-play")
        env = os.environ.copy()
        env["DISPLAY"] = self.target_display

        count = 1
        while self.is_playing:
            GLib.idle_add(self.lbl_status.set_text, f"▶ Playback loop #{count} ({speed}x speed) di {self.target_display}...\nLaptopmu bebas dipakai ngetik / browsing!")
            proc = subprocess.Popen([play_bin, DEFAULT_MACRO, str(speed)], env=env)
            while proc.poll() is None:
                if not self.is_playing:
                    proc.terminate()
                    break
                time.sleep(0.1)

            if not loop or not self.is_playing:
                break
            count += 1
            time.sleep(0.5)

        self.is_playing = False
        GLib.idle_add(self._reset_play_ui)

    def _reset_play_ui(self):
        self.btn_play.set_label("▶ Play Macro")
        self.btn_rec.set_sensitive(True)
        self.lbl_status.set_text("Playback selesai. Macro standby.")

def main():
    app = AFKHubApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
