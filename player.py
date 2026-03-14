#!/usr/bin/env python3
"""
PlayAds Player v6.1
- Layout profissional renovado (2 painéis no Player, sidebar elegante)
- Pasta  local/  para mídias baixadas — sempre visível na aba All
- Clique na mídia abre modal: hora agendada + loops + botão tocar
- Desconectar limpa todos os JSONs e cache
- Duck de volume síncrono + SSE listeners + agendamentos
"""

import os, sys, json, time, threading, platform, logging, queue, hashlib, webbrowser, math
from datetime import datetime
from pathlib import Path

# ─── Deps ───────────────────────────────────────────────────────────────────
try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 2, 4096)
    pygame.mixer.init()
except ImportError:
    print("ERRO: pip install pygame"); sys.exit(1)

try:
    import requests
except ImportError:
    print("ERRO: pip install requests"); sys.exit(1)

try:
    from pycaw.pycaw import AudioUtilities
    import comtypes
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

import tkinter as tk
from tkinter import ttk, messagebox

# ─── Paleta ─────────────────────────────────────────────────────────────────
BG      = "#0d0b14"
SURF    = "#13111f"
SURF2   = "#1a1728"
SURF3   = "#221f33"
SURF4   = "#2a2740"
BORDER  = "#332f4d"
PURPLE  = "#9b59f5"
PURPLE2 = "#7c3aed"
PURPLE3 = "#4c1d95"
PURPLE4 = "#3b1585"
TEXT    = "#f0eeff"
MUTED   = "#7a7490"
MUTED2  = "#a89ec0"
DANGER  = "#f43f5e"
WARN    = "#f59e0b"
GREEN   = "#10b981"
CYAN    = "#06b6d4"

FH1    = ("Segoe UI", 13, "bold")
FH2    = ("Segoe UI", 11, "bold")
FTIT   = ("Segoe UI", 10, "bold")
FBODY  = ("Segoe UI", 9)
FSMALL = ("Segoe UI", 8)
FMONO  = ("Consolas", 9)
FMONO2 = ("Consolas", 8)
FXSMALL= ("Segoe UI", 7)

# ─── Caminhos ────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
LOCAL_DIR       = BASE_DIR / "local"          # ← pasta de mídias baixadas
LOCAL_DIR.mkdir(exist_ok=True)
CACHE_INDEX     = BASE_DIR / "local" / ".index.json"
ACTIVATION_FILE = BASE_DIR / "activation.json"
CONFIG_FILE     = BASE_DIR / "playads_config.json"
LOCAL_PL_FILE   = BASE_DIR / "local_playlists.json"
LOCAL_AD_FILE   = BASE_DIR / "local_anuncios.json"
LOCAL_LOG_FILE  = BASE_DIR / "local_logs.json"

# ─── Firebase ────────────────────────────────────────────────────────────────
FIREBASE_WEB_API_KEY = "AIzaSyBgwB_2syWdyK5Wc0E9rJIlDnXjwTf1OWE"
FIREBASE_DB_URL      = "https://anucio-web-default-rtdb.firebaseio.com"
FIREBASE_AUTH_URL    = "https://identitytoolkit.googleapis.com/v1/accounts"
FIREBASE_REFRESH_URL = "https://securetoken.googleapis.com/v1/token"
WEB_URL              = "https://anucio-web.web.app"

# ─── Config ──────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "player_nome":    "Player Principal",
    "volume_anuncio": 100,
    "volume_outros":  10,
    "duck_fade_ms":   1200,
}

def load_config():
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False))
    raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    for k, v in DEFAULT_CONFIG.items():
        raw.setdefault(k, v)
    return raw

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

# ─── Auth ────────────────────────────────────────────────────────────────────
class _Auth:
    id_token = refresh_token = ""
    expires_at = 0.0
    lock = threading.Lock()

_AUTH = _Auth()

def auth_sign_in(email, password):
    try:
        r = requests.post(
            f"{FIREBASE_AUTH_URL}:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
            json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
        if not r.ok: return False
        d = r.json()
        with _AUTH.lock:
            _AUTH.id_token      = d["idToken"]
            _AUTH.refresh_token = d["refreshToken"]
            _AUTH.expires_at    = time.time() + int(d.get("expiresIn", 3600)) - 60
        return True
    except: return False

def auth_refresh():
    if not _AUTH.refresh_token: return False
    try:
        r = requests.post(
            f"{FIREBASE_REFRESH_URL}?key={FIREBASE_WEB_API_KEY}",
            json={"grant_type": "refresh_token", "refresh_token": _AUTH.refresh_token}, timeout=10)
        if not r.ok: return False
        d = r.json()
        with _AUTH.lock:
            _AUTH.id_token      = d["id_token"]
            _AUTH.refresh_token = d["refresh_token"]
            _AUTH.expires_at    = time.time() + int(d.get("expires_in", 3600)) - 60
        return True
    except: return False

def get_token():
    if time.time() >= _AUTH.expires_at: auth_refresh()
    return _AUTH.id_token

def _token_loop():
    while True:
        try:
            rem = _AUTH.expires_at - time.time()
            time.sleep(max(60, rem - 120))
            if _AUTH.refresh_token: auth_refresh()
        except: time.sleep(300)

# ─── Ativação ────────────────────────────────────────────────────────────────
def load_activation():
    if ACTIVATION_FILE.exists():
        try: return json.loads(ACTIVATION_FILE.read_text(encoding="utf-8"))
        except: pass
    return None

def save_activation(uid, email, codigo, senha=""):
    ACTIVATION_FILE.write_text(
        json.dumps({"uid": uid, "email": email, "codigo": codigo, "senha": senha}, indent=2),
        encoding="utf-8")

def clear_all_local():
    """Remove activation + todos os JSONs + cache de áudio na pasta local/."""
    for f in [ACTIVATION_FILE, LOCAL_PL_FILE, LOCAL_AD_FILE, LOCAL_LOG_FILE, CONFIG_FILE, CACHE_INDEX]:
        try:
            if f.exists(): f.unlink()
        except: pass
    for f in LOCAL_DIR.glob("*"):
        try:
            if f.is_file(): f.unlink()
        except: pass

def validate_and_login(codigo, email, senha):
    codigo = codigo.strip().upper()
    try:
        r = requests.get(f"{FIREBASE_DB_URL}/codigos/{codigo}.json", timeout=10)
        if not r.ok: return None, None, "Servidor indisponível."
        data = r.json()
        if not data or not data.get("uid"): return None, None, "Código inválido."
        uid = data["uid"]
    except Exception as e:
        return None, None, f"Erro de conexão: {e}"
    if not auth_sign_in(email, senha): return None, None, "E-mail ou senha incorretos."
    try:
        r2 = requests.get(f"{FIREBASE_DB_URL}/users/{uid}/email.json?auth={get_token()}", timeout=10)
        stored = r2.json() if r2.ok else email
    except: stored = email
    return uid, stored or email, None

# ─── Cache / Local ────────────────────────────────────────────────────────────
def load_cache_index():
    if CACHE_INDEX.exists():
        try: return json.loads(CACHE_INDEX.read_text(encoding="utf-8"))
        except: pass
    return {}

def save_cache_index(idx):
    CACHE_INDEX.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")

def url_key(url): return hashlib.md5(url.encode()).hexdigest()

def get_cached(url):
    e = load_cache_index().get(url_key(url))
    if e and Path(e["path"]).exists(): return e["path"]
    return None

def set_cached(url, path, nome="", tipo=""):
    idx = load_cache_index()
    idx[url_key(url)] = {
        "path": str(path), "nome": nome, "tipo": tipo, "ts": int(time.time()),
        "tamanho": Path(path).stat().st_size if Path(path).exists() else 0
    }
    save_cache_index(idx)

def scan_local_files():
    """Lê pasta local/ e retorna lista de dicts com info das mídias baixadas."""
    idx   = load_cache_index()
    files = []
    for entry in sorted(LOCAL_DIR.iterdir(), key=lambda f: f.stat().st_mtime if f.is_file() else 0, reverse=True):
        if not entry.is_file() or entry.name.startswith("."): continue
        if not entry.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a"): continue
        # Tenta encontrar metadados no índice
        meta = next((v for v in idx.values() if Path(v["path"]) == entry), None)
        files.append({
            "path":    str(entry),
            "nome":    meta["nome"] if meta else entry.stem,
            "tipo":    meta.get("tipo", entry.suffix.lstrip(".").upper()) if meta else entry.suffix.lstrip(".").upper(),
            "ts":      meta["ts"]   if meta else int(entry.stat().st_mtime),
            "tamanho": entry.stat().st_size,
        })
    return files

# ─── Estado Global ────────────────────────────────────────────────────────────
class State:
    lock            = threading.Lock()
    playing         = False
    stop_requested  = False
    current_thread  = None
    current_item    = None
    current_pl_name = ""
    current_pl_id   = ""
    play_ts         = 0.0
    queue_items     = []
    local_playlists = {}
    local_anuncios  = {}
    uid = email = codigo = ""

ST  = State()
EVQ = queue.Queue()
def ev(t, **kw): EVQ.put({"t": t, **kw})

# ─── Logger ──────────────────────────────────────────────────────────────────
class _UIH(logging.Handler):
    def emit(self, r):
        try: ev("log", msg=self.format(r), lvl=r.levelname)
        except: pass

_fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
log  = logging.getLogger("PlayAds")
log.setLevel(logging.INFO); log.handlers.clear()
_sh = logging.StreamHandler(); _sh.setFormatter(_fmt); log.addHandler(_sh)
_uh = _UIH();                  _uh.setFormatter(_fmt); log.addHandler(_uh)

# ─── Volume Duck ──────────────────────────────────────────────────────────────
_saved_vols = {}; _saved_lock = threading.Lock()

def _duck_worker(target_pct, fade_ms, restore):
    if not HAS_PYCAW: return
    try:
        comtypes.CoInitialize()
        sessions = AudioUtilities.GetAllSessions()
        my_pid   = os.getpid(); svols = []
        for s in sessions:
            try:
                sav = s.SimpleAudioVolume
                if sav is None: continue
                if s.Process and s.Process.pid == my_pid: continue
                key = str(s.Process.pid) if s.Process else f"sys_{id(s)}"
                cur = sav.GetMasterVolume()
                if restore:
                    with _saved_lock: orig = _saved_vols.get(key, 1.0)
                    svols.append((sav, cur, orig))
                else:
                    with _saved_lock: _saved_vols[key] = cur
                    svols.append((sav, cur, target_pct / 100.0))
            except: continue
        if not svols: return
        steps = max(20, int(fade_ms / 40)); delay = fade_ms / 1000.0 / steps
        for step in range(1, steps + 1):
            t = step / steps; ease = t * t * (3.0 - 2.0 * t)
            for sav, v0, v1 in svols:
                try: sav.SetMasterVolume(max(0.0, min(1.0, v0 + (v1-v0)*ease)), None)
                except: pass
            time.sleep(delay)
    except Exception as ex: log.warning(f"duck: {ex}")
    finally:
        try: comtypes.CoUninitialize()
        except: pass

# ─── Download / Audio ────────────────────────────────────────────────────────
def is_yt(url): return "youtube.com" in url or "youtu.be" in url

def download_yt(url, nome):
    if not HAS_YTDLP: log.error("yt-dlp não instalado"); return None
    cached = get_cached(url)
    if cached: return cached
    log.info(f"Baixando YouTube: {nome}")
    try:
        fname = f"yt_{url_key(url)}"
        out   = str(LOCAL_DIR / f"{fname}.%(ext)s")
        with yt_dlp.YoutubeDL({
            "format": "bestaudio/best", "outtmpl": out,
            "quiet": True, "no_warnings": True,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
        }) as ydl:
            ydl.download([url])
        mp3 = str(LOCAL_DIR / f"{fname}.mp3")
        if Path(mp3).exists():
            set_cached(url, mp3, nome, "YouTube/MP3")
            ev("local_updated")
            return mp3
        for f in LOCAL_DIR.glob(f"{fname}.*"):
            set_cached(url, str(f), nome, "YouTube")
            ev("local_updated")
            return str(f)
    except Exception as e: log.error(f"YT {nome}: {e}")
    return None

def download_audio(url, nome):
    cached = get_cached(url)
    if cached: return cached
    log.info(f"Baixando: {nome}")
    try:
        r = requests.get(url, timeout=30, stream=True); r.raise_for_status()
        ct  = r.headers.get("Content-Type", "")
        ext = ".wav" if ("wav" in ct or url.lower().endswith(".wav")) else ".mp3"
        out = LOCAL_DIR / f"{url_key(url)}{ext}"
        total = int(r.headers.get("Content-Length", 0)); done = 0
        with open(out, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk); done += len(chunk)
                if total: ev("dl_pct", pct=int(done/total*100))
        tipo = "WAV" if ext == ".wav" else "MP3"
        set_cached(url, str(out), nome, tipo)
        ev("local_updated")
        return str(out)
    except Exception as e: log.error(f"Download {nome}: {e}"); return None

def get_audio(url, nome):
    return download_yt(url, nome) if is_yt(url) else download_audio(url, nome)

# ─── Firebase REST ────────────────────────────────────────────────────────────
def _furl(path):
    return f"{FIREBASE_DB_URL}/users/{ST.uid}{path}.json?auth={get_token()}"

def fb_get(path):
    try:
        r = requests.get(_furl(path), timeout=10)
        if r.status_code == 401: auth_refresh(); r = requests.get(_furl(path), timeout=10)
        return r.json() if r.ok else None
    except: return None

def fb_set(path, data):
    try:
        r = requests.put(_furl(path), json=data, timeout=10)
        if r.status_code == 401: auth_refresh(); requests.put(_furl(path), json=data, timeout=10)
    except: pass

def fb_update(path, data):
    try:
        r = requests.patch(_furl(path), json=data, timeout=10)
        if r.status_code == 401: auth_refresh(); requests.patch(_furl(path), json=data, timeout=10)
    except: pass

def fb_push(path, data):
    try:
        r = requests.post(_furl(path), json=data, timeout=10)
        if r.status_code == 401: auth_refresh(); requests.post(_furl(path), json=data, timeout=10)
    except: pass

def fb_delete(path):
    try:
        r = requests.delete(_furl(path), timeout=10)
        if r.status_code == 401: auth_refresh(); requests.delete(_furl(path), timeout=10)
    except: pass

def fb_log(msg, status="info"):
    fb_push("/logs", {"mensagem": msg, "status": status,
                      "timestamp": int(time.time()*1000), "player_id": ST.codigo or "player"})

def fb_status(rep=None):
    cfg = load_config()
    d = {"nome": cfg.get("player_nome", "Player"), "last_seen": int(time.time()*1000),
         "plataforma": platform.system()+" "+platform.release(), "versao": "6.1"}
    if rep is not None: d["reproducao_atual"] = rep
    fb_update("/player_status", d)

def fb_done(path): fb_update(path, {"executado": True})

# ─── Reprodução ───────────────────────────────────────────────────────────────
def play_item(item, cfg, loops_override=None):
    nome  = item.get("nome", "?")
    url   = item.get("url", "") or item.get("path", "")
    loops = loops_override if loops_override is not None else max(1, int(item.get("loops", 1)))
    if not url: return

    # Suporte a arquivo local direto
    if item.get("path") and Path(item["path"]).exists():
        tmp = item["path"]
    else:
        tmp = get_audio(url, nome)
    if not tmp: fb_log(f"Falha: {nome}", "error"); return

    fade_ms    = int(cfg.get("duck_fade_ms", 1200))
    vol_outros = float(cfg.get("volume_outros", 10))
    vol_ad     = float(cfg.get("volume_anuncio", 100)) / 100.0

    try:
        _duck_worker(vol_outros, fade_ms, restore=False)
        for n in range(1, loops + 1):
            if ST.stop_requested: break
            log.info(f"▶ Tocando: {nome}  ({n}/{loops})")
            ST.play_ts = time.time()
            fb_status(f"{nome} ({n}/{loops})")
            fb_log(f"▶ {nome} (loop {n}/{loops})", "ok")
            ev("now_playing", nome=nome, loop=n, total=loops, pl=ST.current_pl_name)
            try:
                pygame.mixer.music.stop(); pygame.mixer.quit()
                pygame.mixer.init(44100, -16, 2, 4096)
                pygame.mixer.music.load(tmp)
                pygame.mixer.music.set_volume(vol_ad)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if ST.stop_requested: pygame.mixer.music.stop(); break
                    time.sleep(0.1)
            except pygame.error as e:
                log.error(f"Pygame: {e}")
                try: pygame.mixer.quit(); pygame.mixer.init(44100, -16, 2, 4096)
                except: pass
                break
            if n < loops and not ST.stop_requested: time.sleep(0.3)
    finally:
        _duck_worker(100.0, fade_ms, restore=True)
        try: pygame.mixer.music.stop()
        except: pass

def run_playlist(pl, cfg, force=False, loops_override=None):
    nome_pl = pl.get("nome", "Playlist"); itens = pl.get("itens") or []
    if not itens: log.warning(f"Playlist '{nome_pl}' vazia"); ev("stopped"); return
    ST.current_pl_name = nome_pl; ST.queue_items = list(itens)
    fb_log(f"Iniciando: {nome_pl}", "ok"); ev("pl_start", nome=nome_pl, itens=itens)
    now_t = datetime.now().strftime("%H:%M"); played_any = False
    for i, item in enumerate(itens):
        if ST.stop_requested: break
        h = item.get("horario")
        if h and not force and h != now_t: continue
        ST.current_item = item; played_any = True; ev("q_active", idx=i)
        play_item(item, cfg, loops_override=loops_override)
    if not played_any: log.warning(f"Nenhum item tocou em '{nome_pl}'"); ev("stopped")
    with ST.lock: ST.playing = False; ST.current_item = None; ST.current_pl_name = ""
    fb_status(None); fb_log(f"'{nome_pl}' concluída", "ok")
    log.info(f"✓ Playlist '{nome_pl}' concluída"); ev("pl_end", nome=nome_pl)

def stop_all():
    with ST.lock: ST.stop_requested = True
    try: pygame.mixer.music.stop()
    except: pass
    if ST.current_thread and ST.current_thread.is_alive(): ST.current_thread.join(timeout=3)
    with ST.lock: ST.stop_requested = False; ST.playing = False; ST.current_thread = None; ST.current_item = None

def start_playlist(pl, cfg, force=True, loops_override=None):
    stop_all()
    with ST.lock:
        ST.playing = True
        t = threading.Thread(target=run_playlist, args=(pl, cfg, force),
                             kwargs={"loops_override": loops_override}, daemon=True)
        ST.current_thread = t
    t.start()

# ─── SSE ─────────────────────────────────────────────────────────────────────
def _sse_listen(path, callback, label=""):
    lbl = label or path
    while True:
        try:
            tok  = get_token()
            url  = f"{FIREBASE_DB_URL}/users/{ST.uid}{path}.json?auth={tok}"
            resp = requests.get(url, headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
                                stream=True, timeout=60)
            if resp.status_code == 401: auth_refresh(); time.sleep(3); continue
            if resp.status_code != 200: time.sleep(10); continue
            log.info(f"SSE ativo: {lbl}")
            buf = ""; etype = ""; edata = ""
            for chunk in resp.iter_content(chunk_size=1, decode_unicode=True):
                if not chunk: continue
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1); line = line.rstrip("\r")
                    if   line.startswith("event:"): etype = line[6:].strip()
                    elif line.startswith("data:"):  edata = line[5:].strip()
                    elif line == "":
                        if etype in ("put", "patch") and edata:
                            try:
                                payload = json.loads(edata); raw = payload.get("data"); callback(raw)
                            except Exception as ex: log.warning(f"SSE {lbl} parse: {ex}")
                        etype = ""; edata = ""
        except requests.exceptions.Timeout: time.sleep(3)
        except Exception as ex: log.warning(f"SSE {lbl}: {ex} — retry 5s"); time.sleep(5)

def setup_listeners(cfg):
    def on_play(data):
        try:
            if not data: return
            if isinstance(data, dict) and data.get("executado"): return
            plid = data.get("playlist_id") if isinstance(data, dict) else None
            if not plid: return
            snap = fb_get(f"/playlists/{plid}")
            if not snap: log.warning(f"on_play: {plid} não encontrada"); return
            fb_done("/comandos/play_now")
            is_temp = (isinstance(data, dict) and data.get("temp_playlist_id")) or \
                      (isinstance(snap, dict) and snap.get("temp"))
            start_playlist(snap, cfg, force=True)
            if is_temp: time.sleep(0.5); fb_delete(f"/playlists/{plid}")
        except Exception as ex: log.error(f"on_play: {ex}")

    def on_stop(data):
        try:
            if not data: return
            if isinstance(data, dict) and data.get("executado"): return
            fb_done("/comandos/stop"); stop_all(); fb_status(None); ev("stopped")
            log.info("⏹ Parado via painel web")
        except Exception as ex: log.error(f"on_stop: {ex}")

    def on_playlists(data):
        try:
            if data is None or not isinstance(data, dict): return
            filtered = {k: v for k, v in data.items() if isinstance(v, dict) and not v.get("temp")}
            ST.local_playlists = filtered
            ev("fb_data", playlists=filtered, anuncios=ST.local_anuncios)
            try: LOCAL_PL_FILE.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
            except: pass
        except Exception as ex: log.error(f"on_playlists: {ex}")

    def on_anuncios(data):
        try:
            if data is None or not isinstance(data, dict): return
            ST.local_anuncios = data
            ev("fb_data", playlists=ST.local_playlists, anuncios=data)
            try: LOCAL_AD_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except: pass
        except Exception as ex: log.error(f"on_anuncios: {ex}")

    def on_logs(data):
        try:
            if data is None or not isinstance(data, dict): return
            ev("fb_logs", logs=data)
            try: LOCAL_LOG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except: pass
        except Exception as ex: log.error(f"on_logs: {ex}")

    def _initial():
        time.sleep(1)
        try:
            pls = fb_get("/playlists")
            if pls and isinstance(pls, dict): on_playlists(pls)
            ads = fb_get("/anuncios")
            if ads and isinstance(ads, dict): on_anuncios(ads)
            logs = fb_get("/logs")
            if logs and isinstance(logs, dict): on_logs(logs)
        except Exception as ex: log.warning(f"Carga inicial: {ex}")

    threading.Thread(target=_initial, daemon=True).start()
    for path, cb, lbl in [
        ("/comandos/play_now", on_play,      "play_now"),
        ("/comandos/stop",     on_stop,      "stop"),
        ("/playlists",         on_playlists, "playlists"),
        ("/anuncios",          on_anuncios,  "anuncios"),
        ("/logs",              on_logs,      "logs"),
    ]:
        threading.Thread(target=_sse_listen, args=(path, cb), kwargs={"label": lbl}, daemon=True).start()
    log.info("Listeners SSE ativos")

def check_schedules(cfg):
    fired: set = set()
    while True:
        time.sleep(20)
        try:
            if ST.playing: continue
            now = datetime.now(); now_t = now.strftime("%H:%M"); today = now.strftime("%Y-%m-%d")
            fired = {k for k in fired if k.startswith(today)}
            for pl_id, pl in list(ST.local_playlists.items()):
                if not isinstance(pl, dict) or not pl.get("ativa"): continue
                for idx, item in enumerate(pl.get("itens") or []):
                    if not isinstance(item, dict): continue
                    h = item.get("horario")
                    if h != now_t: continue
                    fk = f"{today} {now_t} {pl_id} {idx}"
                    if fk in fired: continue
                    log.info(f"⏰ {now_t}: {pl.get('nome')} → {item.get('nome','?')}")
                    fired.add(fk)
                    sub = {"nome": f"{pl.get('nome','?')} @ {now_t}", "itens": [item]}
                    start_playlist(sub, cfg, force=True); break
                if ST.playing: break
        except Exception as ex: log.error(f"schedule: {ex}")

def heartbeat(cfg):
    while True:
        try:
            rep = ST.current_item.get("nome") if ST.current_item else None
            fb_status(rep)
        except: pass
        time.sleep(10)

def precache_all():
    log.info("Pre-cache iniciando...")
    count = 0
    for pl in ST.local_playlists.values():
        if not isinstance(pl, dict): continue
        for item in (pl.get("itens") or []):
            url = item.get("url", "")
            if url and not get_cached(url):
                get_audio(url, item.get("nome", "?")); count += 1
    log.info(f"Cache: {count} arquivo(s) baixado(s)")
    ev("cache_done"); ev("local_updated")

def load_local_data():
    for path, attr in [(LOCAL_PL_FILE, "local_playlists"), (LOCAL_AD_FILE, "local_anuncios")]:
        try:
            if path.exists(): setattr(ST, attr, json.loads(path.read_text(encoding="utf-8")))
        except: pass

def start_firebase(senha):
    ok = auth_sign_in(ST.email, senha)
    if not ok: log.error("Firebase: falha no login"); return False
    threading.Thread(target=_token_loop, daemon=True).start()
    log.info("Firebase conectado ✓")
    return True


# ─── Canvas Icons ─────────────────────────────────────────────────────────────
def draw_icon(canvas, name, color, size=18, x=0, y=0):
    c = canvas; s = size; cx = x + s//2; cy = y + s//2
    W = 1.8

    def L(*pts, **kw):
        c.create_line(*pts, fill=color, width=W, capstyle="round", joinstyle="round", **kw)
    def R(x1, y1, x2, y2, fill=""):
        c.create_rectangle(x1+x, y1+y, x2+x, y2+y, outline=color, width=W, fill=fill)
    def O(x1, y1, x2, y2, fill=""):
        c.create_oval(x1+x, y1+y, x2+x, y2+y, outline=color, width=W, fill=fill)
    def P(*pts, fill=color):
        shifted = []
        for i in range(0, len(pts), 2): shifted += [pts[i]+x, pts[i+1]+y]
        c.create_polygon(*shifted, fill=fill, outline="")

    if name == "home":
        L(cx-7, cy+7, cx-7, cy, cx, cy-7, cx+7, cy, cx+7, cy+7)
        L(cx-7, cy, cx, cy-7, cx+7, cy)
        R(cx-3, cy+1, cx+3, cy+7, fill=color)
    elif name == "grid":
        for ox, oy in [(-7,-7),(-1,-7),(-7,-1),(-1,-1)]:
            R(cx+ox, cy+oy, cx+ox+5, cy+oy+5)
    elif name == "music":
        O(cx-5, cy, cx+5, cy+6)
        L(cx+5, cy-5, cx+5, cy+2); L(cx-5, cy-5, cx-5, cy+2)
        L(cx-5, cy-5, cx+5, cy-5)
    elif name == "list":
        for oy in [-4, 0, 4]: L(cx-7, cy+oy, cx+3, cy+oy)
        O(cx+3, cy+1, cx+9, cy+7)
        L(cx+9, cy-5, cx+9, cy+4)
    elif name == "monitor":
        R(cx-8, cy-6, cx+8, cy+3)
        L(cx-4, cy+3, cx-4, cy+7); L(cx+4, cy+3, cx+4, cy+7)
        L(cx-5, cy+7, cx+5, cy+7)
        O(cx-2, cy-2, cx+2, cy+2)
    elif name == "activity":
        L(cx-8, cy, cx-4, cy, cx-2, cy-5, cx, cy+5, cx+2, cy-2, cx+5, cy, cx+8, cy)
    elif name == "scroll":
        R(cx-6, cy-7, cx+6, cy+7)
        for oy in [-3, 0, 3]: L(cx-3, cy+oy, cx+3, cy+oy)
    elif name == "settings":
        O(cx-4, cy-4, cx+4, cy+4)
        for a in [0, 45, 90, 135, 180, 225, 270, 315]:
            ra = math.radians(a); lx = cx + 6.5*math.cos(ra); ly = cy + 6.5*math.sin(ra)
            c.create_oval(lx-1.5, ly-1.5, lx+1.5, ly+1.5, fill=color, outline="")
    elif name == "key":
        O(cx-7, cy-4, cx+1, cy+4)
        L(cx+1, cy, cx+8, cy); L(cx+6, cy, cx+6, cy+3); L(cx+4, cy, cx+4, cy+3)
    elif name == "play":
        P(cx-4, cy-6, cx-4, cy+6, cx+7, cy)
    elif name == "stop_sq":
        R(cx-5, cy-5, cx+5, cy+5, fill=color)
    elif name == "folder":
        P(cx-8, cy-3, cx-4, cy-6, cx+8, cy-6, cx+8, cy+6, cx-8, cy+6, fill="")
        R(cx-8, cy-6, cx+8, cy+6)
    elif name == "web":
        O(cx-7, cy-7, cx+7, cy+7)
        L(cx, cy-7, cx, cy+7); L(cx-7, cy, cx+7, cy)
        c.create_arc(cx-7+x, cy-7+y, cx+7+x, cy+7+y, start=50, extent=80, style="arc", outline=color, width=W)
        c.create_arc(cx-7+x, cy-7+y, cx+7+x, cy+7+y, start=230, extent=80, style="arc", outline=color, width=W)
    elif name == "logout":
        L(cx, cy-6, cx-6, cy-6, cx-6, cy+6, cx, cy+6)
        L(cx+2, cy-3, cx+7, cy, cx+2, cy+3); L(cx-1, cy, cx+7, cy)
    elif name == "clock":
        O(cx-7, cy-7, cx+7, cy+7)
        L(cx, cy-4, cx, cy); L(cx, cy, cx+3, cy+3)
    elif name == "download":
        L(cx, cy-6, cx, cy+4); L(cx-4, cy, cx, cy+4, cx+4, cy)
        L(cx-7, cy+7, cx+7, cy+7)
    elif name == "refresh":
        c.create_arc(cx-6+x, cy-6+y, cx+6+x, cy+6+y, start=30, extent=280, style="arc", outline=color, width=W)
        P(cx+5, cy-5, cx+8, cy-2, cx+2, cy-2)


# ══════════════════════════════════════════════════════════════════════════════
#  TELA DE ATIVAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
class ActivationScreen:
    def __init__(self, on_success):
        self.on_success = on_success
        self.root = tk.Tk()
        self.root.title("PlayAds — Ativação")
        self.root.geometry("480x560")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self._build()

    def _build(self):
        r = self.root
        # ── Header ──────────────────────────────────────────────
        hdr = tk.Frame(r, bg=SURF, height=72); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=PURPLE2, width=4).pack(side="left", fill="y")
        cv = tk.Canvas(hdr, width=40, height=40, bg=SURF, highlightthickness=0)
        cv.place(x=20, y=16)
        cv.create_oval(0, 0, 40, 40, fill=PURPLE2, outline="")
        cv.create_oval(2, 2, 38, 38, outline=PURPLE, width=1)
        cv.create_polygon(15, 10, 15, 30, 30, 20, fill="white", outline="")
        tk.Label(hdr, text="PlayAds", bg=SURF, fg=TEXT, font=("Segoe UI", 17, "bold")).place(x=72, y=14)
        tk.Label(hdr, text="v6.1 — Player de Anúncios", bg=SURF, fg=MUTED, font=FSMALL).place(x=73, y=38)
        tk.Frame(r, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(r, bg=BG); body.pack(fill="both", expand=True, padx=36, pady=24)

        tk.Label(body, text="Ativar Player", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(body, text="Digite o código, e-mail e senha da sua conta no painel web.",
                 bg=BG, fg=MUTED, font=FSMALL, wraplength=400, justify="left").pack(anchor="w", pady=(4, 20))

        self._code_var = tk.StringVar()
        self._email_var = tk.StringVar()
        self._senha_var = tk.StringVar()
        self._code_var.trace_add("write", self._fmt_code)
        self._entries = []

        for label, var, hide, ph in [
            ("Código de Ativação", self._code_var,  False, "PLAY-XXXX-XXXX"),
            ("E-mail",            self._email_var, False, "seu@email.com"),
            ("Senha",             self._senha_var, True,  "••••••••"),
        ]:
            tk.Label(body, text=label, bg=BG, fg=MUTED2, font=("Segoe UI", 8, "bold"),
                     anchor="w").pack(fill="x", pady=(0, 3))
            outer = tk.Frame(body, bg=BORDER); outer.pack(fill="x", pady=(0, 14))
            inner = tk.Frame(outer, bg=SURF3);  inner.pack(fill="x", padx=1, pady=1)
            kw = {}
            if hide: kw["show"] = "●"
            ent = tk.Entry(inner, textvariable=var, bg=SURF3, fg=TEXT,
                           insertbackground=PURPLE, relief="flat", bd=10,
                           font=("Consolas", 14, "bold") if label == "Código de Ativação" else FBODY,
                           **kw)
            if label == "Código de Ativação":
                ent.configure(fg=PURPLE, justify="center")
            ent.pack(fill="x")
            ent.bind("<Return>", lambda e, i=len(self._entries): self._next(i))
            self._entries.append(ent)

        self._lbl_st = tk.Label(body, text="", bg=BG, fg=MUTED, font=FSMALL, wraplength=400)
        self._lbl_st.pack(pady=(0, 12))

        self._btn = tk.Button(body, text="Ativar Agora →", bg=PURPLE2, fg=TEXT,
                              font=("Segoe UI", 12, "bold"), relief="flat", bd=0,
                              padx=32, pady=13, cursor="hand2",
                              activebackground=PURPLE3, command=self._validate)
        self._btn.pack(fill="x")
        self._btn.bind("<Enter>", lambda e: self._btn.configure(bg=PURPLE3))
        self._btn.bind("<Leave>", lambda e: self._btn.configure(bg=PURPLE2))

        lnk = tk.Label(body, text="Abrir painel web →", bg=BG, fg=PURPLE,
                        font=FSMALL, cursor="hand2")
        lnk.pack(pady=(14, 0))
        lnk.bind("<Button-1>", lambda e: webbrowser.open(WEB_URL))
        lnk.bind("<Enter>",    lambda e: lnk.configure(fg=TEXT))
        lnk.bind("<Leave>",    lambda e: lnk.configure(fg=PURPLE))

    def _next(self, cur):
        nxt = cur + 1
        if nxt < len(self._entries): self._entries[nxt].focus()
        else: self._validate()

    def _fmt_code(self, *_):
        val = self._code_var.get().upper()
        raw = val.replace("-", "").replace(" ", "")
        if raw.startswith("PLAY"): raw = raw[4:]
        raw = raw[:8]
        parts = ["PLAY"]
        if raw: parts.append(raw[:4])
        if len(raw) > 4: parts.append(raw[4:])
        new = "-".join(parts)
        if new != val:
            self._code_var.set(new)
            self.root.after(1, lambda: self._entries[0].icursor(tk.END))

    def _validate(self):
        codigo = self._code_var.get().strip().upper()
        email  = self._email_var.get().strip()
        senha  = self._senha_var.get().strip()
        if len(codigo) < 10: self._st("Digite o código completo (PLAY-XXXX-XXXX)", WARN); return
        if "@" not in email: self._st("E-mail inválido", WARN); return
        if len(senha) < 6:   self._st("Senha mínima de 6 caracteres", WARN); return
        self._btn.configure(text="Validando...", state="disabled")
        self._st("Verificando no servidor...", MUTED)
        def _run():
            uid, em, err = validate_and_login(codigo, email, senha)
            if uid: save_activation(uid, em or email, codigo, senha); self.root.after(0, lambda: self._ok(uid, em or email, codigo, senha))
            else:   self.root.after(0, lambda: self._fail(err or "Código ou credenciais inválidos."))
        threading.Thread(target=_run, daemon=True).start()

    def _ok(self, uid, email, codigo, senha):
        self._st(f"✓ Ativado! Conta: {email}", GREEN)
        self._btn.configure(text="✓ Ativado!", bg=GREEN, state="disabled")
        self.root.after(1200, lambda: (self.root.destroy(), self.on_success(uid, email, codigo, senha)))

    def _fail(self, msg):
        self._st(msg, DANGER)
        self._btn.configure(text="Ativar Agora →", state="normal")

    def _st(self, t, c): self._lbl_st.configure(text=t, fg=c)
    def run(self):       self.root.mainloop()


# ══════════════════════════════════════════════════════════════════════════════
#  APP PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
class App:
    W, H = 1020, 660

    NAV = [
        ("Player",    "play",     PURPLE),
        ("All",       "folder",   CYAN),
        ("Playlists", "list",     WARN),
        ("Logs",      "scroll",   GREEN),
        ("Config",    "settings", MUTED2),
        ("Conta",     "key",      PURPLE),
    ]

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PlayAds")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.minsize(900, 580)
        self.root.configure(bg=BG)

        self._page          = "Player"
        self._playlists     = {}
        self._anuncios      = {}
        self._eq_phase      = 0.0
        self._eq_running    = False
        self._all_loop_vars = {}
        self._nav_canvas    = {}
        self._nav_label     = {}
        self._nav_bar       = {}
        self._nav_row       = {}

        self._styles()
        self._build()
        self.root.after(120, self._poll)

    # ── Styles ───────────────────────────────────────────────────
    def _styles(self):
        s = ttk.Style(); s.theme_use("default")
        s.configure("PA.Horizontal.TProgressbar",
                    troughcolor=SURF3, background=PURPLE, borderwidth=0, thickness=3)
        s.configure("Treeview", background=SURF2, fieldbackground=SURF2,
                    foreground=TEXT, rowheight=30, borderwidth=0, font=FBODY)
        s.configure("Treeview.Heading", background=SURF3, foreground=MUTED2,
                    relief="flat", font=("Segoe UI", 7, "bold"))
        s.map("Treeview", background=[("selected", SURF4)], foreground=[("selected", TEXT)])
        s.configure("Vertical.TScrollbar", troughcolor=SURF2, background=SURF3, borderwidth=0, arrowsize=10)

    # ── Build ────────────────────────────────────────────────────
    def _build(self):
        sb = tk.Frame(self.root, bg=SURF, width=210)
        sb.pack(side="left", fill="y"); sb.pack_propagate(False)
        tk.Frame(self.root, bg=BORDER, width=1).pack(side="left", fill="y")
        main = tk.Frame(self.root, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self._main = main
        self._build_sidebar(sb)
        self._build_pages()
        self._show("Player")

    # ── Sidebar ──────────────────────────────────────────────────
    def _build_sidebar(self, sb):
        # ── Logo ────────────────────────────────────────────────
        logo_f = tk.Frame(sb, bg=SURF, height=70); logo_f.pack(fill="x"); logo_f.pack_propagate(False)
        logo_inner = tk.Frame(logo_f, bg=SURF); logo_inner.place(relx=0.5, rely=0.5, anchor="center")

        cv = tk.Canvas(logo_inner, width=38, height=38, bg=SURF, highlightthickness=0)
        cv.pack(side="left", padx=(0, 10))
        # Gradient-like glow: outer ring then fill
        cv.create_oval(0, 0, 38, 38, fill=PURPLE3, outline="")
        cv.create_oval(2, 2, 36, 36, fill=PURPLE2, outline="")
        cv.create_oval(3, 3, 35, 35, outline=PURPLE, width=1)
        cv.create_polygon(14, 10, 14, 28, 29, 19, fill="white", outline="")

        lf = tk.Frame(logo_inner, bg=SURF); lf.pack(side="left")
        tk.Label(lf, text="PlayAds", bg=SURF, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(lf, text="v6.1", bg=SURF, fg=MUTED, font=FMONO2).pack(anchor="w")

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x")

        # ── Status pill ─────────────────────────────────────────
        self._pill = tk.Frame(sb, bg=SURF3, height=28)
        self._pill.pack(fill="x", padx=10, pady=(8, 6)); self._pill.pack_propagate(False)
        self._pill_dot = tk.Label(self._pill, text="●", bg=SURF3, fg=MUTED, font=FXSMALL)
        self._pill_dot.place(x=8, rely=0.5, anchor="w")
        self._pill_txt = tk.Label(self._pill, text="Inicializando...", bg=SURF3, fg=MUTED, font=FSMALL)
        self._pill_txt.place(x=22, rely=0.5, anchor="w")
        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=10)

        # ── Nav items ───────────────────────────────────────────
        nav_wrap = tk.Frame(sb, bg=SURF); nav_wrap.pack(fill="x", padx=8, pady=(10, 0))

        for page, icon_name, color in self.NAV:
            row = tk.Frame(nav_wrap, bg=SURF, height=44, cursor="hand2")
            row.pack(fill="x", pady=1); row.pack_propagate(False)
            self._nav_row[page] = row

            bar = tk.Frame(row, bg=SURF, width=3)
            bar.pack(side="left", fill="y")
            self._nav_bar[page] = bar

            ico = tk.Canvas(row, width=30, height=30, bg=SURF, highlightthickness=0)
            ico.pack(side="left", padx=(8, 6), pady=7)
            draw_icon(ico, icon_name, MUTED, size=17, x=6, y=6)
            self._nav_canvas[page] = (ico, icon_name, color)

            lbl = tk.Label(row, text=page, bg=SURF, fg=MUTED, font=("Segoe UI", 10), anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self._nav_label[page] = lbl

            def _enter(e, p=page):
                if self._page != p:
                    self._nav_label[p].configure(fg=TEXT)
            def _leave(e, p=page):
                if self._page != p:
                    self._nav_label[p].configure(fg=MUTED)
            def _click(e, p=page): self._show(p)

            for w in (row, ico, lbl):
                w.bind("<Enter>",    _enter)
                w.bind("<Leave>",    _leave)
                w.bind("<Button-1>", _click)

        tk.Frame(sb, bg=SURF).pack(fill="both", expand=True)
        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=10)

        # ── User footer ─────────────────────────────────────────
        uf = tk.Frame(sb, bg=SURF); uf.pack(fill="x", padx=12, pady=10)

        av = tk.Canvas(uf, width=32, height=32, bg=PURPLE3, highlightthickness=1, highlightbackground=BORDER)
        av.pack(side="left", padx=(0, 8))
        av.create_oval(0, 0, 32, 32, fill=PURPLE3, outline="")
        self._av_txt = av.create_text(16, 16, text="?", fill=TEXT, font=("Segoe UI", 12, "bold"))
        self._av_cv  = av

        info = tk.Frame(uf, bg=SURF); info.pack(side="left", fill="x", expand=True)
        self._lbl_uemail = tk.Label(info, text="—", bg=SURF, fg=MUTED2, font=FSMALL, anchor="w")
        self._lbl_uemail.pack(anchor="w")
        self._lbl_ucode = tk.Label(info, text="—", bg=SURF, fg=MUTED, font=FMONO2, anchor="w")
        self._lbl_ucode.pack(anchor="w")

        wcv = tk.Canvas(uf, width=24, height=24, bg=SURF, highlightthickness=0, cursor="hand2")
        wcv.pack(side="right")
        draw_icon(wcv, "web", MUTED, 18, 3, 3)
        wcv.bind("<Button-1>", lambda e: webbrowser.open(WEB_URL))
        wcv.bind("<Enter>",    lambda e: [wcv.delete("all"), draw_icon(wcv, "web", PURPLE, 18, 3, 3)])
        wcv.bind("<Leave>",    lambda e: [wcv.delete("all"), draw_icon(wcv, "web", MUTED,  18, 3, 3)])

    def _update_nav(self, page):
        for p, iname, color in self.NAV:
            active = (p == page)
            bar   = self._nav_bar[p]
            ico, iname_, icol = self._nav_canvas[p]
            lbl   = self._nav_label[p]
            row   = self._nav_row[p]
            ico.delete("all")
            if active:
                bar.configure(bg=icol)
                row.configure(bg=SURF2)
                ico.configure(bg=SURF2)
                lbl.configure(bg=SURF2)
                draw_icon(ico, iname_, icol, 17, 6, 6)
                lbl.configure(fg=TEXT, font=("Segoe UI", 10, "bold"))
            else:
                bar.configure(bg=SURF)
                row.configure(bg=SURF)
                ico.configure(bg=SURF)
                lbl.configure(bg=SURF)
                draw_icon(ico, iname_, MUTED, 17, 6, 6)
                lbl.configure(fg=MUTED, font=("Segoe UI", 10))

    # ── Page helpers ─────────────────────────────────────────────
    def _build_pages(self):
        self._pages = {
            "Player":    self._pg_player(self._main),
            "All":       self._pg_all(self._main),
            "Playlists": self._pg_playlists(self._main),
            "Logs":      self._pg_logs(self._main),
            "Config":    self._pg_config(self._main),
            "Conta":     self._pg_conta(self._main),
        }

    def _show(self, page):
        self._page = page
        for p, f in self._pages.items():
            if p == page: f.pack(fill="both", expand=True)
            else:         f.pack_forget()
        self._update_nav(page)

    def _phdr(self, parent, title, sub="", color=PURPLE, right_widget=None):
        h = tk.Frame(parent, bg=SURF, height=54); h.pack(fill="x"); h.pack_propagate(False)
        tk.Frame(h, bg=color, width=4).pack(side="left", fill="y")
        tk.Label(h, text=title, bg=SURF, fg=TEXT, font=FH1).pack(side="left", padx=(16, 6))
        if sub: tk.Label(h, text=sub, bg=SURF, fg=MUTED, font=FSMALL).pack(side="left")
        if right_widget: right_widget(h)
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

    def _card(self, parent, bg=SURF3):
        return tk.Frame(parent, bg=bg, highlightbackground=BORDER, highlightthickness=1)

    def _stat(self, parent, label, val, col, row, vc=None):
        f = self._card(parent)
        f.grid(row=row, column=col, sticky="ew", padx=3, pady=3)
        tk.Label(f, text=label, bg=SURF3, fg=MUTED, font=FXSMALL).pack(pady=(7, 0))
        lbl = tk.Label(f, text=val, bg=SURF3, fg=vc or TEXT, font=("Segoe UI", 11, "bold"))
        lbl.pack(pady=(2, 7))
        return lbl

    def _mkbtn(self, parent, txt, bg, fg, cmd, px=14, py=7):
        b = tk.Button(parent, text=txt, bg=bg, fg=fg, font=FTIT, relief="flat", bd=0,
                      padx=px, pady=py, cursor="hand2", activebackground=bg, command=cmd)
        orig = bg
        b.bind("<Enter>", lambda e: b.configure(bg=self._lt(orig)))
        b.bind("<Leave>", lambda e: b.configure(bg=orig))
        return b

    @staticmethod
    def _lt(h):
        try:
            h6 = h.replace("#","")[:6]
            r,g,b = int(h6[0:2],16),int(h6[2:4],16),int(h6[4:6],16)
            return "#{:02x}{:02x}{:02x}".format(min(255,r+28),min(255,g+28),min(255,b+28))
        except: return h

    def _scrolled(self, parent, bg=BG):
        """Returns (outer_frame, inner_canvas_frame) with scrollbar."""
        outer  = tk.Frame(parent, bg=bg); outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
        vsb    = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner  = tk.Frame(canvas, bg=bg)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
        return outer, inner

    # ══ PAGE: PLAYER ══════════════════════════════════════════════
    def _pg_player(self, p):
        f = tk.Frame(p, bg=BG)

        # ── Top bar ─────────────────────────────────────────────
        tb = tk.Frame(f, bg=SURF, height=54); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Frame(tb, bg=PURPLE, width=4).pack(side="left", fill="y")
        tk.Label(tb, text="Player", bg=SURF, fg=PURPLE, font=("Segoe UI", 13, "bold")).pack(side="left", padx=16)
        self._lbl_conn_dot = tk.Label(tb, text="●", bg=SURF, fg=MUTED, font=("Segoe UI", 7))
        self._lbl_conn_dot.pack(side="right", padx=(0, 14))
        self._lbl_conn = tk.Label(tb, text="Inicializando...", bg=SURF, fg=MUTED, font=FSMALL)
        self._lbl_conn.pack(side="right")
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(f, bg=BG); body.pack(fill="both", expand=True)

        # ── Left column (artwork + controls) ────────────────────
        left = tk.Frame(body, bg=BG, width=260); left.pack(side="left", fill="y", padx=22, pady=20)
        left.pack_propagate(False)

        # Artwork
        art_wrap = tk.Frame(left, bg=SURF3, highlightbackground=BORDER, highlightthickness=1)
        art_wrap.pack(pady=(0, 16))
        self._art_cv = tk.Canvas(art_wrap, width=120, height=120, bg=SURF3, highlightthickness=0)
        self._art_cv.pack(padx=4, pady=4)
        self._draw_art(idle=True)

        # EQ + status tag
        eq_row = tk.Frame(left, bg=BG); eq_row.pack(fill="x", pady=(0, 8))
        self._eq_cv = tk.Canvas(eq_row, width=32, height=14, bg=BG, highlightthickness=0)
        self._eq_cv.pack(side="left")
        self._lbl_tag = tk.Label(eq_row, text="AGUARDANDO", bg=BG, fg=MUTED, font=FXSMALL)
        self._lbl_tag.pack(side="left", padx=6)
        self._draw_eq(True)

        self._lbl_title = tk.Label(left, text="Nenhuma mídia", bg=BG, fg=TEXT,
                                   font=("Segoe UI", 12, "bold"), anchor="w", wraplength=250, justify="left")
        self._lbl_title.pack(fill="x")
        self._lbl_meta = tk.Label(left, text="—", bg=BG, fg=MUTED, font=FSMALL, anchor="w")
        self._lbl_meta.pack(fill="x", pady=(2, 12))

        self._prog_var = tk.DoubleVar(value=0)
        ttk.Progressbar(left, variable=self._prog_var, maximum=100, style="PA.Horizontal.TProgressbar").pack(fill="x")
        tf = tk.Frame(left, bg=BG); tf.pack(fill="x", pady=(3, 12))
        self._lbl_elapsed = tk.Label(tf, text="0:00", bg=BG, fg=MUTED, font=FMONO)
        self._lbl_elapsed.pack(side="left")

        # Stop button (prominent)
        def _stop_enter(e): sb.configure(bg="#2e0b17")
        def _stop_leave(e): sb.configure(bg="#1a080e")
        sb = tk.Button(left, text="  ⏹  PARAR REPRODUÇÃO  ", bg="#1a080e", fg=DANGER,
                       font=("Segoe UI", 9, "bold"), relief="flat", bd=0, pady=11, cursor="hand2",
                       activebackground="#2e0b17", activeforeground=DANGER, command=self._cmd_stop)
        sb.pack(fill="x")
        sb.bind("<Enter>", _stop_enter); sb.bind("<Leave>", _stop_leave)

        # ── Center divider ──────────────────────────────────────
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y", pady=14)

        # ── Right column (stats + info) ──────────────────────────
        right = tk.Frame(body, bg=BG); right.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        # Stats 2×2
        sc = tk.Frame(right, bg=BG); sc.pack(fill="x", pady=(0, 14))
        sc.columnconfigure((0, 1), weight=1)
        self._s_pl   = self._stat(sc, "PLAYLIST", "—",       0, 0)
        self._s_tr   = self._stat(sc, "FAIXAS",   "0",       1, 0)
        self._s_st   = self._stat(sc, "STATUS",   "Pronto",  0, 1, GREEN)
        self._s_loop = self._stat(sc, "LOOP",     "—",       1, 1)

        # Volume card
        vc = self._card(right); vc.pack(fill="x", pady=(0, 10))
        tk.Label(vc, text="VOLUME  ·  Duck de Volume", bg=SURF3, fg=MUTED, font=FXSMALL).pack(anchor="w", padx=12, pady=(8, 4))
        cfg = load_config()
        for lbl, attr, color, key in [
            ("Anúncio",     "_lbl_vol_ad", PURPLE, "volume_anuncio"),
            ("Outros apps", "_lbl_vol_ot", WARN,   "volume_outros"),
        ]:
            vr = tk.Frame(vc, bg=SURF3); vr.pack(fill="x", padx=12, pady=(0, 4))
            tk.Label(vr, text=lbl, bg=SURF3, fg=MUTED2, font=FSMALL).pack(side="left")
            lv = tk.Label(vr, text=f"{cfg.get(key,'—')}%", bg=SURF3, fg=color, font=FMONO)
            lv.pack(side="right"); setattr(self, attr, lv)
        tk.Frame(vc, bg=SURF3, height=6).pack()

        # Deps warning
        if not HAS_PYCAW:
            tk.Label(right, text="⚠  pycaw não instalado — duck desativado", bg=BG, fg=WARN, font=FSMALL).pack(anchor="w")
        if not HAS_YTDLP:
            tk.Label(right, text="⚠  yt-dlp não instalado — YouTube indisponível", bg=BG, fg=WARN, font=FSMALL).pack(anchor="w")

        # Local storage card
        lsc = self._card(right); lsc.pack(fill="x", pady=(6, 8))
        tk.Label(lsc, text="ARMAZENAMENTO LOCAL  ·  pasta  local/", bg=SURF3, fg=MUTED, font=FXSMALL).pack(anchor="w", padx=12, pady=(8, 4))
        lr = tk.Frame(lsc, bg=SURF3); lr.pack(fill="x", padx=12, pady=(0, 8))
        self._lbl_cache = tk.Label(lr, text="—", bg=SURF3, fg=MUTED2, font=FSMALL)
        self._lbl_cache.pack(side="left")
        self._mkbtn(lr, "Sincronizar", SURF4, PURPLE, self._cmd_precache, px=10, py=3).pack(side="right")

        # Log console
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", pady=(0, 6))
        self._logtxt = tk.Text(right, bg="#07060f", fg=MUTED, font=("Consolas", 7),
                               relief="flat", state="disabled", wrap="word", height=8)
        self._logtxt.pack(fill="both", expand=True)
        for tag, col in [("OK", GREEN), ("ERR", DANGER), ("WARN", WARN), ("INFO", MUTED), ("PL", PURPLE), ("CY", CYAN)]:
            self._logtxt.tag_config(tag, foreground=col)
        return f

    # ══ PAGE: ALL ══════════════════════════════════════════════════
    def _pg_all(self, p):
        f = tk.Frame(p, bg=BG)

        # Header with count on right
        hdr = tk.Frame(f, bg=SURF, height=54); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=CYAN, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="Biblioteca Local", bg=SURF, fg=TEXT, font=FH1).pack(side="left", padx=(16, 6))
        tk.Label(hdr, text="Mídias baixadas na pasta  local/", bg=SURF, fg=MUTED, font=FSMALL).pack(side="left")
        self._lbl_all_count = tk.Label(hdr, text="0 faixas", bg=SURF, fg=MUTED, font=FSMALL)
        self._lbl_all_count.pack(side="right", padx=14)

        # Refresh button
        rcv = tk.Canvas(hdr, width=24, height=24, bg=SURF, highlightthickness=0, cursor="hand2")
        rcv.pack(side="right", padx=4)
        draw_icon(rcv, "refresh", MUTED, 18, 3, 3)
        rcv.bind("<Button-1>", lambda e: self._refresh_all())
        rcv.bind("<Enter>", lambda e: [rcv.delete("all"), draw_icon(rcv, "refresh", CYAN, 18, 3, 3)])
        rcv.bind("<Leave>", lambda e: [rcv.delete("all"), draw_icon(rcv, "refresh", MUTED, 18, 3, 3)])
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        # Search bar
        sb_row = tk.Frame(f, bg=BG); sb_row.pack(fill="x", padx=14, pady=(10, 0))
        so = tk.Frame(sb_row, bg=BORDER); so.pack(side="left", fill="x", expand=True)
        si = tk.Frame(so, bg=SURF3);      si.pack(fill="x", padx=1, pady=1)
        tk.Label(si, text=" 🔍", bg=SURF3, fg=MUTED, font=FSMALL).pack(side="left")
        self._all_q = tk.StringVar()
        self._all_q.trace_add("write", lambda *_: self._refresh_all())
        tk.Entry(si, textvariable=self._all_q, bg=SURF3, fg=TEXT, insertbackground=PURPLE,
                 font=FBODY, relief="flat", bd=8).pack(side="left", fill="x", expand=True)

        # Tab strip: Firebase + Local
        self._all_tab = tk.StringVar(value="local")
        tab_row = tk.Frame(f, bg=BG); tab_row.pack(fill="x", padx=14, pady=(8, 0))
        for tab_val, tab_lbl in [("local", "💾  Local (baixados)"), ("firebase", "☁  Firebase (biblioteca)")]:
            def _tab_click(v=tab_val):
                self._all_tab.set(v); self._refresh_all()
                for child in tab_row.winfo_children():
                    is_this = (child.cget("text") if hasattr(child, "cget") else "") == tab_lbl
                    try:
                        child.configure(bg=SURF3 if v == tab_val else BG,
                                        fg=TEXT   if v == tab_val else MUTED)
                    except: pass
            tb_btn = tk.Button(tab_row, text=tab_lbl, bg=SURF3 if tab_val=="local" else BG,
                               fg=TEXT if tab_val=="local" else MUTED,
                               relief="flat", bd=0, padx=14, pady=7, cursor="hand2", font=FSMALL,
                               command=_tab_click)
            tb_btn.pack(side="left", padx=(0, 4))
            tb_btn.bind("<Enter>", lambda e, b=tb_btn: b.configure(fg=TEXT))
            tb_btn.bind("<Leave>", lambda e, b=tb_btn, v=tab_val: b.configure(fg=TEXT if self._all_tab.get()==v else MUTED))

        # Table header
        thead = tk.Frame(f, bg=SURF3); thead.pack(fill="x", padx=14, pady=(8, 0))
        for txt, anc, px in [("#", "center", 3), ("Nome", "w", 6), ("Tipo", "center", 4),
                             ("Tamanho", "center", 4), ("Agendamentos", "center", 4), ("", "center", 4)]:
            tk.Label(thead, text=txt, bg=SURF3, fg=MUTED, font=FXSMALL,
                     anchor=anc).pack(side="left", padx=px, pady=5,
                                      expand=(txt=="Nome"), fill="x" if txt=="Nome" else "none")

        # Scrollable body
        _, self._all_inner = self._scrolled(tk.Frame(f, bg=BG))
        self._all_inner.master.master.pack(fill="both", expand=True, padx=14, pady=(2, 10))
        return f

    def _get_schedules_for_url(self, url):
        """Retorna lista de (horario, playlist_nome, loops) para uma URL."""
        results = []
        for pl in ST.local_playlists.values():
            if not isinstance(pl, dict): continue
            for item in (pl.get("itens") or []):
                if isinstance(item, dict) and item.get("url") == url:
                    h = item.get("horario")
                    if h:
                        results.append({
                            "horario":  h,
                            "playlist": pl.get("nome", "?"),
                            "loops":    item.get("loops", 1),
                        })
        results.sort(key=lambda x: x["horario"])
        return results

    def _open_media_modal(self, item_data):
        """
        Modal que aparece ao clicar numa mídia:
        mostra horários agendados, loops, e botão Tocar Agora.
        """
        nome  = item_data.get("nome", "?")
        url   = item_data.get("url", "") or item_data.get("path", "")
        tipo  = item_data.get("tipo", "")
        path  = item_data.get("path", "")
        tam   = item_data.get("tamanho", 0)
        sched = self._get_schedules_for_url(url) if url else []

        win = tk.Toplevel(self.root)
        win.title(f"Mídia — {nome}")
        win.geometry("440x480")
        win.configure(bg=SURF)
        win.resizable(False, False)
        win.grab_set(); win.transient(self.root)

        # Header
        mhdr = tk.Frame(win, bg=SURF2, height=60); mhdr.pack(fill="x"); mhdr.pack_propagate(False)
        tk.Frame(mhdr, bg=CYAN, width=4).pack(side="left", fill="y")
        ico_cv = tk.Canvas(mhdr, width=36, height=36, bg=SURF2, highlightthickness=0)
        ico_cv.pack(side="left", padx=(12, 8), pady=12)
        draw_icon(ico_cv, "music", CYAN, 24, 6, 6)
        nf = tk.Frame(mhdr, bg=SURF2); nf.pack(side="left", fill="y", justify="center", pady=10)
        tk.Label(nf, text=nome[:40], bg=SURF2, fg=TEXT, font=("Segoe UI", 11, "bold"), anchor="w").pack(anchor="w")
        tk.Label(nf, text=f"{tipo}  ·  {tam/1048576:.1f} MB" if tam else tipo, bg=SURF2, fg=MUTED, font=FSMALL).pack(anchor="w")
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(win, bg=SURF); body.pack(fill="both", expand=True, padx=20, pady=16)

        # Loops
        tk.Label(body, text="REPETIÇÕES (LOOPS)", bg=SURF, fg=MUTED, font=FXSMALL).pack(anchor="w", pady=(0, 4))
        loops_v = tk.IntVar(value=1)
        loop_row = tk.Frame(body, bg=SURF4); loop_row.pack(anchor="w", pady=(0, 16))
        tk.Button(loop_row, text=" − ", bg=SURF4, fg=PURPLE, relief="flat", bd=0,
                  font=("Segoe UI", 14), cursor="hand2",
                  command=lambda: loops_v.set(max(1, loops_v.get()-1))).pack(side="left", padx=4, pady=4)
        tk.Label(loop_row, textvariable=loops_v, bg=SURF4, fg=TEXT,
                 font=("Segoe UI", 16, "bold"), width=3).pack(side="left")
        tk.Button(loop_row, text=" + ", bg=SURF4, fg=PURPLE, relief="flat", bd=0,
                  font=("Segoe UI", 14), cursor="hand2",
                  command=lambda: loops_v.set(min(99, loops_v.get()+1))).pack(side="left", padx=4, pady=4)
        tk.Label(loop_row, text=" vezes", bg=SURF4, fg=MUTED, font=FSMALL).pack(side="left", padx=(0, 8), pady=4)

        # Agendamentos
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))
        tk.Label(body, text="HORÁRIOS AGENDADOS", bg=SURF, fg=MUTED, font=FXSMALL).pack(anchor="w", pady=(0, 6))

        if sched:
            now_t = datetime.now().strftime("%H:%M")
            for s in sched:
                is_next = (s["horario"] > now_t)
                sr = tk.Frame(body, bg=SURF3); sr.pack(fill="x", pady=2)

                # Time badge
                tc = GREEN if is_next else MUTED
                tbf = tk.Frame(sr, bg=SURF4, padx=8, pady=3); tbf.pack(side="left", padx=(8, 10), pady=6)
                cv_clk = tk.Canvas(tbf, width=14, height=14, bg=SURF4, highlightthickness=0)
                cv_clk.pack(side="left", padx=(0, 4))
                draw_icon(cv_clk, "clock", tc, 12, 1, 1)
                tk.Label(tbf, text=s["horario"], bg=SURF4, fg=tc, font=("Consolas", 10, "bold")).pack(side="left")

                # Playlist + loops
                pf = tk.Frame(sr, bg=SURF3); pf.pack(side="left", fill="x", expand=True, pady=6)
                tk.Label(pf, text=s["playlist"], bg=SURF3, fg=TEXT, font=FBODY, anchor="w").pack(anchor="w")
                lbl_l = tk.Label(pf, text=f"{s['loops']}× loop", bg=SURF3, fg=MUTED, font=FSMALL)
                lbl_l.pack(anchor="w")

                # Next indicator
                if is_next:
                    tk.Label(sr, text="próx ", bg=SURF3, fg=GREEN, font=FXSMALL).pack(side="right", padx=8)
        else:
            tk.Label(body, text="Nenhum horário agendado para esta mídia.",
                     bg=SURF, fg=MUTED, font=FSMALL).pack(anchor="w", pady=6)

        # Arquivo local
        if path and Path(path).exists():
            tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(10, 6))
            tk.Label(body, text="ARQUIVO LOCAL", bg=SURF, fg=MUTED, font=FXSMALL).pack(anchor="w", pady=(0, 2))
            tk.Label(body, text=str(Path(path).name), bg=SURF, fg=CYAN, font=FMONO2, anchor="w").pack(fill="x")

        # Botão Tocar Agora
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(14, 10))

        def _play():
            cfg = load_config()
            n   = loops_v.get()
            pl  = {"nome": f"▶ {nome}", "temp": True,
                   "itens": [{"nome": nome, "url": url, "path": path,
                               "loops": n, "tipo": tipo, "horario": None}]}
            log.info(f"Modal → Tocar: {nome} x{n}")
            start_playlist(pl, cfg, force=True, loops_override=n)
            win.destroy(); self._show("Player")

        play_btn = tk.Button(body, text="  ▶  Tocar Agora  ", bg=PURPLE2, fg=TEXT,
                             font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
                             pady=11, cursor="hand2", activebackground=PURPLE3, command=_play)
        play_btn.pack(fill="x")
        play_btn.bind("<Enter>", lambda e: play_btn.configure(bg=PURPLE3))
        play_btn.bind("<Leave>", lambda e: play_btn.configure(bg=PURPLE2))

        close_btn = tk.Button(body, text="Fechar", bg=SURF2, fg=MUTED, font=FSMALL,
                              relief="flat", bd=0, pady=7, cursor="hand2", command=win.destroy)
        close_btn.pack(fill="x", pady=(6, 0))

    def _refresh_all(self):
        for w in self._all_inner.winfo_children(): w.destroy()
        self._all_loop_vars.clear()

        q   = self._all_q.get().lower() if hasattr(self, "_all_q") else ""
        tab = self._all_tab.get() if hasattr(self, "_all_tab") else "local"

        if tab == "local":
            raw_items = scan_local_files()
            if q: raw_items = [i for i in raw_items if q in i.get("nome","").lower()]
            # Enrich with URL from cache index
            idx = load_cache_index()
            for item in raw_items:
                # Try find URL for this path
                for k, v in idx.items():
                    if v.get("path") == item["path"]:
                        item["url"] = ""   # We have the local path, that's enough
                        break
                if "url" not in item: item["url"] = ""
        else:
            raw_items = []
            for aid, a in sorted(self._anuncios.items(), key=lambda x: x[1].get("nome","").lower()):
                if not isinstance(a, dict): continue
                if q and q not in a.get("nome","").lower(): continue
                raw_items.append({
                    "nome":    a.get("nome","—"),
                    "url":     a.get("url",""),
                    "path":    get_cached(a.get("url","")) or "",
                    "tipo":    a.get("tipo",""),
                    "tamanho": a.get("tamanho", 0),
                    "ts":      a.get("criado_em", 0),
                })

        self._lbl_all_count.configure(text=f"{len(raw_items)} faixa{'s' if len(raw_items)!=1 else ''}")

        if not raw_items:
            empty_msg = ("Nenhum arquivo em  local/  ainda.\nClique em Sincronizar para baixar mídias."
                         if tab == "local" else
                         "Nenhuma mídia no Firebase. Adicione no painel web.")
            tk.Label(self._all_inner, text=empty_msg, bg=BG, fg=MUTED, font=FBODY,
                     justify="center").pack(pady=50)
            return

        for i, item in enumerate(raw_items):
            nome    = item.get("nome", "—")
            tipo    = item.get("tipo", "").upper() or "—"
            tamanho = item.get("tamanho", 0)
            url     = item.get("url", "")
            path    = item.get("path", "")
            yt      = "youtube" in url.lower() or "youtu.be" in url.lower()
            cached  = bool(path and Path(path).exists())
            sched   = self._get_schedules_for_url(url)

            rbg = SURF3 if i % 2 == 0 else SURF2
            row = tk.Frame(self._all_inner, bg=rbg, height=46, cursor="hand2")
            row.pack(fill="x"); row.pack_propagate(False)

            # ── #  ──────────────────────────────────────────────
            tk.Label(row, text=f"{i+1:02d}", bg=rbg, fg=MUTED, font=FMONO, width=4, anchor="center").pack(side="left", padx=(6,2))

            # ── Icon ────────────────────────────────────────────
            icv = tk.Canvas(row, width=22, height=22, bg=rbg, highlightthickness=0)
            icv.pack(side="left", padx=(2, 6), pady=12)
            draw_icon(icv, "music", DANGER if yt else PURPLE, 16, 3, 3)

            # ── Name ────────────────────────────────────────────
            nf = tk.Frame(row, bg=rbg); nf.pack(side="left", fill="x", expand=True)
            tk.Label(nf, text=nome, bg=rbg, fg=TEXT, font=("Segoe UI", 9, "bold"),
                     anchor="w").pack(anchor="w", pady=(8, 0))
            sub_parts = []
            if cached: sub_parts.append("✓ local")
            if sched:  sub_parts.append(f"⏰ {len(sched)} agendamento{'s' if len(sched)>1 else ''}")
            tk.Label(nf, text="  ·  ".join(sub_parts) if sub_parts else "sem agendamentos",
                     bg=rbg, fg=CYAN if sched else MUTED, font=FXSMALL, anchor="w").pack(anchor="w", pady=(0, 8))

            # ── Type badge ──────────────────────────────────────
            bb = DANGER if yt else PURPLE
            bf = tk.Frame(row, bg=SURF4, padx=6, pady=2); bf.pack(side="left", padx=6)
            tk.Label(bf, text="YT" if yt else tipo[:4], bg=SURF4, fg=bb, font=FXSMALL).pack()

            # ── Size ────────────────────────────────────────────
            sz = f"{tamanho/1048576:.1f} MB" if tamanho else "—"
            tk.Label(row, text=sz, bg=rbg, fg=MUTED, font=FMONO2, width=7, anchor="center").pack(side="left", padx=4)

            # ── Quick play button (without modal) ───────────────
            def _qplay(it=item):
                cfg = load_config()
                pl  = {"nome": f"▶ {it['nome']}", "temp": True,
                       "itens": [{"nome": it["nome"], "url": it.get("url",""),
                                  "path": it.get("path",""), "loops": 1,
                                  "tipo": it.get("tipo",""), "horario": None}]}
                start_playlist(pl, cfg, force=True)
                self._show("Player")

            qb = tk.Button(row, text="▶", bg=PURPLE2, fg=TEXT, font=("Segoe UI", 8, "bold"),
                           relief="flat", bd=0, padx=10, pady=6, cursor="hand2",
                           activebackground=PURPLE3, command=_qplay)
            qb.pack(side="right", padx=4)
            qb.bind("<Enter>", lambda e, b=qb: b.configure(bg=PURPLE3))
            qb.bind("<Leave>", lambda e, b=qb: b.configure(bg=PURPLE2))

            # ── Click anywhere → modal ───────────────────────────
            def _click_row(e, it=item, b=qb):
                # Don't open modal if clicking the play button
                if e.widget is b: return
                self._open_media_modal(it)

            for w in (row, nf) + tuple(nf.winfo_children()):
                try: w.bind("<Button-1>", _click_row)
                except: pass
            row.bind("<Button-1>", _click_row)

            # Hover effect
            def _hl(e, r=row, bg=rbg, b=qb):
                hl = self._lt(bg)
                r.configure(bg=hl)
                for ch in r.winfo_children():
                    try:
                        if ch.cget("bg") == bg: ch.configure(bg=hl)
                    except: pass
            def _uhl(e, r=row, bg=rbg):
                r.configure(bg=bg)
                for ch in r.winfo_children():
                    try:
                        if ch.cget("bg") != PURPLE2 and ch.cget("bg") != PURPLE3:
                            ch.configure(bg=bg)
                    except: pass
            row.bind("<Enter>", _hl); row.bind("<Leave>", _uhl)

    # ══ PAGE: PLAYLISTS ════════════════════════════════════════════
    def _pg_playlists(self, p):
        f = tk.Frame(p, bg=BG)
        self._phdr(f, "Playlists", "Duplo clique para tocar", WARN)
        wrap = tk.Frame(f, bg=SURF2, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True, padx=14, pady=10)
        cols = ("nome", "faixas", "status", "acao")
        self._tv_pl = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        sb2 = ttk.Scrollbar(wrap, orient="vertical", command=self._tv_pl.yview)
        self._tv_pl.configure(yscrollcommand=sb2.set)
        self._tv_pl.heading("nome",   text="Nome da Playlist")
        self._tv_pl.heading("faixas", text="Faixas")
        self._tv_pl.heading("status", text="Status")
        self._tv_pl.heading("acao",   text="Ação")
        self._tv_pl.column("nome",   width=280, anchor="w")
        self._tv_pl.column("faixas", width=60,  anchor="center")
        self._tv_pl.column("status", width=90,  anchor="center")
        self._tv_pl.column("acao",   width=120, anchor="center")
        self._tv_pl.tag_configure("ativa",   foreground=GREEN)
        self._tv_pl.tag_configure("inativa", foreground=MUTED)
        self._tv_pl.tag_configure("playing", foreground=PURPLE, font=FTIT)
        self._tv_pl.bind("<Double-1>", self._pl_dbl)
        self._tv_pl.bind("<Button-1>", self._pl_click)
        sb2.pack(side="right", fill="y"); self._tv_pl.pack(fill="both", expand=True)
        return f

    # ══ PAGE: LOGS ═════════════════════════════════════════════════
    def _pg_logs(self, p):
        f = tk.Frame(p, bg=BG)
        hdr = tk.Frame(f, bg=SURF, height=54); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=GREEN, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="Logs", bg=SURF, fg=TEXT, font=FH1).pack(side="left", padx=(16,6))
        self._lbl_logcount = tk.Label(hdr, text="0 registros", bg=SURF, fg=MUTED, font=FSMALL)
        self._lbl_logcount.pack(side="right", padx=14)
        self._mkbtn(hdr, "Limpar", SURF, MUTED, self._clear_log_tv, px=10, py=4).pack(side="right", padx=4, pady=10)
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        wrap = tk.Frame(f, bg=SURF2, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True, padx=14, pady=10)
        cols = ("time", "status", "msg")
        self._tv_log = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="none")
        sb_l = ttk.Scrollbar(wrap, orient="vertical", command=self._tv_log.yview)
        self._tv_log.configure(yscrollcommand=sb_l.set)
        self._tv_log.heading("time",   text="Horário")
        self._tv_log.heading("status", text="Status")
        self._tv_log.heading("msg",    text="Mensagem")
        self._tv_log.column("time",   width=130, anchor="center")
        self._tv_log.column("status", width=80,  anchor="center")
        self._tv_log.column("msg",    minwidth=300, anchor="w")
        self._tv_log.tag_configure("ok",    foreground=GREEN)
        self._tv_log.tag_configure("error", foreground=DANGER)
        self._tv_log.tag_configure("info",  foreground=MUTED2)
        sb_l.pack(side="right", fill="y"); self._tv_log.pack(fill="both", expand=True)
        return f

    def _clear_log_tv(self):
        for r in self._tv_log.get_children(): self._tv_log.delete(r)
        self._lbl_logcount.configure(text="0 registros")

    def _refresh_logs(self, logs_dict):
        tv = self._tv_log
        for r in tv.get_children(): tv.delete(r)
        entries = sorted(
            [(k, v) for k, v in logs_dict.items() if isinstance(v, dict)],
            key=lambda x: x[1].get("timestamp", 0), reverse=True
        )[:150]
        for _, l in entries:
            ts  = l.get("timestamp", 0)
            ts_s = datetime.fromtimestamp(ts/1000).strftime("%d/%m %H:%M:%S") if ts else "—"
            st  = l.get("status", "info")
            tv.insert("", "end", values=(ts_s, st.upper(), l.get("mensagem","")), tags=(st,))
        self._lbl_logcount.configure(text=f"{len(entries)} registro{'s' if len(entries)!=1 else ''}")

    # ══ PAGE: CONFIG ═══════════════════════════════════════════════
    def _pg_config(self, p):
        f = tk.Frame(p, bg=BG)
        self._phdr(f, "Configurações", "", MUTED2)
        body = tk.Frame(f, bg=BG); body.pack(fill="both", expand=True, padx=32, pady=24)
        tk.Label(body, text="Configurações do Player", bg=BG, fg=TEXT, font=FH2).pack(anchor="w", pady=(0, 20))
        cfg = load_config()
        fields = [
            ("Nome do Player",     "player_nome",    "Identificação deste player"),
            ("Volume anúncio (%)", "volume_anuncio", "0 – 100  (volume dos anúncios)"),
            ("Volume outros (%)",  "volume_outros",  "0 – 100  (outras apps ao tocar anúncio)"),
            ("Fade duck (ms)",     "duck_fade_ms",   "500 – 3000  (duração do fade)"),
        ]
        self._cfg_vars = {}
        for label, key, hint in fields:
            row = tk.Frame(body, bg=BG); row.pack(fill="x", pady=7)
            lf2 = tk.Frame(row, bg=BG, width=220); lf2.pack(side="left", fill="y"); lf2.pack_propagate(False)
            tk.Label(lf2, text=label, bg=BG, fg=TEXT, font=FBODY, anchor="w").pack(anchor="w")
            tk.Label(lf2, text=hint,  bg=BG, fg=MUTED, font=FXSMALL, anchor="w").pack(anchor="w")
            var = tk.StringVar(value=str(cfg.get(key, "")))
            self._cfg_vars[key] = var
            eo = tk.Frame(row, bg=BORDER); eo.pack(side="left", fill="x", expand=True)
            ei = tk.Frame(eo, bg=SURF3);   ei.pack(fill="x", padx=1, pady=1)
            tk.Entry(ei, textvariable=var, bg=SURF3, fg=TEXT, insertbackground=PURPLE,
                     font=FMONO, relief="flat", bd=9).pack(fill="x")

        self._mkbtn(body, "  Salvar Configurações  ", PURPLE2, TEXT, self._save_cfg, px=24, py=11).pack(anchor="w", pady=(24, 0))
        return f

    def _save_cfg(self):
        cfg = load_config(); nc = dict(cfg)
        for k, var in self._cfg_vars.items():
            raw = var.get().strip()
            try: nc[k] = int(raw)
            except:
                try: nc[k] = float(raw)
                except: nc[k] = raw
        save_config(nc)
        self._lbl_vol_ad.configure(text=f"{nc.get('volume_anuncio',100)}%")
        self._lbl_vol_ot.configure(text=f"{nc.get('volume_outros',10)}%")
        messagebox.showinfo("Salvo", "Configurações salvas com sucesso!")

    # ══ PAGE: CONTA ════════════════════════════════════════════════
    def _pg_conta(self, p):
        f = tk.Frame(p, bg=BG)
        self._phdr(f, "Conta", "Ativação e credenciais", PURPLE)
        body = tk.Frame(f, bg=BG); body.pack(fill="both", expand=True, padx=32, pady=24)

        card = self._card(body); card.pack(fill="x", pady=(0, 24))
        tk.Label(card, text="CONTA ATIVADA", bg=SURF3, fg=PURPLE, font=FXSMALL).pack(anchor="w", padx=14, pady=(12, 6))
        for label, attr in [("E-mail", "_act_email"), ("Código", "_act_codigo"), ("Status", "_act_status")]:
            row = tk.Frame(card, bg=SURF3); row.pack(fill="x", padx=14, pady=3)
            tk.Label(row, text=label, bg=SURF3, fg=MUTED, font=FSMALL, width=10, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="—", bg=SURF3, fg=TEXT, font=FMONO)
            lbl.pack(side="left"); setattr(self, attr, lbl)
        tk.Frame(card, bg=SURF3, height=10).pack()

        # Local folder info
        info_card = self._card(body); info_card.pack(fill="x", pady=(0, 24))
        tk.Label(info_card, text="PASTA LOCAL", bg=SURF3, fg=MUTED, font=FXSMALL).pack(anchor="w", padx=14, pady=(12, 4))
        tk.Label(info_card, text=str(LOCAL_DIR), bg=SURF3, fg=CYAN, font=FMONO2, anchor="w").pack(fill="x", padx=14)
        ir = tk.Frame(info_card, bg=SURF3); ir.pack(fill="x", padx=14, pady=(4, 10))
        self._lbl_conta_local = tk.Label(ir, text="—", bg=SURF3, fg=MUTED2, font=FSMALL)
        self._lbl_conta_local.pack(side="left")

        tk.Label(body, text="Desconectar apaga activation.json, todos os JSONs locais e os arquivos em  local/",
                 bg=BG, fg=MUTED, font=FSMALL, wraplength=520, justify="left").pack(anchor="w", pady=(0, 16))

        disc = tk.Button(body, text="  Desconectar e Redefinir  ", bg="#1a080e", fg=DANGER,
                         font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                         padx=24, pady=11, cursor="hand2",
                         activebackground="#2e0b17", command=self._cmd_disconnect)
        disc.pack(anchor="w")
        disc.bind("<Enter>", lambda e: disc.configure(bg="#2e0b17"))
        disc.bind("<Leave>", lambda e: disc.configure(bg="#1a080e"))
        return f

    # ── EQ / Artwork ─────────────────────────────────────────────
    def _draw_art(self, idle=True):
        c = self._art_cv; c.delete("all")
        c.create_rectangle(0, 0, 128, 128, fill=SURF3, outline="")
        if idle:
            c.create_oval(40, 40, 88, 88, fill=SURF4, outline=BORDER, width=1)
            c.create_oval(53, 53, 75, 75, fill=SURF2, outline="")
        else:
            ph = self._eq_phase
            for i, (r, col) in enumerate([(46, "#3b1585"), (32, "#7c3aed"), (20, "#9b59f5")]):
                w = 1 + int(math.sin(ph+i)*2)
                c.create_oval(64-r+w, 64-r-w, 64+r+w, 64+r+w, outline=col, width=2)
            c.create_oval(50, 50, 78, 78, fill=PURPLE2, outline="")
            c.create_polygon(56, 44, 56, 84, 82, 64, fill="white", outline="")

    def _draw_eq(self, idle=True):
        c = self._eq_cv; c.delete("all")
        col = MUTED if idle else PURPLE
        hs = [3, 6, 4, 8] if idle else [2 + int(11*abs(math.sin(self._eq_phase+i*0.85))) for i in range(4)]
        for i, h in enumerate(hs):
            c.create_rectangle(i*8, 14-h, i*8+6, 14, fill=col, outline="")

    def _tick_eq(self):
        if not self._eq_running: return
        self._eq_phase += 0.22
        self._draw_eq(False); self._draw_art(False)
        self.root.after(100, self._tick_eq)

    def _start_eq(self):
        if not self._eq_running: self._eq_running = True; self._tick_eq()

    def _stop_eq(self):
        self._eq_running = False; self._draw_eq(True); self._draw_art(True)

    # ── Playlists treeview ────────────────────────────────────────
    def _refresh_playlists(self):
        tv = self._tv_pl
        for r in tv.get_children(): tv.delete(r)
        for pl_id, pl in self._playlists.items():
            if not isinstance(pl, dict): continue
            nome  = pl.get("nome", "—")
            faixas = len(pl.get("itens") or [])
            ativa  = pl.get("ativa", False)
            tag    = "playing" if ST.current_pl_id == pl_id else ("ativa" if ativa else "inativa")
            tv.insert("", "end", values=(nome, faixas, "Ativa" if ativa else "Inativa", "▶ Tocar"),
                      tags=(tag, pl_id))

    def _pl_click(self, e):
        tv = self._tv_pl; col = tv.identify_column(e.x); rid = tv.identify_row(e.y)
        if not rid: return
        if col == "#4":
            tags = tv.item(rid, "tags"); pl_id = tags[1] if len(tags)>1 else None
            if pl_id and pl_id in self._playlists: self._ask_loops(pl_id)

    def _pl_dbl(self, e):
        tv = self._tv_pl; sel = tv.selection()
        if not sel: return
        tags = tv.item(sel[0], "tags"); pl_id = tags[1] if len(tags)>1 else None
        if pl_id and pl_id in self._playlists: self._ask_loops(pl_id)

    def _ask_loops(self, pl_id):
        pl = self._playlists.get(pl_id)
        if not pl: return
        win = tk.Toplevel(self.root); win.title("Tocar Playlist"); win.geometry("300x210")
        win.configure(bg=SURF); win.resizable(False, False); win.grab_set(); win.transient(self.root)
        tk.Label(win, text=pl.get("nome",""), bg=SURF, fg=TEXT, font=FH2).pack(pady=(18, 4))
        tk.Label(win, text="Quantas vezes repetir?", bg=SURF, fg=MUTED, font=FSMALL).pack()
        sf = tk.Frame(win, bg=SURF); sf.pack(pady=(10, 14))
        lv = tk.IntVar(value=1)
        for txt, cmd in [("−", lambda: lv.set(max(1,lv.get()-1))), ("+", lambda: lv.set(min(99,lv.get()+1)))]:
            tk.Button(sf, text=txt, bg=SURF3, fg=TEXT, relief="flat", bd=0, font=("Segoe UI", 15),
                      padx=12, pady=3, cursor="hand2", command=cmd).pack(side="left", padx=3)
            if txt == "−":
                tk.Label(sf, textvariable=lv, bg=SURF3, fg=PURPLE, font=("Segoe UI", 18, "bold"),
                         width=3, pady=4).pack(side="left", padx=2)
        def _go():
            n = lv.get(); win.destroy(); cfg = load_config(); ST.current_pl_id = pl_id
            start_playlist(pl, cfg, True, loops_override=n); self._show("Player")
        gb = tk.Button(win, text="  ▶  Tocar Agora  ", bg=PURPLE2, fg=TEXT,
                       font=("Segoe UI", 11, "bold"), relief="flat", bd=0, padx=24, pady=10,
                       cursor="hand2", activebackground=PURPLE3, command=_go)
        gb.pack(); gb.bind("<Enter>", lambda e: gb.configure(bg=PURPLE3)); gb.bind("<Leave>", lambda e: gb.configure(bg=PURPLE2))

    # ── Commands ─────────────────────────────────────────────────
    def _cmd_stop(self):
        def _go():
            try: fb_set("/comandos/stop", {"timestamp": int(time.time()*1000), "executado": False})
            except: pass
            stop_all(); ev("stopped")
        threading.Thread(target=_go, daemon=True).start()

    def _cmd_precache(self):
        threading.Thread(target=precache_all, daemon=True).start()

    def _cmd_disconnect(self):
        if not messagebox.askyesno("Desconectar",
                                   "Isso irá apagar:\n\n"
                                   "• activation.json\n"
                                   "• local_playlists.json\n"
                                   "• local_anuncios.json\n"
                                   "• local_logs.json\n"
                                   "• playads_config.json\n"
                                   "• Todos os arquivos em  local/\n\n"
                                   "Deseja continuar?"):
            return
        stop_all(); clear_all_local(); self.root.destroy()

    def _update_local_lbl(self):
        files = scan_local_files()
        total = sum(f.get("tamanho", 0) for f in files) / 1048576
        self._lbl_cache.configure(text=f"{len(files)} arquivo(s) · {total:.1f} MB · pasta local/")
        try: self._lbl_conta_local.configure(text=f"{len(files)} arquivo(s) · {total:.1f} MB")
        except: pass

    def _update_status(self, text, color):
        self._lbl_conn.configure(text=text, fg=color)
        self._lbl_conn_dot.configure(fg=color)
        self._pill_dot.configure(fg=color)
        self._pill_txt.configure(text=text, fg=color)

    def set_account(self):
        self._lbl_uemail.configure(text=ST.email or "—")
        self._lbl_ucode.configure(text=ST.codigo or "—")
        self._av_cv.itemconfigure(self._av_txt, text=(ST.email or "?")[0].upper())
        self._act_email.configure(text=ST.email or "—")
        self._act_codigo.configure(text=ST.codigo or "—")
        self._act_status.configure(text="● Ativo", fg=GREEN)

    # ══ POLL ══════════════════════════════════════════════════════
    def _poll(self):
        try:
            while True:
                e = EVQ.get_nowait(); t = e["t"]

                if t == "log":
                    msg = e["msg"]; lvl = e.get("lvl", "INFO")
                    self._logtxt.configure(state="normal")
                    tag = ("PL"   if any(x in msg for x in ("▶", "✓", "Playlist")) else
                           "OK"   if any(x in msg for x in ("Firebase", "SSE", "ativo", "conectado")) else
                           "CY"   if "Tocando" in msg else
                           "ERR"  if lvl == "ERROR" else
                           "WARN" if lvl in ("WARNING", "WARN") else "INFO")
                    self._logtxt.insert("end", msg + "\n", tag)
                    self._logtxt.see("end")
                    ln = int(self._logtxt.index("end-1c").split(".")[0])
                    if ln > 400: self._logtxt.delete("1.0", f"{ln-400}.0")
                    self._logtxt.configure(state="disabled")

                elif t == "now_playing":
                    nome, lp, tl, pl = e["nome"], e["loop"], e["total"], e["pl"]
                    self._lbl_tag.configure(text="▶ REPRODUZINDO", fg=PURPLE)
                    self._lbl_title.configure(text=nome)
                    ls = f"  Loop {lp}/{tl}" if tl > 1 else ""
                    self._lbl_meta.configure(text=f"{pl}{ls}".strip() if pl else (ls.strip() or "—"))
                    self._s_st.configure(text="Tocando",   fg=WARN)
                    self._s_loop.configure(text=f"{lp}/{tl}" if tl > 1 else "1×", fg=PURPLE)
                    self._update_status("Reproduzindo", WARN)
                    self._start_eq(); self._prog_var.set(0)

                elif t == "pl_start":
                    itens = e["itens"]
                    pnome = e["nome"]
                    self._s_pl.configure(text=(pnome[:14]+"…") if len(pnome)>14 else pnome)
                    self._s_tr.configure(text=str(len(itens)))
                    self._refresh_playlists()

                elif t == "pl_end":
                    self._stop_eq()
                    self._lbl_tag.configure(text="✓ CONCLUÍDO", fg=GREEN)
                    self._s_st.configure(text="Pronto", fg=GREEN)
                    self._s_loop.configure(text="—", fg=MUTED)
                    self._update_status("Pronto", GREEN)
                    self._prog_var.set(100); self._refresh_playlists()

                elif t == "stopped":
                    self._stop_eq()
                    self._lbl_tag.configure(text="AGUARDANDO", fg=MUTED)
                    self._lbl_title.configure(text="Nenhuma mídia")
                    self._lbl_meta.configure(text="—")
                    self._s_st.configure(text="Pronto", fg=GREEN)
                    self._s_loop.configure(text="—", fg=MUTED)
                    self._update_status("Pronto", GREEN)
                    self._prog_var.set(0); ST.current_pl_id = ""
                    self._refresh_playlists()

                elif t == "dl_pct":
                    self._prog_var.set(e["pct"] * 0.5)

                elif t == "firebase_ok":
                    self._update_status("Conectado", GREEN)
                    self._s_st.configure(text="Pronto", fg=GREEN)

                elif t == "firebase_err":
                    self._update_status("Erro Firebase", DANGER)
                    self._s_st.configure(text="Erro", fg=DANGER)

                elif t == "fb_data":
                    self._playlists = e.get("playlists", {})
                    self._anuncios  = e.get("anuncios", {})
                    self._refresh_playlists()
                    self._refresh_all()
                    total_tr = sum(len(p.get("itens") or []) for p in self._playlists.values() if isinstance(p, dict))
                    self._s_tr.configure(text=str(total_tr))
                    self._update_local_lbl()

                elif t == "fb_logs":
                    self._refresh_logs(e.get("logs", {}))

                elif t in ("cache_done", "local_updated"):
                    self._update_local_lbl()
                    if self._page == "All": self._refresh_all()

        except queue.Empty: pass

        if ST.playing and ST.play_ts:
            el = time.time() - ST.play_ts
            self._lbl_elapsed.configure(text=f"{int(el//60)}:{int(el%60):02d}")
            cur = self._prog_var.get()
            if cur < 99: self._prog_var.set(min(99, cur + 0.07))

        self.root.after(120, self._poll)

    def run(self): self.root.mainloop()


# ══════════════════════════════════════════════════════════════════════════════
#  BOOTSTRAP
# ══════════════════════════════════════════════════════════════════════════════
def start_backend(app, senha):
    if not start_firebase(senha):
        ev("firebase_err"); return

    cfg = load_config()
    load_local_data()

    if ST.local_playlists or ST.local_anuncios:
        ev("fb_data", playlists=ST.local_playlists, anuncios=ST.local_anuncios)

    if LOCAL_LOG_FILE.exists():
        try:
            logs = json.loads(LOCAL_LOG_FILE.read_text(encoding="utf-8"))
            if logs: ev("fb_logs", logs=logs)
        except: pass

    fb_status(None); fb_log(f"PlayAds v6.1 iniciado — {ST.email}", "ok")
    ev("firebase_ok"); ev("local_updated")

    threading.Thread(target=heartbeat,       args=(cfg,), daemon=True).start()
    threading.Thread(target=check_schedules, args=(cfg,), daemon=True).start()
    threading.Thread(target=setup_listeners, args=(cfg,), daemon=True).start()
    threading.Thread(target=precache_all,    daemon=True).start()

    cfg2 = load_config()
    app._lbl_vol_ad.configure(text=f"{cfg2.get('volume_anuncio',100)}%")
    app._lbl_vol_ot.configure(text=f"{cfg2.get('volume_outros',10)}%")
    app.set_account()

    log.info(f"Conta: {ST.email}  |  Código: {ST.codigo}")
    log.info("pycaw:  " + ("ativo ✓"       if HAS_PYCAW  else "não instalado"))
    log.info("yt-dlp: " + ("ativo ✓"       if HAS_YTDLP  else "não instalado"))
    log.info(f"Pasta local: {LOCAL_DIR}")


def main():
    act = load_activation()

    def on_activated(uid, email, codigo, senha):
        ST.uid = uid; ST.email = email; ST.codigo = codigo
        app = App()
        threading.Thread(target=start_backend, args=(app, senha), daemon=True).start()
        app.run()

    if act:
        senha = act.get("senha", "")
        if senha:
            on_activated(act["uid"], act["email"], act["codigo"], senha)
        else:
            clear_all_local()
            ActivationScreen(on_activated).run()
    else:
        ActivationScreen(on_activated).run()


if __name__ == "__main__":
    main()