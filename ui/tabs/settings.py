"""Settings tab — ADB / BlueStacks configuration."""

import customtkinter as ctk
from tkinter import filedialog
import threading
from config import cfg, save_cfg

ACCENT  = "#e94560"
SUCCESS = "#4ecca3"
WARNING = "#f0a500"


class SettingsTab:
    def __init__(self, parent, logs, status_var):
        self.parent     = parent
        self.logs       = logs
        self.status_var = status_var
        self._build()

    def _build(self):
        self.parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.parent, text="Settings",
                     font=ctk.CTkFont("Helvetica", 16, "bold")).grid(
                         row=0, column=0, sticky="w", padx=20, pady=(18, 2))

        # ── ADB / Emulator ────────────────────────────────────────────────────
        adb_card = ctk.CTkFrame(self.parent, fg_color="#1a1a2e", corner_radius=10)
        adb_card.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 6))
        adb_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(adb_card, text="BlueStacks / ADB",
                     font=ctk.CTkFont("Helvetica", 12, "bold")).grid(
                         row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(adb_card,
                     text="BlueStacks connects on localhost:5555 by default.\n"
                          "Start BlueStacks first, then hit Connect.",
                     font=ctk.CTkFont("Helvetica", 10), text_color="#555",
                     justify="left").grid(
                         row=1, column=0, columnspan=3, sticky="w", padx=16, pady=(0, 8))

        # Host
        ctk.CTkLabel(adb_card, text="ADB host", text_color="#aaa").grid(
            row=2, column=0, sticky="w", padx=16, pady=6)
        self._host_var = ctk.StringVar(value=cfg.get("adb", {}).get("host", "localhost"))
        ctk.CTkEntry(adb_card, textvariable=self._host_var,
                     width=160, height=32, corner_radius=6).grid(
                         row=2, column=1, sticky="w", pady=6)

        # Port
        ctk.CTkLabel(adb_card, text="Port", text_color="#aaa").grid(
            row=3, column=0, sticky="w", padx=16, pady=6)
        self._port_var = ctk.StringVar(value=str(cfg.get("adb", {}).get("port", 5555)))
        ctk.CTkEntry(adb_card, textvariable=self._port_var,
                     width=100, height=32, corner_radius=6).grid(
                         row=3, column=1, sticky="w", pady=6)

        # ADB path (optional)
        ctk.CTkLabel(adb_card, text="ADB path", text_color="#aaa").grid(
            row=4, column=0, sticky="w", padx=16, pady=6)
        self._adb_var = ctk.StringVar(value=cfg.get("adb", {}).get("adb_path", ""))
        ctk.CTkEntry(adb_card, textvariable=self._adb_var,
                     placeholder_text="Leave blank to auto-detect",
                     height=32, corner_radius=6).grid(
                         row=4, column=1, sticky="ew", padx=(0, 6), pady=6)
        ctk.CTkButton(adb_card, text="Browse", width=80, height=32,
                      corner_radius=6, fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._browse_adb).grid(row=4, column=2, padx=(0, 16), pady=6)

        # BlueStacks exe (optional)
        ctk.CTkLabel(adb_card, text="BlueStacks exe", text_color="#aaa").grid(
            row=5, column=0, sticky="w", padx=16, pady=6)
        self._exe_var = ctk.StringVar(value=cfg.get("adb", {}).get("emulator_exe", ""))
        ctk.CTkEntry(adb_card, textvariable=self._exe_var,
                     placeholder_text="HD-Player.exe  (optional — for auto-launch)",
                     height=32, corner_radius=6).grid(
                         row=5, column=1, sticky="ew", padx=(0, 6), pady=6)
        ctk.CTkButton(adb_card, text="Browse", width=80, height=32,
                      corner_radius=6, fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._browse_exe).grid(row=5, column=2, padx=(0, 16), pady=6)

        # ADB status
        self._status_var_adb = ctk.StringVar(value="Not connected")
        ctk.CTkLabel(adb_card, textvariable=self._status_var_adb,
                     font=ctk.CTkFont("Helvetica", 10),
                     text_color="#555").grid(
                         row=6, column=0, columnspan=3, sticky="w", padx=16, pady=(0, 6))

        ctk.CTkButton(adb_card, text="Save settings", width=120, height=28,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      corner_radius=6, command=self._save).grid(
                          row=7, column=2, sticky="e", padx=16, pady=(4, 14))

        # ── Launch controls ───────────────────────────────────────────────────
        launch_card = ctk.CTkFrame(self.parent, fg_color="#1a1a2e", corner_radius=10)
        launch_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(6, 20))
        launch_card.grid_columnconfigure(0, weight=1)
        launch_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(launch_card, text="Emulator controls",
                     font=ctk.CTkFont("Helvetica", 12, "bold")).grid(
                         row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8))

        ctk.CTkButton(launch_card, text="⚡  Connect ADB",
                      height=40, corner_radius=8,
                      fg_color=ACCENT, hover_color="#c73652",
                      font=ctk.CTkFont("Helvetica", 12, "bold"),
                      command=self._connect).grid(
                          row=1, column=0, sticky="ew", padx=(16, 6), pady=(0, 10))

        ctk.CTkButton(launch_card, text="▶  Launch BlueStacks",
                      height=40, corner_radius=8,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._launch).grid(
                          row=1, column=1, sticky="ew", padx=(6, 16), pady=(0, 10))

        ctk.CTkButton(launch_card, text="✕  Close BlueStacks",
                      height=36, corner_radius=8,
                      fg_color="#2a0a12", hover_color="#3d0f1a", text_color=ACCENT,
                      command=self._close).grid(
                          row=2, column=0, columnspan=2,
                          sticky="ew", padx=16, pady=(0, 14))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _browse_adb(self):
        path = filedialog.askopenfilename(
            title="Select adb.exe or HD-Adb.exe",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self._adb_var.set(path)

    def _browse_exe(self):
        path = filedialog.askopenfilename(
            title="Select HD-Player.exe",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self._exe_var.set(path)

    def _save(self):
        if "adb" not in cfg:
            cfg["adb"] = {}
        cfg["adb"]["host"]         = self._host_var.get().strip()
        cfg["adb"]["port"]         = int(self._port_var.get().strip() or "5555")
        cfg["adb"]["adb_path"]     = self._adb_var.get().strip()
        cfg["adb"]["emulator_exe"] = self._exe_var.get().strip()
        save_cfg()
        self.logs.log("Settings saved", "success")

    def _connect(self):
        self._save()
        threading.Thread(target=self._do_connect, daemon=True).start()

    def _do_connect(self):
        self.parent.after(0, lambda: self._status_var_adb.set("Connecting…"))
        self.logs.log(f"Connecting to ADB at "
                      f"{cfg.get('adb',{}).get('host','localhost')}:"
                      f"{cfg.get('adb',{}).get('port',5555)}…", "info")
        try:
            from bot.adb import connect
            device = connect()
            msg = f"✓  Connected: {device.serial}"
            self.logs.log(msg, "success")
            self.parent.after(0, lambda: self._status_var_adb.set(msg))
        except Exception as e:
            msg = f"✗  {e}"
            self.logs.log(f"ADB connect failed: {e}", "error")
            self.parent.after(0, lambda: self._status_var_adb.set(msg))

    def _launch(self):
        self._save()
        threading.Thread(target=self._do_launch, daemon=True).start()

    def _do_launch(self):
        try:
            from bot.launcher import launch
            self.status_var.set("Starting BlueStacks…")
            self.logs.log("Starting BlueStacks…", "info")
            serial = launch()
            self.logs.log(f"Ready: {serial}", "success")
        except Exception as e:
            self.logs.log(f"Launch failed: {e}", "error")
        finally:
            self.parent.after(0, lambda: self.status_var.set("Idle"))

    def _close(self):
        try:
            from bot.launcher import close
            close()
            self.logs.log("BlueStacks closed", "warn")
        except Exception as e:
            self.logs.log(f"Close failed: {e}", "error")
