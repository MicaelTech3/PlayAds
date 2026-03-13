#!/usr/bin/env python3
"""
PlayAds Player v6.0
- Layout profissional inspirado no painel web
- Sidebar com ícones SVG-style via Canvas
- Telas: Player, All, Playlists, Logs, Config, Conta
- Desconectar apaga todos os JSONs locais
- Duck de volume síncrono + SSE listeners
"""

import os, sys, json, time, threading, platform, logging, queue, hashlib, webbrowser, glob
from datetime import datetime
from pathlib import Path

# ── Deps ──────────────────────────────────────────────────────────
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

# ── Paleta ────────────────────────────────────────────────────────
BG      = "#0d0b14"
SURF    = "#13111f"
SURF2   = "#1a1728"
SURF3   = "#221f33"
SURF4   = "#2a2740"
BORDER  = "#332f4d"
PURPLE  = "#9b59f5"
PURPLE2 = "#7c3aed"
PURPLE3 = "#4c1d95"
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

# ── Caminhos ──────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
CACHE_DIR       = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_INDEX     = CACHE_DIR / "index.json"
ACTIVATION_FILE = BASE_DIR / "activation.json"
CONFIG_FILE     = BASE_DIR / "playads_config.json"
LOCAL_PL_FILE   = BASE_DIR / "local_playlists.json"
LOCAL_AD_FILE   = BASE_DIR / "local_anuncios.json"
LOCAL_LOG_FILE  = BASE_DIR / "local_logs.json"

# ── Firebase ──────────────────────────────────────────────────────
FIREBASE_WEB_API_KEY = "AIzaSyBgwB_2syWdyK5Wc0E9rJIlDnXjwTf1OWE"
FIREBASE_DB_URL      = "https://anucio-web-default-rtdb.firebaseio.com"
FIREBASE_AUTH_URL    = "https://identitytoolkit.googleapis.com/v1/accounts"
FIREBASE_REFRESH_URL = "https://securetoken.googleapis.com/v1/token"
WEB_URL              = "https://anucio-web.web.app"

# ── Config ────────────────────────────────────────────────────────
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

# ── Auth ──────────────────────────────────────────────────────────
class _Auth:
    id_token      = ""
    refresh_token = ""
    expires_at    = 0.0
    lock          = threading.Lock()

_AUTH = _Auth()

def auth_sign_in(email, password):
    try:
        url = f"{FIREBASE_AUTH_URL}:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
        r = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
        if not r.ok:
            return False
        d = r.json()
        with _AUTH.lock:
            _AUTH.id_token      = d["idToken"]
            _AUTH.refresh_token = d["refreshToken"]
            _AUTH.expires_at    = time.time() + int(d.get("expiresIn", 3600)) - 60
        return True
    except:
        return False

def auth_refresh():
    if not _AUTH.refresh_token: return False
    try:
        url = f"{FIREBASE_REFRESH_URL}?key={FIREBASE_WEB_API_KEY}"
        r = requests.post(url, json={"grant_type": "refresh_token", "refresh_token": _AUTH.refresh_token}, timeout=10)
        if not r.ok: return False
        d = r.json()
        with _AUTH.lock:
            _AUTH.id_token      = d["id_token"]
            _AUTH.refresh_token = d["refresh_token"]
            _AUTH.expires_at    = time.time() + int(d.get("expires_in", 3600)) - 60
        return True
    except:
        return False

def get_token():
    if time.time() >= _AUTH.expires_at:
        auth_refresh()
    return _AUTH.id_token

def _token_loop():
    while True:
        try:
            rem = _AUTH.expires_at - time.time()
            time.sleep(max(60, rem - 120))
            if _AUTH.refresh_token:
                auth_refresh()
        except:
            time.sleep(300)

# ── Ativação ──────────────────────────────────────────────────────
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
    """Apaga activation + todos os JSONs locais ao desconectar."""
    for f in [ACTIVATION_FILE, LOCAL_PL_FILE, LOCAL_AD_FILE, LOCAL_LOG_FILE, CONFIG_FILE, CACHE_INDEX]:
        try:
            if f.exists(): f.unlink()
        except: pass
    # Apaga arquivos de cache de áudio
    for f in CACHE_DIR.glob("*"):
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

    ok = auth_sign_in(email, senha)
    if not ok: return None, None, "E-mail ou senha incorretos."

    try:
        tok = get_token()
        r2 = requests.get(f"{FIREBASE_DB_URL}/users/{uid}/email.json?auth={tok}", timeout=10)
        stored_email = r2.json() if r2.ok else email
    except:
        stored_email = email

    return uid, stored_email or email, None

# ── Cache ─────────────────────────────────────────────────────────
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

def set_cached(url, path, nome=""):
    idx = load_cache_index()
    idx[url_key(url)] = {"path": str(path), "nome": nome, "ts": int(time.time())}
    save_cache_index(idx)

# ── Estado global ─────────────────────────────────────────────────
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
    uid             = ""
    email           = ""
    codigo          = ""

ST   = State()
EVQ: queue.Queue = queue.Queue()
def ev(tipo, **kw): EVQ.put({"t": tipo, **kw})

# ── Logger ────────────────────────────────────────────────────────
class _UIHandler(logging.Handler):
    def emit(self, r):
        try: ev("log", msg=self.format(r), lvl=r.levelname)
        except: pass

_fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
log  = logging.getLogger("PlayAds")
log.setLevel(logging.INFO)
log.handlers.clear()
_sh = logging.StreamHandler(); _sh.setFormatter(_fmt); log.addHandler(_sh)
_uh = _UIHandler(); _uh.setFormatter(_fmt); log.addHandler(_uh)

# ── Duck de volume ────────────────────────────────────────────────
_saved_vols = {}
_saved_lock = threading.Lock()

def _duck_worker(target_pct, fade_ms, restore):
    if not HAS_PYCAW: return
    try:
        comtypes.CoInitialize()
        sessions = AudioUtilities.GetAllSessions()
        my_pid   = os.getpid()
        svols    = []
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
        steps = max(20, int(fade_ms / 40))
        delay = fade_ms / 1000.0 / steps
        for step in range(1, steps + 1):
            t   = step / steps
            ease = t * t * (3.0 - 2.0 * t)
            for sav, v0, v1 in svols:
                try: sav.SetMasterVolume(max(0.0, min(1.0, v0 + (v1 - v0) * ease)), None)
                except: pass
            time.sleep(delay)
    except Exception as ex: log.warning(f"duck: {ex}")
    finally:
        try: comtypes.CoUninitialize()
        except: pass

# ── Download / Audio ──────────────────────────────────────────────
def is_yt(url): return "youtube.com" in url or "youtu.be" in url

def download_yt(url, nome):
    if not HAS_YTDLP: log.error("yt-dlp não instalado"); return None
    cached = get_cached(url)
    if cached: return cached
    log.info(f"Baixando YouTube: {nome}")
    try:
        out = str(CACHE_DIR / f"yt_{url_key(url)}.%(ext)s")
        with yt_dlp.YoutubeDL({
            "format": "bestaudio/best", "outtmpl": out,
            "quiet": True, "no_warnings": True,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
        }) as ydl:
            ydl.download([url])
        mp3 = str(CACHE_DIR / f"yt_{url_key(url)}.mp3")
        if Path(mp3).exists(): set_cached(url, mp3, nome); return mp3
        for f in CACHE_DIR.glob(f"yt_{url_key(url)}.*"):
            set_cached(url, str(f), nome); return str(f)
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
        out = CACHE_DIR / f"{url_key(url)}{ext}"
        total = int(r.headers.get("Content-Length", 0)); done = 0
        with open(out, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk); done += len(chunk)
                if total: ev("dl_pct", pct=int(done / total * 100))
        set_cached(url, str(out), nome); return str(out)
    except Exception as e: log.error(f"Download {nome}: {e}"); return None

def get_audio(url, nome):
    return download_yt(url, nome) if is_yt(url) else download_audio(url, nome)

# ── Firebase REST ─────────────────────────────────────────────────
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
    fb_push("/logs", {"mensagem": msg, "status": status, "timestamp": int(time.time() * 1000),
                      "player_id": ST.codigo or "player"})

def fb_status(rep=None):
    cfg = load_config()
    d = {"nome": cfg.get("player_nome", "Player"), "last_seen": int(time.time() * 1000),
         "plataforma": platform.system() + " " + platform.release(), "versao": "6.0"}
    if rep is not None: d["reproducao_atual"] = rep
    fb_update("/player_status", d)

def fb_done(path): fb_update(path, {"executado": True})

# ── Reprodução ────────────────────────────────────────────────────
def play_item(item, cfg, loops_override=None):
    nome  = item.get("nome", "?")
    url   = item.get("url", "")
    loops = loops_override if loops_override is not None else max(1, int(item.get("loops", 1)))
    if not url: return

    tmp = get_audio(url, nome)
    if not tmp: fb_log(f"Falha: {nome}", "error"); return

    fade_ms    = int(cfg.get("duck_fade_ms", 1200))
    vol_outros = float(cfg.get("volume_outros", 10))
    vol_ad     = float(cfg.get("volume_anuncio", 100)) / 100.0

    try:
        _duck_worker(vol_outros, fade_ms, restore=False)
        for n in range(1, loops + 1):
            if ST.stop_requested: break
            log.info(f"▶ Tocando: {nome} ({n}/{loops})")
            ST.play_ts = time.time()
            fb_status(f"{nome} ({n}/{loops})")
            fb_log(f"▶ {nome} (loop {n}/{loops})", "ok")
            ev("now_playing", nome=nome, loop=n, total=loops, pl=ST.current_pl_name)
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
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
    nome_pl = pl.get("nome", "Playlist")
    itens   = pl.get("itens") or []
    if not itens:
        log.warning(f"Playlist '{nome_pl}' vazia"); ev("stopped"); return

    ST.current_pl_name = nome_pl
    ST.queue_items     = list(itens)
    fb_log(f"Iniciando: {nome_pl}", "ok")
    ev("pl_start", nome=nome_pl, itens=itens)

    now_t      = datetime.now().strftime("%H:%M")
    played_any = False
    for i, item in enumerate(itens):
        if ST.stop_requested: break
        h = item.get("horario")
        if h and not force and h != now_t:
            continue
        ST.current_item = item
        played_any = True
        ev("q_active", idx=i)
        play_item(item, cfg, loops_override=loops_override)

    if not played_any:
        log.warning(f"Nenhum item tocou em '{nome_pl}'"); ev("stopped")

    with ST.lock:
        ST.playing         = False
        ST.current_item    = None
        ST.current_pl_name = ""
    fb_status(None)
    fb_log(f"'{nome_pl}' concluída", "ok")
    log.info(f"✓ Playlist '{nome_pl}' concluída")
    ev("pl_end", nome=nome_pl)

def stop_all():
    with ST.lock: ST.stop_requested = True
    try: pygame.mixer.music.stop()
    except: pass
    if ST.current_thread and ST.current_thread.is_alive():
        ST.current_thread.join(timeout=3)
    with ST.lock:
        ST.stop_requested  = False
        ST.playing         = False
        ST.current_thread  = None
        ST.current_item    = None

def start_playlist(pl, cfg, force=True, loops_override=None):
    stop_all()
    with ST.lock:
        ST.playing = True
        t = threading.Thread(target=run_playlist, args=(pl, cfg, force),
                             kwargs={"loops_override": loops_override}, daemon=True)
        ST.current_thread = t
    t.start()

# ── SSE Listeners ─────────────────────────────────────────────────
def _sse_listen(path, callback, label=""):
    lbl = label or path
    while True:
        try:
            tok = get_token()
            url = f"{FIREBASE_DB_URL}/users/{ST.uid}{path}.json?auth={tok}"
            resp = requests.get(url, headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
                                stream=True, timeout=60)
            if resp.status_code == 401:
                auth_refresh(); time.sleep(3); continue
            if resp.status_code != 200:
                time.sleep(10); continue
            log.info(f"SSE ativo: {lbl}")
            buf = ""; etype = ""; edata = ""
            for chunk in resp.iter_content(chunk_size=1, decode_unicode=True):
                if not chunk: continue
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.rstrip("\r")
                    if line.startswith("event:"):  etype = line[6:].strip()
                    elif line.startswith("data:"): edata = line[5:].strip()
                    elif line == "":
                        if etype in ("put", "patch") and edata:
                            try:
                                payload = json.loads(edata)
                                raw     = payload.get("data")
                                callback(raw)
                            except Exception as ex:
                                log.warning(f"SSE {lbl} parse: {ex}")
                        etype = ""; edata = ""
        except requests.exceptions.Timeout:
            time.sleep(3)
        except Exception as ex:
            log.warning(f"SSE {lbl}: {ex} — retry 5s")
            time.sleep(5)

def setup_listeners(cfg):
    def on_play(data):
        try:
            if not data: return
            if isinstance(data, dict) and data.get("executado"): return
            plid = data.get("playlist_id") if isinstance(data, dict) else None
            if not plid: return
            snap = fb_get(f"/playlists/{plid}")
            if not snap: log.warning(f"on_play: playlist {plid} não encontrada"); return
            fb_done("/comandos/play_now")
            is_temp = (isinstance(data, dict) and data.get("temp_playlist_id")) or \
                      (isinstance(snap, dict) and snap.get("temp"))
            start_playlist(snap, cfg, force=True)
            if is_temp:
                time.sleep(0.5); fb_delete(f"/playlists/{plid}")
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
            now   = datetime.now()
            now_t = now.strftime("%H:%M")
            today = now.strftime("%Y-%m-%d")
            fired = {k for k in fired if k.startswith(today)}
            for pl_id, pl in list(ST.local_playlists.items()):
                if not isinstance(pl, dict) or not pl.get("ativa"): continue
                for idx, item in enumerate(pl.get("itens") or []):
                    if not isinstance(item, dict): continue
                    h = item.get("horario")
                    if h != now_t: continue
                    fk = f"{today} {now_t} {pl_id} {idx}"
                    if fk in fired: continue
                    log.info(f"⏰ Agendamento {now_t}: {pl.get('nome')} → {item.get('nome','?')}")
                    fired.add(fk)
                    sub = {"nome": f"{pl.get('nome','?')} @ {now_t}", "itens": [item]}
                    start_playlist(sub, cfg, force=True)
                    break
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
    ev("cache_done")

def load_local_data():
    for path, attr in [(LOCAL_PL_FILE, "local_playlists"), (LOCAL_AD_FILE, "local_anuncios")]:
        try:
            if path.exists():
                setattr(ST, attr, json.loads(path.read_text(encoding="utf-8")))
        except: pass

def start_firebase(senha):
    ok = auth_sign_in(ST.email, senha)
    if not ok: log.error("Firebase: falha no login"); return False
    threading.Thread(target=_token_loop, daemon=True).start()
    log.info("Firebase conectado ✓")
    return True


# ══════════════════════════════════════════════════════════════════
#  TELA DE ATIVAÇÃO
# ══════════════════════════════════════════════════════════════════
class ActivationScreen:
    def __init__(self, on_success):
        self.on_success = on_success
        self.root = tk.Tk()
        self.root.title("PlayAds — Ativação")
        self.root.geometry("460x540")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self._build()

    def _build(self):
        r = self.root

        # Header
        hdr = tk.Frame(r, bg=SURF, height=68)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=PURPLE2, width=4).pack(side="left", fill="y")
        cv = tk.Canvas(hdr, width=36, height=36, bg=SURF, highlightthickness=0)
        cv.place(x=20, y=16)
        cv.create_oval(0, 0, 36, 36, fill=PURPLE2, outline="")
        cv.create_polygon(13, 9, 13, 27, 27, 18, fill="white", outline="")
        tk.Label(hdr, text="PlayAds", bg=SURF, fg=TEXT, font=("Segoe UI", 16, "bold")).place(x=66, y=16)
        tk.Label(hdr, text="v6.0", bg=SURF, fg=MUTED, font=FMONO2).place(x=67, y=38)
        tk.Frame(r, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(r, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=20)

        tk.Label(body, text="Ativar Player", bg=BG, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(body, text="Informe seu código de ativação, e-mail e senha do painel web.",
                 bg=BG, fg=MUTED, font=FSMALL, wraplength=390, justify="left").pack(anchor="w", pady=(4, 16))

        # Campos
        self._code_var  = tk.StringVar()
        self._email_var = tk.StringVar()
        self._senha_var = tk.StringVar()
        self._code_var.trace_add("write", self._format_code)

        fields = [
            ("Código de Ativação", self._code_var, False, "PLAY-XXXX-XXXX"),
            ("E-mail",             self._email_var, False, "seu@email.com"),
            ("Senha",              self._senha_var, True,  "••••••••"),
        ]
        self._entries = []
        for label, var, is_pass, ph in fields:
            tk.Label(body, text=label, bg=BG, fg=MUTED2, font=FSMALL).pack(anchor="w", pady=(0, 3))
            outer = tk.Frame(body, bg=BORDER)
            outer.pack(fill="x", pady=(0, 12))
            inner = tk.Frame(outer, bg=SURF3)
            inner.pack(fill="x", padx=1, pady=1)
            kw = {}
            if is_pass: kw["show"] = "●"
            ent = tk.Entry(inner, textvariable=var, bg=SURF3, fg=TEXT if label != "Código de Ativação" else PURPLE,
                          insertbackground=PURPLE, font=FMONO if label == "Código de Ativação" else FBODY,
                          relief="flat", bd=10, **kw)
            if label == "Código de Ativação":
                ent.configure(font=("Consolas", 15, "bold"), justify="center")
            ent.pack(fill="x")
            ent.bind("<Return>", lambda e, i=len(self._entries): self._next_entry(i))
            self._entries.append(ent)

        self._lbl_st = tk.Label(body, text="", bg=BG, fg=MUTED, font=FSMALL, wraplength=380)
        self._lbl_st.pack(pady=(0, 10))

        self._btn = tk.Button(body, text="Ativar Agora", bg=PURPLE2, fg=TEXT,
                              font=("Segoe UI", 12, "bold"), relief="flat", bd=0,
                              padx=32, pady=12, cursor="hand2",
                              activebackground=PURPLE3, command=self._validate)
        self._btn.pack(fill="x")
        self._btn.bind("<Enter>", lambda e: self._btn.configure(bg=PURPLE3))
        self._btn.bind("<Leave>", lambda e: self._btn.configure(bg=PURPLE2))

        lf = tk.Frame(body, bg=BG); lf.pack(pady=(14, 0))
        lnk = tk.Label(lf, text="Abrir painel web →", bg=BG, fg=PURPLE, font=FSMALL, cursor="hand2")
        lnk.pack()
        lnk.bind("<Button-1>", lambda e: webbrowser.open(WEB_URL))
        lnk.bind("<Enter>",    lambda e: lnk.configure(fg=TEXT))
        lnk.bind("<Leave>",    lambda e: lnk.configure(fg=PURPLE))

    def _next_entry(self, current):
        nxt = current + 1
        if nxt < len(self._entries): self._entries[nxt].focus()
        else: self._validate()

    def _format_code(self, *_):
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
        if "@" not in email: self._st("Digite um e-mail válido", WARN); return
        if len(senha) < 6:  self._st("Senha mínima de 6 caracteres", WARN); return

        self._btn.configure(text="Validando...", state="disabled")
        self._st("Verificando no servidor...", MUTED)

        def _run():
            uid, em, err = validate_and_login(codigo, email, senha)
            if uid:
                save_activation(uid, em or email, codigo, senha)
                self.root.after(0, lambda: self._ok(uid, em or email, codigo, senha))
            else:
                self.root.after(0, lambda: self._fail(err or "Código ou credenciais inválidos."))
        threading.Thread(target=_run, daemon=True).start()

    def _ok(self, uid, email, codigo, senha):
        self._st(f"Ativado! Conta: {email}", GREEN)
        self._btn.configure(text="✓ Ativado!", bg=GREEN, state="disabled")
        self.root.after(1200, lambda: (self.root.destroy(), self.on_success(uid, email, codigo, senha)))

    def _fail(self, msg):
        self._st(msg, DANGER)
        self._btn.configure(text="Ativar Agora", state="normal")

    def _st(self, t, c): self._lbl_st.configure(text=t, fg=c)
    def run(self):       self.root.mainloop()


# ══════════════════════════════════════════════════════════════════
#  CANVAS ICONS (substituem lucide/SVG dentro do tkinter)
# ══════════════════════════════════════════════════════════════════
def draw_icon(canvas, name, color, size=18, x=0, y=0):
    """Desenha ícones vetoriais via Canvas primitives."""
    c, s = canvas, size
    cx, cy = x + s//2, y + s//2

    def line(*pts, **kw): c.create_line(*pts, fill=color, width=1.8, capstyle="round", **kw)
    def rect(x1, y1, x2, y2, **kw): c.create_rectangle(x1+x, y1+y, x2+x, y2+y, outline=color, width=1.8, **kw)
    def oval(x1, y1, x2, y2, **kw): c.create_oval(x1+x, y1+y, x2+x, y2+y, outline=color, width=1.8, **kw)
    def poly(*pts, **kw):
        shifted = []
        for i in range(0, len(pts), 2):
            shifted.extend([pts[i]+x, pts[i+1]+y])
        c.create_polygon(*shifted, fill=color, outline=color, **kw)

    if name == "home":
        line(cx-7, cy+6, cx-7, cy-1, cx, cy-7, cx+7, cy-1, cx+7, cy+6)
        line(cx-7, cy-1, cx, cy-7, cx+7, cy-1)
        rect(cx-3, cy+1, cx+3, cy+6)
    elif name == "grid":
        for ox, oy in [(-5,-5),(1,-5),(-5,1),(1,1)]:
            rect(cx+ox, cy+oy, cx+ox+5, cy+oy+5)
    elif name == "music":
        oval(cx-6, cy-2, cx+6, cy+6)
        line(cx+6, cy-6, cx+6, cy+2)
        line(cx-6, cy-6, cx-6, cy+1)
        line(cx-6, cy-6, cx+6, cy-6)
    elif name == "list":
        for oy in [-4, 0, 4]:
            line(cx-6, cy+oy, cx+7, cy+oy)
        c.create_oval(cx+4, cy+2, cx+9, cy+7, outline=color, width=1.8)
        line(cx+9, cy-4, cx+9, cy+4)
    elif name == "monitor":
        rect(cx-8, cy-6, cx+8, cy+4)
        line(cx-4, cy+4, cx-4, cy+8)
        line(cx+4, cy+4, cx+4, cy+8)
        line(cx-5, cy+8, cx+5, cy+8)
        c.create_oval(cx-2, cy-1, cx+2, cy+3, outline=color, width=1.5)
    elif name == "activity":
        line(cx-8, cy, cx-3, cy, cx-1, cy-6, cx+1, cy+6, cx+3, cy, cx+8, cy)
    elif name == "scroll":
        rect(cx-7, cy-8, cx+7, cy+8, fill="", dash=(2,))
        for oy in [-3, 0, 3]:
            line(cx-4, cy+oy, cx+4, cy+oy)
    elif name == "settings":
        oval(cx-4, cy-4, cx+4, cy+4)
        for angle in [0, 60, 120, 180, 240, 300]:
            import math
            a = math.radians(angle)
            lx, ly = cx + 6*math.cos(a), cy + 6*math.sin(a)
            c.create_oval(lx-1.5, ly-1.5, lx+1.5, ly+1.5, fill=color, outline="")
    elif name == "key":
        oval(cx-6, cy-4, cx+2, cy+4)
        line(cx+2, cy, cx+8, cy)
        line(cx+6, cy, cx+6, cy+3)
        line(cx+4, cy, cx+4, cy+3)
    elif name == "play":
        poly(cx-4, cy-6, cx-4, cy+6, cx+7, cy)
    elif name == "stop":
        rect(cx-5, cy-5, cx+5, cy+5, fill=color)
    elif name == "wifi":
        oval(cx-7, cy-3, cx+7, cy+7)
        oval(cx-4, cy, cx+4, cy+5)
        c.create_oval(cx-1.5, cy+3.5, cx+1.5, cy+6.5, fill=color, outline="")
    elif name == "wifi_off":
        line(cx-8, cy-5, cx+8, cy+5)
        oval(cx-5, cy-2, cx+5, cy+6)
    elif name == "chevron_left":
        line(cx+3, cy-6, cx-3, cy, cx+3, cy+6)
    elif name == "chevron_right":
        line(cx-3, cy-6, cx+3, cy, cx-3, cy+6)
    elif name == "web":
        oval(cx-7, cy-7, cx+7, cy+7)
        line(cx, cy-7, cx, cy+7)
        line(cx-7, cy, cx+7, cy)
        c.create_arc(cx-7, cy-7, cx+7, cy+7, start=60, extent=60, style="arc", outline=color, width=1.5)
    elif name == "logout":
        line(cx-2, cy-6, cx-7, cy-6, cx-7, cy+6, cx-2, cy+6)
        line(cx+1, cy-3, cx+6, cy, cx+1, cy+3)
        line(cx-2, cy, cx+6, cy)


# ══════════════════════════════════════════════════════════════════
#  APP PRINCIPAL
# ══════════════════════════════════════════════════════════════════
class App:
    W, H = 960, 620

    NAV = [
        ("Player",    "play",     PURPLE),
        ("All",       "grid",     CYAN),
        ("Playlists", "list",     WARN),
        ("Logs",      "scroll",   GREEN),
        ("Config",    "settings", MUTED2),
        ("Conta",     "key",      PURPLE),
    ]

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PlayAds")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.minsize(860, 540)
        self.root.configure(bg=BG)

        self._page         = "Player"
        self._playlists    = {}
        self._anuncios     = {}
        self._logs         = []
        self._eq_phase     = 0.0
        self._eq_running   = False
        self._all_loop_vars= {}
        self._nav_canvas   = {}    # page → canvas widget for icon
        self._nav_label    = {}    # page → label widget
        self._nav_bar      = {}    # page → bar frame

        self._styles()
        self._build()
        self.root.after(120, self._poll)

    def _styles(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("PA.Horizontal.TProgressbar",
                    troughcolor=SURF3, background=PURPLE, borderwidth=0, thickness=3)
        s.configure("Treeview", background=SURF2, fieldbackground=SURF2,
                    foreground=TEXT, rowheight=32, borderwidth=0, font=FBODY)
        s.configure("Treeview.Heading", background=SURF3, foreground=MUTED2,
                    relief="flat", font=("Segoe UI", 7, "bold"))
        s.map("Treeview", background=[("selected", SURF4)], foreground=[("selected", TEXT)])
        s.configure("Vertical.TScrollbar", troughcolor=SURF2, background=SURF3, borderwidth=0, arrowsize=10)

    # ══ BUILD ════════════════════════════════════════════════════
    def _build(self):
        sb = tk.Frame(self.root, bg=SURF, width=200)
        sb.pack(side="left", fill="y"); sb.pack_propagate(False)
        tk.Frame(self.root, bg=BORDER, width=1).pack(side="left", fill="y")
        main = tk.Frame(self.root, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self._main = main
        self._build_sidebar(sb)
        self._build_pages()
        self._show("Player")

    # ══ SIDEBAR ══════════════════════════════════════════════════
    def _build_sidebar(self, sb):
        # Logo area
        logo_area = tk.Frame(sb, bg=SURF, height=64)
        logo_area.pack(fill="x"); logo_area.pack_propagate(False)
        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x")

        logo_inner = tk.Frame(logo_area, bg=SURF)
        logo_inner.place(relx=0.5, rely=0.5, anchor="center")

        ico_cv = tk.Canvas(logo_inner, width=34, height=34, bg=SURF, highlightthickness=0)
        ico_cv.pack(side="left", padx=(0, 10))
        ico_cv.create_oval(0, 0, 34, 34, fill=PURPLE2, outline="", tags="bg")
        ico_cv.create_polygon(13, 9, 13, 25, 26, 17, fill="white", outline="")
        # Subtle glow ring
        ico_cv.create_oval(1, 1, 33, 33, outline=PURPLE, width=1)

        lf = tk.Frame(logo_inner, bg=SURF)
        lf.pack(side="left")
        tk.Label(lf, text="PlayAds", bg=SURF, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(lf, text="v6.0", bg=SURF, fg=MUTED, font=FMONO2).pack(anchor="w")

        # Status pill
        self._pill_f = tk.Frame(sb, bg=SURF3, height=26)
        self._pill_f.pack(fill="x", padx=12, pady=(8, 4)); self._pill_f.pack_propagate(False)
        self._pill_dot = tk.Label(self._pill_f, text="●", bg=SURF3, fg=MUTED, font=("Segoe UI", 7))
        self._pill_dot.place(x=8, rely=0.5, anchor="w")
        self._pill_txt = tk.Label(self._pill_f, text="Inicializando", bg=SURF3, fg=MUTED, font=FSMALL)
        self._pill_txt.place(x=22, rely=0.5, anchor="w")

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=12)

        # Nav
        nav_f = tk.Frame(sb, bg=SURF)
        nav_f.pack(fill="x", padx=8, pady=(8, 0))

        for page, icon_name, color in self.NAV:
            row = tk.Frame(nav_f, bg=SURF, height=42, cursor="hand2")
            row.pack(fill="x", pady=1); row.pack_propagate(False)

            # Active bar
            bar = tk.Frame(row, bg=SURF, width=3)
            bar.pack(side="left", fill="y")
            self._nav_bar[page] = bar

            # Icon canvas
            ico = tk.Canvas(row, width=28, height=28, bg=SURF, highlightthickness=0)
            ico.pack(side="left", padx=(8, 6), pady=7)
            draw_icon(ico, icon_name, MUTED, size=16, x=6, y=6)
            self._nav_canvas[page] = (ico, icon_name, color)

            # Label
            lbl = tk.Label(row, text=page, bg=SURF, fg=MUTED,
                           font=("Segoe UI", 11), anchor="w", cursor="hand2")
            lbl.pack(side="left", fill="x", expand=True)
            self._nav_label[page] = lbl

            # Hover / click
            def _enter(e, r=row, p=page):
                if self._page != p:
                    self._nav_label[p].configure(fg=TEXT)
            def _leave(e, r=row, p=page):
                if self._page != p:
                    self._nav_label[p].configure(fg=MUTED)
            def _click(e, p=page): self._show(p)

            for w in (row, ico, lbl):
                w.bind("<Enter>", _enter)
                w.bind("<Leave>", _leave)
                w.bind("<Button-1>", _click)

        # Spacer
        tk.Frame(sb, bg=SURF).pack(fill="both", expand=True)
        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x", padx=12)

        # User bottom
        ub = tk.Frame(sb, bg=SURF)
        ub.pack(fill="x", padx=12, pady=10)

        # Avatar
        av = tk.Canvas(ub, width=30, height=30, bg=PURPLE3, highlightthickness=1,
                       highlightbackground=BORDER)
        av.pack(side="left", padx=(0, 8))
        av.create_oval(0, 0, 30, 30, fill=PURPLE3, outline="")
        self._av_txt = av.create_text(15, 15, text="?", fill=TEXT, font=("Segoe UI", 11, "bold"))
        self._av_cv  = av

        info = tk.Frame(ub, bg=SURF)
        info.pack(side="left", fill="x", expand=True)
        self._lbl_uemail = tk.Label(info, text="—", bg=SURF, fg=MUTED2, font=FSMALL, anchor="w")
        self._lbl_uemail.pack(anchor="w")
        self._lbl_ucode = tk.Label(info, text="—", bg=SURF, fg=MUTED, font=FMONO2, anchor="w")
        self._lbl_ucode.pack(anchor="w")

        # Web icon
        web_cv = tk.Canvas(ub, width=22, height=22, bg=SURF, highlightthickness=0, cursor="hand2")
        web_cv.pack(side="right", padx=(4, 0))
        draw_icon(web_cv, "web", MUTED, size=18, x=2, y=2)
        web_cv.bind("<Button-1>", lambda e: webbrowser.open(WEB_URL))
        web_cv.bind("<Enter>",    lambda e: [web_cv.delete("all"), draw_icon(web_cv, "web", PURPLE, 18, 2, 2)])
        web_cv.bind("<Leave>",    lambda e: [web_cv.delete("all"), draw_icon(web_cv, "web", MUTED,  18, 2, 2)])

    def _update_nav(self, page):
        for p, icon_name, color in self.NAV:
            active = (p == page)
            bar    = self._nav_bar[p]
            ico, iname, icol = self._nav_canvas[p]
            lbl    = self._nav_label[p]
            ico.delete("all")
            if active:
                bar.configure(bg=icol)
                draw_icon(ico, iname, icol, size=16, x=6, y=6)
                lbl.configure(fg=TEXT, font=("Segoe UI", 11, "bold"))
            else:
                bar.configure(bg=SURF)
                draw_icon(ico, iname, MUTED, size=16, x=6, y=6)
                lbl.configure(fg=MUTED, font=("Segoe UI", 11))

    # ══ PAGES ════════════════════════════════════════════════════
    def _build_pages(self):
        self._pages = {
            "Player":    self._page_player(self._main),
            "All":       self._page_all(self._main),
            "Playlists": self._page_playlists(self._main),
            "Logs":      self._page_logs(self._main),
            "Config":    self._page_config(self._main),
            "Conta":     self._page_conta(self._main),
        }

    def _show(self, page):
        self._page = page
        for p, f in self._pages.items():
            (f.pack if p == page else f.pack_forget)(fill="both", expand=True) if p == page else f.pack_forget()
        self._update_nav(page)

    def _phdr(self, parent, title, subtitle="", color=PURPLE):
        """Standard page header."""
        h = tk.Frame(parent, bg=SURF, height=52)
        h.pack(fill="x"); h.pack_propagate(False)
        tk.Frame(h, bg=color, width=4).pack(side="left", fill="y")
        tk.Label(h, text=title, bg=SURF, fg=TEXT, font=FH1).pack(side="left", padx=(14, 6), pady=14)
        if subtitle:
            tk.Label(h, text=subtitle, bg=SURF, fg=MUTED, font=FSMALL).pack(side="left", pady=14)
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

    # ══ PAGE: PLAYER ═════════════════════════════════════════════
    def _page_player(self, p):
        f = tk.Frame(p, bg=BG)

        # Top bar
        tb = tk.Frame(f, bg=SURF, height=52); tb.pack(fill="x"); tb.pack_propagate(False)
        tk.Frame(tb, bg=PURPLE, width=4).pack(side="left", fill="y")
        tk.Label(tb, text="Player", bg=SURF, fg=PURPLE, font=("Segoe UI", 13, "bold")).pack(side="left", padx=14)
        self._lbl_conn_dot = tk.Label(tb, text="●", bg=SURF, fg=MUTED, font=("Segoe UI", 8))
        self._lbl_conn_dot.pack(side="right", padx=(0, 6))
        self._lbl_conn = tk.Label(tb, text="Inicializando...", bg=SURF, fg=MUTED, font=FSMALL)
        self._lbl_conn.pack(side="right")
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(f, bg=BG)
        body.pack(fill="both", expand=True)

        # Left
        left = tk.Frame(body, bg=BG, width=280)
        left.pack(side="left", fill="y", padx=20, pady=18)
        left.pack_propagate(False)

        # Artwork circle
        art_outer = tk.Frame(left, bg=SURF3)
        art_outer.pack(pady=(0, 14))
        self._art_cv = tk.Canvas(art_outer, width=116, height=116, bg=SURF3, highlightthickness=0)
        self._art_cv.pack()
        self._draw_art(idle=True)

        # EQ row
        eq_row = tk.Frame(left, bg=BG); eq_row.pack(fill="x", pady=(0, 6))
        self._eq_cv = tk.Canvas(eq_row, width=30, height=14, bg=BG, highlightthickness=0)
        self._eq_cv.pack(side="left")
        self._lbl_tag = tk.Label(eq_row, text="AGUARDANDO", bg=BG, fg=MUTED, font=("Segoe UI", 7, "bold"))
        self._lbl_tag.pack(side="left", padx=6)
        self._draw_eq(True)

        self._lbl_title = tk.Label(left, text="Nenhuma mídia", bg=BG, fg=TEXT,
                                   font=("Segoe UI", 12, "bold"), anchor="w", wraplength=260, justify="left")
        self._lbl_title.pack(fill="x", pady=(0, 2))
        self._lbl_meta = tk.Label(left, text="—", bg=BG, fg=MUTED, font=FSMALL, anchor="w")
        self._lbl_meta.pack(fill="x", pady=(0, 10))

        self._prog_var = tk.DoubleVar(value=0)
        ttk.Progressbar(left, variable=self._prog_var, maximum=100, style="PA.Horizontal.TProgressbar").pack(fill="x")

        tf = tk.Frame(left, bg=BG); tf.pack(fill="x", pady=(2, 10))
        self._lbl_elapsed = tk.Label(tf, text="0:00", bg=BG, fg=MUTED, font=FMONO)
        self._lbl_elapsed.pack(side="left")

        # Stop button
        stop_btn = tk.Button(left, text="  ⏹  PARAR  ", bg="#1a080e", fg=DANGER,
                             font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                             padx=0, pady=10, cursor="hand2",
                             activebackground="#2a0f18", activeforeground=DANGER,
                             command=self._cmd_stop)
        stop_btn.pack(fill="x")
        stop_btn.bind("<Enter>", lambda e: stop_btn.configure(bg="#2a0f18"))
        stop_btn.bind("<Leave>", lambda e: stop_btn.configure(bg="#1a080e"))

        # Divider
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y", pady=12)

        # Right
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=18, pady=18)

        # Stats
        sc = tk.Frame(right, bg=BG); sc.pack(fill="x", pady=(0, 12))
        sc.columnconfigure((0, 1), weight=1)
        self._s_pl   = self._stat(sc, "PLAYLIST", "—",     0, 0)
        self._s_tr   = self._stat(sc, "FAIXAS",   "0",     1, 0)
        self._s_st   = self._stat(sc, "STATUS",   "Pronto", 0, 1, GREEN)
        self._s_loop = self._stat(sc, "LOOP",     "—",     1, 1)

        # Volume card
        vc = self._card(right)
        vc.pack(fill="x", pady=(0, 8))
        tk.Label(vc, text="VOLUME", bg=SURF3, fg=MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        cfg = load_config()
        for lbl, attr, color, key in [
            ("Anúncio",   "_lbl_vol_ad", PURPLE, "volume_anuncio"),
            ("Outros apps", "_lbl_vol_ot", WARN,   "volume_outros"),
        ]:
            vr = tk.Frame(vc, bg=SURF3); vr.pack(fill="x", padx=10, pady=(0, 4))
            tk.Label(vr, text=lbl, bg=SURF3, fg=MUTED2, font=FSMALL).pack(side="left")
            lv = tk.Label(vr, text=f"{cfg.get(key, '—')}%", bg=SURF3, fg=color, font=FMONO)
            lv.pack(side="right"); setattr(self, attr, lv)

        # Warnings
        if not HAS_PYCAW:
            self._warn_lbl(right, "pycaw não instalado — duck de volume desativado")
        if not HAS_YTDLP:
            self._warn_lbl(right, "yt-dlp não instalado — YouTube indisponível")

        # Cache card
        cc = self._card(right); cc.pack(fill="x", pady=(0, 8))
        tk.Label(cc, text="CACHE OFFLINE", bg=SURF3, fg=MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        cr = tk.Frame(cc, bg=SURF3); cr.pack(fill="x", padx=10, pady=(0, 6))
        self._lbl_cache = tk.Label(cr, text="—", bg=SURF3, fg=MUTED2, font=FSMALL)
        self._lbl_cache.pack(side="left")
        self._mkbtn(cr, "Sincronizar", SURF4, PURPLE, self._cmd_precache, py=3).pack(side="right")

        # Log
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", pady=(0, 4))
        self._logtxt = tk.Text(right, bg="#07060f", fg=MUTED, font=("Consolas", 7),
                               relief="flat", state="disabled", wrap="word", height=7)
        self._logtxt.pack(fill="both", expand=True)
        for tag, col in [("OK", GREEN), ("ERR", DANGER), ("WARN", WARN), ("INFO", MUTED), ("PL", PURPLE), ("CYAN", CYAN)]:
            self._logtxt.tag_config(tag, foreground=col)
        return f

    # ══ PAGE: ALL ════════════════════════════════════════════════
    def _page_all(self, p):
        f = tk.Frame(p, bg=BG)

        # Header
        hdr = tk.Frame(f, bg=SURF, height=52); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=CYAN, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="Todas as Mídias", bg=SURF, fg=TEXT, font=FH1).pack(side="left", padx=14)
        self._lbl_all_count = tk.Label(hdr, text="0 faixas", bg=SURF, fg=MUTED, font=FSMALL)
        self._lbl_all_count.pack(side="right", padx=14)
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        # Search bar
        sb_f = tk.Frame(f, bg=BG); sb_f.pack(fill="x", padx=12, pady=(10, 0))
        so = tk.Frame(sb_f, bg=BORDER); so.pack(side="left", fill="x", expand=True)
        si = tk.Frame(so, bg=SURF3); si.pack(fill="x", padx=1, pady=1)
        tk.Label(si, text="  🔍", bg=SURF3, fg=MUTED, font=FSMALL).pack(side="left")
        self._all_q = tk.StringVar()
        self._all_q.trace_add("write", lambda *_: self._refresh_all())
        tk.Entry(si, textvariable=self._all_q, bg=SURF3, fg=TEXT, insertbackground=PURPLE,
                 font=FBODY, relief="flat", bd=7).pack(side="left", fill="x", expand=True)

        # Table header
        thead = tk.Frame(f, bg=SURF3); thead.pack(fill="x", padx=12, pady=(8, 0))
        for txt, w in [("#", 4), ("Nome", 26), ("Tipo", 8), ("Loops", 10), ("Prox.", 8), ("Ação", 12)]:
            tk.Label(thead, text=txt, bg=SURF3, fg=MUTED, font=("Segoe UI", 7, "bold"),
                     width=w, anchor="center" if txt != "Nome" else "w").pack(side="left", padx=3, pady=5)

        # Scrollable list
        wrap = tk.Frame(f, bg=BG); wrap.pack(fill="both", expand=True, padx=12, pady=(2, 8))
        canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        self._all_frame = tk.Frame(canvas, bg=BG)
        self._all_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._all_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
        return f

    def _next_schedule(self, url):
        now_t = datetime.now().strftime("%H:%M")
        candidates = []
        for pl in ST.local_playlists.values():
            if not isinstance(pl, dict) or not pl.get("ativa"): continue
            for item in (pl.get("itens") or []):
                if isinstance(item, dict) and item.get("url") == url and item.get("horario"):
                    candidates.append(item["horario"])
        if not candidates: return ""
        future = [h for h in candidates if h > now_t]
        return min(future) if future else min(candidates)

    def _refresh_all(self):
        for w in self._all_frame.winfo_children(): w.destroy()
        self._all_loop_vars.clear()

        q = self._all_q.get().lower() if hasattr(self, "_all_q") else ""
        items = sorted(self._anuncios.items(), key=lambda x: x[1].get("nome", "").lower())
        if q: items = [(k, v) for k, v in items if q in v.get("nome", "").lower()]

        self._lbl_all_count.configure(text=f"{len(items)} faixa{'s' if len(items) != 1 else ''}")

        if not items:
            tk.Label(self._all_frame,
                     text="Nenhuma mídia encontrada. Adicione anúncios no painel web." if not q else "Nenhum resultado.",
                     bg=BG, fg=MUTED, font=FBODY).pack(pady=40)
            return

        for i, (aid, a) in enumerate(items):
            nome     = a.get("nome", "—")
            url      = a.get("url", "")
            tipo     = a.get("tipo", "")
            yt       = "youtube" in url.lower() or "youtu.be" in url.lower()
            proximo  = self._next_schedule(url)
            rbg      = SURF3 if i % 2 == 0 else SURF2

            row = tk.Frame(self._all_frame, bg=rbg, height=44)
            row.pack(fill="x"); row.pack_propagate(False)

            tk.Label(row, text=f"{i+1:02d}", bg=rbg, fg=MUTED, font=FMONO, width=4, anchor="center").pack(side="left", padx=(6,2))

            # Icon + name
            icon_cv = tk.Canvas(row, width=22, height=22, bg=rbg, highlightthickness=0)
            icon_cv.pack(side="left", padx=(2, 4), pady=11)
            draw_icon(icon_cv, "music", DANGER if yt else PURPLE, size=16, x=3, y=3)

            tk.Label(row, text=nome, bg=rbg, fg=TEXT, font=FBODY, width=26, anchor="w").pack(side="left", padx=2)

            # Type badge
            bb = DANGER if yt else PURPLE; btxt = "YT" if yt else ("WAV" if "wav" in tipo.lower() else "MP3")
            bf = tk.Frame(row, bg=SURF4, padx=7, pady=2); bf.pack(side="left", padx=4)
            tk.Label(bf, text=btxt, bg=SURF4, fg=bb, font=("Segoe UI", 7, "bold")).pack()

            # Loop stepper
            loop_v = tk.IntVar(value=1); self._all_loop_vars[aid] = loop_v
            sf = tk.Frame(row, bg=SURF4); sf.pack(side="left", padx=6)
            for txt, cmd in [("−", lambda v=loop_v: v.set(max(1, v.get()-1))),
                             ("+", lambda v=loop_v: v.set(min(99, v.get()+1)))]:
                tk.Button(sf, text=txt, bg=SURF4, fg=PURPLE, relief="flat", bd=0,
                          font=("Segoe UI", 12), width=2, cursor="hand2", command=cmd).pack(side="left")
                if txt == "−":
                    tk.Label(sf, textvariable=loop_v, bg=SURF4, fg=TEXT, font=FMONO, width=2).pack(side="left")
            tk.Label(sf, text="×", bg=SURF4, fg=MUTED, font=FSMALL).pack(side="left", padx=(0, 3))

            # Schedule
            tk.Label(row, text=proximo or "—", bg=rbg, fg=CYAN if proximo else MUTED,
                     font=FMONO, width=7, anchor="center").pack(side="left", padx=4)

            # Play button
            def _play(an=a, v=loop_v):
                cfg = load_config()
                pl  = {"nome": f"▶ {an.get('nome','?')}", "temp": True,
                       "itens": [{"nome": an.get("nome","?"), "url": an.get("url",""),
                                  "loops": v.get(), "tipo": an.get("tipo",""), "horario": None}]}
                log.info(f"All → Tocar: {an.get('nome')} x{v.get()}")
                start_playlist(pl, cfg, force=True, loops_override=v.get())
                self._show("Player")

            pb = tk.Button(row, text="▶ Tocar", bg=PURPLE2, fg=TEXT,
                           font=("Segoe UI", 8, "bold"), relief="flat", bd=0,
                           padx=12, pady=5, cursor="hand2",
                           activebackground=PURPLE3, command=_play)
            pb.pack(side="left", padx=8)
            pb.bind("<Enter>", lambda e, b=pb: b.configure(bg=PURPLE3))
            pb.bind("<Leave>", lambda e, b=pb: b.configure(bg=PURPLE2))

            # Row hover
            def _hl(e, r=row, bg=rbg):
                hl = self._lighten(bg)
                r.configure(bg=hl)
                for ch in r.winfo_children():
                    try:
                        if ch.cget("bg") == bg: ch.configure(bg=hl)
                    except: pass
            def _uhl(e, r=row, bg=rbg):
                r.configure(bg=bg)
                for ch in r.winfo_children():
                    try: ch.configure(bg=bg)
                    except: pass
            row.bind("<Enter>", _hl); row.bind("<Leave>", _uhl)

    # ══ PAGE: PLAYLISTS ══════════════════════════════════════════
    def _page_playlists(self, p):
        f = tk.Frame(p, bg=BG)
        self._phdr(f, "Playlists", "Duplo clique para tocar", WARN)

        wrap = tk.Frame(f, bg=SURF2, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True, padx=12, pady=10)

        cols = ("nome", "faixas", "status", "acao")
        self._tv_pl = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        sb2 = ttk.Scrollbar(wrap, orient="vertical", command=self._tv_pl.yview)
        self._tv_pl.configure(yscrollcommand=sb2.set)
        self._tv_pl.heading("nome",   text="Nome da Playlist")
        self._tv_pl.heading("faixas", text="Faixas")
        self._tv_pl.heading("status", text="Status")
        self._tv_pl.heading("acao",   text="Ação")
        self._tv_pl.column("nome",   width=260, anchor="w")
        self._tv_pl.column("faixas", width=60,  anchor="center")
        self._tv_pl.column("status", width=90,  anchor="center")
        self._tv_pl.column("acao",   width=110, anchor="center")
        self._tv_pl.tag_configure("ativa",   foreground=GREEN)
        self._tv_pl.tag_configure("inativa", foreground=MUTED)
        self._tv_pl.tag_configure("playing", foreground=PURPLE, font=FTIT)
        self._tv_pl.bind("<Double-1>",  self._pl_dbl)
        self._tv_pl.bind("<Button-1>",  self._pl_click)
        sb2.pack(side="right", fill="y")
        self._tv_pl.pack(fill="both", expand=True)
        return f

    # ══ PAGE: LOGS ═══════════════════════════════════════════════
    def _page_logs(self, p):
        f = tk.Frame(p, bg=BG)
        hdr = tk.Frame(f, bg=SURF, height=52); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=GREEN, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="Logs", bg=SURF, fg=TEXT, font=FH1).pack(side="left", padx=14)
        self._lbl_log_count = tk.Label(hdr, text="0 registros", bg=SURF, fg=MUTED, font=FSMALL)
        self._lbl_log_count.pack(side="right", padx=14)
        btn_clear = tk.Button(hdr, text="Limpar", bg=SURF, fg=MUTED, relief="flat",
                              font=FSMALL, cursor="hand2", command=self._clear_log_ui)
        btn_clear.pack(side="right")
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        # Log table via Treeview for best performance
        wrap = tk.Frame(f, bg=SURF2, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True, padx=12, pady=10)
        cols = ("time", "status", "msg")
        self._tv_log = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="none")
        sb_l = ttk.Scrollbar(wrap, orient="vertical", command=self._tv_log.yview)
        self._tv_log.configure(yscrollcommand=sb_l.set)
        self._tv_log.heading("time",   text="Horário")
        self._tv_log.heading("status", text="Status")
        self._tv_log.heading("msg",    text="Mensagem")
        self._tv_log.column("time",   width=120, anchor="center")
        self._tv_log.column("status", width=80,  anchor="center")
        self._tv_log.column("msg",    width=500, anchor="w")
        self._tv_log.tag_configure("ok",    foreground=GREEN)
        self._tv_log.tag_configure("error", foreground=DANGER)
        self._tv_log.tag_configure("info",  foreground=MUTED2)
        sb_l.pack(side="right", fill="y")
        self._tv_log.pack(fill="both", expand=True)
        return f

    def _clear_log_ui(self):
        for row in self._tv_log.get_children(): self._tv_log.delete(row)
        self._lbl_log_count.configure(text="0 registros")

    def _refresh_logs(self, logs_dict):
        """Renderiza logs do Firebase na treeview."""
        tv = self._tv_log
        for row in tv.get_children(): tv.delete(row)
        entries = sorted(
            [(k, v) for k, v in logs_dict.items() if isinstance(v, dict)],
            key=lambda x: x[1].get("timestamp", 0), reverse=True
        )[:150]
        for _, l in entries:
            ts  = l.get("timestamp", 0)
            ts_str = datetime.fromtimestamp(ts/1000).strftime("%d/%m %H:%M:%S") if ts else "—"
            st  = l.get("status", "info")
            msg = l.get("mensagem", "")
            tv.insert("", "end", values=(ts_str, st.upper(), msg), tags=(st,))
        self._lbl_log_count.configure(text=f"{len(entries)} registro{'s' if len(entries) != 1 else ''}")

    # ══ PAGE: CONFIG ═════════════════════════════════════════════
    def _page_config(self, p):
        f = tk.Frame(p, bg=BG)
        self._phdr(f, "Configurações", "", MUTED2)

        body = tk.Frame(f, bg=BG); body.pack(fill="both", expand=True, padx=28, pady=20)

        tk.Label(body, text="Configurações do Player", bg=BG, fg=TEXT, font=FH2).pack(anchor="w", pady=(0, 16))

        cfg = load_config()
        fields = [
            ("Nome do Player",     "player_nome",    "Ex: Loja Centro"),
            ("Volume anúncio (%)", "volume_anuncio", "0–100"),
            ("Volume outros (%)",  "volume_outros",  "0–100 (ao tocar anúncio)"),
            ("Fade duck (ms)",     "duck_fade_ms",   "500–3000"),
        ]
        self._cfg_vars = {}
        for label, key, hint in fields:
            row = tk.Frame(body, bg=BG); row.pack(fill="x", pady=6)
            lf2 = tk.Frame(row, bg=BG); lf2.pack(side="left", fill="y")
            tk.Label(lf2, text=label, bg=BG, fg=TEXT, font=FBODY, width=22, anchor="w").pack(anchor="w")
            tk.Label(lf2, text=hint,  bg=BG, fg=MUTED, font=FSMALL, anchor="w").pack(anchor="w")
            var = tk.StringVar(value=str(cfg.get(key, "")))
            self._cfg_vars[key] = var
            eo = tk.Frame(row, bg=BORDER); eo.pack(side="right", fill="x", expand=True)
            ei = tk.Frame(eo, bg=SURF3);   ei.pack(fill="x", padx=1, pady=1)
            tk.Entry(ei, textvariable=var, bg=SURF3, fg=TEXT, insertbackground=PURPLE,
                     font=FMONO, relief="flat", bd=8).pack(fill="x")

        save_btn = tk.Button(body, text="  Salvar Configurações  ", bg=PURPLE2, fg=TEXT,
                             font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                             padx=20, pady=10, cursor="hand2",
                             activebackground=PURPLE3, command=self._save_cfg)
        save_btn.pack(anchor="w", pady=(20, 0))
        save_btn.bind("<Enter>", lambda e: save_btn.configure(bg=PURPLE3))
        save_btn.bind("<Leave>", lambda e: save_btn.configure(bg=PURPLE2))
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
        self._lbl_vol_ad.configure(text=f"{nc.get('volume_anuncio', 100)}%")
        self._lbl_vol_ot.configure(text=f"{nc.get('volume_outros', 10)}%")
        messagebox.showinfo("Salvo", "Configurações salvas com sucesso!")

    # ══ PAGE: CONTA ══════════════════════════════════════════════
    def _page_conta(self, p):
        f = tk.Frame(p, bg=BG)
        self._phdr(f, "Conta", "Informações de ativação", PURPLE)

        body = tk.Frame(f, bg=BG); body.pack(fill="both", expand=True, padx=28, pady=24)

        # Info card
        card = self._card(body); card.pack(fill="x", pady=(0, 20))
        tk.Label(card, text="CONTA ATIVADA", bg=SURF3, fg=PURPLE,
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=14, pady=(12, 6))

        for label, attr in [("E-mail", "_act_email"), ("Código", "_act_codigo"), ("Status", "_act_status")]:
            row = tk.Frame(card, bg=SURF3); row.pack(fill="x", padx=14, pady=4)
            tk.Label(row, text=label, bg=SURF3, fg=MUTED, font=FSMALL, width=10, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="—", bg=SURF3, fg=TEXT, font=FMONO)
            lbl.pack(side="left"); setattr(self, attr, lbl)
        tk.Frame(card, bg=SURF3, height=10).pack()

        tk.Label(body,
                 text="Para usar outro código, clique em Desconectar. Todos os dados locais\n"
                      "serão apagados e o software será encerrado para nova ativação.",
                 bg=BG, fg=MUTED, font=FSMALL, justify="left").pack(anchor="w", pady=(0, 20))

        disc_btn = tk.Button(body, text="  Desconectar e Redefinir  ", bg="#1a080e", fg=DANGER,
                             font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                             padx=20, pady=10, cursor="hand2",
                             activebackground="#2a0f18", command=self._cmd_disconnect)
        disc_btn.pack(anchor="w")
        disc_btn.bind("<Enter>", lambda e: disc_btn.configure(bg="#2a0f18"))
        disc_btn.bind("<Leave>", lambda e: disc_btn.configure(bg="#1a080e"))
        return f

    # ══ HELPERS ══════════════════════════════════════════════════
    def _card(self, parent):
        return tk.Frame(parent, bg=SURF3, highlightbackground=BORDER, highlightthickness=1)

    def _stat(self, parent, label, val, col, row, vc=None):
        f = self._card(parent)
        f.grid(row=row, column=col, sticky="ew", padx=3, pady=3)
        tk.Label(f, text=label, bg=SURF3, fg=MUTED, font=("Segoe UI", 7, "bold")).pack(pady=(6, 0))
        lbl = tk.Label(f, text=val, bg=SURF3, fg=vc or TEXT, font=("Segoe UI", 11, "bold"))
        lbl.pack(pady=(0, 6)); return lbl

    def _mkbtn(self, parent, text, bg, fg, cmd, px=12, py=6):
        b = tk.Button(parent, text=text, bg=bg, fg=fg, font=FTIT, relief="flat", bd=0,
                      padx=px, pady=py, cursor="hand2", activebackground=bg, activeforeground=fg, command=cmd)
        b.bind("<Enter>", lambda e: b.configure(bg=self._lighten(bg)))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def _warn_lbl(self, parent, msg):
        tk.Label(parent, text=f"⚠ {msg}", bg=BG, fg=WARN, font=FSMALL).pack(anchor="w", pady=(0, 2))

    @staticmethod
    def _lighten(h):
        try:
            h6 = h.replace("#", "")[:6]
            r, g, b = int(h6[0:2], 16), int(h6[2:4], 16), int(h6[4:6], 16)
            return "#{:02x}{:02x}{:02x}".format(min(255, r+24), min(255, g+24), min(255, b+24))
        except: return h

    # ── EQ / Artwork ─────────────────────────────────────────────
    def _draw_art(self, idle=True):
        import math
        c = self._art_cv; c.delete("all")
        c.create_rectangle(0, 0, 116, 116, fill=SURF3, outline="")
        if idle:
            c.create_oval(38, 38, 78, 78, fill=SURF4, outline=BORDER, width=2)
            c.create_oval(50, 50, 66, 66, fill=SURF2, outline="")
        else:
            p = self._eq_phase
            for i, (r, col) in enumerate([(44, "#4c1d95"), (30, "#7c3aed"), (18, "#9b59f5")]):
                wave = int(math.sin(p + i) * 4)
                c.create_oval(58-r+wave, 58-r-wave, 58+r+wave, 58+r+wave, outline=col, width=2)
            c.create_oval(48, 48, 68, 68, fill=PURPLE2, outline="")
            c.create_polygon(54, 44, 54, 72, 76, 58, fill="white", outline="")

    def _draw_eq(self, idle=True):
        c = self._eq_cv; c.delete("all")
        col = MUTED if idle else PURPLE
        p   = self._eq_phase
        import math
        hs = [3, 6, 4, 8] if idle else [2 + int(11 * abs(math.sin(p + i * 0.9))) for i in range(4)]
        for i, h in enumerate(hs):
            c.create_rectangle(i*7, 14-h, i*7+5, 14, fill=col, outline="")

    def _tick_eq(self):
        if not self._eq_running: return
        self._eq_phase += 0.22
        self._draw_eq(False); self._draw_art(False)
        self.root.after(100, self._tick_eq)

    def _start_eq(self):
        if not self._eq_running: self._eq_running = True; self._tick_eq()

    def _stop_eq(self):
        self._eq_running = False; self._draw_eq(True); self._draw_art(True)

    # ── Queue page ────────────────────────────────────────────────
    def _render_queue(self, itens, active=-1):
        # Displayed in Logs page or main — now we use a floating queue in Player
        pass  # queue shown in Fila page below

    # ── Playlists treeview ────────────────────────────────────────
    def _refresh_playlists(self):
        tv = self._tv_pl
        for row in tv.get_children(): tv.delete(row)
        for pl_id, pl in self._playlists.items():
            if not isinstance(pl, dict): continue
            nome   = pl.get("nome", "—")
            faixas = len(pl.get("itens") or [])
            ativa  = pl.get("ativa", False)
            tag    = "playing" if ST.current_pl_id == pl_id else ("ativa" if ativa else "inativa")
            tv.insert("", "end",
                      values=(nome, faixas, "Ativa" if ativa else "Inativa", "▶ Tocar"),
                      tags=(tag, pl_id))

    def _pl_click(self, e):
        tv = self._tv_pl
        col = tv.identify_column(e.x); rid = tv.identify_row(e.y)
        if not rid: return
        if col == "#4":
            tags = tv.item(rid, "tags"); pl_id = tags[1] if len(tags) > 1 else None
            if pl_id and pl_id in self._playlists: self._ask_loops(pl_id)

    def _pl_dbl(self, e):
        tv = self._tv_pl; sel = tv.selection()
        if not sel: return
        tags = tv.item(sel[0], "tags"); pl_id = tags[1] if len(tags) > 1 else None
        if pl_id and pl_id in self._playlists: self._ask_loops(pl_id)

    def _ask_loops(self, pl_id):
        pl = self._playlists.get(pl_id)
        if not pl: return
        win = tk.Toplevel(self.root)
        win.title("Tocar Agora")
        win.geometry("300x200")
        win.configure(bg=SURF)
        win.resizable(False, False)
        win.grab_set(); win.transient(self.root)

        tk.Label(win, text="Quantas vezes repetir?", bg=SURF, fg=TEXT, font=FH2).pack(pady=(18, 4))
        tk.Label(win, text=pl.get("nome", ""), bg=SURF, fg=MUTED, font=FSMALL).pack(pady=(0, 12))

        sf = tk.Frame(win, bg=SURF); sf.pack(pady=(0, 16))
        loops_v = tk.IntVar(value=1)
        for txt, cmd in [("−", lambda: loops_v.set(max(1, loops_v.get()-1))),
                         ("+", lambda: loops_v.set(min(99, loops_v.get()+1)))]:
            tk.Button(sf, text=txt, bg=SURF3, fg=TEXT, relief="flat", bd=0,
                      font=("Segoe UI", 15), padx=12, pady=3, cursor="hand2", command=cmd).pack(side="left", padx=3)
            if txt == "−":
                tk.Label(sf, textvariable=loops_v, bg=SURF3, fg=PURPLE,
                         font=("Segoe UI", 18, "bold"), width=3, pady=4).pack(side="left", padx=2)

        def _go():
            n = loops_v.get(); win.destroy()
            cfg = load_config(); ST.current_pl_id = pl_id
            start_playlist(pl, cfg, True, loops_override=n)
            self._show("Player")

        gb = tk.Button(win, text="  Tocar Agora  ", bg=PURPLE2, fg=TEXT,
                       font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
                       padx=24, pady=10, cursor="hand2",
                       activebackground=PURPLE3, command=_go)
        gb.pack()
        gb.bind("<Enter>", lambda e: gb.configure(bg=PURPLE3))
        gb.bind("<Leave>", lambda e: gb.configure(bg=PURPLE2))

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
                                   "Isso irá:\n\n"
                                   "• Apagar activation.json\n"
                                   "• Apagar todos os JSONs locais\n"
                                   "• Limpar cache de áudio\n\n"
                                   "Deseja continuar?"):
            return
        stop_all()
        clear_all_local()
        self.root.destroy()

    def _update_cache_lbl(self):
        idx   = load_cache_index()
        total = sum(Path(e["path"]).stat().st_size for e in idx.values() if Path(e["path"]).exists()) / 1048576
        self._lbl_cache.configure(text=f"{len(idx)} arquivo(s) · {total:.1f} MB")

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

    # ══ POLL ═════════════════════════════════════════════════════
    def _poll(self):
        try:
            while True:
                e = EVQ.get_nowait(); t = e["t"]

                if t == "log":
                    msg = e["msg"]; lvl = e.get("lvl", "INFO")
                    self._logtxt.configure(state="normal")
                    tag = ("PL"   if any(x in msg for x in ("▶", "✓", "Playlist", "Concluí")) else
                           "OK"   if any(x in msg for x in ("Firebase", "ativo", "SSE", "Cache")) else
                           "CYAN" if "Tocando" in msg else
                           "ERR"  if lvl == "ERROR" else
                           "WARN" if lvl in ("WARNING", "WARN") else "INFO")
                    self._logtxt.insert("end", msg + "\n", tag)
                    self._logtxt.see("end")
                    lines = int(self._logtxt.index("end-1c").split(".")[0])
                    if lines > 400: self._logtxt.delete("1.0", f"{lines-400}.0")
                    self._logtxt.configure(state="disabled")

                elif t == "now_playing":
                    nome, lp, tl, pl = e["nome"], e["loop"], e["total"], e["pl"]
                    self._lbl_tag.configure(text="▶ REPRODUZINDO", fg=PURPLE)
                    self._lbl_title.configure(text=nome)
                    ls = f"Loop {lp}/{tl}" if tl > 1 else ""
                    self._lbl_meta.configure(text=f"{pl}  {ls}".strip() if pl else (ls or "—"))
                    self._s_st.configure(text="Tocando", fg=WARN)
                    self._s_loop.configure(text=f"{lp}/{tl}" if tl > 1 else "1×", fg=PURPLE)
                    self._update_status("Reproduzindo", WARN)
                    self._start_eq(); self._prog_var.set(0)

                elif t == "pl_start":
                    itens = e["itens"]
                    self._s_pl.configure(text=(e["nome"][:14] + "…") if len(e["nome"]) > 14 else e["nome"])
                    self._s_tr.configure(text=str(len(itens)))
                    self._refresh_playlists()

                elif t == "pl_end":
                    self._stop_eq()
                    self._lbl_tag.configure(text="✓ CONCLUÍDO", fg=GREEN)
                    self._s_st.configure(text="Pronto", fg=GREEN)
                    self._s_loop.configure(text="—", fg=MUTED)
                    self._update_status("Pronto", GREEN)
                    self._prog_var.set(100)
                    self._refresh_playlists()

                elif t == "stopped":
                    self._stop_eq()
                    self._lbl_tag.configure(text="AGUARDANDO", fg=MUTED)
                    self._lbl_title.configure(text="Nenhuma mídia")
                    self._lbl_meta.configure(text="—")
                    self._s_st.configure(text="Pronto", fg=GREEN)
                    self._s_loop.configure(text="—", fg=MUTED)
                    self._update_status("Pronto", GREEN)
                    self._prog_var.set(0)
                    ST.current_pl_id = ""
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
                    self._update_cache_lbl()

                elif t == "fb_logs":
                    self._refresh_logs(e.get("logs", {}))

                elif t == "cache_done":
                    self._update_cache_lbl()

        except queue.Empty: pass

        if ST.playing and ST.play_ts:
            el = time.time() - ST.play_ts
            self._lbl_elapsed.configure(text=f"{int(el//60)}:{int(el%60):02d}")
            cur = self._prog_var.get()
            if cur < 50 or (50 <= cur < 99):
                self._prog_var.set(min(99, cur + 0.08))

        self.root.after(120, self._poll)

    def run(self): self.root.mainloop()


# ══════════════════════════════════════════════════════════════════
#  BOOTSTRAP
# ══════════════════════════════════════════════════════════════════
def start_backend(app, senha):
    if not start_firebase(senha):
        ev("firebase_err"); return

    cfg = load_config()
    load_local_data()

    if ST.local_playlists or ST.local_anuncios:
        ev("fb_data", playlists=ST.local_playlists, anuncios=ST.local_anuncios)

    # Carrega logs locais
    if LOCAL_LOG_FILE.exists():
        try:
            logs = json.loads(LOCAL_LOG_FILE.read_text(encoding="utf-8"))
            if logs: ev("fb_logs", logs=logs)
        except: pass

    fb_status(None)
    fb_log(f"PlayAds v6.0 iniciado — {ST.email}", "ok")
    ev("firebase_ok")

    threading.Thread(target=heartbeat,       args=(cfg,), daemon=True).start()
    threading.Thread(target=check_schedules, args=(cfg,), daemon=True).start()
    threading.Thread(target=setup_listeners, args=(cfg,), daemon=True).start()
    threading.Thread(target=precache_all,    daemon=True).start()

    cfg2 = load_config()
    app._lbl_vol_ad.configure(text=f"{cfg2.get('volume_anuncio', 100)}%")
    app._lbl_vol_ot.configure(text=f"{cfg2.get('volume_outros', 10)}%")
    app.set_account()

    log.info(f"Conta: {ST.email} | Código: {ST.codigo}")
    log.info("pycaw: "  + ("ativo ✓" if HAS_PYCAW  else "não instalado"))
    log.info("yt-dlp: " + ("ativo ✓" if HAS_YTDLP  else "não instalado"))


def main():
    act = load_activation()

    def on_activated(uid, email, codigo, senha):
        ST.uid    = uid
        ST.email  = email
        ST.codigo = codigo
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