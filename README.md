# Linux AFK Game Hub & TinyTask 🚀

Aplikasi desktop terintegrasi untuk Linux (X11 & Wayland/Hyprland) yang memungkinkan kamu melakukan **AFK Farming pada game (seperti Roblox, Minecraft Bedrock, dll)** dalam sandbox terisolasi dengan optimisasi konsumsi daya (FPS & Resolusi), dilengkapi dengan fitur perekam & pemutar makro **TinyTask**.

---

## ✨ Fitur Utama
1. **Layar Game Terisolasi (Gamescope)**: Kursor mouse & keyboard fisik kamu di desktop utama bebas 100% dipakai untuk browsing/kerja/ngetik selagi game berjalan di background.
2. **Resource Saver**: Pilihan batas FPS (10, 15, 20, 30 FPS) dan resolusi rendah (540p, 720p) agar laptop tetap dingin dan hemat baterai saat ditinggal semalaman.
3. **Built-in TinyTask**:
   - 🔴 **Record**: Merekam pergerakan keyboard, mouse klik, dan drag kamera secara langsung.
   - ▶ **Playback & Continuous Loop**: Mengulang otomatis aksi farming tanpa henti.
   - ⚡ **Speed Multiplier**: 0.5x, 1x, 1.5x, 2x playback speed.
4. **Anti-Flicker & Camera Fix**: Konfigurasi driver NVIDIA & mode relative mouse sudah otomatis tertanam.

---

## 📦 Prasyarat & Dependensi

Sebelum menginstal, pastikan paket berikut sudah terpasang di sistem:

### Arch Linux / CachyOS / Manjaro:
```bash
sudo pacman -S gamescope gcc python-gobject python-evdev libxtst libx11
```

### Ubuntu / Debian / Pop!_OS:
```bash
sudo apt update
sudo apt install gamescope gcc python3-gi python3-evdev libxtst-dev libx11-dev
```

### Fedora:
```bash
sudo dnf install gamescope gcc python3-gobject python3-evdev libXtst-devel libX11-devel
```

> **Catatan Izin Input (evdev):**  
> Agar recorder bisa membaca input mouse & keyboard tanpa sudo, pastikan user kamu masuk grup `input`:
> ```bash
> sudo usermod -aG input $USER
> ```
> *(Log out lalu log in kembali agar izin grup aktif)*

---

## 🚀 Cara Instalasi

1. Clone atau ekstrak repository ini ke laptop:
   ```bash
   cd linux-afk-hub
   ```
2. Jalankan script installer otomatis:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
3. Buka aplikasi via menu launcher (**AFK Game Hub & TinyTask**) atau lewat terminal:
   ```bash
   afk-hub
   ```

---

## 🛠️ Struktur Project

```text
linux-afk-hub/
├── install.sh             # Script instalasi 1-klik untuk user/developer
├── README.md              # Dokumentasi & panduan pemakaian
├── assets/
│   └── afk-hub.desktop    # File integrasi desktop launcher
└── src/
    ├── afk-hub.py         # GUI utama (GTK3 + Python)
    ├── tinytask-rec.py    # Mesin perekam event (Linux evdev)
    └── tinytask-play.c    # Mesin pemutar event berpresisi tinggi (C + XTest)
```

---

## 👨‍💻 Kontribusi & Pengembangan
Silakan fork repository ini, tambahkan fitur profil macro custom, integrasi OCR bot, atau launcher game baru sesuai kebutuhan!
