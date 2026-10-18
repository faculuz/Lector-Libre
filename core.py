# Lector Libre - núcleo: configuración, texto, motores de voz, reproductor, OCR, ePub y exportación
import os, sys, json, re, time, html, wave, zipfile, hashlib, threading, asyncio
from collections import Counter
import numpy as np
from PySide6.QtCore import QObject, Signal

APP = "Lector Libre"
DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LectorLibre")
MODEL_DIR = os.path.join(DIR, "models")
PIPER_DIR = os.path.join(MODEL_DIR, "piper")
os.makedirs(PIPER_DIR, exist_ok=True)
CFG = os.path.join(DIR, "config.json")
HIST = os.path.join(DIR, "historial.json")
BOOKMARKS = os.path.join(DIR, "marcadores.json")
LOG = os.path.join(DIR, "registro.txt")
SR = 24000

def log(*a):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + " ".join(map(str, a)) + "\n")
    except Exception:
        pass

def res(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

DEFAULT_PRONUNCIATION = {
    "Acts 29": "Hechos veintinueve",
    "Acts29": "Hechos veintinueve",
}

DEFAULT = {
    "engine": "kokoro",
    "voice_es": "ef_dora",
    "voice_en": "af_heart",
    "edge_es": "es-AR-ElenaNeural",
    "edge_en": "en-US-AriaNeural",
    "piper_es": "es_AR-daniela-high",
    "piper_en": "en_US-lessac-medium",
    "lang_default": "es",
    "autodetect": True,
    "speed": 1.0,
    "hk_read": "ctrl+alt+r",
    "hk_pause": "ctrl+alt+p",
    "hk_ocr": "ctrl+alt+o",
    "hk_page": "ctrl+alt+w",
    "mini": True,
    "mini_compact": False,
    "mini_pos": None,
    "word_highlight": True,
    "autostart": False,
    "first_run": True,
    "pronunciation": dict(DEFAULT_PRONUNCIATION),
}
cfg = dict(DEFAULT)
try:
    loaded = json.load(open(CFG, encoding="utf-8"))
    cfg.update(loaded)
    if not isinstance(cfg.get("pronunciation"), dict):
        cfg["pronunciation"] = dict(DEFAULT_PRONUNCIATION)
    else:
        for k, v in DEFAULT_PRONUNCIATION.items():
            cfg["pronunciation"].setdefault(k, v)
except Exception:
    pass

_MODS_ONLY = {"ctrl", "alt", "shift", "windows", "left windows", "right windows", "windows izquierda", "windows derecha"}
for _hk_k in ("hk_read", "hk_pause", "hk_ocr", "hk_page"):
    if cfg.get(_hk_k, "").strip().lower() in _MODS_ONLY:
        cfg[_hk_k] = DEFAULT[_hk_k]

def save_cfg():
    try:
        with open(CFG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log("save_cfg", e)

KOKORO_ES = ["ef_dora", "em_alex", "em_santa"]
KOKORO_EN = ["af_heart", "af_bella", "af_nicole", "am_michael", "am_fenrir", "bf_emma", "bm_george"]
EDGE_ES = ["es-AR-ElenaNeural", "es-AR-TomasNeural", "es-MX-DaliaNeural", "es-ES-AlvaroNeural"]
EDGE_EN = ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"]

PIPER_CATALOG = {
    "es_AR-daniela-high": ("AR · Daniela (Piper)", "es/es_AR/daniela/high/es_AR-daniela-high"),
    "es_MX-claude-high": ("MX · Claude (Piper)", "es/es_MX/claude/high/es_MX-claude-high"),
    "es_MX-ald-medium": ("MX · Ald (Piper)", "es/es_MX/ald/medium/es_MX-ald-medium"),
    "es_ES-davefx-medium": ("ES · Davefx (Piper)", "es/es_ES/davefx/medium/es_ES-davefx-medium"),
    "en_US-lessac-medium": ("US · Lessac (Piper)", "en/en_US/lessac/medium/en_US-lessac-medium"),
    "en_US-amy-medium": ("US · Amy (Piper)", "en/en_US/amy/medium/en_US-amy-medium"),
}
PIPER_ES = ["es_AR-daniela-high", "es_MX-claude-high", "es_MX-ald-medium", "es_ES-davefx-medium"]
PIPER_EN = ["en_US-lessac-medium", "en_US-amy-medium"]

def voice_label(v):
    if v in PIPER_CATALOG:
        return PIPER_CATALOG[v][0]
    if "-" in v:  # edge
        tag = "UK" if v.startswith("en-GB") else ("US" if v.startswith("en") else ("AR" if "es-AR" in v else ("MX" if "es-MX" in v else "ES")))
        return f"{tag} · {v.split('-')[-1].replace('Neural', '')} (online)"
    tag = "ES" if v[0] in "e" else ("UK" if v[0] == "b" else "US")
    return f"{tag} · {v.split('_', 1)[1].capitalize()}"

_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL_FILES = [
    (_URL + "kokoro-v1.0.onnx", os.path.join(MODEL_DIR, "kokoro-v1.0.onnx")),
    (_URL + "voices-v1.0.bin", os.path.join(MODEL_DIR, "voices-v1.0.bin")),
]

_PIPER_HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"

def piper_paths(voice_id):
    return (
        os.path.join(PIPER_DIR, f"{voice_id}.onnx"),
        os.path.join(PIPER_DIR, f"{voice_id}.onnx.json"),
    )

def piper_voice_ready(voice_id):
    return all(os.path.isfile(p) for p in piper_paths(voice_id))

def models_ready():
    eng = cfg.get("engine", "kokoro")
    if eng == "kokoro":
        return all(os.path.isfile(p) for _, p in MODEL_FILES)
    if eng == "piper":
        return piper_voice_ready(cfg.get("piper_es", PIPER_ES[0])) and piper_voice_ready(cfg.get("piper_en", PIPER_EN[0]))
    return True

def download_piper_voice(voice_id, progress=None, step_prefix=""):
    import requests
    if voice_id not in PIPER_CATALOG:
        raise RuntimeError(f"Voz Piper desconocida: {voice_id}")
    rel = PIPER_CATALOG[voice_id][1]
    onnx_dst, json_dst = piper_paths(voice_id)
    pairs = [
        (_PIPER_HF + rel + ".onnx", onnx_dst),
        (_PIPER_HF + rel + ".onnx.json", json_dst),
    ]
    for url, dst in pairs:
        if os.path.isfile(dst):
            continue
        tmp = dst + ".part"
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(tmp, "wb") as f:
                for c in r.iter_content(1 << 18):
                    if c:
                        f.write(c)
                        done += len(c)
                        if progress:
                            progress(done, total, f"{step_prefix}Descargando {voice_label(voice_id)}...")
        os.replace(tmp, dst)

def download_models(progress):
    import requests
    eng = cfg.get("engine", "kokoro")
    if eng == "piper":
        voices = [cfg.get("piper_es", PIPER_ES[0]), cfg.get("piper_en", PIPER_EN[0])]
        for idx, vid in enumerate(voices, 1):
            download_piper_voice(vid, progress, f"({idx}/{len(voices)}) ")
        return
    for i, (url, dst) in enumerate(MODEL_FILES, 1):
        if os.path.isfile(dst):
            continue
        tmp = dst + ".part"
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(tmp, "wb") as f:
                for c in r.iter_content(1 << 20):
                    f.write(c)
                    done += len(c)
                    progress(done, total, f"Descargando voces ({i}/{len(MODEL_FILES)})")
        os.replace(tmp, dst)

# ---------- historial y marcadores (#9) ----------
def load_history():
    try:
        return json.load(open(HIST, encoding="utf-8"))
    except Exception:
        return []

def add_history(texto, fuente):
    h = load_history()
    h.insert(0, {"fecha": time.strftime("%d/%m %H:%M"), "fuente": fuente, "texto": texto[:200000]})
    try:
        with open(HIST, "w", encoding="utf-8") as f:
            json.dump(h[:50], f, ensure_ascii=False)
    except Exception as e:
        log("history", e)

def clear_history():
    try:
        os.remove(HIST)
    except Exception:
        pass

def doc_key(text, fuente=""):
    norm = re.sub(r"\s+", " ", (text or "").strip())[:8000]
    if not norm:
        return ""
    return hashlib.sha1(norm.encode("utf-8", "ignore")).hexdigest()[:16]

def load_bookmarks():
    try:
        data = json.load(open(BOOKMARKS, encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_bookmark(text, fuente, sentence_idx, char_pos, total_sentences, note=""):
    key = doc_key(text, fuente)
    if not key or total_sentences <= 0:
        return
    bms = load_bookmarks()
    snippet = " ".join((text[char_pos:char_pos + 120] or text[:120]).split())
    bms[key] = {
        "key": key,
        "fuente": fuente or "Documento",
        "fecha": time.strftime("%d/%m %H:%M"),
        "idx": int(sentence_idx),
        "pos": int(char_pos),
        "total": int(total_sentences),
        "nota": note,
        "preview": snippet[:100],
        "texto": text[:200000],
    }
    # Keep latest 60 bookmarks
    ordered = sorted(bms.values(), key=lambda x: x.get("fecha", ""), reverse=True)[:60]
    bms = {item["key"]: item for item in ordered}
    try:
        with open(BOOKMARKS, "w", encoding="utf-8") as f:
            json.dump(bms, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log("save_bookmark", e)

def get_bookmark(text, fuente=""):
    key = doc_key(text, fuente)
    if not key:
        return None
    return load_bookmarks().get(key)

def delete_bookmark(key):
    bms = load_bookmarks()
    if key in bms:
        del bms[key]
        try:
            with open(BOOKMARKS, "w", encoding="utf-8") as f:
                json.dump(bms, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

# ---------- diccionario de pronunciación (#12) ----------
def apply_pronunciation(text):
    rules = cfg.get("pronunciation") or {}
    if not rules or not text:
        return text
    out = text
    # Sort longest keys first so longer phrases match before sub-words
    for src, dst in sorted(rules.items(), key=lambda kv: len(kv[0]), reverse=True):
        src_s = str(src).strip()
        dst_s = str(dst).strip()
        if not src_s or not dst_s:
            continue
        pattern = r"(?<!\w)" + re.escape(src_s) + r"(?!\w)"
        out = re.sub(pattern, dst_s, out, flags=re.IGNORECASE)
    return out

# ---------- texto y palabras (#10) ----------
_ABBR = re.compile(r"(?:\b(?:Sr|Sra|Srta|Dr|Dra|Lic|Ing|Prof|etc|ej|Mr|Mrs|Ms|vs|St|No|pág|aprox)|\b[A-Z])\.$")

def split_text(text):
    """Devuelve [(oración, inicio, fin)] con posiciones en el texto original."""
    out = []
    for m in re.finditer(r"[^\n]+", text):
        para, base = m.group(), m.start()
        spans, start = [], 0
        for s in re.finditer(r"[.!?…]+[\"'”»)\]]*(?=\s|$)", para):
            if _ABBR.search(para[:s.end()]) and s.group() == ".":
                continue
            spans.append((start, s.end()))
            start = s.end()
        if start < len(para):
            spans.append((start, len(para)))
        for a, b in spans:
            while b - a > 400:  # cortar oraciones muy largas
                seg = para[a:a + 400]
                cut = max(seg.rfind(", "), seg.rfind("; "))
                if cut < 100:
                    cut = seg.rfind(" ")
                if cut < 50:
                    cut = 400
                spans_add(out, para, base, a, a + cut + 1)
                a = a + cut + 1
            spans_add(out, para, base, a, b)
    return out

def spans_add(out, para, base, a, b):
    seg = para[a:b]
    l = len(seg) - len(seg.lstrip())
    r = len(seg.rstrip())
    if seg.strip() and re.search(r"\w", seg):
        out.append((seg.strip(), base + a + l, base + a + r))

def word_spans_in_sentence(sentence):
    """Devuelve [(palabra, rel_start, rel_end)] dentro de la oración."""
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", sentence)]

def estimate_word_timings(sentence, audio_samples, sr=SR):
    """Calcula [(rel_start, rel_end, t_start_sec, t_end_sec)] proporcional al peso fonético de cada palabra."""
    words = word_spans_in_sentence(sentence)
    if not words:
        return []
    arr = np.asarray(audio_samples, dtype=np.float32).reshape(-1)
    total_dur = len(arr) / float(sr) if len(arr) else 0.0
    if total_dur <= 0.02:
        return []
    # Trim leading/trailing silence so word highlights match spoken audio closely
    thr = 0.012
    nz = np.where(np.abs(arr) > thr)[0]
    if len(nz) >= 2:
        t0 = max(0.0, float(nz[0]) / sr - 0.01)
        t1 = min(total_dur, float(nz[-1]) / sr + 0.02)
    else:
        t0, t1 = 0.0, total_dur
    span_dur = max(0.05, t1 - t0)
    weights = []
    for w, _, _ in words:
        clean = re.sub(r"\W+", "", w)
        w_len = max(1.5, float(len(clean)))
        if re.search(r"[,:;—–]", w):
            w_len += 2.2
        weights.append(w_len)
    tot_w = sum(weights) or 1.0
    out = []
    acc = t0
    for (w, rs, re_), wg in zip(words, weights):
        d = span_dur * (wg / tot_w)
        out.append((rs, re_, acc, acc + d))
        acc += d
    return out

def _detect(t):
    try:
        from langdetect import DetectorFactory, detect_langs
        DetectorFactory.seed = 0
        for c in detect_langs(t):
            if c.lang in ("es", "en"):
                return c.lang
        return None
    except Exception:
        return None

_EN_HINT = re.compile(r"\b(the|and|is|are|you|with|this|that|have|what|for|of|to|it)\b", re.I)
_ES_HINT = re.compile(r"\b(el|la|los|las|que|de|y|es|en|un|una|por|para|con|no|se)\b", re.I)

def detect_lang(sentence, paragraph_lang):
    s = sentence.strip()
    if len(s) < 25:
        en, es = len(_EN_HINT.findall(s)), len(_ES_HINT.findall(s))
        if en > es:
            return "en"
        if es > en or re.search(r"[áéíóúñ¿¡]", s, re.I):
            return "es"
        return paragraph_lang
    return _detect(s) or paragraph_lang

def lang_for_chunks(text, chunks):
    d = cfg.get("lang_default", "es")
    if not cfg.get("autodetect", True):
        return [d] * len(chunks)
    paras = {}
    out = []
    for s, a, b in chunks:
        ps = text.rfind("\n", 0, a) + 1
        pe = text.find("\n", b)
        pe = len(text) if pe < 0 else pe
        if ps not in paras:
            paras[ps] = _detect(text[ps:pe]) or d
        out.append(detect_lang(s, paras[ps]))
    return out

# ---------- time-stretch sin cambiar el tono (#4: WSOLA) ----------
def resample(a, sr_in, sr_out):
    if len(a) == 0 or abs(sr_in - sr_out) < 1e-3:
        return np.asarray(a, dtype=np.float32)
    n = max(1, int(len(a) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)

def time_stretch_pitch_preserving(audio, rate, sr=SR):
    """Acelera o desacelera audio manteniendo el tono natural mediante WSOLA (Waveform Similarity Overlap-Add)."""
    x = np.asarray(audio, dtype=np.float32).reshape(-1)
    if len(x) < 1024 or abs(rate - 1.0) < 0.03:
        return x
    win_len = int(sr * 0.030)  # ventana de 30 ms
    if win_len % 2 == 1:
        win_len += 1
    half = win_len // 2
    search = int(sr * 0.012)   # búsqueda de fase de ±12 ms
    hann = np.hanning(win_len).astype(np.float32)

    out_len = max(win_len + 1, int(len(x) / rate))
    y = np.zeros(out_len + win_len, dtype=np.float32)
    y[:win_len] = x[:win_len] * hann

    in_pos = float(half * rate)
    out_pos = half
    prev_natural = half

    while out_pos + win_len < out_len and int(in_pos) + win_len + search < len(x):
        center = int(round(in_pos))
        lo = max(0, center - search)
        hi = min(len(x) - win_len, center + search)
        if hi > lo and prev_natural + half <= len(x):
            target = x[prev_natural:prev_natural + half]
            t_norm = float(np.dot(target, target))
            best_off = center
            if t_norm > 1e-7:
                # Evaluar candidatos cada 4 muestras para máxima velocidad y precisión de fase
                cands = range(lo, hi + 1, 4)
                best_corr = -1e18
                for c in cands:
                    seg = x[c:c + half]
                    corr = float(np.dot(target, seg))
                    if corr > best_corr:
                        best_corr = corr
                        best_off = c
            chosen = best_off
        else:
            chosen = max(0, min(center, len(x) - win_len))

        y[out_pos:out_pos + win_len] += x[chosen:chosen + win_len] * hann
        prev_natural = chosen + half
        out_pos += half
        in_pos += half * rate

    return np.clip(y[:out_pos + half], -1.0, 1.0)

# ---------- motores (#7 Piper + #4 Time-stretch + #12 Diccionario) ----------
class Engine:
    def __init__(self):
        self._k = None
        self._piper = {}
        self._lock = threading.Lock()

    def kokoro(self):
        with self._lock:
            if self._k is None:
                prepare_kokoro_runtime()
                from kokoro_onnx import Kokoro
                self._k = Kokoro(MODEL_FILES[0][1], MODEL_FILES[1][1])
            return self._k

    def piper_voice(self, voice_id):
        with self._lock:
            if voice_id not in self._piper:
                if not piper_voice_ready(voice_id):
                    download_piper_voice(voice_id)
                from piper import PiperVoice
                onnx_p, json_p = piper_paths(voice_id)
                self._piper[voice_id] = PiperVoice.load(onnx_p, config_path=json_p)
            return self._piper[voice_id]

    def synth_kokoro(self, text, lang, speed):
        v = cfg["voice_es"] if lang == "es" else cfg["voice_en"]
        kl = "es" if lang == "es" else ("en-gb" if v.startswith("b") else "en-us")
        k = self.kokoro()
        base_speed = float(max(0.5, min(1.85, speed)))
        with self._lock:
            samples, sr = k.create(text, voice=v, speed=base_speed, lang=kl)
        a = np.asarray(samples, dtype=np.float32).reshape(-1)
        if sr != SR:
            a = resample(a, sr, SR)
        if speed > 1.85:
            a = time_stretch_pitch_preserving(a, speed / 1.85, SR)
        return a

    def synth_piper(self, text, lang, speed):
        from piper.config import SynthesisConfig
        v = cfg.get("piper_es", PIPER_ES[0]) if lang == "es" else cfg.get("piper_en", PIPER_EN[0])
        pv = self.piper_voice(v)
        base_speed = float(max(0.5, min(1.8, speed)))
        syn_cfg = SynthesisConfig(length_scale=1.0 / base_speed)
        chunks = []
        with self._lock:
            for ch in pv.synthesize(text, syn_config=syn_cfg):
                chunks.append(np.asarray(ch.audio_float_array, dtype=np.float32).reshape(-1))
                sr = ch.sample_rate
        if not chunks:
            return np.zeros(int(SR * 0.1), dtype=np.float32)
        a = np.concatenate(chunks)
        if sr != SR:
            a = resample(a, sr, SR)
        if speed > 1.8:
            a = time_stretch_pitch_preserving(a, speed / 1.8, SR)
        return a

    def synth_edge(self, text, lang, speed, return_words=False):
        import edge_tts, miniaudio
        v = cfg["edge_es"] if lang == "es" else cfg["edge_en"]
        base_speed = min(speed, 2.0)
        rate = f"{int(round((base_speed - 1) * 100)):+d}%"
        words_meta = []

        async def run():
            buf = bytearray()
            comm = edge_tts.Communicate(text, v, rate=rate, boundary="WordBoundary")
            async for c in comm.stream():
                ctype = c.get("type")
                if ctype == "audio":
                    buf += c["data"]
                elif ctype == "WordBoundary":
                    words_meta.append((c.get("text", ""), c.get("offset", 0) / 1e7, c.get("duration", 0) / 1e7))
            return bytes(buf)

        data = asyncio.run(run())
        if not data:
            raise RuntimeError("Edge no devolvió audio")
        d = miniaudio.decode(data, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=SR)
        a = np.asarray(d.samples, dtype=np.float32)
        stretch = (speed / 2.0) if speed > 2.0 else 1.0
        if stretch > 1.02:
            a = time_stretch_pitch_preserving(a, stretch, SR)
        if return_words:
            return a, [(w, off / stretch, dur / stretch) for w, off, dur in words_meta]
        return a

    def synth(self, text, lang, speed):
        spoken = apply_pronunciation(text)
        eng = cfg.get("engine", "kokoro")
        if eng == "edge":
            try:
                return self.synth_edge(spoken, lang, speed)
            except Exception as e:
                log("edge falló", e)
                if not models_ready():
                    raise RuntimeError("Sin conexión para la voz online y la voz local no está descargada")
                return self.synth_kokoro(spoken, lang, speed)
        if eng == "piper":
            try:
                return self.synth_piper(spoken, lang, speed)
            except Exception as e:
                log("piper falló", e)
                if all(os.path.isfile(p) for _, p in MODEL_FILES):
                    return self.synth_kokoro(spoken, lang, speed)
                raise
        return self.synth_kokoro(spoken, lang, speed)

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

# ---------- reproductor con resaltado por palabra (#10) y cambio de velocidad/voz sin reiniciar oración (#8) ----------
class Player(QObject):
    sentence_started = Signal(int, int, int)
    word_started = Signal(int, int, int)
    state_changed = Signal(str)
    finished = Signal()
    error = Signal(str)
    AHEAD = 3

    def __init__(self):
        super().__init__()
        self.text = ""
        self.fuente = ""
        self.chunks = []
        self.langs = []
        self.idx = 0
        self.state = "stopped"
        self._gen = 0
        self._cache = {}
        self._cv = threading.Condition()
        self._paused = threading.Event()
        self._live_speed_target = None  # Para #8: aplicar time-stretch al resto de la oración actual sin reiniciarla

    def load(self, text, fuente=""):
        self.stop()
        self.text = text
        self.fuente = fuente
        self.chunks = split_text(text)
        self.langs = lang_for_chunks(text, self.chunks)

    def index_for_pos(self, pos):
        for i, (_, a, b) in enumerate(self.chunks):
            if pos <= b:
                return i
        return 0

    def _set_state(self, s):
        self.state = s
        self.state_changed.emit(s)

    def play(self, from_idx=0):
        if not self.chunks:
            return
        with self._cv:
            self._gen += 1
            g = self._gen
            self._cache = {}
            self._live_speed_target = None
            self.idx = max(0, min(from_idx, len(self.chunks) - 1))
            self._paused.clear()
            self._cv.notify_all()
        self._set_state("playing")
        threading.Thread(target=self._producer, args=(g, self.idx), daemon=True).start()
        threading.Thread(target=self._consumer, args=(g,), daemon=True).start()

    def toggle_pause(self):
        if self.state == "playing":
            self._paused.set()
            self._set_state("paused")
            self._save_progress_bookmark()
        elif self.state == "paused":
            self._paused.clear()
            self._set_state("playing")
        elif self.chunks:
            self.play(self.idx if self.idx < len(self.chunks) else 0)

    def stop(self):
        if self.state != "stopped":
            self._save_progress_bookmark()
        with self._cv:
            self._gen += 1
            self._cache = {}
            self._cv.notify_all()
        self._paused.clear()
        if self.state != "stopped":
            self._set_state("stopped")

    def _save_progress_bookmark(self):
        if len(self.chunks) >= 3 and 0 <= self.idx < len(self.chunks):
            _, a, _ = self.chunks[self.idx]
            save_bookmark(self.text, self.fuente, self.idx, a, len(self.chunks))

    def next(self):
        if self.chunks and self.state != "stopped":
            self.play(min(self.idx + 1, len(self.chunks) - 1))

    def prev(self):
        if self.chunks and self.state != "stopped":
            self.play(max(self.idx - 1, 0))

    def set_speed(self, x):
        """#8: Cambia la velocidad al vuelo sin reiniciar la oración actual.
        Estira el resto del audio de la oración actual con WSOLA y regenera el buffer futuro."""
        new_s = float(x)
        cfg["speed"] = new_s
        save_cfg()
        if self.state == "stopped":
            return
        with self._cv:
            self._live_speed_target = new_s
            for k in list(self._cache.keys()):
                if k > self.idx:
                    del self._cache[k]
            self._cv.notify_all()
        threading.Thread(target=self._producer, args=(self._gen, self.idx + 1), daemon=True).start()

    def reset_voices(self):
        """#8: Cambia la voz sin reiniciar la oración que ya está sonando; aplica a partir de la siguiente."""
        if self.state == "stopped":
            return
        with self._cv:
            for k in list(self._cache.keys()):
                if k > self.idx:
                    del self._cache[k]
            self._cv.notify_all()
        threading.Thread(target=self._producer, args=(self._gen, self.idx + 1), daemon=True).start()

    def _alive(self, g):
        return g == self._gen

    def _producer(self, g, start_idx=None):
        i = self.idx if start_idx is None else start_idx
        while self._alive(g) and i < len(self.chunks):
            with self._cv:
                while self._alive(g) and i > self.idx + self.AHEAD:
                    self._cv.wait(0.2)
                if not self._alive(g):
                    return
                if i in self._cache:
                    i += 1
                    continue
            spd = cfg.get("speed", 1.0)
            try:
                audio = engine.synth(self.chunks[i][0], self.langs[i], spd)
                payload = (audio, spd)
            except Exception as e:
                log("synth", repr(e))
                payload = e
            with self._cv:
                if not self._alive(g):
                    return
                self._cache[i] = payload
                self._cv.notify_all()
            if isinstance(payload, Exception):
                return
            i += 1

    def _consumer(self, g):
        import sounddevice as sd
        try:
            with sd.OutputStream(samplerate=SR, channels=1, dtype="float32", blocksize=1024) as st:
                while self._alive(g) and self.idx < len(self.chunks):
                    i = self.idx
                    with self._cv:
                        while self._alive(g) and i not in self._cache:
                            self._cv.wait(0.1)
                        if not self._alive(g):
                            return
                        item = self._cache.pop(i)
                    if isinstance(item, Exception):
                        raise item
                    audio, synth_speed = item
                    sent_text, a, b = self.chunks[i]
                    self.sentence_started.emit(i, a, b)
                    if i % 3 == 0:
                        self._save_progress_bookmark()

                    w_timings = estimate_word_timings(sent_text, audio, SR)
                    w_idx = 0
                    pos = 0
                    cur_speed = synth_speed

                    while pos < len(audio):
                        if not self._alive(g):
                            return
                        if self._paused.is_set():
                            time.sleep(0.04)
                            continue
                        # #8: Si el usuario cambió la velocidad a mitad de la oración, estirar el tramo restante
                        if self._live_speed_target is not None and abs(self._live_speed_target - cur_speed) > 0.04:
                            target_s = self._live_speed_target
                            self._live_speed_target = None
                            ratio = target_s / max(0.25, cur_speed)
                            rem = audio[pos:]
                            stretched = time_stretch_pitch_preserving(rem, ratio, SR)
                            audio = np.concatenate([audio[:pos], stretched])
                            cur_speed = target_s
                            w_timings = estimate_word_timings(sent_text, audio, SR)

                        t_sec = pos / float(SR)
                        while w_idx < len(w_timings) and t_sec >= w_timings[w_idx][2]:
                            rs, re_, _, _ = w_timings[w_idx]
                            self.word_started.emit(i, a + rs, a + re_)
                            w_idx += 1

                        st.write(audio[pos:pos + 1024].reshape(-1, 1))
                        pos += 1024

                    st.write(np.zeros((int(SR * 0.10), 1), np.float32))
                    with self._cv:
                        if not self._alive(g):
                            return
                        self.idx = i + 1
                        self._cv.notify_all()
            if self._alive(g):
                self.idx = 0
                self._set_state("stopped")
                self.finished.emit()
        except Exception as e:
            log("player", repr(e))
            if self._alive(g):
                self.stop()
                self.error.emit(friendly_error(e))

def friendly_error(e):
    s = str(e)
    if "PortAudio" in s or "device" in s.lower():
        return "No encontré un parlante o auricular para reproducir el audio."
    if "conexión" in s or "online" in s:
        return s
    return "No pude leer el texto: " + s[:150]

# ---------- exportar audio y audiolibro por capítulos (#11) ----------
def _save_pcm_file(pcm_int16, path):
    if path.lower().endswith(".mp3"):
        import lameenc
        enc = lameenc.Encoder()
        enc.set_bit_rate(128)
        enc.set_in_sample_rate(SR)
        enc.set_channels(1)
        enc.set_quality(2)
        with open(path, "wb") as f:
            f.write(enc.encode(pcm_int16.tobytes()) + enc.flush())
    else:
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm_int16.tobytes())

def export_audio(text, path, progress):
    chunks = split_text(text)
    langs = lang_for_chunks(text, chunks)
    if not chunks:
        raise RuntimeError("No hay texto para exportar")
    sil = np.zeros(int(SR * 0.25), np.float32)
    parts = []
    for i, (s, _, _) in enumerate(chunks):
        progress(i, len(chunks), f"Oración {i + 1} de {len(chunks)}")
        parts += [engine.synth(s, langs[i], cfg.get("speed", 1.0)), sil]
    pcm = (np.clip(np.concatenate(parts), -1, 1) * 32767).astype(np.int16)
    _save_pcm_file(pcm, path)
    progress(len(chunks), len(chunks), "Listo")
    return path

_CHAP_RE = re.compile(
    r"(?m)^\s*(?:[#]{1,3}\s+.+|(?:Cap[íi]tulo|Chapter|Parte|Part|Secci[óo]n|Libro|Acto)\s+(?:\d+|[IVXLCDM]+|[\wÁÉÍÓÚÑáéíóúñ]+)[^\n]*)\s*$",
    re.IGNORECASE,
)

def split_into_chapters(text):
    """Divide un documento largo en [(titulo_capitulo, contenido)] por encabezados o bloques lógicos."""
    matches = list(_CHAP_RE.finditer(text))
    chapters = []
    if len(matches) >= 2:
        if matches[0].start() > 200:
            intro = text[:matches[0].start()].strip()
            if intro:
                chapters.append(("00 - Introducción", intro))
        for idx, m in enumerate(matches, 1):
            title = re.sub(r"^[#\s]+", "", m.group(0)).strip()[:60]
            start = m.start()
            end = matches[idx].start() if idx < len(matches) else len(text)
            body = text[start:end].strip()
            if body:
                chapters.append((f"{idx:02d} - {title}", body))
        if chapters:
            return chapters

    # Fallback: dividir cada ~4500 caracteres en límite de párrafo
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    buf, acc, idx = [], 0, 1
    for p in paras:
        buf.append(p)
        acc += len(p)
        if acc >= 4500:
            first_line = buf[0].splitlines()[0][:45].strip(" .,:;#")
            chapters.append((f"Capítulo {idx:02d} - {first_line}", "\n\n".join(buf)))
            buf, acc = [], 0
            idx += 1
    if buf:
        first_line = buf[0].splitlines()[0][:45].strip(" .,:;#")
        chapters.append((f"Capítulo {idx:02d} - {first_line}", "\n\n".join(buf)))
    return chapters or [("Capítulo 01", text)]

def export_audiobook(text, out_dir, fmt, progress, chapters_override=None):
    """#11: Exporta un documento o libro en múltiples archivos de audio por capítulo + playlist .m3u."""
    os.makedirs(out_dir, exist_ok=True)
    chapters = chapters_override if chapters_override else split_into_chapters(text)
    all_Jobs = []
    for title, body in chapters:
        ch_chunks = split_text(body)
        if ch_chunks:
            all_Jobs.append((title, body, ch_chunks, lang_for_chunks(body, ch_chunks)))
    if not all_Jobs:
        raise RuntimeError("No hay capítulos con texto para exportar")

    total_sents = sum(len(c) for _, _, c, _ in all_Jobs)
    done_sents = 0
    sil = np.zeros(int(SR * 0.25), np.float32)
    ext = ".mp3" if fmt.lower().strip(".") == "mp3" else ".wav"
    saved_files = []

    for c_idx, (title, _, ch_chunks, langs) in enumerate(all_Jobs, 1):
        safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" ._")[:80] or f"Capitulo_{c_idx:02d}"
        fname = f"{safe_title}{ext}"
        fpath = os.path.join(out_dir, fname)
        parts = []
        for s_idx, (s, _, _) in enumerate(ch_chunks):
            progress(done_sents, total_sents, f"Cap. {c_idx}/{len(all_Jobs)} ({safe_title[:28]}) · oración {s_idx + 1}/{len(ch_chunks)}")
            parts += [engine.synth(s, langs[s_idx], cfg.get("speed", 1.0)), sil]
            done_sents += 1
        pcm = (np.clip(np.concatenate(parts), -1, 1) * 32767).astype(np.int16)
        _save_pcm_file(pcm, fpath)
        saved_files.append(fname)

    m3u_path = os.path.join(out_dir, "Audiolibro.m3u")
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for fn in saved_files:
            f.write(fn + "\n")
    progress(total_sents, total_sents, "Audiolibro completado")
    return saved_files

# ---------- extracción inteligente: PDF sin encabezados/pies repetidos (#2), ePub (#10), Web y Formularios (#2) ----------
def _clean_pdf_pages(raw_pages):
    """Elimina números de página sueltos y encabezados/pies que se repiten en múltiples páginas."""
    if len(raw_pages) <= 1:
        return "\n\n".join(raw_pages).strip()

    def norm_line(ln):
        return re.sub(r"\d+", "#", ln.strip().lower())

    top_counts = Counter()
    bot_counts = Counter()
    split_pages = []
    for p in raw_pages:
        lines = [l.strip() for l in p.splitlines() if l.strip()]
        split_pages.append(lines)
        if lines and len(lines[0]) < 90:
            top_counts[norm_line(lines[0])] += 1
        if len(lines) >= 2 and len(lines[-1]) < 90:
            bot_counts[norm_line(lines[-1])] += 1

    min_rep = max(2, int(len(raw_pages) * 0.4))
    page_num_re = re.compile(
        r"^(?:p[áa]g(?:ina)?\.?\s*\d+(?:\s*(?:de|/)\s*\d+)?|\d+\s*(?:de|/)\s*\d+|\d{1,4}|[-–—]\s*\d+\s*[-–—])$",
        re.I,
    )

    cleaned_pages = []
    for lines in split_pages:
        if not lines:
            continue
        new_lines = []
        for idx, l in enumerate(lines):
            is_top = idx == 0
            is_bot = idx == len(lines) - 1 and len(lines) >= 2
            nl = norm_line(l)
            if is_top and (page_num_re.match(l) or top_counts[nl] >= min_rep):
                continue
            if is_bot and (page_num_re.match(l) or bot_counts[nl] >= min_rep):
                continue
            new_lines.append(l)
        if new_lines:
            cleaned_pages.append("\n".join(new_lines))
    return "\n\n".join(cleaned_pages).strip()

def extract_epub_chapters(path):
    """#10 & #11: Extrae capítulos de un archivo .epub en orden de lectura (spine)."""
    from bs4 import BeautifulSoup
    chapters = []
    with zipfile.ZipFile(path, "r") as z:
        namelist = z.namelist()
        opf_path = None
        if "META-INF/container.xml" in namelist:
            c_soup = BeautifulSoup(z.read("META-INF/container.xml"), "html.parser")
            rf = c_soup.find("rootfile")
            if rf and rf.get("full-path"):
                opf_path = rf.get("full-path")
        if not opf_path:
            opf_cands = [n for n in namelist if n.lower().endswith(".opf")]
            opf_path = opf_cands[0] if opf_cands else None

        ordered_hrefs = []
        base_dir = os.path.dirname(opf_path).replace("\\", "/") if opf_path else ""
        if opf_path and opf_path in namelist:
            opf_soup = BeautifulSoup(z.read(opf_path), "html.parser")
            manifest = {}
            for item in opf_soup.find_all("item"):
                iid = item.get("id")
                href = item.get("href")
                if iid and href:
                    full_h = f"{base_dir}/{href}".lstrip("/") if base_dir else href
                    manifest[iid] = full_h
            for iref in opf_soup.find_all("itemref"):
                idref = iref.get("idref")
                if idref in manifest:
                    ordered_hrefs.append(manifest[idref])

        if not ordered_hrefs:
            ordered_hrefs = sorted(n for n in namelist if n.lower().endswith((".xhtml", ".html", ".htm")))

        for idx, href in enumerate(ordered_hrefs, 1):
            cand = href if href in namelist else next((n for n in namelist if n.endswith(href)), None)
            if not cand:
                continue
            raw_html = z.read(cand).decode("utf-8", "ignore")
            soup = BeautifulSoup(raw_html, "html.parser")
            for bad in soup(["script", "style", "nav", "head"]):
                bad.decompose()
            h_tag = soup.find(["h1", "h2", "h3", "title"])
            title = h_tag.get_text(" ", strip=True) if h_tag else f"Capítulo {idx:02d}"
            paras = [p.get_text(" ", strip=True) for p in soup.find_all(["h1", "h2", "h3", "p", "li", "blockquote"])]
            paras = [p for p in paras if p]
            body = "\n\n".join(paras) if paras else soup.get_text("\n", strip=True)
            if len(body.strip()) > 20:
                chapters.append((f"{idx:02d} - {title[:50]}", f"# {title}\n\n{body.strip()}"))
    return chapters

def extract_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        raw_pages = [(p.extract_text() or "").strip() for p in PdfReader(path).pages]
        return _clean_pdf_pages([p for p in raw_pages if p])
    if ext == ".docx":
        import docx
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    if ext == ".epub":
        chaps = extract_epub_chapters(path)
        return "\n\n".join(body for _, body in chaps).strip()
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "ignore")

def extract_structured_html(raw_html):
    """#2: Extracción inteligente para páginas web y formularios (ej. Acts 29):
    Lee encabezados, artículos, etiquetas de formulario, preguntas y respuestas,
    y salta menús, barras de navegación, cabeceras y pies de página."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw_html, "html.parser")

    # Eliminar navegación, menús, pies y ruido visual
    for tag in soup.find_all(["script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "menu"]):
        tag.decompose()
    for el in list(soup.find_all(True)):
        if el.attrs is None:
            continue
        role = str(el.get("role", "")).lower()
        cls_id = " ".join(
            [str(el.get("id", "")), " ".join(el.get("class", []) if isinstance(el.get("class"), list) else [str(el.get("class", ""))])]
        ).lower()
        if role in ("navigation", "banner", "contentinfo", "menubar", " menu", "toolbar", "complementary"):
            el.decompose()
            continue
        if re.search(r"\b(navbar|nav-menu|sidebar|footer|cookie|breadcrumb|pagination|topbar|menu-item)\b", cls_id):
            el.decompose()

    root = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.find("article") or soup.find("form") or soup.body or soup
    lines = []
    seen = set()

    def emit_line(txt):
        t = re.sub(r"\s+", " ", (txt or "").strip())
        if len(t) < 2 or t in seen:
            return
        seen.add(t)
        lines.append(t)

    # Mapear labels por atributo 'for'
    labels_by_for = {}
    for lb in root.find_all("label"):
        f_id = lb.get("for")
        if f_id:
            labels_by_for[f_id] = lb.get_text(" ", strip=True)

    for el in root.find_all(["h1", "h2", "h3", "h4", "legend", "p", "li", "blockquote", "label", "input", "textarea", "select", "dd", "dt"]):
        name = el.name
        if name in ("h1", "h2", "h3", "h4", "legend"):
            emit_line(f"\n# {el.get_text(' ', strip=True)}")
        elif name in ("p", "li", "blockquote", "dt", "dd"):
            if el.find_parent(["label", "button", "nav", "footer"]):
                continue
            emit_line(el.get_text(" ", strip=True))
        elif name == "label":
            emit_line(f"Pregunta: {el.get_text(' ', strip=True)}")
        elif name == "textarea":
            val = (el.string or el.get_text(" ", strip=True) or el.get("value") or "").strip()
            lbl = labels_by_for.get(el.get("id"), "") or el.get("aria-label", "") or el.get("placeholder", "")
            if lbl:
                emit_line(f"Pregunta: {lbl}")
            if val:
                emit_line(f"Respuesta: {val}")
        elif name == "select":
            sel_opts = [o.get_text(" ", strip=True) for o in el.find_all("option") if o.has_attr("selected")]
            if not sel_opts and el.find("option"):
                sel_opts = [el.find("option").get_text(" ", strip=True)]
            if sel_opts:
                emit_line(f"Opción seleccionada: {', '.join(sel_opts)}")
        elif name == "input":
            itype = (el.get("type") or "text").lower()
            if itype in ("hidden", "submit", "button", "reset", "image", "password"):
                continue
            if itype in ("checkbox", "radio"):
                if el.has_attr("checked"):
                    lbl = labels_by_for.get(el.get("id"), "") or el.get("aria-label", "") or el.get("value", "")
                    if lbl:
                        emit_line(f"Seleccionado: {lbl}")
            else:
                val = (el.get("value") or "").strip()
                if val:
                    emit_line(f"Respuesta: {val}")

    structured = "\n".join(lines).strip()
    if len(structured) >= 20:
        return structured
    return ""

def extract_url(url):
    if not re.match(r"https?://", url):
        url = "https://" + url
    import requests
    raw_html = ""
    try:
        raw_html = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
    except Exception as e:
        log("requests url", e)

    if raw_html:
        # Si contiene formularios o campos de preguntas/respuestas, priorizar el extractor estructurado
        if "<form" in raw_html.lower() or "<textarea" in raw_html.lower() or "question" in raw_html.lower():
            s_txt = extract_structured_html(raw_html)
            if len(s_txt) > 120:
                return s_txt
        try:
            import trafilatura
            t = trafilatura.extract(raw_html, include_comments=False, include_Fallback=True)
            if t and len(t) > 200:
                return t
        except Exception as e:
            log("trafilatura", e)
        s_txt = extract_structured_html(raw_html)
        if s_txt:
            return s_txt

    raise RuntimeError("No se pudo extraer texto de la dirección indicada.")

# ---------- lectura desde el cursor / página actual con UI Automation (#1, #2, #6) ----------
_NOISE_ROLES = {"MenuBar", "MenuItem", "ToolBar", "StatusBar", "ScrollBar", "TabItem", "TitleBar", "Header", "HeaderItem"}
_last_external_hwnd = None

def update_external_foreground():
    """Registra periódicamente el HWND de la última ventana externa activa (navegador, Word, PDF, etc.)."""
    global _last_external_hwnd
    try:
        import ctypes
        u32 = ctypes.windll.user32
        hwnd = u32.GetForegroundWindow()
        if not hwnd or not u32.IsWindowVisible(hwnd):
            return
        pid = ctypes.c_ulong(0)
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value and pid.value != os.getpid():
            _last_external_hwnd = hwnd
    except Exception:
        pass

def restore_external_foreground():
    """Si el usuario hizo clic en un botón de Lector Libre, devuelve el foco a la ventana externa anterior."""
    try:
        import ctypes
        u32 = ctypes.windll.user32
        cur = u32.GetForegroundWindow()
        pid = ctypes.c_ulong(0)
        if cur:
            u32.GetWindowThreadProcessId(cur, ctypes.byref(pid))
        if (not cur or pid.value == os.getpid()) and _last_external_hwnd and u32.IsWindow(_last_external_hwnd):
            u32.SetForegroundWindow(_last_external_hwnd)
            time.sleep(0.12)
    except Exception:
        pass

def read_from_cursor_or_selection(prefer_full_page=False):
    """
    1) Si prefer_full_page=True (#6 'Leer esta página'), extrae de forma inteligente el contenido y formularios
       de la ventana/pestaña activa (vía UI Automation o URL del navegador), saltando menús y barras.
    2) Si hay texto seleccionado, lo devuelve.
    3) Si no hay selección (#1), usa UI Automation TextPattern desde la posición del cursor (caret) hasta el final,
       o recorre los elementos de contenido/formulario desde el elemento con foco hacia adelante.
       Respaldo final: simula Ctrl+Shift+End, copia y restaura el cursor.
    Devuelve (texto, fuente).
    """
    import pyperclip, keyboard
    restore_external_foreground()

    if prefer_full_page:
        txt, src = _extract_active_window_smart(from_focus_only=False)
        if txt and len(txt.strip()) > 20:
            return txt.strip(), src

    # Paso A: Intentar copiar selección actual sin alterar el cursor
    try:
        old_clip = pyperclip.paste()
    except Exception:
        old_clip = ""
    try:
        pyperclip.copy("")
    except Exception:
        pass
    for k in ("ctrl", "alt", "shift", "windows"):
        try:
            keyboard.release(k)
        except Exception:
            pass
    time.sleep(0.12)
    keyboard.send("ctrl+c")
    sel_text = ""
    for _ in range(6):
        time.sleep(0.07)
        try:
            sel_text = pyperclip.paste()
            if sel_text:
                break
        except Exception:
            pass

    if sel_text and sel_text.strip() and not prefer_full_page:
        try:
            if old_clip:
                pyperclip.copy(old_clip)
        except Exception:
            pass
        return sel_text.strip(), "Selección"

    # Paso B (#1): No había texto seleccionado -> Leer desde la posición del cursor con UI Automation
    uia_text, uia_src = _extract_from_cursor_uia()
    if uia_text and len(uia_text.strip()) > 5:
        try:
            if old_clip:
                pyperclip.copy(old_clip)
        except Exception:
            pass
        return uia_text.strip(), uia_src

    # Paso C (#1 Respaldo): Simular Ctrl+Shift+End para copiar desde el cursor hasta el final y deshacer selección
    try:
        pyperclip.copy("")
        keyboard.send("ctrl+shift+end")
        time.sleep(0.14)
        keyboard.send("ctrl+c")
        for _ in range(8):
            time.sleep(0.08)
            try:
                sel_text = pyperclip.paste()
                if sel_text:
                    break
            except Exception:
                pass
        keyboard.send("left")  # Devolver el cursor a donde estaba sin dejar todo pintado
    except Exception as e:
        log("fallback shift+ctrl+end", e)
    finally:
        try:
            if old_clip:
                pyperclip.copy(old_clip)
        except Exception:
            pass

    if sel_text and sel_text.strip():
        return sel_text.strip(), "Desde el cursor"
    return "", ""

def _extract_from_cursor_uia():
    """Intenta obtener el texto desde el cursor/foco actual usando Windows UI Automation."""
    try:
        import uiautomation as auto
        with auto.UIAutomationInitializerInThread():
            focused = auto.GetFocusedControl()
            if not focused:
                return "", ""
            # 1. Intentar TextPattern desde el caret/selección hasta el fin del documento
            try:
                tp = focused.GetTextPattern()
                if tp:
                    sels = tp.GetSelection()
                    doc_range = tp.DocumentRange
                    if sels and len(sels) > 0 and doc_range:
                        caret_range = sels[0].Clone()
                        # Mover el extremo final del rango del cursor al final del documento
                        caret_range.MoveEndpointByRange(
                            auto.TextPatternRangeEndpoint.End,
                            doc_range,
                            auto.TextPatternRangeEndpoint.End,
                        )
                        txt = caret_range.GetText(-1)
                        if txt and len(txt.strip()) > 3:
                            return txt.strip(), "Desde el cursor (UIA)"
                    full_doc = doc_range.GetText(-1) if doc_range else ""
                    if full_doc and len(full_doc.strip()) > 3:
                        return full_doc.strip(), "Documento desde cursor"
            except Exception:
                pass

            # 2. Si es un campo o nodo dentro de una página web / formulario (ej. Acts 29),
            # recorrer el árbol desde el control en foco hacia adelante
            txt, src = _extract_active_window_smart(from_focus_only=True)
            if txt:
                return txt, src
    except Exception as e:
        log("uia cursor", e)
    return "", ""

def _extract_active_window_smart(from_focus_only=False):
    """Extrae texto, etiquetas, preguntas y respuestas de la ventana/página activa usando UI Automation,
    saltando menús, pestañas y barras de navegación."""
    try:
        import uiautomation as auto
        with auto.UIAutomationInitializerInThread():
            fg = auto.GetForegroundControl()
            focused = auto.GetFocusedControl() if from_focus_only else None
            if not fg:
                return "", ""
            win_title = (fg.Name or "Página activa")[:50]

            # Buscar primero el contenedor Document (contenido de la página en Chrome/Edge/Firefox/Apps)
            doc_ctrl = None
            for c, depth in auto.WalkControl(fg, maxDepth=8):
                if c.ControlTypeName == "DocumentControl":
                    doc_ctrl = c
                    break
            root = doc_ctrl or fg

            started = not bool(focused)
            lines = []
            seen = set()

            def add_line(s):
                t = re.sub(r"\s+", " ", (s or "").strip())
                if len(t) < 2 or t in seen:
                    return
                seen.add(t)
                lines.append(t)

            for ctrl, depth in auto.WalkControl(root, maxDepth=14):
                ctype = ctrl.ControlTypeName
                if ctype in ("MenuBarControl", "MenuItemControl", "ToolBarControl", "TabControl", "TabItemControl", "StatusBarControl", "TitleBarControl", "ScrollBarControl"):
                    continue
                if not started:
                    try:
                        if auto.ControlsAreSame(ctrl, focused):
                            started = True
                        else:
                            continue
                    except Exception:
                        started = True

                name = (ctrl.Name or "").strip()
                if ctype == "HeaderControl" or "Heading" in (ctrl.LocalizedControlType or ""):
                    if name:
                        add_line(f"\n# {name}")
                elif ctype == "EditControl":
                    val = ""
                    try:
                        vp = ctrl.GetValuePattern()
                        if vp:
                            val = (vp.Value or "").strip()
                    except Exception:
                        pass
                    if name and len(name) > 2:
                        add_line(f"Pregunta: {name}")
                    if val:
                        add_line(f"Respuesta: {val}")
                elif ctype == "ComboBoxControl":
                    val = ""
                    try:
                        vp = ctrl.GetValuePattern()
                        if vp:
                            val = (vp.Value or "").strip()
                    except Exception:
                        pass
                    if name:
                        add_line(f"Campo: {name}")
                    if val:
                        add_line(f"Opción: {val}")
                elif ctype in ("RadioButtonControl", "CheckBoxControl"):
                    try:
                        # Mostrar opciones marcadas o con etiqueta clara
                        tp = ctrl.GetTogglePattern()
                        if tp and tp.ToggleState == 1 and name:
                            add_line(f"Seleccionado: {name}")
                    except Exception:
                        pass
                elif ctype in ("TextControl", "DataItemControl", "ListItemControl"):
                    if name and len(name) >= 3:
                        add_line(name)

            out = "\n".join(lines).strip()
            if len(out) > 20:
                return out, f"Página: {win_title}"
    except Exception as e:
        log("extract_active_window_smart", e)
    return "", ""

# ---------- OCR de pantalla con Windows OCR (#5) ----------
def recognize_image_winocr(pil_image, lang=None):
    """Ejecuta el motor nativo Windows Media OCR sobre una imagen PIL."""
    import winocr
    ocr_lang = lang or cfg.get("lang_default", "es")

    async def _run(l_code):
        return (await winocr.recognize_pil(pil_image, l_code)).text

    for candidate in (ocr_lang, "es", "en"):
        try:
            txt = asyncio.run(_run(candidate))
            if txt and txt.strip():
                return txt.strip()
        except Exception:
            continue
    return ""
