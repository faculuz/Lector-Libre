# Lector Libre - interfaz (PySide6)
import os, threading
from PySide6.QtCore import Qt, QObject, Signal, QEventLoop, QTimer, QPoint, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QFont, QAction, QTextCursor, QTextFormat, QGuiApplication
from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow, QToolBar, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QProgressDialog, QDialog, QLineEdit, QFileDialog, QInputDialog, QMessageBox,
    QListWidget, QListWidgetItem, QCheckBox, QFormLayout, QDialogButtonBox, QFrame)
from core import *

ACCENT = "#7c5cff"
QSS = """
* { font-family: "Segoe UI"; font-size: 10pt; color: #e8e8f0; }
QMainWindow, QDialog, QWidget#win { background: #14151a; }
QToolBar { background: #1d1f27; border: none; padding: 6px; spacing: 6px; }
QToolBar QToolButton { background: transparent; border-radius: 8px; padding: 6px 12px; }
QToolBar QToolButton:hover { background: #2a2d3a; }
QPushButton { background: #262935; border: none; border-radius: 10px; padding: 7px 14px; }
QPushButton:hover { background: #33374a; }
QPushButton#primary { background: #7c5cff; font-weight: 600; }
QPushButton#primary:hover { background: #8f74ff; }
QTextEdit, QListWidget, QLineEdit, QComboBox { background: #1d1f27; border: 1px solid #2a2d3a; border-radius: 10px; padding: 6px;
  selection-background-color: #7c5cff; }
QTextEdit:focus, QLineEdit:focus, QComboBox:focus { border-color: #7c5cff; }
QComboBox QAbstractItemView { background: #1d1f27; border: 1px solid #2a2d3a; selection-background-color: #7c5cff; }
QComboBox::drop-down { border: none; width: 20px; }
QListWidget::item { padding: 8px; border-radius: 8px; }
QListWidget::item:selected { background: #2f2a52; }
QStatusBar { background: #1d1f27; color: #9a9ab0; }
QMenu { background: #1d1f27; border: 1px solid #2a2d3a; border-radius: 8px; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 6px; }
QMenu::item:selected { background: #7c5cff; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #555a70; background: #1d1f27; }
QCheckBox::indicator:checked { background: #7c5cff; border-color: #7c5cff; }
QProgressBar { background: #1d1f27; border: none; border-radius: 6px; text-align: center; height: 12px; }
QProgressBar::chunk { background: #7c5cff; border-radius: 6px; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #33374a; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
"""

def make_icon():
    p = res("icon.ico")
    if os.path.isfile(p): return QIcon(p)
    pix = QPixmap(64, 64); pix.fill(Qt.transparent)
    g = QPainter(pix); g.setRenderHint(QPainter.Antialiasing)
    g.setBrush(QColor(ACCENT)); g.setPen(Qt.NoPen); g.drawEllipse(2, 2, 60, 60)
    g.setPen(QPen(Qt.white, 4, cap=Qt.RoundCap))
    for i, h in enumerate((10, 22, 30, 22, 10)):
        x = 16 + i * 8; g.drawLine(x, 32 - h // 2, x, 32 + h // 2)
    g.end(); return QIcon(pix)

def voices_for_engine():
    return (EDGE_ES, EDGE_EN, "edge_es", "edge_en") if cfg.get("engine") == "edge" else (KOKORO_ES, KOKORO_EN, "voice_es", "voice_en")

def hide_on_close(w):
    w.closeEvent = lambda e: (e.ignore(), w.hide())

# ---------- progreso en segundo plano ----------
class _Bridge(QObject):
    prog = Signal(int, int, str)
    done = Signal(bool, object)

def run_with_progress(parent, title, fn):
    """Ejecuta fn(progress_cb) en un hilo mostrando una barra. Devuelve (ok, resultado_o_error)."""
    dlg = QProgressDialog(title, None, 0, 100, parent)
    dlg.setWindowTitle(APP); dlg.setMinimumWidth(380); dlg.setMinimumDuration(0)
    dlg.setWindowModality(Qt.ApplicationModal); dlg.setAutoClose(False); dlg.setAutoReset(False)
    br = _Bridge(); loop = QEventLoop(); out = {}
    def on_prog(d, t, label):
        if t > 0:
            dlg.setMaximum(100); dlg.setValue(int(d * 100 / t))
            extra = f"  {d / 1e6:.0f} de {t / 1e6:.0f} MB" if t > 5e6 else ""
        else:
            dlg.setMaximum(0); extra = ""
        dlg.setLabelText(f"{label}{extra}")
    def on_done(ok, r): out["r"] = (ok, r); loop.quit()
    br.prog.connect(on_prog); br.done.connect(on_done)
    def work():
        try: br.done.emit(True, fn(lambda d, t, l="": br.prog.emit(int(d), int(t), str(l))))
        except Exception as e:
            log("run_with_progress", repr(e)); br.done.emit(False, e)
    threading.Thread(target=work, daemon=True).start()
    dlg.show(); loop.exec(); dlg.close()
    return out["r"]

# ---------- mini reproductor flotante ----------
class MiniPlayer(QWidget):
    def __init__(self, player):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground); self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.player = player; self._drag = None
        self.hide_timer = QTimer(self, singleShot=True, interval=4000, timeout=self._auto_hide)
        lay = QHBoxLayout(self); lay.setContentsMargins(16, 10, 12, 10); lay.setSpacing(6)
        def btn(t, tip, cb, big=False):
            b = QPushButton(t); b.setToolTip(tip); b.clicked.connect(cb); b.setCursor(Qt.PointingHandCursor)
            s = 40 if big else 32; b.setFixedSize(s, s)
            b.setStyleSheet(f"QPushButton{{background:{ACCENT if big else 'transparent'};border-radius:{s//2}px;font-size:{14 if big else 12}pt;padding:0}}"
                            f"QPushButton:hover{{background:{'#8f74ff' if big else '#2f3242'}}}")
            lay.addWidget(b); return b
        btn("⏮", "Oración anterior", player.prev)
        self.b_play = btn("⏸", "Pausar / reanudar", player.toggle_pause, True)
        btn("⏭", "Oración siguiente", player.next)
        btn("⏹", "Detener", player.stop)
        self.lbl = QLabel(""); self.lbl.setFixedWidth(240); self.lbl.setStyleSheet("color:#b8b8cc;padding-left:6px")
        lay.addWidget(self.lbl)
        self.speed = QComboBox(); self.speed.setToolTip("Velocidad")
        for i in range(2, 13): self.speed.addItem(f"{i / 4:g}x", i / 4)
        self._set_speed_combo(); self.speed.activated.connect(lambda i: player.set_speed(self.speed.itemData(i)))
        lay.addWidget(self.speed)
        self.voice = QComboBox(); self.voice.setToolTip("Voz (español / inglés)"); self.voice.setMinimumWidth(130)
        self.voice.activated.connect(self._voice_chosen); lay.addWidget(self.voice)
        btn("✕", "Ocultar", self.hide)
        self.refresh_voices()
        player.sentence_started.connect(self._on_sentence); player.state_changed.connect(self._on_state)
        player.finished.connect(lambda: self.hide_timer.start())
        self.adjustSize(); self._place()

    def _set_speed_combo(self):
        i = self.speed.findData(round(cfg.get("speed", 1.0) * 4) / 4); self.speed.setCurrentIndex(max(i, 0))

    def refresh_voices(self):
        es, en, kes, ken = voices_for_engine(); self.voice.clear()
        for v in es + en: self.voice.addItem(voice_label(v), v)
        self.voice.insertSeparator(len(es))
        self.voice.setCurrentIndex(max(0, self.voice.findData(cfg.get(kes))))
        self._set_speed_combo()

    def _voice_chosen(self, i):
        v = self.voice.itemData(i)
        if not v: return
        es, en, kes, ken = voices_for_engine()
        cfg[kes if v in es else ken] = v; save_cfg(); self.player.reset_voices()

    def _place(self):
        pos = cfg.get("mini_pos")
        scr = QGuiApplication.primaryScreen().availableGeometry()
        if pos and any(s.availableGeometry().contains(QPoint(*pos)) for s in QGuiApplication.screens()):
            self.move(*pos)
        else:
            self.move(scr.center().x() - self.width() // 2, scr.bottom() - self.height() - 24)

    def paintEvent(self, e):
        g = QPainter(self); g.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        g.setPen(QPen(QColor(255, 255, 255, 28), 1)); g.setBrush(QColor(29, 31, 39, 242))
        g.drawRoundedRect(r, r.height() / 2, r.height() / 2)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self._drag = e.globalPosition().toPoint() - self.pos()
    def mouseMoveEvent(self, e):
        if self._drag is not None: self.move(e.globalPosition().toPoint() - self._drag)
    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None; cfg["mini_pos"] = [self.x(), self.y()]; save_cfg()

    def _on_sentence(self, i, a, b):
        t = self.player.chunks[i][0] if i < len(self.player.chunks) else ""
        self.lbl.setText(self.lbl.fontMetrics().elidedText(t, Qt.ElideRight, 230)); self.hide_timer.stop()
    def _on_state(self, s):
        self.b_play.setText("⏸" if s == "playing" else "▶")
        if s == "stopped": self.lbl.setText("Listo"); self.hide_timer.start()
        else: self.hide_timer.stop()
    def _auto_hide(self):
        if self.underMouse() or self.player.state != "stopped": self.hide_timer.start()
        else: self.hide()

# ---------- ventana del lector ----------
class ReaderWindow(QMainWindow):
    def __init__(self, player, on_export, on_history, on_settings, ensure_ready):
        super().__init__(); self.setObjectName("win")
        self.player, self.on_export, self.ensure_ready = player, on_export, ensure_ready
        self.fuente = "Lector"
        self.setWindowTitle(APP); self.setWindowIcon(make_icon()); self.resize(900, 680)
        tb = QToolBar(); tb.setMovable(False); self.addToolBar(tb)
        def act(t, cb, tip=""):
            a = QAction(t, self); a.setToolTip(tip or t); a.triggered.connect(cb); tb.addAction(a); return a
        act("📋  Pegar", self.paste, "Pegar texto del portapapeles")
        act("📂  Abrir archivo", self.open_file, "TXT, PDF o Word")
        act("🌐  Abrir web", self.open_url, "Leer un artículo de internet")
        tb.addSeparator()
        self.a_play = act("▶  Leer", self.read_pause, "Leer desde donde está el cursor")
        act("⏹  Detener", player.stop)
        tb.addSeparator()
        act("💾  Exportar audio", lambda: on_export(self.edit.toPlainText()), "Guardar como MP3 o WAV")
        act("🕘  Historial", on_history); act("⚙  Configuración", on_settings)
        self.edit = QTextEdit(); self.edit.setAcceptRichText(False)
        self.edit.setFont(QFont("Segoe UI", 13)); self.edit.document().setDocumentMargin(24)
        self.edit.setPlaceholderText("Pegá o escribí un texto acá, abrí un archivo o una página web, y tocá «Leer».\n\n"
                                     "También podés seleccionar texto en cualquier programa y apretar " + cfg["hk_read"].upper() + ".")
        self.edit.textChanged.connect(self._edited)
        w = QWidget(); w.setObjectName("win"); l = QVBoxLayout(w); l.setContentsMargins(14, 10, 14, 10); l.addWidget(self.edit)
        self.setCentralWidget(w)
        self.statusBar().showMessage("Listo")
        player.sentence_started.connect(self._on_sentence); player.state_changed.connect(self._on_state)
        hide_on_close(self)

    def _mine(self): return self.player.text == self.edit.toPlainText()
    def _edited(self):
        if self.player.state != "stopped" and not self._mine(): self.edit.setExtraSelections([])

    def set_text(self, text, fuente):
        self.fuente = fuente; self.edit.setPlainText(text)
        self.edit.moveCursor(QTextCursor.Start); self.statusBar().showMessage(fuente)

    def paste(self):
        t = QApplication.clipboard().text()
        if t: self.set_text(t, "Portapapeles")

    def _load(self, fn, fuente):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try: t = fn()
        except Exception as e:
            QApplication.restoreOverrideCursor(); log("abrir", repr(e))
            QMessageBox.warning(self, APP, f"No pude abrirlo:\n{str(e)[:200]}"); return
        QApplication.restoreOverrideCursor()
        if not t or not t.strip():
            QMessageBox.information(self, APP, "No encontré texto para leer (si es un PDF escaneado, no tiene texto seleccionable)."); return
        self.set_text(t, fuente)

    def open_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "Abrir archivo", "", "Documentos (*.txt *.pdf *.docx *.md);;Todos (*.*)")
        if p: self._load(lambda: extract_file(p), f"{os.path.splitext(p)[1][1:].upper()}: {os.path.basename(p)}")

    def open_url(self):
        u, ok = QInputDialog.getText(self, APP, "Pegá la dirección de la página:")
        if ok and u.strip():
            from urllib.parse import urlparse
            dom = urlparse(u if "://" in u else "https://" + u).netloc
            self._load(lambda: extract_url(u.strip()), f"Web: {dom}")

    def read_pause(self):
        if self.player.state != "stopped" and self._mine(): self.player.toggle_pause(); return
        text = self.edit.toPlainText()
        if not text.strip(): return
        if not self.ensure_ready(): return
        pos = self.edit.textCursor().position()
        self.player.load(text)
        add_history(text, self.fuente)
        self.player.play(self.player.index_for_pos(pos) if pos < len(text) - 1 else 0)

    def _on_sentence(self, i, a, b):
        n = len(self.player.chunks)
        if not self._mine(): self.statusBar().showMessage(f"Leyendo selección · oración {i + 1} de {n}"); return
        sel = QTextEdit.ExtraSelection()
        c = QColor(ACCENT); c.setAlpha(90); sel.format.setBackground(c)
        cur = self.edit.textCursor(); cur.setPosition(a); cur.setPosition(b, QTextCursor.KeepAnchor); sel.cursor = cur
        self.edit.setExtraSelections([sel])
        vc = QTextCursor(self.edit.document()); vc.setPosition(b); self.edit.setTextCursor(vc); self.edit.ensureCursorVisible()
        self.statusBar().showMessage(f"{'Voz online' if cfg.get('engine') == 'edge' else 'Voz local'} · oración {i + 1} de {n}")

    def _on_state(self, s):
        self.a_play.setText("⏸  Pausa" if s == "playing" else "▶  Leer")
        if s == "stopped": self.edit.setExtraSelections([]); self.statusBar().showMessage("Listo")

# ---------- historial ----------
class HistoryWindow(QWidget):
    def __init__(self, open_cb):
        super().__init__(); self.setObjectName("win"); self.open_cb = open_cb
        self.setWindowTitle(f"Historial · {APP}"); self.setWindowIcon(make_icon()); self.resize(620, 520)
        l = QVBoxLayout(self); l.setContentsMargins(16, 16, 16, 16)
        t = QLabel("Historial de lecturas"); t.setStyleSheet("font-size:15pt;font-weight:600"); l.addWidget(t)
        self.list = QListWidget(); self.list.itemDoubleClicked.connect(lambda *_: self._open()); l.addWidget(self.list)
        h = QHBoxLayout(); l.addLayout(h)
        b = QPushButton("Abrir en lector"); b.setObjectName("primary"); b.clicked.connect(self._open); h.addWidget(b)
        b = QPushButton("Copiar"); b.clicked.connect(self._copy); h.addWidget(b); h.addStretch()
        b = QPushButton("Borrar historial"); b.clicked.connect(self._clear); h.addWidget(b)
        hide_on_close(self)

    def refresh(self):
        self.list.clear()
        for e in load_history():
            prev = " ".join(e.get("texto", "").split())[:80]
            it = QListWidgetItem(f"{e.get('fecha', '')}  ·  {e.get('fuente', '')}\n{prev}")
            it.setData(Qt.UserRole, e); self.list.addItem(it)
    def _cur(self):
        it = self.list.currentItem(); return it.data(Qt.UserRole) if it else None
    def _open(self):
        e = self._cur()
        if e: self.open_cb(e["texto"], e.get("fuente", "Historial"))
    def _copy(self):
        e = self._cur()
        if e: QApplication.clipboard().setText(e["texto"])
    def _clear(self):
        if QMessageBox.question(self, APP, "¿Borrar todo el historial?") == QMessageBox.Yes:
            clear_history(); self.refresh()

# ---------- configuración ----------
class _HK(QObject):
    got = Signal(object, str)

class SettingsDialog(QDialog):
    def __init__(self, on_saved, parent=None):
        super().__init__(parent); self.on_saved = on_saved
        self.setWindowTitle(f"Configuración · {APP}"); self.setWindowIcon(make_icon()); self.setMinimumWidth(500)
        self.hk = _HK(); self.hk.got.connect(lambda w, t: (w.setText(t), w.setEnabled(True)))
        f = QFormLayout(self); f.setContentsMargins(20, 20, 20, 20); f.setVerticalSpacing(12)
        self.engine = QComboBox(); self.engine.addItem("Kokoro (sin internet)", "kokoro"); self.engine.addItem("Edge (online, gratis)", "edge")
        self.engine.currentIndexChanged.connect(self._fill_voices); f.addRow("Motor de voz", self.engine)
        self.v_es = QComboBox(); self.v_en = QComboBox(); f.addRow("Voz en español", self.v_es); f.addRow("Voz en inglés", self.v_en)
        self.lang = QComboBox(); self.lang.addItem("Español", "es"); self.lang.addItem("Inglés", "en"); f.addRow("Idioma por defecto", self.lang)
        self.auto = QCheckBox("Detectar idioma por oración (texto mixto español / inglés)"); f.addRow("", self.auto)
        self.speed = QComboBox()
        for i in range(2, 13): self.speed.addItem(f"{i / 4:g}x", i / 4)
        f.addRow("Velocidad", self.speed)
        self.hk_read = QLineEdit(); self.hk_pause = QLineEdit()
        f.addRow("Atajo: leer selección", self._hk_row(self.hk_read)); f.addRow("Atajo: pausar / reanudar", self._hk_row(self.hk_pause))
        self.mini = QCheckBox("Mostrar mini reproductor flotante"); f.addRow("", self.mini)
        self.autostart = QCheckBox("Iniciar Lector Libre con Windows"); f.addRow("", self.autostart)
        test = QPushButton("🔊  Probar voz"); test.clicked.connect(self._test); f.addRow("", test)
        bb = QDialogButtonBox(); ok = bb.addButton("Guardar", QDialogButtonBox.AcceptRole); ok.setObjectName("primary")
        bb.addButton("Cancelar", QDialogButtonBox.RejectRole); bb.accepted.connect(self._save); bb.rejected.connect(self.reject)
        f.addRow(bb); self.load()

    def _hk_row(self, edit):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.addWidget(edit)
        b = QPushButton("Grabar"); b.setToolTip("Tocá y apretá la combinación de teclas"); h.addWidget(b)
        def rec():
            edit.setEnabled(False); edit.setText("Apretá las teclas…")
            def run():
                try:
                    import keyboard; t = keyboard.read_hotkey(suppress=False)
                except Exception as e: log("read_hotkey", e); t = ""
                self.hk.got.emit(edit, t)
            threading.Thread(target=run, daemon=True).start()
        b.clicked.connect(rec); return w

    def _fill_voices(self):
        edge = self.engine.currentData() == "edge"
        for box, lst, key in ((self.v_es, EDGE_ES if edge else KOKORO_ES, "edge_es" if edge else "voice_es"),
                              (self.v_en, EDGE_EN if edge else KOKORO_EN, "edge_en" if edge else "voice_en")):
            box.clear()
            for v in lst: box.addItem(voice_label(v), v)
            box.setCurrentIndex(max(0, box.findData(cfg.get(key))))

    def load(self):
        self.engine.setCurrentIndex(max(0, self.engine.findData(cfg.get("engine")))); self._fill_voices()
        self.lang.setCurrentIndex(max(0, self.lang.findData(cfg.get("lang_default"))))
        self.auto.setChecked(cfg.get("autodetect", True))
        self.speed.setCurrentIndex(max(0, self.speed.findData(round(cfg.get("speed", 1.0) * 4) / 4)))
        self.hk_read.setText(cfg["hk_read"]); self.hk_pause.setText(cfg["hk_pause"])
        self.mini.setChecked(cfg.get("mini", True)); self.autostart.setChecked(cfg.get("autostart", False))
    refresh_engine_ui = load

    def _apply(self):
        edge = self.engine.currentData() == "edge"
        cfg["engine"] = self.engine.currentData()
        cfg["edge_es" if edge else "voice_es"] = self.v_es.currentData()
        cfg["edge_en" if edge else "voice_en"] = self.v_en.currentData()
        cfg["lang_default"] = self.lang.currentData(); cfg["autodetect"] = self.auto.isChecked()
        cfg["speed"] = self.speed.currentData()

    def _test(self):
        old = dict(cfg); self._apply()
        def run():
            try:
                import sounddevice as sd, numpy as np
                a = np.concatenate([engine.synth("Hola, soy tu lector.", "es", cfg["speed"]),
                                    np.zeros(6000, np.float32), engine.synth("Hello, I am your reader.", "en", cfg["speed"])])
                sd.play(a, SR); sd.wait()
            except Exception as e: log("probar voz", repr(e))
            finally: cfg.clear(); cfg.update(old)
        if cfg["engine"] == "kokoro" and not models_ready():
            cfg.clear(); cfg.update(old)
            QMessageBox.information(self, APP, "La voz local todavía no está descargada."); return
        threading.Thread(target=run, daemon=True).start()

    def _save(self):
        r, p = self.hk_read.text().strip().lower(), self.hk_pause.text().strip().lower()
        try:
            import keyboard
            for h in (r, p): keyboard.parse_hotkey(h)
        except Exception:
            QMessageBox.warning(self, APP, "Uno de los atajos no es válido. Probá con algo como ctrl+alt+r."); return
        if r == p: QMessageBox.warning(self, APP, "Los dos atajos no pueden ser iguales."); return
        self._apply(); cfg.update(hk_read=r, hk_pause=p, mini=self.mini.isChecked(), autostart=self.autostart.isChecked())
        save_cfg(); self.accept(); self.on_saved()
