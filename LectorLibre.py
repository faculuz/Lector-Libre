# Lector Libre - lector de texto en voz alta gratuito para Windows
VERSION = "1.2.0"
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

import time, re, ctypes, threading, tempfile, subprocess, winreg, requests, keyboard
from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QFileDialog, QInputDialog, QMessageBox
from core import (
    APP, cfg, save_cfg, models_ready, download_models, add_history,
    export_audio, export_audiobook, read_from_cursor_or_selection,
    recognize_image_winocr, update_external_foreground, Player, log
)
from ui import (
    QSS, make_icon, MiniPlayer, ReaderWindow, HistoryWindow, SettingsDialog,
    WelcomeTutorialDialog, ScreenOcrSelector, run_with_progress
)

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

        self.ocr_selector = ScreenOcrSelector()
        self.ocr_selector.area_captured.connect(self.on_ocr_image)

        self.mini = MiniPlayer(
            self.player,
            on_read_sel=lambda: threading.Thread(target=self.trigger_read_sel, daemon=True).start(),
            on_read_page=lambda: threading.Thread(target=self.trigger_read_page, daemon=True).start(),
            on_ocr=self.trigger_ocr,
            on_open_reader=self.open_reader,
        )
        self.reader = ReaderWindow(
            self.player,
            on_export=self.handle_export,
            on_export_audiobook=self.handle_export_audiobook,
            on_ocr=self.trigger_ocr,
            on_read_page=lambda: threading.Thread(target=self.trigger_read_page, daemon=True).start(),
            on_history=self.open_history,
            on_settings=self.open_settings,
            ensure_ready=self.ensure_models,
            on_voice_studio=self.open_voice_studio,
            on_tutorial=self.show_welcome,
        )
        self.mini.settings_changed.connect(self.reader.refresh_voices)
        self.reader.settings_changed.connect(self.mini.refresh_voices)

        self.hist_win = HistoryWindow(self.on_history_open)
        self.settings_dlg = None

        self.update_info = {"ver": None, "url": None}
        self.hk_handles = []
        self._downloading = False

        self.fg_timer = QTimer(self, interval=250, timeout=update_external_foreground)
        self.fg_timer.start()

        self.read_text_sig.connect(self.on_read_text)
        self.toast_sig.connect(self.show_toast)
        self.update_found_sig.connect(self.on_update_found)
        self.toggle_sig.connect(self.on_toggle_cmd)

        self.init_tray()
        self.register_hotkeys()
        cfg["autostart"] = self.autostart_enabled()
        save_cfg()
        self.reader.show()
        self.reader.raise_()
        self.reader.activateWindow()
        if cfg.get("mini", True):
            self.mini.show()
            self.mini.raise_()

        threading.Thread(target=self.updater_worker, daemon=True).start()

        if cfg.get("show_welcome_tutorial", True):
            QTimer.singleShot(500, self.show_welcome)
        elif cfg.get("engine") in ("kokoro", "piper") and not models_ready():
            QTimer.singleShot(1500, self.ensure_models)

    def init_tray(self):
        self.tray = QSystemTrayIcon(make_icon(), self.qapp)
        self.tray.setToolTip(APP)
        self.menu = QMenu()

        self.act_open = self.menu.addAction("Abrir lector", self.open_reader)
        self.act_mini = self.menu.addAction("Mostrar botón / reproductor flotante", self.show_mini)
        self.act_read_sel = self.menu.addAction(
            f"Leer selección o desde cursor ({cfg.get('hk_read', '')})",
            lambda: threading.Thread(target=self.trigger_read_sel, daemon=True).start(),
        )
        self.act_read_page = self.menu.addAction(
            f"Leer esta página / ventana ({cfg.get('hk_page', 'ctrl+alt+w')})",
            lambda: threading.Thread(target=self.trigger_read_page, daemon=True).start(),
        )
        self.act_ocr = self.menu.addAction(
            f"OCR de zona de pantalla ({cfg.get('hk_ocr', 'ctrl+alt+o')})",
            self.trigger_ocr,
        )
        self.act_pause = self.menu.addAction("Pausar/Reanudar", self.player.toggle_pause)
        self.act_stop = self.menu.addAction("Detener", self.player.stop)
        self.menu.addSeparator()
        self.act_voice_studio = self.menu.addAction("★ Estudio de Voz (Clonar / Crear)", self.open_voice_studio)
        self.act_settings = self.menu.addAction("Configuración y Pronunciación", self.open_settings)
        self.act_hist = self.menu.addAction("Historial y Marcadores", self.open_history)
        self.act_tutorial = self.menu.addAction("Ver tutorial de bienvenida", self.show_welcome)
        self.act_update = self.menu.addAction("Instalar actualización", self.install_update)
        self.act_update.setVisible(False)
        self.act_check_update = self.menu.addAction(
            "Buscar actualizaciones",
            lambda: threading.Thread(target=self.check_update, args=(True,), daemon=True).start(),
        )
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
        self.reader.raise_()
        self.reader.activateWindow()

    def show_mini(self):
        self.mini.show()
        self.mini.raise_()

    def open_history(self):
        self.hist_win.refresh()
        self.hist_win.show()
        self.hist_win.activateWindow()

    def on_history_open(self, texto, fuente, jump_idx=None):
        self.reader.set_text(texto, fuente, jump_idx=jump_idx)
        self.open_reader()
        if jump_idx is not None and self.ensure_models():
            self.player.load(texto, fuente)
            self.player.play(jump_idx)

    def open_settings(self, tab_idx=0):
        if not self.settings_dlg:
            self.settings_dlg = SettingsDialog(self.on_settings_saved)
        self.settings_dlg.load()
        if isinstance(tab_idx, int) and 0 <= tab_idx < self.settings_dlg.tabs.count():
            self.settings_dlg.tabs.setCurrentIndex(tab_idx)
        self.settings_dlg.show()
        self.settings_dlg.raise_()
        self.settings_dlg.activateWindow()

    def open_voice_studio(self):
        self.open_settings(tab_idx=1)

    def on_settings_saved(self):
        self.register_hotkeys()
        self.apply_autostart(cfg.get("autostart", False))
        self.act_read_sel.setText(f"Leer selección o desde cursor ({cfg.get('hk_read', '')})")
        self.act_read_page.setText(f"Leer esta página / ventana ({cfg.get('hk_page', 'ctrl+alt+w')})")
        self.act_ocr.setText(f"OCR de zona de pantalla ({cfg.get('hk_ocr', 'ctrl+alt+o')})")
        self.mini.refresh_voices()
        self.reader.refresh_voices()
        if self.mini.compact != bool(cfg.get("mini_compact", False)):
            self.mini.compact = bool(cfg.get("mini_compact", False))
            self.mini._apply_mode()
        if cfg.get("mini", True):
            self.mini.show()
        else:
            self.mini.hide()
        self.player.reset_voices()

    def autostart_enabled(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
                winreg.QueryValueEx(k, "LectorLibre")
                return True
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

        bindings = [
            (cfg.get("hk_read", "ctrl+alt+r"), lambda: threading.Thread(target=self.trigger_read_sel, daemon=True).start(), "leer"),
            (cfg.get("hk_pause", "ctrl+alt+p"), lambda: self.toggle_sig.emit("pause"), "pausar"),
            (cfg.get("hk_page", "ctrl+alt+w"), lambda: threading.Thread(target=self.trigger_read_page, daemon=True).start(), "leer página"),
            (cfg.get("hk_ocr", "ctrl+alt+o"), lambda: self.toggle_sig.emit("ocr"), "OCR"),
        ]
        for hk, fn, label in bindings:
            if not hk:
                continue
            try:
                self.hk_handles.append(keyboard.add_hotkey(hk, fn))
            except Exception:
                self.toast_sig.emit(f"Atajo inválido para {label}: {hk}")

    def on_toggle_cmd(self, cmd):
        if cmd == "pause":
            self.player.toggle_pause()
        elif cmd == "ocr":
            self.trigger_ocr()

    def trigger_read_sel(self):
        """#1: Lee la selección actual o, si no hay nada seleccionado, lee desde la posición del cursor hasta que se detenga."""
        text, src = read_from_cursor_or_selection(prefer_full_page=False)
        if text:
            self.read_text_sig.emit(text, src or "Selección / Cursor")
        else:
            self.toast_sig.emit("No encontré texto en la selección ni bajo el cursor")

    def trigger_read_page(self):
        """#6 & #2: Modo 'Leer esta página' con un clic para el navegador o formulario activo."""
        text, src = read_from_cursor_or_selection(prefer_full_page=True)
        if text:
            self.read_text_sig.emit(text, src or "Página activa")
        else:
            self.toast_sig.emit("No pude extraer el contenido de la página activa")

    def trigger_ocr(self):
        """#5: Abre el selector de zona en pantalla para OCR de Windows."""
        self.ocr_selector.start_capture()

    def on_ocr_image(self, pil_img):
        def work():
            txt = recognize_image_winocr(pil_img)
            if txt:
                self.read_text_sig.emit(txt, "OCR de pantalla")
            else:
                self.toast_sig.emit("No se detectó texto en la zona seleccionada")

        threading.Thread(target=work, daemon=True).start()

    def ensure_models(self):
        if self._downloading:
            return False
        if cfg.get("engine") in ("kokoro", "piper") and not models_ready():
            self._downloading = True
            try:
                ok, err = run_with_progress(None, "Descargando la voz seleccionada (una sola vez)...", download_models)
            finally:
                self._downloading = False
            if not ok:
                r = QMessageBox.question(
                    None,
                    APP,
                    f"No se pudo descargar la voz ({str(err)[:120]}).\n\n¿Querés usar la voz online gratuita (Edge) mientras tanto?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if r == QMessageBox.Yes:
                    cfg["engine"] = "edge"
                    save_cfg()
                    if self.settings_dlg:
                        self.settings_dlg.refresh_engine_ui()
                    self.mini.refresh_voices()
                    return True
                return False
        return True

    def on_read_text(self, text, fuente):
        if not self.ensure_models():
            return
        add_history(text, fuente)
        self.player.load(text, fuente)
        if not self.player.chunks:
            self.show_toast("No encontré texto para leer")
            return
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

    def handle_export_audiobook(self, text, epub_chapters=None):
        """#11: Exporta el documento entero como audiolibro separado por capítulos."""
        if not text.strip():
            QMessageBox.information(self.reader, APP, "No hay texto en el lector para exportar como audiolibro.")
            return
        if not self.ensure_models():
            return
        out_dir = QFileDialog.getExistingDirectory(self.reader, "Elegí la carpeta donde guardar los capítulos del audiolibro")
        if not out_dir:
            return
        fmt, ok_fmt = QInputDialog.getItem(self.reader, APP, "Formato de audio por capítulo:", ["MP3", "WAV"], 0, False)
        if not ok_fmt:
            return
        ok, res = run_with_progress(
            self.reader,
            "Exportando audiolibro por capítulos...",
            lambda pcb: export_audiobook(text, out_dir, fmt, pcb, chapters_override=epub_chapters),
        )
        if ok:
            QMessageBox.information(
                self.reader,
                APP,
                f"Audiolibro exportado ({len(res)} capítulos + lista Audiolibro.m3u) en:\n{out_dir}",
            )
        else:
            QMessageBox.critical(self.reader, APP, f"Error al exportar audiolibro:\n{res}")

    def show_welcome(self):
        dlg = WelcomeTutorialDialog(on_open_voice_studio=self.open_voice_studio, parent=self.reader)
        dlg.exec()
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
