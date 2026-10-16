# Lector Libre - núcleo: configuración, texto, motores de voz, reproductor y exportación
import os, sys, json, re, time, html, wave, threading, asyncio
import numpy as np
from PySide6.QtCore import QObject, Signal

APP = "Lector Libre"
DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LectorLibre")
MODEL_DIR = os.path.join(DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)
CFG = os.path.join(DIR, "config.json")
HIST = os.path.join(DIR, "historial.json")
LOG = os.path.join(DIR, "registro.txt")
SR = 24000

def log(*a):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + " ".join(map(str, a)) + "\n")
    except Exception: pass

def res(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

DEFAULT = {"engine": "kokoro", "voice_es": "ef_dora", "voice_en": "af_heart",
           "edge_es": "es-AR-ElenaNeural", "edge_en": "en-US-AriaNeural",
           "lang_default": "es", "autodetect": True, "speed": 1.0,
           "hk_read": "ctrl+alt+r", "hk_pause": "ctrl+alt+p", "mini": True,
           "mini_pos": None, "autostart": False, "first_run": True}
cfg = dict(DEFAULT)
try: cfg.update(json.load(open(CFG, encoding="utf-8")))
except Exception: pass
def save_cfg():
    try:
        with open(CFG, "w", encoding="utf-8") as f: json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e: log("save_cfg", e)

KOKORO_ES = ["ef_dora", "em_alex", "em_santa"]
KOKORO_EN = ["af_heart", "af_bella", "af_nicole", "am_michael", "am_fenrir", "bf_emma", "bm_george"]
EDGE_ES = ["es-AR-ElenaNeural", "es-AR-TomasNeural", "es-MX-DaliaNeural", "es-ES-AlvaroNeural"]
EDGE_EN = ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"]

def voice_label(v):
    if "-" in v:  # edge
        flag = "🇬🇧" if v.startswith("en-GB") else ("🇺🇸" if v.startswith("en") else "🇪🇸")
        return f"{flag} {v.split('-')[-1].replace('Neural', '')} (online)"
    flag = "🇪🇸" if v[0] in "e" else ("🇬🇧" if v[0] == "b" else "🇺🇸")
    return f"{flag} {v.split('_', 1)[1].capitalize()}"

_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL_FILES = [(_URL + "kokoro-v1.0.onnx", os.path.join(MODEL_DIR, "kokoro-v1.0.onnx")),
               (_URL + "voices-v1.0.bin", os.path.join(MODEL_DIR, "voices-v1.0.bin"))]
def models_ready():
    return all(os.path.isfile(p) for _, p in MODEL_FILES)
def download_models(progress):
    import requests
    for i, (url, dst) in enumerate(MODEL_FILES, 1):
        if os.path.isfile(dst): continue
        tmp = dst + ".part"
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0)); done = 0
            with open(tmp, "wb") as f:
                for c in r.iter_content(1 << 20):
                    f.write(c); done += len(c)
                    progress(done, total, f"Descargando voces ({i}/{len(MODEL_FILES)})")
        os.replace(tmp, dst)

# ---------- historial ----------
def load_history():
    try: return json.load(open(HIST, encoding="utf-8"))
    except Exception: return []
def add_history(texto, fuente):
    h = load_history()
    h.insert(0, {"fecha": time.strftime("%d/%m %H:%M"), "fuente": fuente, "texto": texto[:200000]})
    try:
        with open(HIST, "w", encoding="utf-8") as f: json.dump(h[:50], f, ensure_ascii=False)
    except Exception as e: log("history", e)
def clear_history():
    try: os.remove(HIST)
    except Exception: pass

# ---------- texto ----------
_ABBR = re.compile(r"(?:\b(?:Sr|Sra|Srta|Dr|Dra|Lic|Ing|Prof|etc|ej|Mr|Mrs|Ms|vs|St|No|pág|aprox)|\b[A-Z])\.$")

def split_text(text):
    """Devuelve [(oración, inicio, fin)] con posiciones en el texto original."""
    out = []
    for m in re.finditer(r"[^\n]+", text):
        para, base = m.group(), m.start()
        spans, start = [], 0
        for s in re.finditer(r"[.!?…]+[\"'”»)\]]*(?=\s|$)", para):
            if _ABBR.search(para[:s.end()]) and s.group() == ".": continue
            spans.append((start, s.end())); start = s.end()
        if start < len(para): spans.append((start, len(para)))
        for a, b in spans:
            while b - a > 400:  # cortar oraciones muy largas
                seg = para[a:a + 400]
                cut = max(seg.rfind(", "), seg.rfind("; "))
                if cut < 100: cut = seg.rfind(" ")
                if cut < 50: cut = 400
                spans_add(out, para, base, a, a + cut + 1); a = a + cut + 1
            spans_add(out, para, base, a, b)
    return out

def spans_add(out, para, base, a, b):
    seg = para[a:b]; l = len(seg) - len(seg.lstrip()); r = len(seg.rstrip())
    if seg.strip() and re.search(r"\w", seg):
        out.append((seg.strip(), base + a + l, base + a + r))

def _detect(t):
    try:
        from langdetect import DetectorFactory, detect_langs
        DetectorFactory.seed = 0
        for c in detect_langs(t):
            if c.lang in ("es", "en"): return c.lang
        return None
    except Exception: return None

_EN_HINT = re.compile(r"\b(the|and|is|are|you|with|this|that|have|what|for|of|to|it)\b", re.I)
_ES_HINT = re.compile(r"\b(el|la|los|las|que|de|y|es|en|un|una|por|para|con|no|se)\b", re.I)
def detect_lang(sentence, paragraph_lang):
    s = sentence.strip()
    if len(s) < 25:
        en, es = len(_EN_HINT.findall(s)), len(_ES_HINT.findall(s))
        if en > es: return "en"
        if es > en or re.search(r"[áéíóúñ¿¡]", s, re.I): return "es"
        return paragraph_lang
    return _detect(s) or paragraph_lang

def lang_for_chunks(text, chunks):
    d = cfg.get("lang_default", "es")
    if not cfg.get("autodetect", True): return [d] * len(chunks)
    paras = {}
    out = []
    for s, a, b in chunks:
        ps = text.rfind("\n", 0, a) + 1; pe = text.find("\n", b); pe = len(text) if pe < 0 else pe
        if ps not in paras: paras[ps] = _detect(text[ps:pe]) or d
        out.append(detect_lang(s, paras[ps]))
    return out

# ---------- motores ----------
class Engine:
    def __init__(self):
        self._k = None; self._lock = threading.Lock()
    def kokoro(self):
        with self._lock:
            if self._k is None:
                prepare_kokoro_runtime()
                from kokoro_onnx import Kokoro
                self._k = Kokoro(MODEL_FILES[0][1], MODEL_FILES[1][1])
            return self._k
    def synth_kokoro(self, text, lang, speed):
        v = cfg["voice_es"] if lang == "es" else cfg["voice_en"]
        kl = "es" if lang == "es" else ("en-gb" if v.startswith("b") else "en-us")
        k = self.kokoro()
        with self._lock:
            samples, sr = k.create(text, voice=v, speed=float(max(0.5, min(2.0, speed))), lang=kl)
        a = np.asarray(samples, dtype=np.float32).reshape(-1)
        if sr != SR: a = resample(a, sr, SR)
        if speed > 2.0: a = resample(a, SR * speed / 2.0, SR)  # Kokoro llega a 2x; el resto acelerando
        return a
    def synth_edge(self, text, lang, speed):
        import edge_tts, miniaudio
        v = cfg["edge_es"] if lang == "es" else cfg["edge_en"]
        rate = f"{int(round((min(speed, 3.0) - 1) * 100)):+d}%"
        async def run():
            buf = bytearray()
            async for c in edge_tts.Communicate(text, v, rate=rate).stream():
                if c.get("type") == "audio": buf += c["data"]
            return bytes(buf)
        data = asyncio.run(run())
        if not data: raise RuntimeError("Edge no devolvió audio")
        d = miniaudio.decode(data, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=SR)
        return np.asarray(d.samples, dtype=np.float32)
    def synth(self, text, lang, speed):
        if cfg.get("engine") == "edge":
            try: return self.synth_edge(text, lang, speed)
            except Exception as e:
                log("edge falló", e)
                if not models_ready(): raise RuntimeError("Sin conexión para la voz online y la voz local no está descargada")
        return self.synth_kokoro(text, lang, speed)

def resample(a, sr_in, sr_out):
    n = max(1, int(len(a) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)

def prepare_kokoro_runtime():
    """En el exe, PyInstaller mueve el DLL de espeak a la raíz del paquete.
    espeakng_loader lo busca junto a su módulo: apuntarlo al archivo que sí se empaquetó."""
    if not getattr(sys, "frozen", False):
        return
    import espeakng_loader
    meipass = getattr(sys, "_MEIPASS", None)
    roots = [p for p in (meipass, os.path.dirname(os.path.abspath(sys.executable))) if p]
    lib_names = ("espeak-ng.dll", "libespeak-ng.dll", "libespeak-ng.so", "libespeak-ng.dylib")
    lib = data = None
    for root in roots:
        for sub in (os.path.join(root, "espeakng_loader"), root):
            if lib is None:
                for name in lib_names:
                    cand = os.path.join(sub, name)
                    if os.path.isfile(cand):
                        lib = cand
                        break
            if data is None and os.path.isdir(os.path.join(sub, "espeak-ng-data")):
                data = os.path.join(sub, "espeak-ng-data")
    if not lib or not data:
        raise RuntimeError(f"Faltan archivos de espeak en el paquete (lib={lib}, data={data})")
    espeakng_loader.get_library_path = lambda _lib=lib: _lib
    espeakng_loader.get_data_path = lambda _data=data: _data
    os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = lib
    os.environ["PHONEMIZER_ESPEAK_DATA_PATH"] = data
    os.environ["PATH"] = os.path.dirname(lib) + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        for d in dict.fromkeys(os.path.dirname(p) for p in (lib, meipass) if p):
            try:
                os.add_dll_directory(d)
            except (OSError, FileNotFoundError):
                pass
    log("espeak bundle", lib, data)

engine = Engine()

# ---------- reproductor por oraciones ----------
class Player(QObject):
    sentence_started = Signal(int, int, int)
    state_changed = Signal(str)
    finished = Signal()
    error = Signal(str)
    AHEAD = 3

    def __init__(self):
        super().__init__()
        self.text = ""; self.chunks = []; self.langs = []
        self.idx = 0; self.state = "stopped"
        self._gen = 0; self._cache = {}; self._cv = threading.Condition()
        self._paused = threading.Event()

    def load(self, text):
        self.stop()
        self.text = text; self.chunks = split_text(text); self.langs = lang_for_chunks(text, self.chunks)

    def index_for_pos(self, pos):
        for i, (_, a, b) in enumerate(self.chunks):
            if pos <= b: return i
        return 0

    def _set_state(self, s):
        self.state = s; self.state_changed.emit(s)

    def play(self, from_idx=0):
        if not self.chunks: return
        with self._cv:
            self._gen += 1; g = self._gen
            self._cache = {}; self.idx = max(0, min(from_idx, len(self.chunks) - 1))
            self._paused.clear(); self._cv.notify_all()
        self._set_state("playing")
        threading.Thread(target=self._producer, args=(g,), daemon=True).start()
        threading.Thread(target=self._consumer, args=(g,), daemon=True).start()

    def toggle_pause(self):
        if self.state == "playing": self._paused.set(); self._set_state("paused")
        elif self.state == "paused": self._paused.clear(); self._set_state("playing")
        elif self.chunks: self.play(self.idx if self.idx < len(self.chunks) else 0)

    def stop(self):
        with self._cv:
            self._gen += 1; self._cache = {}; self._cv.notify_all()
        self._paused.clear()
        if self.state != "stopped": self._set_state("stopped")

    def next(self):
        if self.chunks and self.state != "stopped": self.play(min(self.idx + 1, len(self.chunks) - 1))
    def prev(self):
        if self.chunks and self.state != "stopped": self.play(max(self.idx - 1, 0))
    def set_speed(self, x):
        cfg["speed"] = float(x); save_cfg(); self._restart()
    def reset_voices(self):
        self._restart()
    def _restart(self):
        if self.state != "stopped":
            paused = self.state == "paused"; self.play(self.idx)
            if paused: self.toggle_pause()

    def _alive(self, g): return g == self._gen

    def _producer(self, g):
        i = self.idx
        while self._alive(g) and i < len(self.chunks):
            with self._cv:
                while self._alive(g) and i > self.idx + self.AHEAD: self._cv.wait(0.2)
            if not self._alive(g): return
            try: audio = engine.synth(self.chunks[i][0], self.langs[i], cfg.get("speed", 1.0))
            except Exception as e:
                log("synth", repr(e)); audio = e
            with self._cv:
                if not self._alive(g): return
                self._cache[i] = audio; self._cv.notify_all()
            if isinstance(audio, Exception): return
            i += 1

    def _consumer(self, g):
        import sounddevice as sd
        try:
            with sd.OutputStream(samplerate=SR, channels=1, dtype="float32", blocksize=2048) as st:
                while self._alive(g) and self.idx < len(self.chunks):
                    i = self.idx
                    with self._cv:
                        while self._alive(g) and i not in self._cache: self._cv.wait(0.2)
                        if not self._alive(g): return
                        audio = self._cache.pop(i)
                    if isinstance(audio, Exception): raise audio
                    _, a, b = self.chunks[i]
                    self.sentence_started.emit(i, a, b)
                    pos = 0
                    while pos < len(audio):
                        if not self._alive(g): return
                        if self._paused.is_set(): time.sleep(0.05); continue
                        st.write(audio[pos:pos + 2048].reshape(-1, 1)); pos += 2048
                    st.write(np.zeros((int(SR * 0.12), 1), np.float32))
                    with self._cv:
                        if not self._alive(g): return
                        self.idx = i + 1; self._cv.notify_all()
            if self._alive(g):
                self.idx = 0; self._set_state("stopped"); self.finished.emit()
        except Exception as e:
            log("player", repr(e))
            if self._alive(g):
                self.stop(); self.error.emit(friendly_error(e))

def friendly_error(e):
    s = str(e)
    if "PortAudio" in s or "device" in s.lower(): return "No encontré un parlante o auricular para reproducir el audio."
    if "conexión" in s or "online" in s: return s
    return "No pude leer el texto: " + s[:150]

# ---------- exportar ----------
def export_audio(text, path, progress):
    chunks = split_text(text); langs = lang_for_chunks(text, chunks)
    if not chunks: raise RuntimeError("No hay texto para exportar")
    sil = np.zeros(int(SR * 0.25), np.float32); parts = []
    for i, (s, _, _) in enumerate(chunks):
        progress(i, len(chunks), f"Oración {i + 1} de {len(chunks)}")
        parts += [engine.synth(s, langs[i], cfg.get("speed", 1.0)), sil]
    pcm = (np.clip(np.concatenate(parts), -1, 1) * 32767).astype(np.int16)
    if path.lower().endswith(".mp3"):
        import lameenc
        enc = lameenc.Encoder(); enc.set_bit_rate(128); enc.set_in_sample_rate(SR)
        enc.set_channels(1); enc.set_quality(2)
        with open(path, "wb") as f: f.write(enc.encode(pcm.tobytes()) + enc.flush())
    else:
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    progress(len(chunks), len(chunks), "Listo")
    return path

# ---------- extracción ----------
def extract_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n\n".join((p.extract_text() or "").strip() for p in PdfReader(path).pages).strip()
    if ext == ".docx":
        import docx
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: pass
    return raw.decode("utf-8", "ignore")

def extract_url(url):
    if not re.match(r"https?://", url): url = "https://" + url
    try:
        import trafilatura
        t = trafilatura.extract(trafilatura.fetch_url(url) or "", include_comments=False)
        if t and len(t) > 200: return t
    except Exception as e: log("trafilatura", e)
    import requests
    h = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
    h = re.sub(r"(?is)<(script|style|nav|header|footer|aside|noscript)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)</(p|div|h\d|li|br|tr)>|<br\s*/?>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in t.splitlines()]
    return "\n".join(l for l in lines if len(l) > 40)
