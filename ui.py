# Lector Libre - interfaz rediseñada (PySide6)
import os, re, threading
from PIL import Image
from PySide6.QtCore import Qt, QObject, Signal, QEventLoop, QTimer, QPoint, QPointF, QRect, QRectF, QSize
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QFont, QAction, QTextCursor, QTextFormat,
    QGuiApplication, QLinearGradient, QRadialGradient, QPainterPath, QPolygonF, QCursor
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QProgressDialog, QDialog, QLineEdit, QFileDialog, QInputDialog, QMessageBox,
    QListWidget, QListWidgetItem, QCheckBox, QFormLayout, QDialogButtonBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QSlider, QMenu
)
from core import *

ACCENT = "#7c5cff"
QSS = """
* { font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 10pt; color: #ececf4; }
QMainWindow, QDialog, QWidget#win { background: #0f1117; }
QFrame#headerBar {
    background: #161821;
    border-bottom: 1px solid #242838;
}
QFrame#readerCard {
    background: #151821;
    border: 1px solid #232736;
    border-radius: 14px;
}
QFrame#sideCard {
    background: #141720;
    border: 1px solid #232736;
    border-radius: 14px;
}
QFrame#bottomPlayer {
    background: #161924;
    border-top: 1px solid #262a3b;
}
QPushButton {
    background: #212534;
    border: 1px solid rgba(255, 255, 255, 16);
    border-radius: 9px;
    padding: 6px 12px;
    color: #e6e6f2;
    font-weight: 500;
}
QPushButton:hover {
    background: #2c3146;
    border-color: rgba(124, 92, 255, 110);
}
QPushButton#ghost {
    background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(255, 255, 255, 14);
    border-radius: 9px;
    padding: 6px 11px;
}
QPushButton#ghost:hover {
    background: rgba(124, 92, 255, 42);
    border-color: rgba(143, 116, 255, 120);
}
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9072ff, stop:1 #6c47ff);
    border: 1px solid rgba(255, 255, 255, 55);
    font-weight: 600;
    color: #ffffff;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a086ff, stop:1 #7b58ff);
}
QTextEdit#editor {
    background: transparent;
    border: none;
    selection-background-color: #7c5cff;
    color: #ececf4;
}
QListWidget, QLineEdit, QComboBox, QTableWidget {
    background: #181b26;
    border: 1px solid #282d40;
    border-radius: 10px;
    padding: 6px 10px;
    selection-background-color: #7c5cff;
}
QLineEdit:focus, QComboBox:focus, QTableWidget:focus, QListWidget:focus {
    border-color: #7c5cff;
}
QComboBox QAbstractItemView {
    background: #181b26;
    border: 1px solid #2e3348;
    selection-background-color: #7c5cff;
    padding: 4px;
}
QComboBox::drop-down { border: none; width: 18px; }
QListWidget::item { padding: 8px 10px; border-radius: 8px; margin-bottom: 2px; }
QListWidget::item:hover { background: rgba(255, 255, 255, 10); }
QListWidget::item:selected { background: rgba(124, 92, 255, 65); color: #ffffff; font-weight: 600; }
QMenu {
    background: #181b26;
    border: 1px solid #2c3146;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item { padding: 7px 20px; border-radius: 7px; }
QMenu::item:selected { background: #7c5cff; color: #ffffff; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border-radius: 5px;
    border: 1px solid #484e68;
    background: #181b26;
}
QCheckBox::indicator:hover { border-color: #8f74ff; }
QCheckBox::indicator:checked {
    background: #7c5cff;
    border-color: #9c82ff;
}
QProgressBar { background: #181b26; border: none; border-radius: 6px; text-align: center; height: 12px; }
QProgressBar::chunk { background: #7c5cff; border-radius: 6px; }
QSlider::groove:horizontal {
    height: 6px;
    background: #25293a;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c5cff, stop:1 #a890ff);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #7c5cff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #e6dfff;
    transform: scale(1.1);
}
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar::handle:vertical { background: #2c3146; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3d4460; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QTabWidget::pane { border: 1px solid #262b3d; border-radius: 12px; background: #141720; top: -1px; }
QTabBar::tab {
    background: #181b26;
    border: 1px solid #262b3d;
    padding: 8px 18px;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    margin-right: 6px;
    color: #a6abc2;
}
QTabBar::tab:selected {
    background: #7c5cff;
    border-color: #7c5cff;
    color: #ffffff;
    font-weight: 600;
}
QHeaderView::section {
    background: #1f2332;
    border: none;
    border-bottom: 1px solid #2d3246;
    padding: 8px 10px;
    font-weight: 600;
    color: #cfd3e6;
}
"""

def make_icon():
    p = res("icon.ico")
    if os.path.isfile(p):
        return QIcon(p)
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    g = QPainter(pix)
    g.setRenderHint(QPainter.Antialiasing)
    g.setBrush(QColor(ACCENT))
    g.setPen(Qt.NoPen)
    g.drawEllipse(2, 2, 60, 60)
    g.setPen(QPen(Qt.white, 4, cap=Qt.RoundCap))
    for i, h in enumerate((10, 22, 30, 22, 10)):
        x = 16 + i * 8
        g.drawLine(x, 32 - h // 2, x, 32 + h // 2)
    g.end()
    return QIcon(pix)

def vec_icon(kind, size=16, color="#ededf7"):
    pix = QPixmap(size * 2, size * 2)
    pix.setDevicePixelRatio(2.0)
    pix.fill(Qt.transparent)
    g = QPainter(pix)
    g.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    g.setPen(Qt.NoPen)
    g.setBrush(c)
    s = float(size)
    stroke = QPen(c, 1.65, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    if kind == "play":
        g.drawPolygon(QPolygonF([QPointF(s * 0.30, s * 0.20), QPointF(s * 0.30, s * 0.80), QPointF(s * 0.80, s * 0.50)]))
    elif kind == "pause":
        g.drawRoundedRect(QRectF(s * 0.26, s * 0.22, s * 0.16, s * 0.56), 1.5, 1.5)
        g.drawRoundedRect(QRectF(s * 0.58, s * 0.22, s * 0.16, s * 0.56), 1.5, 1.5)
    elif kind == "stop":
        g.drawRoundedRect(QRectF(s * 0.26, s * 0.26, s * 0.48, s * 0.48), 2.0, 2.0)
    elif kind == "prev":
        g.drawRoundedRect(QRectF(s * 0.22, s * 0.24, s * 0.10, s * 0.52), 1.0, 1.0)
        g.drawPolygon(QPolygonF([QPointF(s * 0.76, s * 0.24), QPointF(s * 0.76, s * 0.76), QPointF(s * 0.36, s * 0.50)]))
    elif kind == "next":
        g.drawRoundedRect(QRectF(s * 0.68, s * 0.24, s * 0.10, s * 0.52), 1.0, 1.0)
        g.drawPolygon(QPolygonF([QPointF(s * 0.24, s * 0.24), QPointF(s * 0.24, s * 0.76), QPointF(s * 0.64, s * 0.50)]))
    elif kind == "paste":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawRoundedRect(QRectF(s * 0.22, s * 0.22, s * 0.56, s * 0.64), 2.0, 2.0)
        g.setBrush(c)
        g.drawRoundedRect(QRectF(s * 0.36, s * 0.12, s * 0.28, s * 0.14), 1.2, 1.2)
    elif kind == "folder":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(s * 0.14, s * 0.28)
        path.lineTo(s * 0.40, s * 0.28)
        path.lineTo(s * 0.48, s * 0.38)
        path.lineTo(s * 0.86, s * 0.38)
        path.lineTo(s * 0.86, s * 0.78)
        path.lineTo(s * 0.14, s * 0.78)
        path.closeSubpath()
        g.drawPath(path)
    elif kind == "globe":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawEllipse(QRectF(s * 0.16, s * 0.16, s * 0.68, s * 0.68))
        g.drawEllipse(QRectF(s * 0.34, s * 0.16, s * 0.32, s * 0.68))
        g.drawLine(QPointF(s * 0.18, s * 0.50), QPointF(s * 0.82, s * 0.50))
    elif kind == "page":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawRoundedRect(QRectF(s * 0.20, s * 0.15, s * 0.60, s * 0.70), 2.0, 2.0)
        g.drawLine(QPointF(s * 0.32, s * 0.35), QPointF(s * 0.68, s * 0.35))
        g.drawLine(QPointF(s * 0.32, s * 0.51), QPointF(s * 0.68, s * 0.51))
        g.drawLine(QPointF(s * 0.32, s * 0.67), QPointF(s * 0.54, s * 0.67))
    elif kind == "ocr":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        for x0, dx in ((0.18, 0.16), (0.82, -0.16)):
            for y0, dy in ((0.18, 0.16), (0.82, -0.16)):
                g.drawLine(QPointF(s * x0, s * y0), QPointF(s * (x0 + dx), s * y0))
                g.drawLine(QPointF(s * x0, s * y0), QPointF(s * x0, s * (y0 + dy)))
        g.drawEllipse(QPointF(s * 0.50, s * 0.50), s * 0.14, s * 0.14)
    elif kind == "bookmark":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(s * 0.26, s * 0.16)
        path.lineTo(s * 0.74, s * 0.16)
        path.lineTo(s * 0.74, s * 0.84)
        path.lineTo(s * 0.50, s * 0.66)
        path.lineTo(s * 0.26, s * 0.84)
        path.closeSubpath()
        g.drawPath(path)
    elif kind == "export":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawLine(QPointF(s * 0.50, s * 0.18), QPointF(s * 0.50, s * 0.64))
        g.drawLine(QPointF(s * 0.32, s * 0.48), QPointF(s * 0.50, s * 0.66))
        g.drawLine(QPointF(s * 0.68, s * 0.48), QPointF(s * 0.50, s * 0.66))
        g.drawLine(QPointF(s * 0.22, s * 0.80), QPointF(s * 0.78, s * 0.80))
    elif kind == "history":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawEllipse(QRectF(s * 0.16, s * 0.16, s * 0.68, s * 0.68))
        g.drawLine(QPointF(s * 0.50, s * 0.32), QPointF(s * 0.50, s * 0.52))
        g.drawLine(QPointF(s * 0.50, s * 0.52), QPointF(s * 0.65, s * 0.60))
    elif kind == "settings":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        for idx, y in enumerate((0.28, 0.50, 0.72)):
            g.drawLine(QPointF(s * 0.18, s * y), QPointF(s * 0.82, s * y))
            cx = s * (0.36 if idx % 2 == 0 else 0.64)
            g.setBrush(QColor("#161821"))
            g.drawEllipse(QPointF(cx, s * y), s * 0.09, s * 0.09)
    elif kind == "chapters":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        for y in (0.28, 0.50, 0.72):
            g.drawLine(QPointF(s * 0.36, s * y), QPointF(s * 0.82, s * y))
            g.drawEllipse(QPointF(s * 0.21, s * y), s * 0.04, s * 0.04)
    elif kind == "window":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawRoundedRect(QRectF(s * 0.16, s * 0.20, s * 0.68, s * 0.60), 2.0, 2.0)
        g.drawLine(QPointF(s * 0.16, s * 0.36), QPointF(s * 0.84, s * 0.36))
    elif kind == "volume":
        g.setPen(stroke); g.setBrush(c)
        g.drawPolygon(QPolygonF([
            QPointF(s * 0.18, s * 0.40), QPointF(s * 0.34, s * 0.40),
            QPointF(s * 0.54, s * 0.22), QPointF(s * 0.54, s * 0.78),
            QPointF(s * 0.34, s * 0.60), QPointF(s * 0.18, s * 0.60)
        ]))
        g.setBrush(Qt.NoBrush)
        g.drawArc(QRectF(s * 0.42, s * 0.30, s * 0.32, s * 0.40), -60 * 16, 120 * 16)
    elif kind == "expand":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawLine(QPointF(s * 0.56, s * 0.44), QPointF(s * 0.78, s * 0.22))
        g.drawLine(QPointF(s * 0.58, s * 0.22), QPointF(s * 0.78, s * 0.22))
        g.drawLine(QPointF(s * 0.78, s * 0.22), QPointF(s * 0.78, s * 0.42))
        g.drawLine(QPointF(s * 0.44, s * 0.56), QPointF(s * 0.22, s * 0.78))
        g.drawLine(QPointF(s * 0.42, s * 0.78), QPointF(s * 0.22, s * 0.78))
        g.drawLine(QPointF(s * 0.22, s * 0.78), QPointF(s * 0.22, s * 0.58))
    elif kind == "collapse":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawLine(QPointF(s * 0.80, s * 0.20), QPointF(s * 0.56, s * 0.44))
        g.drawLine(QPointF(s * 0.56, s * 0.26), QPointF(s * 0.56, s * 0.44))
        g.drawLine(QPointF(s * 0.56, s * 0.44), QPointF(s * 0.74, s * 0.44))
        g.drawLine(QPointF(s * 0.20, s * 0.80), QPointF(s * 0.44, s * 0.56))
        g.drawLine(QPointF(s * 0.44, s * 0.74), QPointF(s * 0.44, s * 0.56))
        g.drawLine(QPointF(s * 0.44, s * 0.56), QPointF(s * 0.26, s * 0.56))
    elif kind == "close":
        g.setPen(stroke)
        g.drawLine(QPointF(s * 0.28, s * 0.28), QPointF(s * 0.72, s * 0.72))
        g.drawLine(QPointF(s * 0.72, s * 0.28), QPointF(s * 0.28, s * 0.72))
    elif kind == "mic":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawRoundedRect(QRectF(s * 0.36, s * 0.16, s * 0.28, s * 0.44), s * 0.14, s * 0.14)
        g.drawArc(QRectF(s * 0.24, s * 0.30, s * 0.52, s * 0.42), -180 * 16, 180 * 16)
        g.drawLine(QPointF(s * 0.50, s * 0.72), QPointF(s * 0.50, s * 0.86))
        g.drawLine(QPointF(s * 0.34, s * 0.86), QPointF(s * 0.66, s * 0.86))
    elif kind == "help":
        g.setPen(stroke); g.setBrush(Qt.NoBrush)
        g.drawEllipse(QRectF(s * 0.16, s * 0.16, s * 0.68, s * 0.68))
        g.drawArc(QRectF(s * 0.36, s * 0.28, s * 0.28, s * 0.22), 0 * 16, 180 * 16)
        g.drawLine(QPointF(s * 0.64, s * 0.39), QPointF(s * 0.50, s * 0.52))
        g.drawLine(QPointF(s * 0.50, s * 0.52), QPointF(s * 0.50, s * 0.57))
        g.setPen(Qt.NoPen); g.setBrush(c)
        g.drawEllipse(QPointF(s * 0.50, s * 0.69), s * 0.045, s * 0.045)
    elif kind == "sparkle":
        g.setPen(Qt.NoPen); g.setBrush(c)
        g.drawPolygon(QPolygonF([
            QPointF(s * 0.50, s * 0.14), QPointF(s * 0.60, s * 0.40),
            QPointF(s * 0.86, s * 0.50), QPointF(s * 0.60, s * 0.60),
            QPointF(s * 0.50, s * 0.86), QPointF(s * 0.40, s * 0.60),
            QPointF(s * 0.14, s * 0.50), QPointF(s * 0.40, s * 0.40),
        ]))
    g.end()
    return QIcon(pix)

def voices_for_engine(eng=None):
    eng = eng or cfg.get("engine", "kokoro")
    if eng == "edge":
        return (EDGE_ES, EDGE_EN, "edge_es", "edge_en")
    if eng == "piper":
        pes, pen = get_piper_lists()
        return (pes, pen, "piper_es", "piper_en")
    kes_l, ken_l = get_kokoro_lists()
    return (kes_l, ken_l, "voice_es", "voice_en")

def hide_on_close(w):
    w.closeEvent = lambda e: (e.ignore(), w.hide())

def format_eta_seconds(sec):
    if sec <= 5:
        return "menos de 5 s"
    if sec < 60:
        return f"~{int(round(sec / 5.0) * 5)} s"
    mins = int(round(sec / 60.0))
    return f"~{max(1, mins)} min"

# ---------- progreso en segundo plano ----------
class _Bridge(QObject):
    prog = Signal(int, int, str)
    done = Signal(bool, object)

def run_with_progress(parent, title, fn):
    dlg = QProgressDialog(title, None, 0, 100, parent)
    dlg.setWindowTitle(APP)
    dlg.setMinimumWidth(380)
    dlg.setMinimumDuration(0)
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.setAutoClose(False)
    dlg.setAutoReset(False)
    br = _Bridge()
    loop = QEventLoop()
    out = {}

    def on_prog(d, t, label):
        if t > 0:
            dlg.setMaximum(100)
            dlg.setValue(int(d * 100 / t))
            extra = f"  {d / 1e6:.0f} de {t / 1e6:.0f} MB" if t > 5e6 else ""
        else:
            dlg.setMaximum(0)
            extra = ""
        dlg.setLabelText(f"{label}{extra}")

    def on_done(ok, r):
        out["r"] = (ok, r)
        loop.quit()

    br.prog.connect(on_prog)
    br.done.connect(on_done)

    def work():
        try:
            br.done.emit(True, fn(lambda d, t, l="": br.prog.emit(int(d), int(t), str(l))))
        except Exception as e:
            log("run_with_progress", repr(e))
            br.done.emit(False, e)

    threading.Thread(target=work, daemon=True).start()
    dlg.show()
    loop.exec()
    dlg.close()
    return out["r"]

# ---------- selector de zona de pantalla para OCR (#5) ----------
class ScreenOcrSelector(QWidget):
    area_captured = Signal(object)

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self._origin = None
        self._current = None
        self._screen_pixmap = None
        self._virt_geo = QRect()

    def start_capture(self):
        scr = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self._virt_geo = scr.geometry()
        self._screen_pixmap = scr.grabWindow(0)
        self.setGeometry(self._virt_geo)
        self._origin = None
        self._current = None
        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, e):
        g = QPainter(self)
        g.setRenderHint(QPainter.Antialiasing)
        if self._screen_pixmap:
            g.drawPixmap(0, 0, self._screen_pixmap)
        g.fillRect(self.rect(), QColor(10, 12, 18, 145))

        if self._origin and self._current:
            sel = QRect(self._origin, self._current).normalized()
            if self._screen_pixmap and sel.width() > 2 and sel.height() > 2:
                dpr = self._screen_pixmap.devicePixelRatio()
                src_r = QRect(int(sel.x() * dpr), int(sel.y() * dpr), int(sel.width() * dpr), int(sel.height() * dpr))
                g.drawPixmap(sel, self._screen_pixmap, src_r)
            g.setPen(QPen(QColor(ACCENT), 2))
            g.setBrush(Qt.NoBrush)
            g.drawRect(sel)
        else:
            g.setPen(QColor("#ffffff"))
            g.setFont(QFont("Segoe UI", 13, QFont.Bold))
            g.drawText(
                self.rect(),
                Qt.AlignTop | Qt.AlignHCenter,
                "\nArrastrá el mouse sobre la zona de texto que querés leer (Esc para cancelar)",
            )

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._origin = e.position().toPoint()
            self._current = self._origin
            self.update()
        elif e.button() == Qt.RightButton:
            self.hide()

    def mouseMoveEvent(self, e):
        if self._origin:
            self._current = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._origin and self._current:
            sel = QRect(self._origin, self._current).normalized()
            self.hide()
            if sel.width() > 12 and sel.height() > 10 and self._screen_pixmap:
                dpr = self._screen_pixmap.devicePixelRatio()
                cropped = self._screen_pixmap.copy(
                    int(sel.x() * dpr), int(sel.y() * dpr), int(sel.width() * dpr), int(sel.height() * dpr)
                )
                qimg = cropped.toImage().convertToFormat(cropped.toImage().Format.Format_RGBA8888)
                w, h = qimg.width(), qimg.height()
                ptr = qimg.constBits()
                pil_img = Image.frombytes("RGBA", (w, h), bytes(ptr), "raw", "RGBA").convert("RGB")
                self.area_captured.emit(pil_img)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.hide()


# ---------- mini reproductor y botón flotante (#3 y #6) ----------
class WaveformBadge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.playing = False
        self._phase = 0
        self.setFixedSize(26, 28)
        self._timer = QTimer(self, interval=120, timeout=self._tick)

    def set_playing(self, p):
        self.playing = p
        if p:
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self):
        self._phase = (self._phase + 1) % 5
        self.update()

    def paintEvent(self, e):
        g = QPainter(self)
        g.setRenderHint(QPainter.Antialiasing)
        if self.playing:
            base = [8, 16, 12, 18, 10]
            bars = base[self._phase:] + base[:self._phase]
        else:
            bars = (4, 6, 4, 6, 4)
        pen = QPen(QColor("#a892ff" if self.playing else "#6e718a"), 2.4, Qt.SolidLine, Qt.RoundCap)
        g.setPen(pen)
        cy = self.height() / 2.0
        for idx, h in enumerate(bars):
            x = 3 + idx * 5
            g.drawLine(QPointF(x, cy - h / 2.0), QPointF(x, cy + h / 2.0))


class MiniPlayer(QWidget):
    settings_changed = Signal()

    def __init__(self, player, on_read_sel=None, on_read_page=None, on_ocr=None, on_open_reader=None):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.player = player
        self.on_read_sel = on_read_sel
        self.on_read_page = on_read_page
        self.on_ocr = on_ocr
        self.on_open_reader = on_open_reader
        self._drag = None
        self.compact = bool(cfg.get("mini_compact", False))
        self.progress = 0.0
        self.hide_timer = QTimer(self, singleShot=True, interval=4000, timeout=self._auto_hide)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        self.card = QWidget(self)
        outer.addWidget(self.card)
        self.lay = QHBoxLayout(self.card)
        self.lay.setSpacing(6)

        def icon_btn(kind, tip, cb, primary=False, small=False):
            b = QPushButton()
            b.setToolTip(tip)
            b.clicked.connect(cb)
            b.setCursor(Qt.PointingHandCursor)
            s = 38 if primary else (28 if small else 32)
            ic_sz = 18 if primary else (14 if small else 15)
            b.setFixedSize(s, s)
            b.setIcon(vec_icon(kind, ic_sz, "#ffffff" if primary else "#d8d8ea"))
            b.setIconSize(QSize(ic_sz, ic_sz))
            if primary:
                b.setStyleSheet(
                    f"QPushButton{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #9478ff,stop:1 #6c47ff);"
                    f"border:1px solid rgba(255,255,255,65);border-radius:{s//2}px;padding:0}}"
                    f"QPushButton:hover{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #a48cff,stop:1 #7b58ff)}}"
                )
            else:
                b.setStyleSheet(
                    f"QPushButton{{background:rgba(255,255,255,11);border:1px solid rgba(255,255,255,18);border-radius:{s//2}px;padding:0}}"
                    f"QPushButton:hover{{background:rgba(124,92,255,55);border-color:rgba(143,116,255,120)}}"
                )
            self.lay.addWidget(b)
            return b

        def v_sep():
            f = QFrame(self.card)
            f.setFixedSize(1, 22)
            f.setStyleSheet("background:rgba(255,255,255,22);border:none")
            self.lay.addWidget(f)
            return f

        # 1. Grupo Transporte (unido y coherente)
        self.b_prev = icon_btn("prev", "Oración anterior", player.prev)
        self.b_play = icon_btn("play", "Leer selección / desde el cursor o Pausar", self._on_play_clicked, primary=True)
        self.wave = WaveformBadge(self.card)
        self.lay.addWidget(self.wave)
        self.b_next = icon_btn("next", "Oración siguiente", player.next)
        self.b_stop = icon_btn("stop", "Detener", player.stop)

        self.sep1 = v_sep()

        # 2. Estado y vista previa de oración (ancho generoso sin recorte)
        self.txt_wrap = QWidget(self.card)
        txt_box = QVBoxLayout(self.txt_wrap)
        txt_box.setContentsMargins(4, 0, 4, 0)
        txt_box.setSpacing(1)
        self.badge = QLabel("LISTO PARA LEER")
        self.badge.setStyleSheet("color:#a690ff;font-size:7.5pt;font-weight:700;letter-spacing:0.6px")
        txt_box.addWidget(self.badge)
        self.lbl = QLabel("Tocá ▶ para leer selección o cursor")
        self.lbl.setFixedWidth(235)
        self.lbl.setStyleSheet("color:#ededf7;font-size:9.5pt;font-weight:500")
        txt_box.addWidget(self.lbl)
        self.lay.addWidget(self.txt_wrap)

        self.sep2 = v_sep()

        # 3. Acciones de captura rápida (Página activa, OCR, Abrir ventana principal)
        self.b_page = icon_btn("page", "Leer esta página o formulario activo (1 clic)", lambda: self.on_read_page() if self.on_read_page else None, small=True)
        self.b_ocr = icon_btn("ocr", "Capturar zona de pantalla con OCR", lambda: self.on_ocr() if self.on_ocr else None, small=True)
        self.b_win = icon_btn("window", "Abrir ventana principal del lector", lambda: self.on_open_reader() if self.on_open_reader else None, small=True)

        self.sep3 = v_sep()

        # 4. Velocidad y Voz
        combo_qss = (
            "QComboBox{background:rgba(255,255,255,13);border:1px solid rgba(255,255,255,22);"
            "border-radius:13px;padding:4px 10px;color:#e6e6f2;font-size:9pt;font-weight:500}"
            "QComboBox:hover{background:rgba(255,255,255,22);border-color:rgba(143,116,255,140)}"
            "QComboBox::drop-down{border:none;width:16px}"
        )
        self.speed = QComboBox()
        self.speed.setToolTip("Velocidad (con tono natural)")
        self.speed.setFixedWidth(68)
        self.speed.setStyleSheet(combo_qss)
        for i in range(2, 17):
            self.speed.addItem(f"{i / 4:g}×", i / 4)
        self._set_speed_combo()
        self.speed.activated.connect(self._speed_chosen)
        self.lay.addWidget(self.speed)

        self.voice = QComboBox()
        self.voice.setToolTip("Voz (cambio en vivo sin reiniciar oración)")
        self.voice.setMinimumWidth(124)
        self.voice.setStyleSheet(combo_qss)
        self.voice.activated.connect(self._voice_chosen)
        self.lay.addWidget(self.voice)

        self.b_mode = icon_btn("expand" if self.compact else "collapse", "Alternar modo compacto / expandido", self.toggle_compact, small=True)
        self.b_close = icon_btn("close", "Ocultar flotante", self.hide, small=True)

        # En modo compacto dejamos SOLO el botón Play/Pause, la onda animada y el botón de expandir
        self._expanded_only = (
            self.b_prev, self.b_next, self.b_stop, self.sep1, self.txt_wrap,
            self.sep2, self.b_page, self.b_ocr, self.b_win, self.sep3,
            self.speed, self.voice, self.b_close
        )
        self.refresh_voices()
        player.sentence_started.connect(self._on_sentence)
        player.state_changed.connect(self._on_state)
        player.finished.connect(lambda: self.hide_timer.start())
        self._apply_mode(init=True)
        self._place()

    def _on_play_clicked(self):
        if self.player.state == "stopped" and self.on_read_sel:
            self.on_read_sel()
        else:
            self.player.toggle_pause()

    def _speed_chosen(self, i):
        self.player.set_speed(self.speed.itemData(i))
        self.settings_changed.emit()

    def toggle_compact(self):
        self.compact = not self.compact
        cfg["mini_compact"] = self.compact
        save_cfg()
        self._apply_mode()

    def _apply_mode(self, init=False):
        right = self.geometry().right()
        for w in self._expanded_only:
            w.setVisible(not self.compact)
        self.wave.setVisible(self.compact)
        self.lay.setContentsMargins(*((8, 7, 10, 7) if self.compact else (12, 9, 12, 9)))
        self.b_mode.setIcon(vec_icon("expand" if self.compact else "collapse", 14, "#d8d8ea"))
        self.b_mode.setToolTip("Expandir mini reproductor" if self.compact else "Achicar a botón flotante compacto")
        self.card.adjustSize()
        self.adjustSize()
        if not init:
            scr = QGuiApplication.primaryScreen().availableGeometry()
            nx = max(scr.left() + 4, min(right - self.width() + 1, scr.right() - self.width() - 4))
            self.move(nx, self.y())
            cfg["mini_pos"] = [self.x(), self.y()]
            save_cfg()
        self.update()

    def _set_speed_combo(self):
        i = self.speed.findData(round(cfg.get("speed", 1.0) * 4) / 4)
        self.speed.setCurrentIndex(max(i, 0))

    def refresh_voices(self):
        es, en, kes, ken = voices_for_engine()
        self.voice.clear()
        for v in es + en:
            self.voice.addItem(voice_label(v), v)
        self.voice.insertSeparator(len(es))
        self.voice.setCurrentIndex(max(0, self.voice.findData(cfg.get(kes))))
        self._set_speed_combo()

    def _voice_chosen(self, i):
        v = self.voice.itemData(i)
        if not v:
            return
        es, en, kes, ken = voices_for_engine()
        cfg[kes if v in es else ken] = v
        save_cfg()
        self.player.reset_voices()
        self.settings_changed.emit()

    def _place(self):
        pos = cfg.get("mini_pos")
        scr = QGuiApplication.primaryScreen().availableGeometry()
        if pos and any(s.availableGeometry().contains(QPoint(*pos)) for s in QGuiApplication.screens()):
            self.move(*pos)
        else:
            self.move(scr.center().x() - self.width() // 2, scr.bottom() - self.height() - 24)

    def paintEvent(self, e):
        g = QPainter(self)
        g.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.card.geometry())
        radius = r.height() / 2.0
        for i in range(5, 0, -1):
            er = r.adjusted(-i * 1.5, -i * 1.3 + 2, i * 1.5, i * 1.6 + 2)
            g.setPen(Qt.NoPen)
            g.setBrush(QColor(8, 9, 15, int(20 * (6 - i) / 5)))
            g.drawRoundedRect(er, radius + i, radius + i)

        grad = QLinearGradient(r.topLeft(), r.bottomLeft())
        grad.setColorAt(0.0, QColor(34, 37, 50, 246))
        grad.setColorAt(1.0, QColor(20, 22, 30, 248))
        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)
        g.fillPath(path, grad)

        glow = QRadialGradient(QPointF(r.left() + (28 if self.compact else 64), r.center().y()), 56)
        glow.setColorAt(0.0, QColor(124, 92, 255, 55))
        glow.setColorAt(1.0, QColor(124, 92, 255, 0))
        g.fillPath(path, glow)

        if not self.compact and self.player.state != "stopped" and self.progress > 0:
            g.save()
            g.setClipPath(path)
            track_h = 2.5
            track_r = QRectF(r.left() + 18, r.bottom() - track_h, r.width() - 36, track_h)
            g.fillRect(track_r, QColor(255, 255, 255, 18))
            prog_r = QRectF(track_r.left(), track_r.top(), track_r.width() * self.progress, track_h)
            pgrad = QLinearGradient(prog_r.topLeft(), prog_r.topRight())
            pgrad.setColorAt(0.0, QColor("#7c5cff"))
            pgrad.setColorAt(1.0, QColor("#b39dff"))
            g.fillRect(prog_r, pgrad)
            g.restore()

        bgrad = QLinearGradient(r.topLeft(), r.bottomLeft())
        bgrad.setColorAt(0.0, QColor(255, 255, 255, 48))
        bgrad.setColorAt(1.0, QColor(124, 92, 255, 36))
        g.setPen(QPen(bgrad, 1.1))
        g.setBrush(Qt.NoBrush)
        g.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            cfg["mini_pos"] = [self.x(), self.y()]
            save_cfg()

    def _on_sentence(self, i, a, b):
        n = max(1, len(self.player.chunks))
        t = self.player.chunks[i][0] if i < len(self.player.chunks) else ""
        self.badge.setText(f"LEYENDO  ·  {i + 1} / {n}")
        self.lbl.setText(self.lbl.fontMetrics().elidedText(f"«{t}»", Qt.ElideRight, 228))
        self.progress = (i + 1) / n
        self.hide_timer.stop()
        self.update()

    def _on_state(self, s):
        playing = s == "playing"
        self.b_play.setIcon(vec_icon("pause" if playing else "play", 18, "#ffffff"))
        self.wave.set_playing(playing)
        if s == "paused":
            self.badge.setText(self.badge.text().replace("LEYENDO", "EN PAUSA"))
            self.hide_timer.stop()
        elif s == "stopped":
            self.badge.setText("LISTO PARA LEER")
            self.lbl.setText("Tocá ▶ para leer selección o cursor")
            self.progress = 0.0
            if not self.compact:
                self.hide_timer.start()
        else:
            self.hide_timer.stop()
        self.update()

    def _auto_hide(self):
        if self.compact:
            return
        if self.underMouse() or self.player.state != "stopped":
            self.hide_timer.start()
        else:
            self.hide()


# ---------- Editor con doble clic para saltar a cualquier oración ----------
class JumpableTextEdit(QTextEdit):
    sentence_double_clicked = Signal(int)

    def mouseDoubleClickEvent(self, e):
        super().mouseDoubleClickEvent(e)
        if e.button() == Qt.LeftButton:
            cur = self.cursorForPosition(e.position().toPoint())
            self.sentence_double_clicked.emit(cur.position())


# ---------- Ventana principal estilo Estudio Moderno ----------
class ReaderWindow(QMainWindow):
    settings_changed = Signal()

    def __init__(self, player, on_export, on_export_audiobook, on_ocr, on_read_page, on_history, on_settings, ensure_ready, on_voice_studio=None, on_tutorial=None):
        super().__init__()
        self.setObjectName("win")
        self.player = player
        self.on_export = on_export
        self.on_export_audiobook = on_export_audiobook
        self.on_ocr = on_ocr
        self.on_read_page = on_read_page
        self.ensure_ready = ensure_ready
        self.on_voice_studio = on_voice_studio or on_settings
        self.on_tutorial = on_tutorial
        self.fuente = "Lector"
        self._last_sent_span = None
        self._epub_chapters = None
        self._pending_bookmark = None
        self._chapter_offsets = []
        self._slider_dragging = False

        self.setWindowTitle(APP)
        self.setWindowIcon(make_icon())
        self.resize(1100, 720)

        root_w = QWidget()
        root_w.setObjectName("win")
        root_lay = QVBoxLayout(root_w)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        self.setCentralWidget(root_w)

        # 1. Header Bar limpia con íconos vectoriales (sin desborde "...")
        header = QFrame()
        header.setObjectName("headerBar")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 10, 16, 10)
        h_lay.setSpacing(7)

        def top_btn(icon_name, text, cb, tip=""):
            b = QPushButton(f" {text}")
            b.setObjectName("ghost")
            b.setIcon(vec_icon(icon_name, 15, "#dcdcf0"))
            b.setIconSize(QSize(15, 15))
            b.setToolTip(tip or text)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(cb)
            h_lay.addWidget(b)
            return b

        self.b_chaps = top_btn("chapters", "Capítulos", self._toggle_chapters_panel, "Mostrar u ocultar índice de capítulos/secciones")
        top_btn("paste", "Pegar", self.paste, "Pegar texto del portapapeles")
        top_btn("folder", "Abrir archivo", self.open_file, "Abrir TXT, PDF, Word (.docx) o libro ePub (.epub)")
        top_btn("globe", "Web / URL", self.open_url, "Extraer artículo o formulario desde una dirección web")
        top_btn("page", "Leer página", self.on_read_page, "Extraer y leer la pestaña del navegador o formulario activo")
        top_btn("ocr", "OCR", self.on_ocr, "Seleccionar una zona de la pantalla para leer texto en imágenes")

        h_lay.addStretch(1)

        top_btn("bookmark", "Marcador", self.manual_bookmark, "Guardar posición actual para retomar más tarde")

        # Botón desplegable único para Exportar (Audio único o Audiolibro por capítulos)
        self.b_export = QPushButton(" Exportar ▾")
        self.b_export.setObjectName("ghost")
        self.b_export.setIcon(vec_icon("export", 15, "#dcdcf0"))
        self.b_export.setIconSize(QSize(15, 15))
        self.b_export.setCursor(Qt.PointingHandCursor)
        exp_menu = QMenu(self.b_export)
        exp_menu.addAction("Exportar como archivo único (MP3 / WAV)", lambda: self.on_export(self.edit.toPlainText()))
        exp_menu.addAction("Exportar audiolibro separado por capítulos", lambda: self.on_export_audiobook(self.edit.toPlainText(), self._epub_chapters))
        self.b_export.setMenu(exp_menu)
        h_lay.addWidget(self.b_export)

        top_btn("sparkle", "Mi Voz", self.on_voice_studio, "Abrir Estudio de Voz: clonar o diseñar tu propia voz por única vez")
        top_btn("history", "Historial", on_history, "Ver historial de lecturas y marcadores guardados")
        top_btn("settings", "Ajustes", on_settings, "Configurar motor de voz, atajos y diccionario de pronunciación")
        if self.on_tutorial:
            top_btn("help", "Tutorial", self.on_tutorial, "Ver guía interactiva y consejos de uso de Lector Libre")

        root_lay.addWidget(header)

        # 2. Cuerpo central (Banner de marcador + Panel lateral de capítulos + Lienzo de lectura)
        body_wrap = QWidget()
        body_v = QVBoxLayout(body_wrap)
        body_v.setContentsMargins(16, 12, 16, 12)
        body_v.setSpacing(10)

        self.resume_bar = QFrame()
        self.resume_bar.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #251f42,stop:1 #1d1a30);"
            "border:1px solid #5a46b8;border-radius:11px;padding:6px 12px}"
        )
        rb_lay = QHBoxLayout(self.resume_bar)
        rb_lay.setContentsMargins(8, 4, 8, 4)
        ic_bm = QLabel()
        ic_bm.setPixmap(vec_icon("bookmark", 16, "#b49eff").pixmap(16, 16))
        rb_lay.addWidget(ic_bm)
        self.resume_lbl = QLabel("")
        self.resume_lbl.setStyleSheet("color:#e6e1ff;font-weight:600;border:none;background:transparent")
        rb_lay.addWidget(self.resume_lbl, 1)
        b_res = QPushButton("Retomar desde ahí")
        b_res.setObjectName("primary")
        b_res.setIcon(vec_icon("play", 14, "#ffffff"))
        b_res.setCursor(Qt.PointingHandCursor)
        b_res.clicked.connect(self._resume_clicked)
        rb_lay.addWidget(b_res)
        b_ign = QPushButton()
        b_ign.setIcon(vec_icon("close", 13, "#cfcfe2"))
        b_ign.setFixedSize(30, 30)
        b_ign.clicked.connect(self.resume_bar.hide)
        rb_lay.addWidget(b_ign)
        self.resume_bar.hide()
        body_v.addWidget(self.resume_bar)

        split_h = QHBoxLayout()
        split_h.setSpacing(12)

        # Panel lateral de Capítulos / Secciones
        self.chap_panel = QFrame()
        self.chap_panel.setObjectName("sideCard")
        self.chap_panel.setFixedWidth(235)
        cp_lay = QVBoxLayout(self.chap_panel)
        cp_lay.setContentsMargins(12, 12, 12, 12)
        cp_lay.setSpacing(8)
        cp_title = QLabel("ÍNDICE / SECCIONES")
        cp_title.setStyleSheet("color:#8f95b2;font-size:8pt;font-weight:700;letter-spacing:0.8px")
        cp_lay.addWidget(cp_title)
        self.chap_list = QListWidget()
        self.chap_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chap_list.setWordWrap(True)
        self.chap_list.setStyleSheet("border:none;background:transparent;padding:0")
        self.chap_list.itemClicked.connect(self._on_chapter_clicked)
        cp_lay.addWidget(self.chap_list)
        split_h.addWidget(self.chap_panel)

        # Lienzo principal de lectura
        reader_card = QFrame()
        reader_card.setObjectName("readerCard")
        rc_lay = QVBoxLayout(reader_card)
        rc_lay.setContentsMargins(18, 12, 18, 12)
        rc_lay.setSpacing(6)

        meta_row = QHBoxLayout()
        self.doc_title_lbl = QLabel("Lector")
        self.doc_title_lbl.setStyleSheet("color:#a594ff;font-size:9pt;font-weight:700;letter-spacing:0.4px")
        meta_row.addWidget(self.doc_title_lbl)
        meta_row.addStretch()
        self.doc_stats_lbl = QLabel("Doble clic en cualquier oración para saltar a leer desde ahí")
        self.doc_stats_lbl.setStyleSheet("color:#7d829c;font-size:8.5pt")
        meta_row.addWidget(self.doc_stats_lbl)
        rc_lay.addLayout(meta_row)

        self.edit = JumpableTextEdit()
        self.edit.setObjectName("editor")
        self.edit.setAcceptRichText(False)
        self.edit.setFont(QFont("Segoe UI", 13))
        self.edit.document().setDocumentMargin(20)
        self.edit.setPlaceholderText(
            "Pegá o escribí un texto acá, abrí un archivo (TXT, PDF, Word, ePub), una página web o usá «OCR pantalla».\n\n"
            f"• Atajo leer selección o desde el cursor: {cfg['hk_read'].upper()}\n"
            f"• Atajo leer página activa del navegador: {cfg.get('hk_page', 'ctrl+alt+w').upper()}\n"
            f"• Atajo OCR de zona de la pantalla: {cfg.get('hk_ocr', 'ctrl+alt+o').upper()}"
        )
        self.edit.textChanged.connect(self._edited)
        self.edit.sentence_double_clicked.connect(self._on_text_double_clicked)
        rc_lay.addWidget(self.edit, 1)

        split_h.addWidget(reader_card, 1)
        body_v.addLayout(split_h, 1)
        root_lay.addWidget(body_wrap, 1)

        # 3. Barra de Reproducción Integrada Abajo (Bottom Player Dock)
        bottom = QFrame()
        bottom.setObjectName("bottomPlayer")
        bottom.setFixedHeight(78)
        b_lay = QHBoxLayout(bottom)
        b_lay.setContentsMargins(20, 10, 20, 10)
        b_lay.setSpacing(12)

        def dock_btn(kind, tip, cb, primary=False):
            b = QPushButton()
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(cb)
            s = 44 if primary else 34
            ic = 20 if primary else 15
            b.setFixedSize(s, s)
            b.setIcon(vec_icon(kind, ic, "#ffffff" if primary else "#dcdcf0"))
            b.setIconSize(QSize(ic, ic))
            if primary:
                b.setStyleSheet(
                    f"QPushButton{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #9478ff,stop:1 #6c47ff);"
                    f"border:1px solid rgba(255,255,255,65);border-radius:{s//2}px;padding:0}}"
                    f"QPushButton:hover{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #a48cff,stop:1 #7b58ff)}}"
                )
            else:
                b.setStyleSheet(
                    f"QPushButton{{background:#212534;border:1px solid rgba(255,255,255,16);border-radius:{s//2}px;padding:0}}"
                    f"QPushButton:hover{{background:#2e3348;border-color:rgba(143,116,255,120)}}"
                )
            b_lay.addWidget(b)
            return b

        self.b_dock_prev = dock_btn("prev", "Oración anterior", player.prev)
        self.b_dock_play = dock_btn("play", "Leer desde el cursor o Pausar", self.read_pause, primary=True)
        self.b_dock_next = dock_btn("next", "Oración siguiente", player.next)
        self.b_dock_stop = dock_btn("stop", "Detener lectura", player.stop)

        # Barra de progreso central interactiva + tiempo restante
        prog_col = QVBoxLayout()
        prog_col.setContentsMargins(8, 2, 8, 2)
        prog_col.setSpacing(4)
        top_prog = QHBoxLayout()
        self.dock_status_lbl = QLabel("Listo para leer")
        self.dock_status_lbl.setStyleSheet("color:#e2e4f0;font-size:9.5pt;font-weight:600")
        top_prog.addWidget(self.dock_status_lbl)
        top_prog.addStretch()
        self.dock_eta_lbl = QLabel("")
        self.dock_eta_lbl.setStyleSheet("color:#959bb8;font-size:8.5pt;font-weight:500")
        top_prog.addWidget(self.dock_eta_lbl)
        prog_col.addLayout(top_prog)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setToolTip("Arrastrá para saltar a cualquier oración del documento")
        self.slider.sliderPressed.connect(lambda: setattr(self, "_slider_dragging", True))
        self.slider.sliderReleased.connect(self._on_slider_released)
        prog_col.addWidget(self.slider)
        b_lay.addLayout(prog_col, 1)

        # Selectores sincronizados de Velocidad y Voz en la ventana principal
        self.dock_speed = QComboBox()
        self.dock_speed.setToolTip("Velocidad de lectura (tono natural)")
        self.dock_speed.setFixedWidth(78)
        for i in range(2, 17):
            self.dock_speed.addItem(f"{i / 4:g}×", i / 4)
        self.dock_speed.activated.connect(self._on_dock_speed)
        b_lay.addWidget(self.dock_speed)

        self.dock_voice = QComboBox()
        self.dock_voice.setToolTip("Voz activa")
        self.dock_voice.setMinimumWidth(155)
        self.dock_voice.activated.connect(self._on_dock_voice)
        b_lay.addWidget(self.dock_voice)

        root_lay.addWidget(bottom)

        self.refresh_voices()
        player.sentence_started.connect(self._on_sentence)
        player.word_started.connect(self._on_word)
        player.state_changed.connect(self._on_state)
        hide_on_close(self)

    def refresh_voices(self):
        es, en, kes, ken = voices_for_engine()
        self.dock_voice.clear()
        for v in es + en:
            self.dock_voice.addItem(voice_label(v), v)
        self.dock_voice.insertSeparator(len(es))
        self.dock_voice.setCurrentIndex(max(0, self.dock_voice.findData(cfg.get(kes))))
        idx_s = self.dock_speed.findData(round(cfg.get("speed", 1.0) * 4) / 4)
        self.dock_speed.setCurrentIndex(max(0, idx_s))
        self._update_doc_stats()

    def _on_dock_speed(self, i):
        self.player.set_speed(self.dock_speed.itemData(i))
        self._update_doc_stats()
        self.settings_changed.emit()

    def _on_dock_voice(self, i):
        v = self.dock_voice.itemData(i)
        if not v:
            return
        es, en, kes, ken = voices_for_engine()
        cfg[kes if v in es else ken] = v
        save_cfg()
        self.player.reset_voices()
        self.settings_changed.emit()

    def _toggle_chapters_panel(self):
        self.chap_panel.setVisible(not self.chap_panel.isVisible())

    def _rebuild_chapters_outline(self, text):
        self.chap_list.clear()
        self._chapter_offsets = []
        for m in re.finditer(r"(?m)^\s*(?:[#]{1,3}\s+.+|(?:Cap[íi]tulo|Chapter|Parte|Part|Secci[óo]n|Pregunta:)\s+[^\n]+)\s*$", text):
            title = re.sub(r"^[#\s]+", "", m.group(0)).strip()
            if len(title) > 2:
                self._chapter_offsets.append((title[:48], m.start()))
                self.chap_list.addItem(title[:48])
        has_chaps = len(self._chapter_offsets) >= 2
        self.chap_panel.setVisible(has_chaps)

    def _on_chapter_clicked(self, item):
        row = self.chap_list.row(item)
        if 0 <= row < len(self._chapter_offsets):
            _, pos = self._chapter_offsets[row]
            cur = self.edit.textCursor()
            cur.setPosition(pos)
            self.edit.setTextCursor(cur)
            self.edit.ensureCursorVisible()
            if self.player.state != "stopped" and self._mine():
                self.player.play(self.player.index_for_pos(pos))

    def _on_text_double_clicked(self, char_pos):
        text = self.edit.toPlainText()
        if not text.strip() or not self.ensure_ready():
            return
        if not self._mine() or not self.player.chunks:
            self.player.load(text, self.fuente)
            add_history(text, self.fuente)
        self.player.play(self.player.index_for_pos(char_pos))

    def _on_slider_released(self):
        self._slider_dragging = False
        val = self.slider.value()
        if self.player.chunks and 0 <= val < len(self.player.chunks):
            self.player.play(val)

    def _update_doc_stats(self):
        text = self.edit.toPlainText().strip()
        if not text:
            self.doc_stats_lbl.setText("Doble clic en cualquier oración para saltar a leer desde ahí")
            return
        words = len(text.split())
        spd = max(0.5, float(cfg.get("speed", 1.0)))
        total_sec = len(text) / (15.5 * spd)
        self.doc_stats_lbl.setText(f"{words} palabras  ·  Duración total {format_eta_seconds(total_sec)} ({spd:g}×)  ·  Doble clic salta de oración")

    def _mine(self):
        return self.player.text == self.edit.toPlainText()

    def _edited(self):
        text = self.edit.toPlainText()
        self._rebuild_chapters_outline(text)
        self._update_doc_stats()
        if self.player.state != "stopped" and not self._mine():
            self.edit.setExtraSelections([])

    def set_text(self, text, fuente, epub_chapters=None, jump_idx=None):
        self.fuente = fuente
        self._epub_chapters = epub_chapters
        self.doc_title_lbl.setText(fuente.upper())
        self.edit.setPlainText(text)
        self.edit.moveCursor(QTextCursor.Start)
        self._rebuild_chapters_outline(text)
        self._update_doc_stats()

        if jump_idx is not None:
            self.resume_bar.hide()
            chunks = split_text(text)
            if 0 <= jump_idx < len(chunks):
                _, a, _ = chunks[jump_idx]
                c = self.edit.textCursor()
                c.setPosition(a)
                self.edit.setTextCursor(c)
                self.edit.ensureCursorVisible()
            return

        bm = get_bookmark(text, fuente)
        if bm and bm.get("idx", 0) > 0:
            self._pending_bookmark = bm
            idx = bm.get("idx", 0)
            tot = bm.get("total", "?")
            self.resume_lbl.setText(f"Marcador guardado en «{fuente}» (oración {idx + 1} de {tot} · {bm.get('fecha', '')})")
            self.resume_bar.show()
        else:
            self._pending_bookmark = None
            self.resume_bar.hide()

    def _resume_clicked(self):
        bm = self._pending_bookmark
        self.resume_bar.hide()
        if not bm:
            return
        text = self.edit.toPlainText()
        if not text.strip() or not self.ensure_ready():
            return
        self.player.load(text, self.fuente)
        add_history(text, self.fuente)
        self.player.play(bm.get("idx", 0))

    def manual_bookmark(self):
        text = self.edit.toPlainText()
        if not text.strip():
            QMessageBox.information(self, APP, "No hay texto en el lector para guardar un marcador.")
            return
        chunks = split_text(text)
        if not chunks:
            return
        pos = self.edit.textCursor().position()
        idx = self.player.idx if (self.player.state != "stopped" and self._mine()) else 0
        if self.player.state == "stopped" or not self._mine():
            for i, (_, a, b) in enumerate(chunks):
                if pos <= b:
                    idx = i
                    break
        _, a, _ = chunks[min(idx, len(chunks) - 1)]
        save_bookmark(text, self.fuente, idx, a, len(chunks), note="Manual")
        self.dock_status_lbl.setText(f"Marcador guardado en oración {idx + 1} de {len(chunks)}")

    def paste(self):
        t = QApplication.clipboard().text()
        if t:
            self.set_text(t, "Portapapeles")

    def _load(self, fn, fuente):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            res_val = fn()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            log("abrir", repr(e))
            QMessageBox.warning(self, APP, f"No pude abrirlo:\n{str(e)[:200]}")
            return
        QApplication.restoreOverrideCursor()
        epub_chaps = None
        if isinstance(res_val, tuple):
            t, epub_chaps = res_val
        else:
            t = res_val
        if not t or not t.strip():
            QMessageBox.information(self, APP, "No encontré texto seleccionable. Podés usar el botón «OCR pantalla» para leerlo desde la imagen.")
            return
        self.set_text(t, fuente, epub_chapters=epub_chaps)

    def open_file(self):
        p, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir archivo",
            "",
            "Documentos y Libros (*.txt *.pdf *.docx *.epub *.md);;Todos (*.*)",
        )
        if not p:
            return
        ext = os.path.splitext(p)[1].lower()
        label = f"{ext[1:].upper()}: {os.path.basename(p)}"
        if ext == ".epub":
            def _load_epub():
                chaps = extract_epub_chapters(p)
                full_t = "\n\n".join(body for _, body in chaps).strip()
                return full_t, chaps
            self._load(_load_epub, label)
        else:
            self._load(lambda: extract_file(p), label)

    def open_url(self):
        u, ok = QInputDialog.getText(self, APP, "Pegá la dirección de la página o formulario:")
        if ok and u.strip():
            from urllib.parse import urlparse
            dom = urlparse(u if "://" in u else "https://" + u).netloc
            self._load(lambda: extract_url(u.strip()), f"Web: {dom}")

    def read_pause(self):
        if self.player.state != "stopped" and self._mine():
            self.player.toggle_pause()
            return
        text = self.edit.toPlainText()
        if not text.strip():
            return
        if not self.ensure_ready():
            return
        pos = self.edit.textCursor().position()
        self.player.load(text, self.fuente)
        add_history(text, self.fuente)
        self.player.play(self.player.index_for_pos(pos) if pos < len(text) - 1 else 0)

    def _apply_highlights(self, sent_span, word_span=None):
        sels = []
        if sent_span:
            a, b = sent_span
            s1 = QTextEdit.ExtraSelection()
            c1 = QColor(ACCENT)
            c1.setAlpha(60)
            s1.format.setBackground(c1)
            cur1 = self.edit.textCursor()
            cur1.setPosition(a)
            cur1.setPosition(b, QTextCursor.KeepAnchor)
            s1.cursor = cur1
            sels.append(s1)
        if word_span and cfg.get("word_highlight", True):
            wa, wb = word_span
            s2 = QTextEdit.ExtraSelection()
            c2 = QColor("#ffb84d")
            c2.setAlpha(195)
            s2.format.setBackground(c2)
            s2.format.setForeground(QColor("#111218"))
            cur2 = self.edit.textCursor()
            cur2.setPosition(wa)
            cur2.setPosition(wb, QTextCursor.KeepAnchor)
            s2.cursor = cur2
            sels.append(s2)
        self.edit.setExtraSelections(sels)

    def _on_sentence(self, i, a, b):
        n = max(1, len(self.player.chunks))
        eng_name = {"edge": "Voz online", "piper": "Piper local", "kokoro": "Kokoro local"}.get(cfg.get("engine"), "Voz local")
        self.slider.setMaximum(max(0, n - 1))
        if not self._slider_dragging:
            self.slider.setValue(i)

        rem_chars = sum(len(s) for s, _, _ in self.player.chunks[i:])
        spd = max(0.5, float(cfg.get("speed", 1.0)))
        rem_sec = rem_chars / (15.5 * spd)
        self.dock_status_lbl.setText(f"{eng_name}  ·  Oración {i + 1} de {n}")
        self.dock_eta_lbl.setText(f"Restan {format_eta_seconds(rem_sec)}")

        if not self._mine():
            return
        self._last_sent_span = (a, b)
        self._apply_highlights(self._last_sent_span, None)
        vc = QTextCursor(self.edit.document())
        vc.setPosition(b)
        self.edit.setTextCursor(vc)
        self.edit.ensureCursorVisible()

        # Sincronizar selección en el panel de capítulos
        if self._chapter_offsets:
            active_chap = 0
            for idx_c, (_, c_pos) in enumerate(self._chapter_offsets):
                if a >= c_pos:
                    active_chap = idx_c
            self.chap_list.setCurrentRow(active_chap)

    def _on_word(self, i, wa, wb):
        if not self._mine() or not self._last_sent_span:
            return
        self._apply_highlights(self._last_sent_span, (wa, wb))

    def _on_state(self, s):
        playing = s == "playing"
        self.b_dock_play.setIcon(vec_icon("pause" if playing else "play", 20, "#ffffff"))
        if s == "paused":
            self.dock_status_lbl.setText(self.dock_status_lbl.text().replace("Oración", "En pausa · Oración"))
        elif s == "stopped":
            self._last_sent_span = None
            self.edit.setExtraSelections([])
            self.dock_status_lbl.setText("Listo para leer")
            self.dock_eta_lbl.setText("")
            self.slider.setValue(0)


# ---------- historial y marcadores (#9) ----------
class HistoryWindow(QWidget):
    def __init__(self, open_cb):
        super().__init__()
        self.setObjectName("win")
        self.open_cb = open_cb
        self.setWindowTitle(f"Historial y Marcadores · {APP}")
        self.setWindowIcon(make_icon())
        self.resize(680, 540)

        l = QVBoxLayout(self)
        l.setContentsMargins(16, 16, 16, 16)
        self.tabs = QTabWidget()
        l.addWidget(self.tabs)

        w_bm = QWidget()
        lb = QVBoxLayout(w_bm)
        self.bm_list = QListWidget()
        self.bm_list.itemDoubleClicked.connect(lambda *_: self._open_bm())
        lb.addWidget(self.bm_list)
        hb = QHBoxLayout()
        lb.addLayout(hb)
        b_ret = QPushButton(" Retomar lectura donde quedé")
        b_ret.setObjectName("primary")
        b_ret.setIcon(vec_icon("play", 14, "#ffffff"))
        b_ret.clicked.connect(self._open_bm)
        hb.addWidget(b_ret)
        hb.addStretch()
        b_del = QPushButton("Borrar marcador")
        b_del.clicked.connect(self._del_bm)
        hb.addWidget(b_del)
        self.tabs.addTab(w_bm, "Marcadores (Retomar)")

        w_hi = QWidget()
        lh = QVBoxLayout(w_hi)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda *_: self._open())
        lh.addWidget(self.list)
        h = QHBoxLayout()
        lh.addLayout(h)
        b = QPushButton("Abrir en lector")
        b.setObjectName("primary")
        b.clicked.connect(self._open)
        h.addWidget(b)
        b = QPushButton("Copiar")
        b.clicked.connect(self._copy)
        h.addWidget(b)
        h.addStretch()
        b = QPushButton("Borrar historial")
        b.clicked.connect(self._clear)
        h.addWidget(b)
        self.tabs.addTab(w_hi, "Historial de lecturas")

        hide_on_close(self)

    def refresh(self):
        self.bm_list.clear()
        bms = sorted(load_bookmarks().values(), key=lambda x: x.get("fecha", ""), reverse=True)
        for b in bms:
            idx = b.get("idx", 0)
            tot = b.get("total", 1)
            pct = int(round((idx + 1) * 100 / max(1, tot)))
            it = QListWidgetItem(
                f"{b.get('fuente', 'Documento')}  ·  Oración {idx + 1}/{tot} ({pct}%)  ·  {b.get('fecha', '')}\n"
                f"«{b.get('preview', '')}»"
            )
            it.setData(Qt.UserRole, b)
            self.bm_list.addItem(it)

        self.list.clear()
        for e in load_history():
            prev = " ".join(e.get("texto", "").split())[:85]
            it = QListWidgetItem(f"{e.get('fecha', '')}  ·  {e.get('fuente', '')}\n{prev}")
            it.setData(Qt.UserRole, e)
            self.list.addItem(it)

    def _cur_bm(self):
        it = self.bm_list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _open_bm(self):
        b = self._cur_bm()
        if b and b.get("texto"):
            self.open_cb(b["texto"], b.get("fuente", "Marcador"), b.get("idx", 0))

    def _del_bm(self):
        b = self._cur_bm()
        if b and b.get("key"):
            delete_bookmark(b["key"])
            self.refresh()

    def _cur(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _open(self):
        e = self._cur()
        if e:
            self.open_cb(e["texto"], e.get("fuente", "Historial"), None)

    def _copy(self):
        e = self._cur()
        if e:
            QApplication.clipboard().setText(e["texto"])

    def _clear(self):
        if QMessageBox.question(self, APP, "¿Borrar todo el historial?") == QMessageBox.Yes:
            clear_history()
            self.refresh()


# ---------- configuración con Piper (#7), Atajos (#1,#5,#6) y Diccionario de pronunciación (#12) ----------
class _HK(QObject):
    got = Signal(object, str)
    rec_done = Signal(object, str)

class SettingsDialog(QDialog):
    def __init__(self, on_saved, parent=None):
        super().__init__(parent)
        self.on_saved = on_saved
        self.setWindowTitle(f"Configuración y Estudio de Voz · {APP}")
        self.setWindowIcon(make_icon())
        self.setMinimumSize(680, 650)
        self.hk = _HK()
        self.hk.got.connect(lambda w, t: (w.setText(t), w.setEnabled(True)))
        self.hk.rec_done.connect(self._on_mic_finished)
        self._recording = False
        self._last_recorded_audio = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # ---------------- Tab 1: General y Voces ----------------
        t_gen = QWidget()
        f = QFormLayout(t_gen)
        f.setContentsMargins(18, 18, 18, 18)
        f.setVerticalSpacing(11)

        self.engine = QComboBox()
        self.engine.addItem("Kokoro (local, sin internet · soporta Mi Voz .npy)", "kokoro")
        self.engine.addItem("Piper (local, voces español latinoamericano .onnx)", "piper")
        self.engine.addItem("Edge Neural HD (online, gratis, multilingüe)", "edge")
        self.engine.currentIndexChanged.connect(self._fill_voices)
        f.addRow("Motor de voz", self.engine)

        self.v_es = QComboBox()
        self.v_en = QComboBox()
        f.addRow("Voz en español", self.v_es)
        f.addRow("Voz en inglés", self.v_en)

        self.lang = QComboBox()
        self.lang.addItem("Español", "es")
        self.lang.addItem("Inglés", "en")
        f.addRow("Idioma por defecto", self.lang)

        self.auto = QCheckBox("Detectar idioma por oración (texto mixto español / inglés)")
        f.addRow("", self.auto)

        self.speed = QComboBox()
        for i in range(2, 17):
            self.speed.addItem(f"{i / 4:g}×", i / 4)
        f.addRow("Velocidad (tono natural)", self.speed)

        self.hk_read = QLineEdit()
        self.hk_pause = QLineEdit()
        self.hk_page = QLineEdit()
        self.hk_ocr = QLineEdit()
        f.addRow("Atajo: leer selección o desde el cursor", self._hk_row(self.hk_read))
        f.addRow("Atajo: pausar / reanudar", self._hk_row(self.hk_pause))
        f.addRow("Atajo: leer esta página (navegador)", self._hk_row(self.hk_page))
        f.addRow("Atajo: OCR de zona de pantalla", self._hk_row(self.hk_ocr))

        self.word_hl = QCheckBox("Resaltar palabra por palabra mientras lee")
        f.addRow("", self.word_hl)
        self.mini = QCheckBox("Mostrar reproductor / botón flotante")
        f.addRow("", self.mini)
        self.mini_compact = QCheckBox("Iniciar flotante en modo compacto (botón chico)")
        f.addRow("", self.mini_compact)
        self.autostart = QCheckBox("Iniciar Lector Libre con Windows")
        f.addRow("", self.autostart)

        test = QPushButton(" Probar voz activa")
        test.setIcon(vec_icon("volume", 16, "#ececf4"))
        test.clicked.connect(self._test)
        f.addRow("", test)
        self.tabs.addTab(t_gen, "Voces y Atajos")

        # ---------------- Tab 2: Estudio de Voz (Clonar / Diseñar por única vez) ----------------
        t_studio = QWidget()
        vs = QVBoxLayout(t_studio)
        vs.setContentsMargins(16, 14, 16, 14)
        vs.setSpacing(10)

        # Tarjeta de consejos prácticos + Guion sugerido
        tips_card = QFrame()
        tips_card.setObjectName("tipsCard")
        tips_card.setStyleSheet(
            "QFrame#tipsCard{background:#181b28;border:1px solid #2d334d;border-radius:11px;padding:8px 12px}"
        )
        tc_lay = QVBoxLayout(tips_card)
        tc_lay.setContentsMargins(6, 4, 6, 4)
        tc_lay.setSpacing(6)

        lbl_tips_title = QLabel("★ CLONACIÓN Y DISEÑO DE VOZ POR ÚNICA VEZ (0% USO EXTRA DE CPU/GPU AL LEER)")
        lbl_tips_title.setStyleSheet("color:#b49eff;font-size:8.5pt;font-weight:700;letter-spacing:0.5px;border:none")
        tc_lay.addWidget(lbl_tips_title)

        lbl_tips = QLabel(
            "• <b>Cómo enviar o grabar el mejor audio:</b> Grabá entre <b>12 y 20 segundos</b> en un lugar silencioso (sin eco ni música), "
            "a <b>15–20 cm</b> del micrófono, con tu tono y ritmo natural de lectura.<br>"
            "• <b>Cómo funciona:</b> Tu grabación se analiza <b>una sola vez</b> para hornear una huella matemática liviana (<code>.npy</code> de 512 KB). "
            "Una vez guardada, funciona igual de rápido que las voces nativas sin exigir el procesador."
        )
        lbl_tips.setWordWrap(True)
        lbl_tips.setStyleSheet("color:#cfd3e8;font-size:9pt;border:none")
        tc_lay.addWidget(lbl_tips)

        script_row = QHBoxLayout()
        lbl_sc = QLabel("Texto sugerido para leer al grabar:")
        lbl_sc.setStyleSheet("color:#9ca3c4;font-size:8.5pt;font-weight:600;border:none")
        script_row.addWidget(lbl_sc)
        self.st_script_combo = QComboBox()
        for title, body in VOICE_SCRIPTS:
            self.st_script_combo.addItem(title, body)
        self.st_script_combo.currentIndexChanged.connect(self._on_script_changed)
        script_row.addWidget(self.st_script_combo, 1)
        tc_lay.addLayout(script_row)

        self.st_script_box = QLabel(VOICE_SCRIPTS[0][1])
        self.st_script_box.setWordWrap(True)
        self.st_script_box.setStyleSheet(
            "background:#12141e;border:1px solid #353b58;border-radius:8px;padding:8px 10px;"
            "color:#f0f0fa;font-size:9.5pt;font-style:italic"
        )
        tc_lay.addWidget(self.st_script_box)
        vs.addWidget(tips_card)

        # Fila de captura / subida de muestra de voz
        cap_row = QHBoxLayout()
        cap_row.setSpacing(8)
        self.b_mic_rec = QPushButton(" Grabar mi voz (15 s)")
        self.b_mic_rec.setIcon(vec_icon("mic", 15, "#ffffff"))
        self.b_mic_rec.setObjectName("primary")
        self.b_mic_rec.clicked.connect(self._toggle_mic_record)
        cap_row.addWidget(self.b_mic_rec)

        b_up_wav = QPushButton(" Subir audio (.wav / .mp3)")
        b_up_wav.setIcon(vec_icon("folder", 15, "#ececf4"))
        b_up_wav.clicked.connect(self._upload_voice_sample)
        cap_row.addWidget(b_up_wav)

        self.b_play_sample = QPushButton(" Escuchar mi muestra")
        self.b_play_sample.setIcon(vec_icon("play", 14, "#ececf4"))
        self.b_play_sample.setEnabled(False)
        self.b_play_sample.clicked.connect(self._play_recorded_sample)
        cap_row.addWidget(self.b_play_sample)
        cap_row.addStretch()
        vs.addLayout(cap_row)

        self.st_analysis_lbl = QLabel("Subí un audio o grabá con el micrófono para analizar tu timbre automáticamente (o diseñalo con los controles de abajo).")
        self.st_analysis_lbl.setWordWrap(True)
        self.st_analysis_lbl.setStyleSheet("color:#a594ff;font-size:8.5pt;font-weight:600")
        vs.addWidget(self.st_analysis_lbl)

        # Formulario de ajuste fino del vector .npy
        form_card = QFrame()
        form_card.setObjectName("formCard")
        form_card.setStyleSheet("QFrame#formCard{background:#151822;border:1px solid #24293b;border-radius:11px;padding:6px 10px}")
        fc_lay = QFormLayout(form_card)
        fc_lay.setContentsMargins(8, 6, 8, 6)
        fc_lay.setVerticalSpacing(7)

        name_lang_row = QHBoxLayout()
        self.st_name = QLineEdit("Mi Voz Natural")
        self.st_name.setPlaceholderText("Nombre para guardar tu voz (ej. Mi Voz)")
        name_lang_row.addWidget(self.st_name, 1)
        self.st_lang = QComboBox()
        self.st_lang.addItem("Español", "es")
        self.st_lang.addItem("Inglés", "en")
        name_lang_row.addWidget(self.st_lang)
        fc_lay.addRow("Nombre e idioma:", name_lang_row)

        bases_row = QHBoxLayout()
        self.st_base1 = QComboBox()
        self.st_base2 = QComboBox()
        for vid, vlbl in STUDIO_BASE_VOICES:
            self.st_base1.addItem(vlbl, vid)
            self.st_base2.addItem(vlbl, vid)
        self.st_base1.setCurrentIndex(1)  # pm_alex
        self.st_base2.setCurrentIndex(7)  # am_fenrir
        bases_row.addWidget(self.st_base1, 1)
        bases_row.addWidget(QLabel("+"))
        bases_row.addWidget(self.st_base2, 1)
        fc_lay.addRow("Timbres base:", bases_row)

        def make_slider_row(min_v, max_v, init_v, suffix="%"):
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            s = QSlider(Qt.Horizontal)
            s.setRange(min_v, max_v)
            s.setValue(init_v)
            lbl = QLabel(f"{init_v:+d}{suffix}" if min_v < 0 else f"{init_v}{suffix}")
            lbl.setFixedWidth(48)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet("color:#b6bbd4;font-size:8.5pt;border:none")
            s.valueChanged.connect(lambda v: lbl.setText(f"{v:+d}{suffix}" if min_v < 0 else f"{v}{suffix}"))
            h.addWidget(s, 1)
            h.addWidget(lbl)
            return w, s

        w_mix, self.sl_mix = make_slider_row(0, 100, 35)
        w_dep, self.sl_depth = make_slider_row(-100, 100, 10)
        w_war, self.sl_warmth = make_slider_row(-100, 100, 20)
        w_exp, self.sl_expr = make_slider_row(-100, 100, 15)

        fc_lay.addRow("Mezcla (Base 1 ↔ Base 2):", w_mix)
        fc_lay.addRow("Cuerpo (Agudo ↔ Profundo):", w_dep)
        fc_lay.addRow("Timbre (Brillante ↔ Cálido):", w_war)
        fc_lay.addRow("Cadencia (Calma ↔ Expresiva):", w_exp)
        vs.addWidget(form_card)

        # Botones de Previsualizar y Guardar huella fija .npy
        act_row = QHBoxLayout()
        b_prev_st = QPushButton(" Probar cómo suena esta voz")
        b_prev_st.setIcon(vec_icon("volume", 15, "#ececf4"))
        b_prev_st.clicked.connect(self._preview_studio_voice)
        act_row.addWidget(b_prev_st)

        b_save_st = QPushButton(" Guardar como voz fija (.npy · 0% CPU extra)")
        b_save_st.setObjectName("primary")
        b_save_st.setIcon(vec_icon("sparkle", 15, "#ffffff"))
        b_save_st.clicked.connect(self._save_studio_voice)
        act_row.addWidget(b_save_st, 1)
        vs.addLayout(act_row)

        # Lista de voces personalizadas ya creadas + importar Piper .onnx
        cust_row = QHBoxLayout()
        self.st_custom_combo = QComboBox()
        self.st_custom_combo.setPlaceholderText("Tus voces personalizadas aparecerán acá...")
        cust_row.addWidget(QLabel("Mis voces:"), 0)
        cust_row.addWidget(self.st_custom_combo, 1)
        b_del_cust = QPushButton("Eliminar")
        b_del_cust.clicked.connect(self._delete_selected_custom_voice)
        cust_row.addWidget(b_del_cust)
        b_imp_onnx = QPushButton("Importar .onnx (Piper)")
        b_imp_onnx.setToolTip("Importar un archivo .onnx + .onnx.json entrenado para Piper")
        b_imp_onnx.clicked.connect(self._import_piper_onnx_dialog)
        cust_row.addWidget(b_imp_onnx)
        vs.addLayout(cust_row)

        self.tabs.addTab(t_studio, "★ Estudio de Voz (Clonar / Crear)")

        # ---------------- Tab 3: Diccionario de pronunciación (#12) ----------------
        t_pron = QWidget()
        vp = QVBoxLayout(t_pron)
        vp.setContentsMargins(18, 18, 18, 18)
        vp.setSpacing(10)
        lbl_p = QLabel("Definí cómo deben pronunciarse siglas, nombres o términos (ej. «Acts 29» → «Hechos veintinueve»):")
        lbl_p.setWordWrap(True)
        lbl_p.setStyleSheet("color:#b6bbd4")
        vp.addWidget(lbl_p)

        self.pron_table = QTableWidget(0, 2)
        self.pron_table.verticalHeader().setVisible(False)
        self.pron_table.setShowGrid(False)
        self.pron_table.setAlternatingRowColors(False)
        self.pron_table.setHorizontalHeaderLabels(["Texto escrito en el documento", "Cómo debe pronunciarlo la voz"])
        self.pron_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        vp.addWidget(self.pron_table)

        hp = QHBoxLayout()
        b_add = QPushButton("＋ Agregar regla")
        b_add.clicked.connect(lambda: self._add_pron_row("", ""))
        hp.addWidget(b_add)
        b_rem = QPushButton("－ Quitar seleccionada")
        b_rem.clicked.connect(self._remove_pron_row)
        hp.addWidget(b_rem)
        hp.addStretch()
        b_test_pron = QPushButton(" Escuchar ejemplo")
        b_test_pron.setIcon(vec_icon("volume", 15, "#ececf4"))
        b_test_pron.clicked.connect(self._test_pronunciation)
        hp.addWidget(b_test_pron)
        vp.addLayout(hp)
        self.tabs.addTab(t_pron, "Diccionario de pronunciación")

        bb = QDialogButtonBox()
        ok = bb.addButton("Guardar cambios", QDialogButtonBox.AcceptRole)
        ok.setObjectName("primary")
        bb.addButton("Cancelar", QDialogButtonBox.RejectRole)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)
        self.load()

    def _on_script_changed(self, idx):
        txt = self.st_script_combo.itemData(idx)
        if txt:
            self.st_script_box.setText(txt)

    def _toggle_mic_record(self):
        if self._recording:
            self._recording = False
            self.b_mic_rec.setText(" Procesando muestra...")
            self.b_mic_rec.setEnabled(False)
            return
        self._recording = True
        self.b_mic_rec.setText("⏹ Detener grabación (grabando...)")

        def rec_worker():
            try:
                import sounddevice as sd
                frames = []
                block = int(SR * 0.1)
                max_blocks = 150  # 15 segundos máx
                with sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=block) as stream:
                    for _ in range(max_blocks):
                        if not self._recording:
                            break
                        data, _ = stream.read(block)
                        frames.append(np.asarray(data, dtype=np.float32).reshape(-1))
                self._recording = False
                if not frames:
                    self.hk.rec_done.emit(None, "Grabación cancelada.")
                    return
                audio = np.concatenate(frames)
                self.hk.rec_done.emit(audio, "")
            except Exception as e:
                self._recording = False
                self.hk.rec_done.emit(None, f"No se pudo acceder al micrófono: {e}")

        threading.Thread(target=rec_worker, daemon=True).start()

    def _on_mic_finished(self, audio, err):
        self.b_mic_rec.setEnabled(True)
        self.b_mic_rec.setText(" Grabar mi voz (15 s)")
        if err:
            QMessageBox.warning(self, APP, err)
            return
        if audio is not None:
            self._last_recorded_audio = audio
            self.b_play_sample.setEnabled(True)
            self._apply_sample_analysis(audio)

    def _upload_voice_sample(self):
        p, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar grabación de muestra de voz",
            "",
            "Archivos de audio (*.wav *.mp3 *.flac *.ogg);;Todos (*.*)",
        )
        if not p:
            return
        try:
            audio = load_audio_any(p, SR)
            self._last_recorded_audio = audio
            self.b_play_sample.setEnabled(True)
            base_title = os.path.splitext(os.path.basename(p))[0][:24]
            self.st_name.setText(f"Mi Voz ({base_title})")
            self._apply_sample_analysis(audio)
        except Exception as e:
            QMessageBox.warning(self, APP, f"No se pudo analizar el archivo de audio:\n{e}")

    def _apply_sample_analysis(self, audio):
        try:
            info = analyze_voice_sample(audio, SR)
        except Exception as e:
            QMessageBox.warning(self, APP, str(e))
            return
        self.st_analysis_lbl.setText("✓ " + info["summary"])
        i1 = self.st_base1.findData(info["base1"])
        i2 = self.st_base2.findData(info["base2"])
        if i1 >= 0:
            self.st_base1.setCurrentIndex(i1)
        if i2 >= 0:
            self.st_base2.setCurrentIndex(i2)
        self.sl_mix.setValue(info["mix_pct"])
        self.sl_depth.setValue(info["depth_pct"])
        self.sl_warmth.setValue(info["warmth_pct"])
        self.sl_expr.setValue(info["expr_pct"])

    def _play_recorded_sample(self):
        if self._last_recorded_audio is None:
            return
        arr = self._last_recorded_audio

        def run():
            try:
                import sounddevice as sd
                sd.play(arr, SR)
                sd.wait()
            except Exception as e:
                log("play_sample", e)

        threading.Thread(target=run, daemon=True).start()

    def _build_current_studio_vec(self):
        return build_custom_kokoro_vector(
            base1=self.st_base1.currentData(),
            base2=self.st_base2.currentData(),
            mix_pct=self.sl_mix.value(),
            depth_pct=self.sl_depth.value(),
            warmth_pct=self.sl_warmth.value(),
            expr_pct=self.sl_expr.value(),
            lang=self.st_lang.currentData(),
        )

    def _preview_studio_voice(self):
        try:
            vec = self._build_current_studio_vec()
        except Exception as e:
            QMessageBox.warning(self, APP, str(e))
            return
        lang = self.st_lang.currentData()
        sample_txt = (
            "Hola, esta es mi nueva voz personalizada en Lector Libre. Se calcula una sola vez y lee al instante sin usar recursos extra."
            if lang == "es"
            else "Hello, this is my custom voice profile in Lector Libre, pre-computed once for instant reading."
        )

        def run():
            try:
                import sounddevice as sd
                a = engine.synth_kokoro(sample_txt, lang, cfg.get("speed", 1.0), voice_override=vec)
                sd.play(a, SR)
                sd.wait()
            except Exception as e:
                log("preview_studio", e)

        threading.Thread(target=run, daemon=True).start()

    def _save_studio_voice(self):
        try:
            vec = self._build_current_studio_vec()
            lang = self.st_lang.currentData()
            vid = save_custom_kokoro_voice(
                name=self.st_name.text(),
                vec=vec,
                lang=lang,
                details={
                    "base1": self.st_base1.currentData(),
                    "base2": self.st_base2.currentData(),
                    "mix": self.sl_mix.value(),
                    "depth": self.sl_depth.value(),
                    "warmth": self.sl_warmth.value(),
                    "expr": self.sl_expr.value(),
                },
            )
        except Exception as e:
            QMessageBox.warning(self, APP, f"No se pudo guardar la voz:\n{e}")
            return

        cfg["engine"] = "kokoro"
        cfg["voice_es" if lang == "es" else "voice_en"] = vid
        save_cfg()
        self.engine.setCurrentIndex(max(0, self.engine.findData("kokoro")))
        self._fill_voices()
        self._refresh_custom_combo()
        self.on_saved()
        QMessageBox.information(
            self,
            APP,
            f"¡Voz «{voice_label(vid)}» guardada y activada!\n\n"
            "Su huella acústica (.npy de 512 KB) quedó pre-calculada en disco: "
            "ahora podés usarla siempre sin ningún consumo extra de CPU o GPU.",
        )

    def _refresh_custom_combo(self):
        self.st_custom_combo.clear()
        for vid, meta in load_custom_voices().items():
            self.st_custom_combo.addItem(f"{meta.get('label', vid)} ({meta.get('created', '')})", vid)

    def _delete_selected_custom_voice(self):
        vid = self.st_custom_combo.currentData()
        if not vid:
            return
        delete_custom_voice(vid)
        self._refresh_custom_combo()
        self._fill_voices()
        self.on_saved()

    def _import_piper_onnx_dialog(self):
        p, _ = QFileDialog.getOpenFileName(
            self,
            "Importar modelo de voz Piper (.onnx)",
            "",
            "Modelo ONNX de Piper (*.onnx)",
        )
        if not p:
            return
        name, ok = QInputDialog.getText(self, APP, "Nombre para mostrar de esta voz:", text=os.path.splitext(os.path.basename(p))[0])
        if not ok:
            return
        try:
            vid = import_custom_piper_voice(p, name=name, lang=self.st_lang.currentData())
        except Exception as e:
            QMessageBox.warning(self, APP, str(e))
            return
        cfg["engine"] = "piper"
        cfg["piper_es" if self.st_lang.currentData() == "es" else "piper_en"] = vid
        save_cfg()
        self.engine.setCurrentIndex(max(0, self.engine.findData("piper")))
        self._fill_voices()
        self._refresh_custom_combo()
        self.on_saved()
        QMessageBox.information(self, APP, f"Modelo Piper «{voice_label(vid)}» importado y activado.")

    def _add_pron_row(self, k="", v=""):
        r = self.pron_table.rowCount()
        self.pron_table.insertRow(r)
        self.pron_table.setRowHeight(r, 36)
        self.pron_table.setItem(r, 0, QTableWidgetItem(str(k)))
        self.pron_table.setItem(r, 1, QTableWidgetItem(str(v)))

    def _remove_pron_row(self):
        r = self.pron_table.currentRow()
        if r >= 0:
            self.pron_table.removeRow(r)

    def _collect_pronunciation(self):
        out = {}
        for r in range(self.pron_table.rowCount()):
            it_k = self.pron_table.item(r, 0)
            it_v = self.pron_table.item(r, 1)
            k = (it_k.text() if it_k else "").strip()
            v = (it_v.text() if it_v else "").strip()
            if k and v:
                out[k] = v
        return out

    def _test_pronunciation(self):
        old = dict(cfg)
        self._apply()
        r = self.pron_table.currentRow()
        if r < 0 and self.pron_table.rowCount() > 0:
            r = 0
        it_k = self.pron_table.item(r, 0) if r >= 0 else None
        sample = it_k.text().strip() if (it_k and it_k.text().strip()) else "Acts 29"

        def run():
            try:
                import sounddevice as sd
                a = engine.synth(f"Probando pronunciación: {sample}.", "es", cfg["speed"])
                sd.play(a, SR)
                sd.wait()
            except Exception as e:
                log("test_pron", repr(e))
            finally:
                cfg.clear()
                cfg.update(old)

        threading.Thread(target=run, daemon=True).start()

    def _hk_row(self, edit):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(edit)
        b = QPushButton("Grabar")
        b.setToolTip("Tocá y apretá la combinación de teclas")
        h.addWidget(b)

        def rec():
            edit.setEnabled(False)
            edit.setText("Apretá las teclas…")

            def run():
                try:
                    import keyboard
                    t = keyboard.read_hotkey(suppress=False)
                except Exception as e:
                    log("read_hotkey", e)
                    t = ""
                self.hk.got.emit(edit, t)

            threading.Thread(target=run, daemon=True).start()

        b.clicked.connect(rec)
        return w

    def _fill_voices(self):
        eng = self.engine.currentData()
        es, en, kes, ken = voices_for_engine(eng)
        for box, lst, key in ((self.v_es, es, kes), (self.v_en, en, ken)):
            box.clear()
            for v in lst:
                box.addItem(voice_label(v), v)
            box.setCurrentIndex(max(0, box.findData(cfg.get(key))))

    def load(self):
        self.engine.setCurrentIndex(max(0, self.engine.findData(cfg.get("engine"))))
        self._fill_voices()
        self._refresh_custom_combo()
        self.lang.setCurrentIndex(max(0, self.lang.findData(cfg.get("lang_default"))))
        self.auto.setChecked(cfg.get("autodetect", True))
        self.speed.setCurrentIndex(max(0, self.speed.findData(round(cfg.get("speed", 1.0) * 4) / 4)))
        self.hk_read.setText(cfg.get("hk_read", "ctrl+alt+r"))
        self.hk_pause.setText(cfg.get("hk_pause", "ctrl+alt+p"))
        self.hk_page.setText(cfg.get("hk_page", "ctrl+alt+w"))
        self.hk_ocr.setText(cfg.get("hk_ocr", "ctrl+alt+o"))
        self.word_hl.setChecked(cfg.get("word_highlight", True))
        self.mini.setChecked(cfg.get("mini", True))
        self.mini_compact.setChecked(cfg.get("mini_compact", False))
        self.autostart.setChecked(cfg.get("autostart", False))

        self.pron_table.setRowCount(0)
        for k, v in (cfg.get("pronunciation") or {}).items():
            self._add_pron_row(k, v)

    refresh_engine_ui = load

    def _apply(self):
        eng = self.engine.currentData()
        _, _, kes, ken = voices_for_engine(eng)
        cfg["engine"] = eng
        cfg[kes] = self.v_es.currentData()
        cfg[ken] = self.v_en.currentData()
        cfg["lang_default"] = self.lang.currentData()
        cfg["autodetect"] = self.auto.isChecked()
        cfg["speed"] = self.speed.currentData()
        cfg["pronunciation"] = self._collect_pronunciation()

    def _test(self):
        old = dict(cfg)
        self._apply()
        if cfg["engine"] in ("kokoro", "piper") and not models_ready():
            ok, err = run_with_progress(self, "Descargando voz seleccionada...", download_models)
            if not ok:
                cfg.clear()
                cfg.update(old)
                QMessageBox.warning(self, APP, f"No se pudo descargar la voz:\n{err}")
                return

        def run():
            try:
                import sounddevice as sd, numpy as np
                a = np.concatenate([
                    engine.synth("Hola, soy tu lector en español.", "es", cfg["speed"]),
                    np.zeros(6000, np.float32),
                    engine.synth("Hello, I am your reader.", "en", cfg["speed"]),
                ])
                sd.play(a, SR)
                sd.wait()
            except Exception as e:
                log("probar voz", repr(e))
            finally:
                cfg.clear()
                cfg.update(old)

        threading.Thread(target=run, daemon=True).start()

    def _save(self):
        r = self.hk_read.text().strip().lower()
        p = self.hk_pause.text().strip().lower()
        w_hk = self.hk_page.text().strip().lower()
        o_hk = self.hk_ocr.text().strip().lower()
        mods = {"ctrl", "alt", "shift", "windows", "left windows", "right windows", "windows izquierda", "windows derecha"}
        try:
            import keyboard
            for h in (r, p, w_hk, o_hk):
                if not h or h in mods:
                    raise ValueError("modifier only")
                keyboard.parse_hotkey(h)
        except Exception:
            QMessageBox.warning(self, APP, "Uno de los atajos no es válido o usa solo una tecla modificadora. Probá con algo como ctrl+alt+r.")
            return
        if len({r, p, w_hk, o_hk}) < 4:
            QMessageBox.warning(self, APP, "Los atajos no pueden repetirse entre sí.")
            return
        self._apply()
        cfg.update(
            hk_read=r,
            hk_pause=p,
            hk_page=w_hk,
            hk_ocr=o_hk,
            word_highlight=self.word_hl.isChecked(),
            mini=self.mini.isChecked(),
            mini_compact=self.mini_compact.isChecked(),
            autostart=self.autostart.isChecked(),
        )
        save_cfg()
        self.accept()
        self.on_saved()


# ---------- Tutorial de Bienvenida Interactivo (con opción "No volver a mostrar") ----------
class WelcomeTutorialDialog(QDialog):
    def __init__(self, on_open_voice_studio=None, parent=None):
        super().__init__(parent)
        self.on_open_voice_studio = on_open_voice_studio
        self.setWindowTitle(f"Guía Rápida de Bienvenida · {APP}")
        self.setWindowIcon(make_icon())
        self.setFixedSize(780, 520)
        self.step = 0

        self.slides = [
            {
                "badge": "PASO 1 DE 5  ·  BIENVENIDA Y MODOS DE USO",
                "title": "Dos formas de usar Lector Libre: Píldora Flotante y Estudio",
                "icon": "expand",
                "body": (
                    "<p style='font-size:10.5pt;color:#e4e6f5;line-height:1.45'>"
                    "<b>Lector Libre</b> está diseñado para acompañarte mientras leés en cualquier programa de Windows sin estorbar:"
                    "</p>"
                    "<ul style='font-size:10pt;color:#cfd3e8;line-height:1.55'>"
                    "<li><b>Botón Flotante Compacto:</b> Una micro-píldora siempre visible (<code>▶ ||| ⤢</code>) que podés arrastrar a cualquier rincón de tu pantalla.</li>"
                    "<li><b>Reproductor Flotante Expandido:</b> Tocá <b>⤢</b> en la píldora para desplegar los controles rápidos de página, OCR, velocidad, voz y progreso.</li>"
                    "<li><b>Ventana Principal de Estudio:</b> Ideal para libros largos (PDF, Word, ePub), artículos web y exportación a audiolibros.</li>"
                    "</ul>"
                ),
                "tip": "Consejo: En Ajustes podés elegir si preferís que el reproductor flotante inicie en modo compacto o expandido.",
            },
            {
                "badge": "PASO 2 DE 5  ·  LECTURA INSTANTÁNEA EN CUALQUIER APP",
                "title": "Cuatro formas de leer sin tener que copiar ni pegar",
                "icon": "page",
                "body": (
                    f"<ul style='font-size:10pt;color:#cfd3e8;line-height:1.55'>"
                    f"<li><b>1. Leer desde el cursor o selección (<code>{cfg.get('hk_read', 'ctrl+alt+r').upper()}</code> o botón ▶):</b> "
                    "Si seleccionás texto, lee solo eso. Si <b>no seleccionás nada</b> y solo dejás el cursor parpadeando en Word, un PDF o una web, lee desde esa posición hasta que lo detengas.</li>"
                    f"<li><b>2. Leer esta página / formulario (<code>{cfg.get('hk_page', 'ctrl+alt+w').upper()}</code> o botón de página):</b> "
                    "Extrae automáticamente el artículo, preguntas y respuestas de la pestaña activa del navegador (ej. Acts 29), saltando menús y pies de página.</li>"
                    f"<li><b>3. OCR de zona de pantalla (<code>{cfg.get('hk_ocr', 'ctrl+alt+o').upper()}</code> o botón de lupa):</b> "
                    "Dibujá un recuadro sobre cualquier imagen, gráfico o PDF escaneado que no permita copiar texto y Lector Libre lo reconoce y lo lee al instante.</li>"
                    "</ul>"
                ),
                "tip": "Consejo: Podés hacer clic directamente en los botones del reproductor flotante: Lector Libre recuerda cuál era tu ventana activa.",
            },
            {
                "badge": "PASO 3 DE 5  ·  ESTUDIO DE LECTURA Y AUDIOLIBROS",
                "title": "Navegación por oraciones, capítulos, marcadores y velocidad hasta 4×",
                "icon": "chapters",
                "body": (
                    "<ul style='font-size:10pt;color:#cfd3e8;line-height:1.55'>"
                    "<li><b>Doble clic para saltar:</b> En el Estudio de lectura, hacé <b>doble clic sobre cualquier oración</b> para empezar a escuchar desde ese punto exacto.</li>"
                    "<li><b>Velocidad natural hasta 4× en vivo:</b> Cambiá la velocidad o la voz mientras escucha sin reiniciar la oración actual y manteniendo el tono natural de la voz.</li>"
                    "<li><b>Índice de capítulos y Marcadores:</b> Tus lecturas largas guardan progreso automáticamente para retomar donde quedaste con un clic.</li>"
                    "<li><b>Exportar como Audiolibro:</b> Desde el botón <b>Exportar ▾</b> podés convertir un documento o libro ePub entero en archivos MP3 separados por capítulo.</li>"
                    "</ul>"
                ),
                "tip": "Consejo: Arrastrá la barra deslizable inferior en cualquier momento para adelantar o retroceder dentro del documento.",
            },
            {
                "badge": "PASO 4 DE 5  ·  ESTUDIO DE VOZ (CLONAR / DISEÑAR UNA VEZ)",
                "title": "Creá o cloná tu propia voz por única vez con 0% de uso extra de CPU",
                "icon": "sparkle",
                "body": (
                    "<p style='font-size:10pt;color:#e4e6f5;line-height:1.45'>"
                    "Desde el botón <b>★ Mi Voz</b> (o en <b>Ajustes → Estudio de Voz</b>) podés crear una voz a tu medida:"
                    "</p>"
                    "<ul style='font-size:10pt;color:#cfd3e8;line-height:1.55'>"
                    "<li><b>Grabá o subí tu voz una sola vez (12 a 20 seg):</b> Lector Libre mide tu tono fundamental, calidez de pecho, claridad y cadencia.</li>"
                    "<li><b>Se guarda como huella fija (<code>.npy</code> de 512 KB):</b> A diferencia de otros clonadores que exigen placa de video en cada frase, acá la huella se calcula <b>una única vez</b> y después lee al instante sin gastar CPU ni GPU.</li>"
                    "<li><b>Consejos al grabar:</b> Hablá en un lugar sin eco, a 15–20 cm del micrófono, leyendo el guion sugerido en pantalla con tu ritmo natural.</li>"
                    "</ul>"
                ),
                "tip": "Consejo: También podés ajustar manualmente los deslizadores de Cuerpo, Calidez y Expresividad antes de guardar tu voz.",
            },
            {
                "badge": "PASO 5 DE 5  ·  PRONUNCIACIÓN Y MOTORES DE VOZ",
                "title": "Diccionario de Pronunciación y 3 motores incluidos",
                "icon": "volume",
                "body": (
                    "<ul style='font-size:10pt;color:#cfd3e8;line-height:1.55'>"
                    "<li><b>Diccionario de Pronunciación:</b> En <b>Ajustes → Diccionario de pronunciación</b> podés definir cómo querés que se lean siglas, nombres o términos en inglés (por ejemplo, <i>«Acts 29»</i> se lee automáticamente como <i>«Hechos veintinueve»</i>).</li>"
                    "<li><b>Kokoro Local (sin internet):</b> Incluye voces Studio en español e inglés y soporta tus voces personalizadas <code>.npy</code>.</li>"
                    "<li><b>Piper Local (latinoamericano):</b> Voces locales para Argentina y México que funcionan 100% sin conexión.</li>"
                    "<li><b>Edge Neural HD (online):</b> Voces neurales multilingües de alta definición de Argentina, Uruguay, Chile, Colombia, México, España y EE. UU.</li>"
                    "</ul>"
                ),
                "tip": "Podés volver a abrir este tutorial cuando quieras desde el botón «? Tutorial» arriba a la derecha.",
            },
        ]

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 18)
        root.setSpacing(14)

        body_h = QHBoxLayout()
        body_h.setSpacing(14)

        # Columna izquierda: pasos
        nav_card = QFrame()
        nav_card.setObjectName("sideCard")
        nav_card.setFixedWidth(224)
        nl = QVBoxLayout(nav_card)
        nl.setContentsMargins(10, 12, 10, 12)
        nl.setSpacing(6)
        lbl_nav = QLabel("GUÍA INTERACTIVA")
        lbl_nav.setStyleSheet("color:#8f95b2;font-size:8pt;font-weight:700;letter-spacing:0.8px;border:none")
        nl.addWidget(lbl_nav)

        self.step_btns = []
        step_titles = [
            "1. Modos de uso",
            "2. Lectura instantánea",
            "3. Estudio y Audiolibros",
            "4. Estudio de Voz (Clonar)",
            "5. Pronunciación y Motores",
        ]
        for idx, st_t in enumerate(step_titles):
            b = QPushButton(st_t)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, i=idx: self._set_step(i))
            nl.addWidget(b)
            self.step_btns.append(b)
        nl.addStretch(1)
        body_h.addWidget(nav_card)

        # Tarjeta derecha: contenido del paso
        content_card = QFrame()
        content_card.setObjectName("readerCard")
        cl = QVBoxLayout(content_card)
        cl.setContentsMargins(22, 18, 22, 18)
        cl.setSpacing(10)

        top_badge_row = QHBoxLayout()
        self.ic_lbl = QLabel()
        top_badge_row.addWidget(self.ic_lbl)
        self.badge_lbl = QLabel()
        self.badge_lbl.setStyleSheet("color:#a594ff;font-size:8.5pt;font-weight:700;letter-spacing:0.8px")
        top_badge_row.addWidget(self.badge_lbl)
        top_badge_row.addStretch()
        cl.addLayout(top_badge_row)

        self.title_lbl = QLabel()
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setStyleSheet("color:#ffffff;font-size:14pt;font-weight:700")
        cl.addWidget(self.title_lbl)

        self.body_lbl = QLabel()
        self.body_lbl.setWordWrap(True)
        self.body_lbl.setTextFormat(Qt.RichText)
        cl.addWidget(self.body_lbl, 1)

        self.tip_frame = QFrame()
        self.tip_frame.setObjectName("tipFrame")
        self.tip_frame.setStyleSheet(
            "QFrame#tipFrame{background:#1b1e2e;border:1px solid #383e5e;border-radius:10px;padding:8px 12px}"
        )
        tf_lay = QHBoxLayout(self.tip_frame)
        tf_lay.setContentsMargins(6, 4, 6, 4)
        self.tip_lbl = QLabel()
        self.tip_lbl.setWordWrap(True)
        self.tip_lbl.setStyleSheet("color:#c4c8e0;font-size:9pt;border:none")
        tf_lay.addWidget(self.tip_lbl)
        cl.addWidget(self.tip_frame)

        body_h.addWidget(content_card, 1)
        root.addLayout(body_h, 1)

        # Barra inferior con checkbox "No volver a mostrar" y botones Anterior / Siguiente
        foot = QHBoxLayout()
        self.chk_dont_show = QCheckBox("No volver a mostrar este tutorial al abrir la aplicación")
        self.chk_dont_show.setChecked(not cfg.get("show_welcome_tutorial", True) or True)
        foot.addWidget(self.chk_dont_show)
        foot.addStretch(1)

        if self.on_open_voice_studio:
            self.b_go_studio = QPushButton(" Ir al Estudio de Voz")
            self.b_go_studio.setIcon(vec_icon("sparkle", 14, "#dcdcf0"))
            self.b_go_studio.clicked.connect(self._open_studio_now)
            foot.addWidget(self.b_go_studio)

        self.b_prev = QPushButton("Anterior")
        self.b_prev.clicked.connect(lambda: self._set_step(self.step - 1))
        foot.addWidget(self.b_prev)

        self.b_next = QPushButton("Siguiente →")
        self.b_next.setObjectName("primary")
        self.b_next.clicked.connect(self._next_or_finish)
        foot.addWidget(self.b_next)

        root.addLayout(foot)
        self._set_step(0)

    def _set_step(self, idx):
        self.step = max(0, min(idx, len(self.slides) - 1))
        s = self.slides[self.step]
        self.ic_lbl.setPixmap(vec_icon(s["icon"], 20, "#a594ff").pixmap(20, 20))
        self.badge_lbl.setText(s["badge"])
        self.title_lbl.setText(s["title"])
        self.body_lbl.setText(s["body"])
        self.tip_lbl.setText("💡 " + s["tip"])

        for i, b in enumerate(self.step_btns):
            if i == self.step:
                b.setStyleSheet(
                    "QPushButton{background:rgba(124,92,255,65);border:1px solid #8f74ff;"
                    "color:#ffffff;font-weight:700;text-align:left;padding:7px 10px;border-radius:8px}"
                )
            else:
                b.setStyleSheet(
                    "QPushButton{background:transparent;border:1px solid transparent;"
                    "color:#9ca3c4;font-weight:500;text-align:left;padding:7px 10px;border-radius:8px}"
                    "QPushButton:hover{background:rgba(255,255,255,10);color:#ececf4}"
                )

        self.b_prev.setEnabled(self.step > 0)
        if self.step == len(self.slides) - 1:
            self.b_next.setText("¡Empezar a usar Lector Libre!")
        else:
            self.b_next.setText("Siguiente →")

    def _save_pref(self):
        cfg["first_run"] = False
        cfg["show_welcome_tutorial"] = not self.chk_dont_show.isChecked()
        save_cfg()

    def _open_studio_now(self):
        self._save_pref()
        self.accept()
        if self.on_open_voice_studio:
            self.on_open_voice_studio()

    def _next_or_finish(self):
        if self.step < len(self.slides) - 1:
            self._set_step(self.step + 1)
        else:
            self._save_pref()
            self.accept()

    def closeEvent(self, e):
        self._save_pref()
        super().closeEvent(e)

