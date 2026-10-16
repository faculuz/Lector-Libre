# Lector Libre - lector de texto en voz alta gratuito para Windows
VERSION = "1.0.0"
REPO = "faculuz/Lector-Libre"
AUMID = "FacundoLuzardo.LectorLibre"

import os, sys

def _run_self_test():
    """Importa Kokoro y sintetiza una frase corta. Sale 0 si el paquete está completo."""
    import traceback
    lines = []

    def emit(msg):
        lines.append(str(msg))
        try:
            print(msg, flush=True)
        except Exception:
            pass

    code = 1
    try:
        emit("SELFTEST: start")
        from core import download_models, engine, log, models_ready, prepare_kokoro_runtime
        prepare_kokoro_runtime()
        emit("SELFTEST: import kokoro_onnx")
        import espeakng_loader
        from kokoro_onnx import Kokoro  # noqa: F401
        lib, data = espeakng_loader.get_library_path(), espeakng_loader.get_data_path()
        emit(f"SELFTEST: espeak lib={lib}")
        emit(f"SELFTEST: espeak data={data}")
        if not os.path.isfile(lib):
            raise RuntimeError(f"No está la biblioteca de espeak: {lib}")
        if not os.path.isdir(data):
            raise RuntimeError(f"No están los datos de espeak: {data}")
        if not models_ready():
            emit("SELFTEST: downloading models")

            def progress(done, total, label):
                if done == 0 or (total and done >= total) or done % (50 << 20) < (1 << 20):
                    emit(f"SELFTEST: {label} {done}/{total}")

            download_models(progress)
        emit("SELFTEST: synthesize")
        audio = engine.synth_kokoro("Hola, esto es una prueba.", "es", 1.0)
        import numpy as np
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        peak = float(np.max(np.abs(samples))) if samples.size else 0.0
        emit(f"SELFTEST: samples={samples.size} peak={peak:.4f}")
        if samples.size < 1000 or peak < 1e-4:
            raise RuntimeError(f"audio inválido samples={samples.size} peak={peak}")
        emit("SELFTEST: ok")
        log("self-test ok", samples.size, peak)
        code = 0
    except Exception:
        emit("SELFTEST: FAIL")
        emit(traceback.format_exc())
        try:
            from core import log
            log("self-test fail")
        except Exception:
            pass
    try:
        with open(os.path.abspath("selftest-result.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + f"\nEXIT={code}\n")
    except Exception:
        pass
    return code

if "--self-test" in sys.argv:
    os._exit(_run_self_test())

import time, re, ctypes, threading, tempfile, subprocess, winreg, requests, pyperclip, keyboard
from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QFileDialog, QMessageBox
from core import (
    APP, cfg, save_cfg, models_ready, download_models, add_history,
    export_audio, Player, log
)
from ui import QSS, make_icon, MiniPlayer, ReaderWindow, HistoryWindow, SettingsDialog, run_with_progress

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(AUMID)
except Exception as e:
    log("SetCurrentProcessExplicitAppUserModelID error:", e)

def _excepthook(et, ev, tb):
    log("Unhandled exception:", et, ev)
    sys.__excepthook__(et, ev, tb)
sys.excepthook = _excepthook

def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3])

class App(QObject):
    read_text_sig = Signal(str, str)
    toast_sig = Signal(str)
    update_found_sig = Signal(str)
    toggle_sig = Signal(str)

    def __init__(self):
        super().__init__()
        self.qapp = QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)
        self.qapp.setStyleSheet(QSS)
        self.qapp.setWindowIcon(make_icon())

        self.player = Player()
        self.player.error.connect(lambda msg: self.show_toast(f"Error: {msg}"))

        self.mini = MiniPlayer(self.player)
        self.reader = ReaderWindow(self.player, self.handle_export, self.open_history, self.open_settings, self.ensure_models)
        self.hist_win = HistoryWindow(self.on_history_open)
        self.settings_dlg = None

        self.update_info = {"ver": None, "url": None}
        self.hk_handles = []
        self._downloading = False

        self.read_text_sig.connect(self.on_read_text)
        self.toast_sig.connect(self.show_toast)
        self.update_found_sig.connect(self.on_update_found)
        self.toggle_sig.connect(self.on_toggle_cmd)

        self.init_tray()
        self.register_hotkeys()
        cfg["autostart"] = self.autostart_enabled(); save_cfg()

        threading.Thread(target=self.updater_worker, daemon=True).start()

        if cfg.get("first_run", True):
            QTimer.singleShot(500, self.show_welcome)
        elif cfg.get("engine") == "kokoro" and not models_ready():
            QTimer.singleShot(1500, self.ensure_models)

    def init_tray(self):
        self.tray = QSystemTrayIcon(make_icon(), self.qapp)
        self.tray.setToolTip(APP)
        self.menu = QMenu()

        self.act_open = self.menu.addAction("Abrir lector", self.open_reader)
        self.act_read_sel = self.menu.addAction(f"Leer selección ({cfg.get('hk_read', '')})", lambda: threading.Thread(target=self.trigger_read_sel, daemon=True).start())
        self.act_pause = self.menu.addAction("Pausar/Reanudar", self.player.toggle_pause)
        self.act_stop = self.menu.addAction("Detener", self.player.stop)
        self.menu.addSeparator()
        self.act_settings = self.menu.addAction("Configuración", self.open_settings)
        self.act_hist = self.menu.addAction("Historial", self.open_history)
        self.act_update = self.menu.addAction("Instalar actualización", self.install_update)
        self.act_update.setVisible(False)
        self.act_check_update = self.menu.addAction("Buscar actualizaciones", lambda: threading.Thread(target=self.check_update, args=(True,), daemon=True).start())
        self.menu.addSeparator()
        self.act_exit = self.menu.addAction("Salir", self.exit_app)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_reader()

    def show_toast(self, text):
        self.tray.showMessage(APP, text, make_icon(), 4000)

    def open_reader(self):
        self.reader.show()
        self.reader.activateWindow()

    def open_history(self):
        self.hist_win.refresh()
        self.hist_win.show()
        self.hist_win.activateWindow()

    def on_history_open(self, texto, fuente):
        self.reader.set_text(texto, fuente)
        self.open_reader()

    def open_settings(self):
        if not self.settings_dlg:
            self.settings_dlg = SettingsDialog(self.on_settings_saved)
        self.settings_dlg.load()
        self.settings_dlg.show()
        self.settings_dlg.activateWindow()

    def on_settings_saved(self):
        self.register_hotkeys()
        self.apply_autostart(cfg.get("autostart", False))
        self.act_read_sel.setText(f"Leer selección ({cfg.get('hk_read', '')})")
        self.mini.refresh_voices()
        self.player.reset_voices()

    def autostart_enabled(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
                winreg.QueryValueEx(k, "LectorLibre"); return True
        except OSError:
            return False

    def apply_autostart(self, enable):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    cmd = f'"{sys.executable}"' if getattr(sys, "frozen", False) else f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                    winreg.SetValueEx(key, "LectorLibre", 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, "LectorLibre")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            log("Autostart error:", e)

    def register_hotkeys(self):
        for h in self.hk_handles:
            try:
                keyboard.remove_hotkey(h)
            except Exception:
                pass
        self.hk_handles.clear()

        r_hk = cfg.get("hk_read", "ctrl+alt+r")
        p_hk = cfg.get("hk_pause", "ctrl+alt+p")
        try:
            h1 = keyboard.add_hotkey(r_hk, lambda: threading.Thread(target=self.trigger_read_sel, daemon=True).start())
            self.hk_handles.append(h1)
        except Exception as e:
            self.toast_sig.emit(f"Atajo inválido para leer: {r_hk}")

        try:
            h2 = keyboard.add_hotkey(p_hk, lambda: self.toggle_sig.emit("pause"))
            self.hk_handles.append(h2)
        except Exception as e:
            self.toast_sig.emit(f"Atajo inválido para pausar: {p_hk}")

    def on_toggle_cmd(self, cmd):
        if cmd == "pause":
            self.player.toggle_pause()

    def trigger_read_sel(self):
        try:
            old = pyperclip.paste()
        except Exception:
            old = ""
        try:
            pyperclip.copy("")
        except Exception:
            pass
        for k in ("ctrl", "alt", "shift", "windows"):
            try:
                keyboard.release(k)
            except Exception:
                pass
        time.sleep(0.15)
        keyboard.send("ctrl+c")
        text = ""
        for _ in range(10):
            time.sleep(0.1)
            try:
                text = pyperclip.paste()
                if text:
                    break
            except Exception:
                pass
        try:
            if old:
                pyperclip.copy(old)
        except Exception:
            pass

        text = text.strip() if text else ""
        if text:
            self.read_text_sig.emit(text, "Selección")
        else:
            self.toast_sig.emit("No hay texto seleccionado")

    def ensure_models(self):
        if self._downloading: return False
        if cfg.get("engine") == "kokoro" and not models_ready():
            self._downloading = True
            try:
                ok, err = run_with_progress(None, "Descargando la voz (una sola vez)...", download_models)
            finally:
                self._downloading = False
            if not ok:
                r = QMessageBox.question(
                    None, APP,
                    f"No se pudo descargar la voz ({str(err)[:120]}).\n\n¿Querés usar la voz online gratuita (Edge) mientras tanto? Se reintentará la próxima vez.",
                    QMessageBox.Yes | QMessageBox.No
                )
                if r == QMessageBox.Yes:
                    cfg["engine"] = "edge"
                    save_cfg()
                    if self.settings_dlg:
                        self.settings_dlg.refresh_engine_ui()
                    return True
                return False
        return True

    def on_read_text(self, text, fuente):
        if not self.ensure_models():
            return
        add_history(text, fuente)
        self.player.load(text)
        if not self.player.chunks:
            self.show_toast("No encontré texto para leer"); return
        self.player.play(0)
        if cfg.get("mini", True):
            self.mini.show()
            self.mini.raise_()

    def handle_export(self, text):
        if not text.strip():
            QMessageBox.information(self.reader, APP, "No hay texto para exportar.")
            return
        if not self.ensure_models():
            return
        path, _ = QFileDialog.getSaveFileName(self.reader, "Exportar audio", "", "Audio MP3 (*.mp3);;Audio WAV (*.wav)")
        if not path:
            return
        ok, res = run_with_progress(self.reader, "Exportando audio...", lambda pcb: export_audio(text, path, pcb))
        if ok:
            QMessageBox.information(self.reader, APP, f"Audio guardado correctamente en:\n{path}")
        else:
            QMessageBox.critical(self.reader, APP, f"Error al exportar audio:\n{res}")

    def show_welcome(self):
        cfg["first_run"] = False
        save_cfg()
        QMessageBox.information(
            None, APP,
            "¡Bienvenido a Lector Libre!\n\n"
            f"• Seleccioná cualquier texto y apretá {cfg.get('hk_read', 'ctrl+alt+r').upper()} para escucharlo.\n"
            "• Ahora se descarga la voz (unos 340 MB, una sola vez). Después funciona sin internet.\n"
            "• Todas las opciones están en el ícono junto al reloj (clic derecho)."
        )
        self.ensure_models()

    def check_update(self, manual=False):
        url = f"https://api.github.com/repos/{REPO}/releases/latest"
        try:
            r = requests.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                tag = data.get("tag_name", "").lstrip("v")
                if vtuple(tag) > vtuple(VERSION):
                    setup_url = None
                    for a in data.get("assets", []):
                        if a.get("name", "").lower().endswith("setup.exe"):
                            setup_url = a.get("browser_download_url")
                            break
                    if setup_url:
                        self.update_info["ver"] = tag
                        self.update_info["url"] = setup_url
                        self.update_found_sig.emit(tag)
                        return
            if manual:
                self.toast_sig.emit(f"Ya tenés la última versión ({VERSION}).")
        except Exception as e:
            log("Update check error:", e)
            if manual:
                self.toast_sig.emit("No pude buscar actualizaciones (¿hay internet?).")

    def on_update_found(self, tag):
        self.act_update.setText(f"Instalar actualización v{tag}")
        self.act_update.setVisible(True)
        self.show_toast(f"Hay una versión nueva ({tag}). Clic derecho en el ícono → Instalar actualización.")

    def updater_worker(self):
        time.sleep(10)
        while True:
            self.check_update(manual=False)
            time.sleep(86400)

    def install_update(self):
        url = self.update_info.get("url")
        if not url:
            return
        dest = os.path.join(tempfile.gettempdir(), "LectorLibre-Setup.exe")

        def dl(pcb):
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                tot = int(r.headers.get("content-length", 0))
                done = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            done += len(chunk)
                            pcb(done, tot, "Descargando actualización...")

        ok, err = run_with_progress(None, "Actualizando...", dl)
        if ok:
            try:
                subprocess.Popen([dest, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"], close_fds=True)
                self.exit_app()
            except Exception as e:
                QMessageBox.critical(None, APP, f"Error al ejecutar actualizador: {e}")
        else:
            QMessageBox.critical(None, APP, f"Error al descargar actualización: {err}")

    def exit_app(self):
        try:
            self.player.stop()
            keyboard.unhook_all()
        except Exception:
            pass
        self.tray.hide()
        os._exit(0)

def main():
    global _mutex
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _mutex = k32.CreateMutexW(None, False, "LectorLibreMutex")
    if ctypes.get_last_error() == 183:
        sys.exit(0)
    app = App()
    sys.exit(app.qapp.exec())

if __name__ == "__main__":
    main()
