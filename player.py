#!/usr/bin/env python3
"""
PlayAds Player v5.1
Sistema de ativação por código único + isolamento por conta Firebase.
"""

import os, sys, json, time, threading, platform, logging, queue, hashlib, webbrowser
from datetime import datetime
from pathlib import Path

# ── Deps ──────────────────────────────────────────────────────────
try:
    import firebase_admin
    from firebase_admin import credentials, db as rtdb
except ImportError:
    print("ERRO: pip install firebase-admin"); sys.exit(1)

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
TEXT    = "#f0eeff"
MUTED   = "#7a7490"
MUTED2  = "#a89ec0"
DANGER  = "#f43f5e"
WARN    = "#f59e0b"
GREEN   = "#10b981"

FONT_TITLE = ("Segoe UI", 10, "bold")
FONT_BODY  = ("Segoe UI", 9)
FONT_SMALL = ("Segoe UI", 8)
FONT_MONO  = ("Consolas", 9)

# ── Caminhos ──────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
CACHE_DIR   = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_INDEX = CACHE_DIR / "index.json"
ACTIVATION_FILE = BASE_DIR / "activation.json"   # uid + email + codigo salvos

# ── Credenciais Firebase embutidas (fixas) ────────────────────────
# Estas credenciais são do projeto compartilhado — o isolamento
# é feito lendo apenas /users/{uid}/ do usuário ativado.
FIREBASE_WEB_API_KEY = "AIzaSyBgwB_2syWdyK5Wc0E9rJIlDnXjwTf1OWE"
FIREBASE_DB_URL      = "https://anucio-web-default-rtdb.firebaseio.com"
CRED_FILE            = BASE_DIR / "serviceAccountKey.json"
WEB_URL              = "https://anucio-web.web.app"   # ← altere após deploy

# ── Config local (volume, player_id, etc) ────────────────────────
CONFIG_FILE = BASE_DIR / "playads_config.json"
DEFAULT_CONFIG = {
    "player_nome": "Player Principal",
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

# ── Ativação ──────────────────────────────────────────────────────
def load_activation():
    """Retorna dict {uid, email, codigo} ou None."""
    if ACTIVATION_FILE.exists():
        try:
            return json.loads(ACTIVATION_FILE.read_text(encoding="utf-8"))
        except: pass
    return None

def save_activation(uid, email, codigo):
    ACTIVATION_FILE.write_text(
        json.dumps({"uid": uid, "email": email, "codigo": codigo},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")

def clear_activation():
    if ACTIVATION_FILE.exists():
        ACTIVATION_FILE.unlink()

def validate_code_firebase(codigo: str):
    """
    Busca /codigos/{codigo}/uid no Firebase.
    Retorna (uid, email) se encontrado, ou (None, None).
    Usa a REST API do Firebase (sem Admin SDK) para não precisar de auth.
    """
    codigo = codigo.strip().upper()
    url = f"{FIREBASE_DB_URL}/codigos/{codigo}.json?key={FIREBASE_WEB_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data or not data.get("uid"):
            return None, None
        uid = data["uid"]
        # Busca o email em /users/{uid}/email
        url2 = f"{FIREBASE_DB_URL}/users/{uid}/email.json?key={FIREBASE_WEB_API_KEY}"
        r2 = requests.get(url2, timeout=10)
        email = r2.json() if r2.ok else "desconhecido"
        return uid, email
    except Exception as e:
        log.error(f"validate_code: {e}")
        return None, None

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
    idx = load_cache_index()
    e = idx.get(url_key(url))
    if e and Path(e["path"]).exists(): return e["path"]
    return None

def set_cached(url, path, nome=""):
    idx = load_cache_index()
    idx[url_key(url)] = {"path": str(path), "nome": nome, "ts": int(time.time())}
    save_cache_index(idx)

# ── Estado ────────────────────────────────────────────────────────
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
    local_playlists : dict = {}
    local_anuncios  : dict = {}
    uid             = ""
    email           = ""
    codigo          = ""

ST = State()

# ── Eventos UI ────────────────────────────────────────────────────
EVQ: queue.Queue = queue.Queue()
def ev(tipo, **kw): EVQ.put({"t": tipo, **kw})

# ── Logger ────────────────────────────────────────────────────────
class _UIHandler(logging.Handler):
    def emit(self, r): ev("log", msg=self.format(r), lvl=r.levelname)

logging.basicConfig(level=logging.INFO, format="[%(H:%M:%S)] %(message)s")
log = logging.getLogger("PlayAds")
log.handlers.clear()
log.addHandler(logging.StreamHandler())
log.addHandler(_UIHandler())

# ── Volume Duck ───────────────────────────────────────────────────
_saved_volumes: dict = {}
_saved_lock = threading.Lock()

def _duck_worker(target_pct: float, fade_ms: int, restore: bool):
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
                    with _saved_lock: orig = _saved_volumes.get(key, 1.0)
                    svols.append((sav, cur, orig))
                else:
                    with _saved_lock: _saved_volumes[key] = cur
                    svols.append((sav, cur, target_pct / 100.0))
            except: continue
        if not svols: return
        steps = max(20, int(fade_ms / 40))
        delay = fade_ms / 1000.0 / steps
        for step in range(1, steps + 1):
            t = step / steps; ease = t*t*(3.0-2.0*t)
            for sav, v0, v1 in svols:
                try: sav.SetMasterVolume(max(0.0, min(1.0, v0+(v1-v0)*ease)), None)
                except: pass
            time.sleep(delay)
    except Exception as ex: log.warning(f"duck: {ex}")
    finally:
        try: comtypes.CoUninitialize()
        except: pass

# ── Download / YouTube ────────────────────────────────────────────
def is_yt(url): return "youtube.com" in url or "youtu.be" in url

def download_yt(url, nome):
    if not HAS_YTDLP: log.error("yt-dlp não instalado"); return None
    cached = get_cached(url)
    if cached: log.info(f"📦 Cache YT: {nome}"); return cached
    try:
        log.info(f"⬇ YouTube: {nome}")
        out = str(CACHE_DIR / f"yt_{url_key(url)}.%(ext)s")
        with yt_dlp.YoutubeDL({
            "format":"bestaudio/best", "outtmpl":out,
            "quiet":True, "no_warnings":True,
            "postprocessors":[{"key":"FFmpegExtractAudio",
                               "preferredcodec":"mp3","preferredquality":"192"}]
        }) as ydl:
            ydl.download([url])
        mp3 = str(CACHE_DIR / f"yt_{url_key(url)}.mp3")
        if Path(mp3).exists():
            set_cached(url, mp3, nome); return mp3
        for f in CACHE_DIR.glob(f"yt_{url_key(url)}.*"):
            set_cached(url, str(f), nome); return str(f)
    except Exception as e: log.error(f"YT {nome}: {e}")
    return None

def download_audio(url, nome):
    cached = get_cached(url)
    if cached: log.info(f"📦 Cache: {nome}"); return cached
    try:
        log.info(f"⬇ Baixando: {nome}")
        r   = requests.get(url, timeout=30, stream=True); r.raise_for_status()
        ct  = r.headers.get("Content-Type","")
        ext = ".wav" if ("wav" in ct or url.lower().endswith(".wav")) else ".mp3"
        out = CACHE_DIR / f"{url_key(url)}{ext}"
        total= int(r.headers.get("Content-Length",0)); done=0
        with open(out,"wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk); done+=len(chunk)
                if total: ev("dl_pct", pct=int(done/total*100))
        set_cached(url, str(out), nome); return str(out)
    except Exception as e: log.error(f"Download {nome}: {e}"); return None

def get_audio(url, nome):
    return download_yt(url, nome) if is_yt(url) else download_audio(url, nome)

# ── Firebase helpers (caminhos /users/{uid}/) ─────────────────────
def user_ref(path=""):
    return rtdb.reference(f"users/{ST.uid}{path}")

def fb_log(msg, status="info"):
    try: user_ref("/logs").push({"mensagem":msg,"status":status,"timestamp":int(time.time()*1000)})
    except: pass

def fb_status(rep=None):
    cfg = load_config()
    try:
        d = {"nome":cfg.get("player_nome","Player"),"last_seen":int(time.time()*1000),
             "plataforma":platform.system()+" "+platform.release(),"versao":"5.1"}
        if rep is not None: d["reproducao_atual"] = rep
        user_ref("/player_status").update(d)
    except: pass

def fb_done(path):
    try: user_ref(path).update({"executado":True})
    except: pass

# ── Reprodução ────────────────────────────────────────────────────
def play_item(item, cfg, loops_override=None):
    nome  = item.get("nome","?")
    url   = item.get("url","")
    loops = loops_override if loops_override is not None else max(1, int(item.get("loops",1)))
    if not url: return

    tmp = get_audio(url, nome)
    if not tmp: fb_log(f"Falha ao obter: {nome}","error"); return

    fade_ms    = int(cfg.get("duck_fade_ms",1200))
    vol_outros = float(cfg.get("volume_outros",10))
    vol_anuncio= float(cfg.get("volume_anuncio",100))/100.0

    try:
        _duck_worker(vol_outros, fade_ms, restore=False)
        for n in range(1, loops+1):
            if ST.stop_requested: break
            log.info(f"▶ {nome}  loop {n}/{loops}")
            ST.play_ts = time.time()
            fb_status(f"{nome} (loop {n}/{loops})")
            fb_log(f"Tocando: {nome} (loop {n}/{loops})","ok")
            ev("now_playing", nome=nome, loop=n, total=loops, pl=ST.current_pl_name)
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                pygame.mixer.init(44100,-16,2,4096)
                pygame.mixer.music.load(tmp)
                pygame.mixer.music.set_volume(vol_anuncio)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if ST.stop_requested: pygame.mixer.music.stop(); break
                    time.sleep(0.1)
            except pygame.error as e:
                log.error(f"Pygame: {e}")
                try: pygame.mixer.quit(); pygame.mixer.init(44100,-16,2,4096)
                except: pass
                break
            if n < loops and not ST.stop_requested: time.sleep(0.3)
    finally:
        _duck_worker(100.0, fade_ms, restore=True)
        try: pygame.mixer.music.stop()
        except: pass

def run_playlist(pl, cfg, force=False, loops_override=None):
    nome_pl = pl.get("nome","Playlist")
    itens   = pl.get("itens") or []
    if not itens:
        log.warning(f"Playlist '{nome_pl}' vazia"); ev("stopped"); return

    ST.current_pl_name = nome_pl
    ST.queue_items     = list(itens)
    fb_log(f"Iniciando: {nome_pl}","ok")
    ev("pl_start", nome=nome_pl, itens=itens)

    now_t = datetime.now().strftime("%H:%M")
    played_any = False
    for i, item in enumerate(itens):
        if ST.stop_requested: break
        h = item.get("horario")
        if h and not force and h != now_t:
            log.info(f"⏰ Pulando '{item.get('nome')}' — agendado {h}"); continue
        ST.current_item = item
        played_any = True
        ev("q_active", idx=i)
        play_item(item, cfg, loops_override=loops_override)

    if not played_any: log.warning(f"Nenhum item tocou em '{nome_pl}'"); ev("stopped")
    with ST.lock: ST.playing=False; ST.current_item=None; ST.current_pl_name=""
    fb_status(None)
    fb_log(f"'{nome_pl}' concluída","ok")
    log.info(f"✓ '{nome_pl}' concluída")
    ev("pl_end", nome=nome_pl)

def stop_all():
    with ST.lock: ST.stop_requested=True
    try: pygame.mixer.music.stop()
    except: pass
    if ST.current_thread and ST.current_thread.is_alive():
        ST.current_thread.join(timeout=3)
    with ST.lock:
        ST.stop_requested=False; ST.playing=False
        ST.current_thread=None; ST.current_item=None

def start_playlist(pl, cfg, force=True, loops_override=None):
    stop_all()
    with ST.lock:
        ST.playing=True
        t = threading.Thread(target=run_playlist,
                             args=(pl,cfg,force),
                             kwargs={"loops_override":loops_override},daemon=True)
        ST.current_thread=t
    t.start()

# ── Listeners Firebase ────────────────────────────────────────────
def setup_listeners(cfg):
    def on_play(e):
        try:
            d = e.data
            if not d or d.get("executado"): return
            plid = d.get("playlist_id")
            if not plid: return
            snap = user_ref(f"/playlists/{plid}").get()
            if not snap: return
            fb_done(f"/comandos/play_now")
            start_playlist(snap, cfg, force=True)
        except Exception as ex: log.error(f"on_play: {ex}")

    def on_stop(e):
        try:
            d = e.data
            if not d or d.get("executado"): return
            fb_done("/comandos/stop")
            stop_all(); fb_status(None); ev("stopped")
        except Exception as ex: log.error(f"on_stop: {ex}")

    def on_playlists(e):
        try:
            d = e.data
            if d and isinstance(d, dict):
                ST.local_playlists = d
                ev("fb_data", playlists=d, anuncios=ST.local_anuncios)
                (BASE_DIR/"local_playlists.json").write_text(
                    json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception as ex: log.error(f"on_playlists: {ex}")

    def on_anuncios(e):
        try:
            d = e.data
            if d and isinstance(d, dict):
                ST.local_anuncios = d
                ev("fb_data", playlists=ST.local_playlists, anuncios=d)
                (BASE_DIR/"local_anuncios.json").write_text(
                    json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception as ex: log.error(f"on_anuncios: {ex}")

    user_ref("/comandos/play_now").listen(on_play)
    user_ref("/comandos/stop").listen(on_stop)
    user_ref("/playlists").listen(on_playlists)
    user_ref("/anuncios").listen(on_anuncios)
    log.info("✅ Listeners ativos")

def check_schedules(cfg):
    while True:
        time.sleep(30)
        try:
            if ST.playing: continue
            now_t = datetime.now().strftime("%H:%M")
            for _, pl in ST.local_playlists.items():
                if not isinstance(pl,dict) or not pl.get("ativa"): continue
                for item in (pl.get("itens") or []):
                    if isinstance(item,dict) and item.get("horario")==now_t:
                        log.info(f"⏰ {now_t} → {pl.get('nome')}")
                        start_playlist(pl,cfg); break
        except Exception as ex: log.error(f"schedule: {ex}")

def heartbeat(cfg):
    while True:
        try:
            rep = ST.current_item.get("nome") if ST.current_item else None
            fb_status(rep)
        except: pass
        time.sleep(10)

def precache_all():
    log.info("📦 Pré-cache iniciando...")
    count=0
    for pl in ST.local_playlists.values():
        if not isinstance(pl,dict): continue
        for item in (pl.get("itens") or []):
            url=item.get("url","")
            if url and not get_cached(url):
                get_audio(url, item.get("nome","?")); count+=1
    log.info(f"✅ Cache: {count} arquivo(s) novos")
    ev("cache_done",count=count)

def load_local_data():
    for fname, attr in [("local_playlists.json","local_playlists"),
                        ("local_anuncios.json","local_anuncios")]:
        try:
            p = BASE_DIR/fname
            if p.exists():
                setattr(ST, attr, json.loads(p.read_text(encoding="utf-8")))
        except: pass

def start_firebase(uid):
    """Inicializa Firebase Admin SDK — chamado após ativação."""
    if firebase_admin._apps: return True
    if not CRED_FILE.exists():
        log.error(f"serviceAccountKey.json não encontrado: {CRED_FILE}")
        return False
    try:
        cred = credentials.Certificate(str(CRED_FILE))
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
        log.info("✅ Firebase conectado")
        return True
    except Exception as e:
        log.error(f"Firebase init: {e}"); return False


# ══════════════════════════════════════════════════════════════════
#  TELA DE ATIVAÇÃO
# ══════════════════════════════════════════════════════════════════
class ActivationScreen:
    """Janela de ativação exibida antes do player principal."""

    def __init__(self, on_success):
        self.on_success = on_success   # callback(uid, email, codigo)
        self.root = tk.Tk()
        self.root.title("PlayAds — Ativação")
        self.root.geometry("480x360")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self._build()

    def _build(self):
        r = self.root

        # Header
        hdr = tk.Frame(r, bg=SURF, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Logo
        cv = tk.Canvas(hdr, width=28, height=28, bg=SURF, highlightthickness=0)
        cv.place(x=18, y=16)
        cv.create_oval(0,0,28,28, fill=PURPLE2, outline="")
        cv.create_polygon(10,6,10,22,22,14, fill="white", outline="")

        tk.Label(hdr, text="PlayAds", bg=SURF, fg=TEXT,
                 font=("Segoe UI",13,"bold")).place(x=52, y=18)
        tk.Label(hdr, text="Ativação do Player", bg=SURF, fg=MUTED,
                 font=FONT_SMALL).place(relx=1, x=-16, y=22, anchor="ne")

        tk.Frame(r, bg=BORDER, height=1).pack(fill="x")

        # Body
        body = tk.Frame(r, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=20)

        tk.Label(body, text="Código de Ativação", bg=BG, fg=TEXT,
                 font=("Segoe UI",13,"bold")).pack(anchor="w")
        tk.Label(body,
                 text="Acesse o painel web → Ativar Player e copie seu código único.",
                 bg=BG, fg=MUTED, font=FONT_SMALL,
                 wraplength=400, justify="left").pack(anchor="w", pady=(4,16))

        # Campo do código
        code_f = tk.Frame(body, bg=SURF2,
                          highlightbackground=BORDER, highlightthickness=1)
        code_f.pack(fill="x", pady=(0,8))

        self._code_var = tk.StringVar()
        self._code_var.trace_add("write", self._on_type)
        entry = tk.Entry(code_f, textvariable=self._code_var,
                         bg=SURF2, fg=TEXT, insertbackground=PURPLE,
                         font=("Consolas",18,"bold"), relief="flat",
                         bd=12, justify="center")
        entry.pack(fill="x")
        entry.bind("<Return>", lambda e: self._validate())
        entry.focus()

        # Placeholder
        self._ph = tk.Label(code_f, text="PLAY-XXXX-XXXX",
                             bg=SURF2, fg=SURF3,
                             font=("Consolas",18,"bold"))
        self._ph.place(relx=0.5, rely=0.5, anchor="center")

        # Status
        self._lbl_status = tk.Label(body, text="", bg=BG, fg=MUTED,
                                    font=FONT_SMALL, wraplength=400)
        self._lbl_status.pack(pady=(0,12))

        # Botão
        self._btn = tk.Button(body, text="Ativar", bg=PURPLE2, fg=TEXT,
                              font=("Segoe UI",11,"bold"), relief="flat",
                              bd=0, padx=32, pady=10, cursor="hand2",
                              command=self._validate)
        self._btn.pack(fill="x")

        # Link web
        link = tk.Label(body, text="🌐  Abrir painel web", bg=BG, fg=PURPLE,
                        font=FONT_SMALL, cursor="hand2")
        link.pack(pady=(12,0))
        link.bind("<Button-1>", lambda e: webbrowser.open(WEB_URL))

    def _on_type(self, *_):
            val = self._code_var.get().upper()
            
            # Gerencia o placeholder (texto de fundo)
            if val:
                self._ph.place_forget()
            else:
                self._ph.place(relx=0.5, rely=0.5, anchor="center")

            # 1. Pega apenas letras e números, ignorando o "PLAY" se o usuário digitar
            raw = val.replace("-", "").replace(" ", "")
            if raw.startswith("PLAY"):
                raw = raw[4:]
            
            # 2. Limita a 8 caracteres (os dois blocos de 4)
            raw = raw[:8]
            
            # 3. Reconstrói a máscara: PLAY-XXXX-XXXX
            parts = ["PLAY"]
            if len(raw) > 0: parts.append(raw[:4])
            if len(raw) > 4: parts.append(raw[4:8])
            
            new_val = "-".join(parts)
            
            # 4. Só atualiza se for diferente para evitar loop infinito
            if new_val != val:
                self._code_var.set(new_val)
                # ISSO AQUI É O QUE DEIXA VOCÊ ESCREVER: move o cursor para o fim
                self.root.after(1, lambda: self._entry.icursor(tk.END))

    def _validate(self):
        codigo = self._code_var.get().strip().upper()
        if not codigo or len(codigo) < 10:
            self._set_status("⚠ Digite o código completo (PLAY-XXXX-XXXX)", WARN)
            return

        self._btn.configure(text="Validando...", state="disabled")
        self._set_status("🔍 Verificando código no servidor...", MUTED)

        def _run():
            uid, email = validate_code_firebase(codigo)
            if uid:
                save_activation(uid, email, codigo)
                self.root.after(0, lambda: self._success(uid, email, codigo))
            else:
                self.root.after(0, lambda: self._fail())

        threading.Thread(target=_run, daemon=True).start()

    def _success(self, uid, email, codigo):
        self._set_status(f"✅ Ativado! Conta: {email}", GREEN)
        self._btn.configure(text="✓ Ativado!", bg=GREEN, state="disabled")
        self.root.after(1200, lambda: (self.root.destroy(), self.on_success(uid, email, codigo)))

    def _fail(self):
        self._set_status("✗ Código inválido. Verifique no painel web.", DANGER)
        self._btn.configure(text="Ativar", state="normal")

    def _set_status(self, text, color):
        self._lbl_status.configure(text=text, fg=color)

    def run(self):
        self.root.mainloop()


# ══════════════════════════════════════════════════════════════════
#  PLAYER PRINCIPAL
# ══════════════════════════════════════════════════════════════════
class App:
    W, H = 820, 520

    PAGES = ["Player","Playlists","Fila","Ativação","Config"]
    ICONS = ["▶", "☰", "≡", "🔑", "⚙"]

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PlayAds")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self._playlists: dict = {}
        self._anuncios:  dict = {}
        self._page       = "Player"
        self._eq_phase   = 0.0
        self._eq_running = False
        self._queue_rows: list = []

        self._setup_styles()
        self._build()
        self.root.after(120, self._poll)

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("P.Horizontal.TProgressbar",
                    troughcolor=SURF3, background=PURPLE, borderwidth=0, thickness=3)
        s.configure("Treeview",
                    background=SURF2, fieldbackground=SURF2,
                    foreground=TEXT, rowheight=32, borderwidth=0, font=FONT_BODY)
        s.configure("Treeview.Heading",
                    background=SURF3, foreground=MUTED2, relief="flat", font=FONT_SMALL)
        s.map("Treeview", background=[("selected",SURF4)], foreground=[("selected",TEXT)])
        s.configure("Vertical.TScrollbar",
                    troughcolor=SURF, background=SURF3, borderwidth=0, arrowsize=10)

    # ── BUILD ─────────────────────────────────────────────────────
    def _build(self):
        self._sidebar = tk.Frame(self.root, bg=SURF, width=64)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)
        self._build_sidebar()
        tk.Frame(self.root, bg=BORDER, width=1).pack(side="left", fill="y")
        main = tk.Frame(self.root, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self._main = main
        self._build_pages()
        self._switch_page("Player")

    # ── SIDEBAR ───────────────────────────────────────────────────
    def _build_sidebar(self):
        sb = self._sidebar

        # Logo
        logo_f = tk.Frame(sb, bg=SURF, height=60)
        logo_f.pack(fill="x")
        logo_f.pack_propagate(False)
        cv = tk.Canvas(logo_f, width=32, height=32, bg=SURF, highlightthickness=0)
        cv.place(relx=0.5, rely=0.5, anchor="center")
        cv.create_oval(0,0,32,32, fill=PURPLE2, outline="")
        cv.create_polygon(12,8,12,24,24,16, fill="white", outline="")

        tk.Frame(sb, bg=BORDER, height=1).pack(fill="x")

        # Nav
        self._nav_btns = {}
        nav_f = tk.Frame(sb, bg=SURF)
        nav_f.pack(fill="x", pady=6)
        for icon, page in zip(self.ICONS, self.PAGES):
            f = tk.Frame(nav_f, bg=SURF)
            f.pack(fill="x", pady=1)
            btn = tk.Label(f, text=icon, bg=SURF, fg=MUTED,
                           font=("Segoe UI",14), cursor="hand2",
                           width=4, pady=9)
            btn.pack()
            btn.bind("<Button-1>", lambda e, p=page: self._switch_page(p))
            btn.bind("<Enter>",    lambda e, b=btn, p=page: b.configure(fg=TEXT if self._page!=p else PURPLE))
            btn.bind("<Leave>",    lambda e, b=btn, p=page: b.configure(fg=PURPLE if self._page==p else MUTED))

            # Tooltip
            tip = tk.Label(self.root, text=page, bg=SURF4, fg=TEXT,
                           font=FONT_SMALL, padx=6, pady=3)
            btn.bind("<Enter>", lambda e, b=btn, t=tip, p=page: [
                b.configure(fg=TEXT),
                t.place(x=66, y=e.widget.winfo_rooty()-self.root.winfo_rooty()+4)
            ])
            btn.bind("<Leave>", lambda e, b=btn, t=tip, p=page: [
                b.configure(fg=PURPLE if self._page==p else MUTED),
                t.place_forget()
            ])
            self._nav_btns[page] = btn

        tk.Frame(sb, bg=SURF).pack(fill="both", expand=True)

        # Status dot
        self._sb_dot = tk.Label(sb, text="●", bg=SURF, fg="#333", font=("Segoe UI",10))
        self._sb_dot.pack(pady=(0,4))

        # Web button
        wf = tk.Frame(sb, bg=SURF, height=44)
        wf.pack(fill="x")
        wf.pack_propagate(False)
        wb = tk.Label(wf, text="🌐", bg=SURF, fg=MUTED,
                      font=("Segoe UI",13), cursor="hand2", pady=8)
        wb.pack()
        wb.bind("<Button-1>", lambda e: webbrowser.open(WEB_URL))
        wb.bind("<Enter>",    lambda e: wb.configure(fg=PURPLE))
        wb.bind("<Leave>",    lambda e: wb.configure(fg=MUTED))
        tk.Frame(sb, bg=SURF, height=4).pack()

    # ── PAGES ─────────────────────────────────────────────────────
    def _build_pages(self):
        self._pages = {
            "Player":    self._build_page_player(self._main),
            "Playlists": self._build_page_playlists(self._main),
            "Fila":      self._build_page_fila(self._main),
            "Ativação":  self._build_page_ativacao(self._main),
            "Config":    self._build_page_config(self._main),
        }

    def _switch_page(self, page):
        self._page = page
        for p, f in self._pages.items():
            if p==page: f.pack(fill="both",expand=True)
            else:       f.pack_forget()
        for p, b in self._nav_btns.items():
            b.configure(fg=PURPLE if p==page else MUTED)

    # ── PAGE: PLAYER ──────────────────────────────────────────────
    def _build_page_player(self, parent):
        f = tk.Frame(parent, bg=BG)

        hdr = tk.Frame(f, bg=SURF, height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="PlayAds", bg=SURF, fg=PURPLE,
                 font=("Segoe UI",12,"bold")).pack(side="left",padx=16,pady=12)
        self._lbl_st = tk.Label(hdr,text="Iniciando...",bg=SURF,fg=MUTED,font=FONT_SMALL)
        self._lbl_st.pack(side="right",padx=14)
        self._dot = tk.Label(hdr,text="●",bg=SURF,fg="#333",font=("Segoe UI",9))
        self._dot.pack(side="right",padx=(0,2))
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(f, bg=BG)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=BG, width=320)
        left.pack(side="left", fill="y", padx=18, pady=14)
        left.pack_propagate(False)

        # Artwork
        art_f = tk.Frame(left, bg=SURF3, width=110, height=110)
        art_f.pack(pady=(4,10))
        art_f.pack_propagate(False)
        self._art_cv = tk.Canvas(art_f, width=110, height=110,
                                 bg=SURF3, highlightthickness=0)
        self._art_cv.pack()
        self._draw_art(idle=True)

        eq_row = tk.Frame(left, bg=BG)
        eq_row.pack(fill="x", pady=(0,3))
        self._eq_cv = tk.Canvas(eq_row, width=24, height=14,
                                bg=BG, highlightthickness=0)
        self._eq_cv.pack(side="left")
        self._lbl_tag = tk.Label(eq_row, text="AGUARDANDO",
                                 bg=BG, fg=MUTED, font=("Segoe UI",7,"bold"))
        self._lbl_tag.pack(side="left", padx=6)
        self._draw_eq(idle=True)

        self._lbl_title = tk.Label(left, text="Nenhuma mídia",
                                   bg=BG, fg=TEXT,
                                   font=("Segoe UI",11,"bold"),
                                   anchor="w", wraplength=295, justify="left")
        self._lbl_title.pack(fill="x", pady=(0,2))
        self._lbl_meta = tk.Label(left, text="—", bg=BG, fg=MUTED,
                                  font=FONT_SMALL, anchor="w")
        self._lbl_meta.pack(fill="x", pady=(0,7))

        self._prog_var = tk.DoubleVar(value=0)
        ttk.Progressbar(left, variable=self._prog_var, maximum=100,
                        style="P.Horizontal.TProgressbar").pack(fill="x", pady=(0,3))
        tf = tk.Frame(left, bg=BG)
        tf.pack(fill="x", pady=(0,8))
        self._lbl_tcur = tk.Label(tf, text="0:00", bg=BG, fg=MUTED, font=FONT_MONO)
        self._lbl_tcur.pack(side="left")
        self._mkbtn(left, "■  PARAR", "#2a0f18", DANGER,
                    self._cmd_stop, pad_x=0, pad_y=7).pack(fill="x", pady=(2,0))

        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y", pady=8)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        sc = tk.Frame(right, bg=BG)
        sc.pack(fill="x", pady=(0,7))
        sc.columnconfigure((0,1), weight=1)
        self._s_pl     = self._stat(sc,"PLAYLIST","—",0,0)
        self._s_faixas = self._stat(sc,"FAIXAS","0",1,0)
        self._s_st     = self._stat(sc,"STATUS","Pronto",0,1,GREEN)
        self._s_loop   = self._stat(sc,"LOOP","—",1,1)

        # Volume
        vf = tk.Frame(right, bg=SURF2, highlightbackground=BORDER, highlightthickness=1)
        vf.pack(fill="x", pady=(0,7), ipady=5)
        tk.Label(vf, text="VOLUME", bg=SURF2, fg=MUTED,
                 font=("Segoe UI",7,"bold")).pack(anchor="w",padx=10,pady=(5,2))
        for lbl, attr, color in [("Anúncio","_lbl_vol_ad",PURPLE),
                                  ("Outros apps","_lbl_vol_ot",WARN)]:
            r2 = tk.Frame(vf, bg=SURF2)
            r2.pack(fill="x", padx=10, pady=1)
            tk.Label(r2, text=lbl, bg=SURF2, fg=MUTED2, font=FONT_SMALL).pack(side="left")
            setattr(self, attr,
                    tk.Label(r2, text="—", bg=SURF2, fg=color, font=FONT_MONO))
            getattr(self, attr).pack(side="right")

        if not HAS_PYCAW:
            tk.Label(right, text="⚠ pycaw não instalado — duck desativado",
                     bg=BG, fg=WARN, font=FONT_SMALL).pack(anchor="w",pady=(0,4))
        if not HAS_YTDLP:
            tk.Label(right, text="⚠ yt-dlp não instalado — pip install yt-dlp",
                     bg=BG, fg=WARN, font=FONT_SMALL).pack(anchor="w",pady=(0,4))

        # Cache
        cf = tk.Frame(right, bg=SURF2, highlightbackground=BORDER, highlightthickness=1)
        cf.pack(fill="x", pady=(0,7), ipady=4)
        tk.Label(cf, text="CACHE OFFLINE", bg=SURF2, fg=MUTED,
                 font=("Segoe UI",7,"bold")).pack(anchor="w",padx=10,pady=(5,2))
        cr = tk.Frame(cf, bg=SURF2)
        cr.pack(fill="x", padx=10)
        self._lbl_cache = tk.Label(cr, text="—", bg=SURF2, fg=MUTED2, font=FONT_SMALL)
        self._lbl_cache.pack(side="left")
        self._mkbtn(cr, "↻ Sync", SURF3, PURPLE, self._cmd_precache,
                    pad_x=6, pad_y=2).pack(side="right")

        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", pady=(0,5))
        self._log_txt = tk.Text(right, bg="#0a0810", fg=MUTED,
                                font=("Consolas",7), relief="flat",
                                state="disabled", wrap="word", height=6)
        self._log_txt.pack(fill="both", expand=True)
        self._log_txt.tag_config("OK",   foreground=PURPLE)
        self._log_txt.tag_config("ERR",  foreground=DANGER)
        self._log_txt.tag_config("WARN", foreground=WARN)
        self._log_txt.tag_config("INFO", foreground=MUTED)
        return f

    # ── PAGE: PLAYLISTS ───────────────────────────────────────────
    def _build_page_playlists(self, parent):
        f = tk.Frame(parent, bg=BG)
        hdr = tk.Frame(f, bg=SURF, height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="Playlists", bg=SURF, fg=TEXT,
                 font=("Segoe UI",11,"bold")).pack(side="left",padx=16,pady=12)
        tk.Label(hdr, text="duplo clique para tocar", bg=SURF,
                 fg=MUTED, font=FONT_SMALL).pack(side="right",padx=14)
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        wrap = tk.Frame(f, bg=SURF2, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True, padx=12, pady=10)

        cols = ("nome","faixas","status","acao")
        self._tv_pl = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        sb2 = ttk.Scrollbar(wrap, orient="vertical", command=self._tv_pl.yview)
        self._tv_pl.configure(yscrollcommand=sb2.set)
        self._tv_pl.heading("nome",   text="Nome")
        self._tv_pl.heading("faixas", text="Faixas")
        self._tv_pl.heading("status", text="Status")
        self._tv_pl.heading("acao",   text="")
        self._tv_pl.column("nome",   width=230, anchor="w")
        self._tv_pl.column("faixas", width=60,  anchor="center")
        self._tv_pl.column("status", width=80,  anchor="center")
        self._tv_pl.column("acao",   width=100, anchor="center")
        self._tv_pl.tag_configure("ativa",   foreground=GREEN)
        self._tv_pl.tag_configure("inativa", foreground=MUTED)
        self._tv_pl.tag_configure("playing", foreground=PURPLE, font=FONT_TITLE)
        self._tv_pl.bind("<Double-1>", self._pl_double_click)
        self._tv_pl.bind("<Button-1>", self._pl_single_click)
        sb2.pack(side="right", fill="y")
        self._tv_pl.pack(fill="both", expand=True)
        return f

    # ── PAGE: FILA ────────────────────────────────────────────────
    def _build_page_fila(self, parent):
        f = tk.Frame(parent, bg=BG)
        hdr = tk.Frame(f, bg=SURF, height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="Fila de Reprodução", bg=SURF, fg=TEXT,
                 font=("Segoe UI",11,"bold")).pack(side="left",padx=16,pady=12)
        self._lbl_pl_atual = tk.Label(hdr, text="", bg=SURF, fg=PURPLE,
                                      font=("Segoe UI",9,"bold"))
        self._lbl_pl_atual.pack(side="left",padx=8)
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")
        wrap = tk.Frame(f, bg=SURF2, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True, padx=12, pady=10)
        self._q_canvas = tk.Canvas(wrap, bg=SURF2, highlightthickness=0)
        sb3 = ttk.Scrollbar(wrap, orient="vertical", command=self._q_canvas.yview)
        self._q_frame = tk.Frame(self._q_canvas, bg=SURF2)
        self._q_frame.bind("<Configure>", lambda e:
            self._q_canvas.configure(scrollregion=self._q_canvas.bbox("all")))
        self._q_canvas.create_window((0,0), window=self._q_frame, anchor="nw")
        self._q_canvas.configure(yscrollcommand=sb3.set)
        sb3.pack(side="right", fill="y")
        self._q_canvas.pack(side="left", fill="both", expand=True)
        self._q_empty()
        return f

    # ── PAGE: ATIVAÇÃO (info somente leitura) ─────────────────────
    def _build_page_ativacao(self, parent):
        f = tk.Frame(parent, bg=BG)
        hdr = tk.Frame(f, bg=SURF, height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="Informações da Conta", bg=SURF, fg=TEXT,
                 font=("Segoe UI",11,"bold")).pack(side="left",padx=16,pady=12)
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(f, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=24)

        # Card info
        card = tk.Frame(body, bg=SURF2, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0,16))
        tk.Label(card, text="CONTA ATIVADA", bg=SURF2, fg=PURPLE,
                 font=("Segoe UI",8,"bold")).pack(anchor="w",padx=14,pady=(12,4))

        for label, attr in [("E-mail","_lbl_act_email"),
                             ("Código","_lbl_act_codigo"),
                             ("Status","_lbl_act_status")]:
            row = tk.Frame(card, bg=SURF2)
            row.pack(fill="x", padx=14, pady=3)
            tk.Label(row, text=label, bg=SURF2, fg=MUTED,
                     font=FONT_SMALL, width=10, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="—", bg=SURF2, fg=TEXT, font=FONT_MONO)
            lbl.pack(side="left")
            setattr(self, attr, lbl)
        tk.Frame(card, bg=SURF2, height=10).pack()

        # Botão desativar
        info_f = tk.Frame(body, bg=BG)
        info_f.pack(fill="x")
        tk.Label(info_f,
                 text="Para usar outro código, desative e abra o software novamente.",
                 bg=BG, fg=MUTED, font=FONT_SMALL, wraplength=500, justify="left").pack(anchor="w")

        self._mkbtn(body, "✕  Desativar e reiniciar pareamento",
                    "#2a0f18", DANGER, self._cmd_deactivate,
                    pad_x=16, pad_y=8).pack(anchor="w", pady=(12,0))
        return f

    # ── PAGE: CONFIG ──────────────────────────────────────────────
    def _build_page_config(self, parent):
        f = tk.Frame(parent, bg=BG)
        hdr = tk.Frame(f, bg=SURF, height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="Configurações", bg=SURF, fg=TEXT,
                 font=("Segoe UI",11,"bold")).pack(side="left",padx=16,pady=12)
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(f, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=12)
        cfg = load_config()
        fields = [
            ("Nome do Player",  "player_nome"),
            ("Volume anúncio %","volume_anuncio"),
            ("Volume outros %", "volume_outros"),
            ("Fade duck (ms)",  "duck_fade_ms"),
        ]
        self._cfg_vars = {}
        for label, key in fields:
            row = tk.Frame(body, bg=BG)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, bg=BG, fg=MUTED2,
                     font=FONT_SMALL, width=20, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(cfg.get(key,"")))
            self._cfg_vars[key] = var
            tk.Entry(row, textvariable=var, bg=SURF3, fg=TEXT,
                     font=FONT_MONO, relief="flat", bd=4,
                     insertbackground=TEXT).pack(side="left", fill="x", expand=True)

        self._mkbtn(body, "💾  Salvar", PURPLE2, TEXT,
                    self._save_config, pad_x=16, pad_y=8).pack(anchor="w", pady=(12,0))
        return f

    # ── Helpers ───────────────────────────────────────────────────
    def _mkbtn(self, parent, text, bg, fg, cmd, pad_x=12, pad_y=6, expand=False):
        orig = bg
        b = tk.Button(parent, text=text, bg=bg, fg=fg,
                      font=FONT_TITLE, relief="flat", bd=0,
                      padx=pad_x, pady=pad_y, cursor="hand2",
                      activebackground=bg, activeforeground=fg, command=cmd)
        b.bind("<Enter>", lambda e: b.config(bg=self._lgt(orig)))
        b.bind("<Leave>", lambda e: b.config(bg=orig))
        return b

    @staticmethod
    def _lgt(h):
        try:
            hx=h.replace("#","")[:6]
            r,g,b=int(hx[0:2],16),int(hx[2:4],16),int(hx[4:6],16)
            return "#{:02x}{:02x}{:02x}".format(min(255,r+28),min(255,g+28),min(255,b+28))
        except: return h

    def _stat(self, parent, label, val, col, row, vc=None):
        f = tk.Frame(parent, bg=SURF3, highlightbackground=BORDER, highlightthickness=1)
        f.grid(row=row, column=col, sticky="ew", padx=2, pady=2)
        tk.Label(f, text=label, bg=SURF3, fg=MUTED,
                 font=("Segoe UI",7,"bold")).pack(pady=(4,0))
        lbl = tk.Label(f, text=val, bg=SURF3, fg=vc or TEXT,
                       font=("Segoe UI",11,"bold"))
        lbl.pack(pady=(0,4))
        return lbl

    def _draw_art(self, idle=True):
        import math
        c = self._art_cv; c.delete("all")
        if idle:
            c.create_rectangle(0,0,110,110, fill=SURF3, outline="")
            c.create_oval(42,42,68,68, fill=SURF4, outline="")
            c.create_oval(50,50,60,60, fill=SURF2, outline="")
        else:
            p=self._eq_phase
            for i in range(3):
                r=18+i*16+int(math.sin(p+i)*4)
                col=["#9b59f5","#7c3aed","#4c1d95"][i]
                c.create_oval(55-r,55-r,55+r,55+r,outline=col,width=2)
            c.create_oval(44,44,66,66,fill=PURPLE2,outline="")
            c.create_polygon(50,40,50,70,70,55,fill="white",outline="")

    def _draw_eq(self, idle=True):
        c=self._eq_cv; c.delete("all")
        p=self._eq_phase; col=MUTED if idle else PURPLE
        hs=[3,6,4,8] if idle else [2+int(10*abs((p+i*0.7)%2-1)) for i in range(4)]
        for i,h in enumerate(hs):
            c.create_rectangle(i*6,14-h,i*6+4,14,fill=col,outline="")

    def _tick_eq(self):
        if not self._eq_running: return
        self._eq_phase+=0.2; self._draw_eq(False); self._draw_art(False)
        self.root.after(100, self._tick_eq)

    def _start_eq(self):
        if not self._eq_running: self._eq_running=True; self._tick_eq()

    def _stop_eq(self):
        self._eq_running=False; self._draw_eq(True); self._draw_art(True)

    def _q_empty(self):
        for w in self._q_frame.winfo_children(): w.destroy()
        self._queue_rows=[]
        tk.Label(self._q_frame, text="♪   Nenhuma playlist em execução",
                 bg=SURF2, fg=MUTED, font=("Segoe UI",10)).pack(pady=30, padx=20)

    def _render_queue(self, itens, active=-1):
        for w in self._q_frame.winfo_children(): w.destroy()
        self._queue_rows=[]
        if not itens: self._q_empty(); return
        for i, item in enumerate(itens):
            is_a=(i==active)
            rbg="#1a1435" if is_a else (SURF3 if i%2==0 else SURF2)
            row=tk.Frame(self._q_frame,bg=rbg,height=34)
            row.pack(fill="x"); row.pack_propagate(False)
            self._queue_rows.append(row)
            tk.Label(row,text=f"  {i+1:02d}  ",bg=rbg,
                     fg=PURPLE if is_a else MUTED,font=FONT_MONO).pack(side="left")
            if is_a: tk.Label(row,text="▶",bg=rbg,fg=PURPLE,
                              font=("Segoe UI",8)).pack(side="left")
            tk.Label(row,text=item.get("nome","—"),bg=rbg,
                     fg=PURPLE if is_a else TEXT,
                     font=("Segoe UI",9,"bold" if is_a else "normal"),
                     anchor="w").pack(side="left",fill="x",expand=True)
            if item.get("horario"):
                self._badge(row,f"⏰ {item['horario']}","#221800",WARN,rbg)
            if int(item.get("loops",1))>1:
                self._badge(row,f"{item['loops']}×","#0e0d24",PURPLE,rbg)
            if is_yt(item.get("url","") or ""):
                self._badge(row,"YT","#1a0a0a",DANGER,rbg)

    def _badge(self, parent, text, bg, fg, fbg):
        outer=tk.Frame(parent,bg=fbg); outer.pack(side="right",padx=(0,6))
        inner=tk.Frame(outer,bg=bg); inner.pack()
        tk.Label(inner,text=text,bg=bg,fg=fg,
                 font=("Segoe UI",7,"bold"),padx=5,pady=1).pack()

    def _highlight_q(self, idx):
        for i, row in enumerate(self._queue_rows):
            is_a=(i==idx)
            rbg="#1a1435" if is_a else (SURF3 if i%2==0 else SURF2)
            row.configure(bg=rbg)
            for ch in row.winfo_children():
                try: ch.configure(bg=rbg)
                except: pass

    def _log(self, msg, lvl):
        self._log_txt.configure(state="normal")
        tag=("OK" if any(x in msg for x in ("✅","▶","✓","📦","⬇"))
             else "ERR" if lvl=="ERROR"
             else "WARN" if lvl in ("WARNING","WARN")
             else "INFO")
        self._log_txt.insert("end",msg+"\n",tag)
        self._log_txt.see("end")
        lines=int(self._log_txt.index("end-1c").split(".")[0])
        if lines>300: self._log_txt.delete("1.0",f"{lines-300}.0")
        self._log_txt.configure(state="disabled")

    def _set_status(self, text, color):
        self._dot.configure(fg=color)
        self._sb_dot.configure(fg=color)
        self._lbl_st.configure(text=text)

    def _refresh_playlists(self):
        tv=self._tv_pl
        for row in tv.get_children(): tv.delete(row)
        for pl_id, pl in self._playlists.items():
            if not isinstance(pl,dict): continue
            nome=pl.get("nome","—")
            faixas=len(pl.get("itens") or [])
            ativa=pl.get("ativa",False)
            tag="playing" if ST.current_pl_id==pl_id else ("ativa" if ativa else "inativa")
            tv.insert("","end",
                      values=(nome,faixas,"● Ativa" if ativa else "○ Inativa","▶ Tocar"),
                      tags=(tag,pl_id))

    def _update_cache_label(self):
        idx=load_cache_index()
        total=sum(Path(e["path"]).stat().st_size for e in idx.values()
                  if Path(e["path"]).exists())/1024/1024
        self._lbl_cache.configure(text=f"{len(idx)} arquivo(s) · {total:.1f} MB")

    def _update_activation_page(self):
        self._lbl_act_email.configure(text=ST.email or "—")
        self._lbl_act_codigo.configure(text=ST.codigo or "—")
        self._lbl_act_status.configure(text="✅ Ativo", fg=GREEN)

    # ── Popup loops ───────────────────────────────────────────────
    def _ask_loops_and_play(self, pl_id):
        pl=self._playlists.get(pl_id)
        if not pl: return
        win=tk.Toplevel(self.root)
        win.title("Tocar agora")
        win.geometry("300x180")
        win.configure(bg=SURF)
        win.resizable(False,False)
        win.grab_set(); win.transient(self.root)
        tk.Label(win,text="Quantas vezes tocar?",
                 bg=SURF,fg=TEXT,font=("Segoe UI",11,"bold")).pack(pady=(18,4))
        tk.Label(win,text=pl.get("nome",""),
                 bg=SURF,fg=MUTED,font=FONT_SMALL).pack(pady=(0,10))
        sf=tk.Frame(win,bg=SURF); sf.pack(pady=(0,14))
        loops_var=tk.IntVar(value=1)
        tk.Button(sf,text="−",bg=SURF3,fg=TEXT,relief="flat",bd=0,
                  font=("Segoe UI",14),padx=10,pady=2,cursor="hand2",
                  command=lambda:loops_var.set(max(1,loops_var.get()-1))).pack(side="left",padx=4)
        tk.Label(sf,textvariable=loops_var,bg=SURF3,fg=PURPLE,
                 font=("Segoe UI",18,"bold"),width=3,pady=4).pack(side="left",padx=2)
        tk.Button(sf,text="+",bg=SURF3,fg=TEXT,relief="flat",bd=0,
                  font=("Segoe UI",14),padx=10,pady=2,cursor="hand2",
                  command=lambda:loops_var.set(min(99,loops_var.get()+1))).pack(side="left",padx=4)
        def _go():
            n=loops_var.get(); win.destroy()
            cfg=load_config()
            ST.current_pl_id=pl_id
            threading.Thread(target=start_playlist,
                             args=(pl,cfg,True),
                             kwargs={"loops_override":n},daemon=True).start()
        self._mkbtn(win,"▶  Tocar agora",PURPLE2,TEXT,_go,pad_x=20,pad_y=8).pack()

    # ── Cliques ───────────────────────────────────────────────────
    def _pl_single_click(self, event):
        tv=self._tv_pl; col=tv.identify_column(event.x); rid=tv.identify_row(event.y)
        if not rid: return
        if col=="#4":
            tags=tv.item(rid,"tags"); pl_id=tags[1] if len(tags)>1 else None
            if pl_id and pl_id in self._playlists: self._ask_loops_and_play(pl_id)

    def _pl_double_click(self, event):
        tv=self._tv_pl; sel=tv.selection()
        if not sel: return
        tags=tv.item(sel[0],"tags"); pl_id=tags[1] if len(tags)>1 else None
        if pl_id and pl_id in self._playlists: self._ask_loops_and_play(pl_id)

    # ── Comandos ──────────────────────────────────────────────────
    def _cmd_stop(self):
        def _go():
            if firebase_admin._apps:
                try: user_ref("/comandos/stop").set({"timestamp":int(time.time()*1000),"executado":False})
                except: pass
            stop_all(); ev("stopped")
        threading.Thread(target=_go,daemon=True).start()

    def _cmd_precache(self):
        threading.Thread(target=precache_all,daemon=True).start()
        log.info("🔄 Pré-cache iniciado...")

    def _save_config(self):
        cfg=load_config(); nc=dict(cfg)
        for k,var in self._cfg_vars.items():
            raw=var.get().strip()
            try: nc[k]=int(raw)
            except ValueError:
                try: nc[k]=float(raw)
                except ValueError: nc[k]=raw
        save_config(nc)
        self._lbl_vol_ad.configure(text=f"{nc.get('volume_anuncio',100)}%")
        self._lbl_vol_ot.configure(text=f"{nc.get('volume_outros',10)}%")
        messagebox.showinfo("Salvo","Configuração salva!")

    def _cmd_deactivate(self):
        if not messagebox.askyesno("Desativar","Desativar e reiniciar o pareamento?\nO software será fechado."): return
        clear_activation()
        self.root.destroy()

    # ── Poll ──────────────────────────────────────────────────────
    def _poll(self):
        try:
            while True:
                e=EVQ.get_nowait(); t=e["t"]
                if t=="log": self._log(e["msg"],e.get("lvl","INFO"))
                elif t=="now_playing":
                    nome,lp,tl,pl=e["nome"],e["loop"],e["total"],e["pl"]
                    self._lbl_tag.configure(text="REPRODUZINDO",fg=PURPLE)
                    self._lbl_title.configure(text=nome)
                    ls=f"  ·  Loop {lp}/{tl}" if tl>1 else ""
                    self._lbl_meta.configure(text=f"{pl}{ls}" if pl else (ls.strip(" · ") or "—"))
                    self._s_st.configure(text="Tocando",fg=WARN)
                    self._s_loop.configure(text=f"{lp}/{tl}" if tl>1 else "1×",fg=PURPLE)
                    self._set_status("Reproduzindo",WARN)
                    self._start_eq(); self._prog_var.set(0)
                    self._switch_page("Fila")
                elif t=="pl_start":
                    itens=e["itens"]
                    self._render_queue(itens,0)
                    self._lbl_pl_atual.configure(text=f"▶  {e['nome']}")
                    self._s_pl.configure(text=e["nome"][:14]+("…" if len(e["nome"])>14 else ""))
                    self._s_faixas.configure(text=str(len(itens)))
                    self._refresh_playlists()
                elif t=="q_active": self._highlight_q(e["idx"])
                elif t=="pl_end":
                    self._stop_eq()
                    self._lbl_tag.configure(text="CONCLUÍDO",fg=GREEN)
                    self._s_st.configure(text="Pronto",fg=GREEN)
                    self._s_loop.configure(text="—",fg=MUTED)
                    self._set_status("Pronto",GREEN)
                    self._prog_var.set(100)
                    self._lbl_pl_atual.configure(text="")
                    self._refresh_playlists()
                elif t=="stopped":
                    self._stop_eq()
                    self._lbl_tag.configure(text="AGUARDANDO",fg=MUTED)
                    self._lbl_title.configure(text="Nenhuma mídia")
                    self._lbl_meta.configure(text="—")
                    self._s_st.configure(text="Parado",fg=MUTED)
                    self._s_loop.configure(text="—",fg=MUTED)
                    self._set_status("Pronto",GREEN)
                    self._prog_var.set(0); self._q_empty()
                    self._lbl_pl_atual.configure(text="")
                    ST.current_pl_id=""
                    self._refresh_playlists()
                elif t=="dl_pct": self._prog_var.set(e["pct"]*0.5)
                elif t=="firebase_ok":
                    self._set_status("Conectado",GREEN)
                    self._s_st.configure(text="Pronto",fg=GREEN)
                elif t=="firebase_err":
                    self._set_status("Firebase: erro",DANGER)
                    self._s_st.configure(text="Erro",fg=DANGER)
                elif t=="fb_data":
                    self._playlists=e.get("playlists",{})
                    self._anuncios=e.get("anuncios",{})
                    self._refresh_playlists()
                    self._s_faixas.configure(
                        text=str(sum(len(p.get("itens") or [])
                                     for p in self._playlists.values()
                                     if isinstance(p,dict))))
                    self._update_cache_label()
                elif t=="cache_done": self._update_cache_label()
        except queue.Empty: pass

        if ST.playing and ST.play_ts:
            el=time.time()-ST.play_ts
            self._lbl_tcur.configure(text=f"{int(el//60)}:{int(el%60):02d}")
            pct=min(99,self._prog_var.get()+0.10)
            if pct>50: self._prog_var.set(pct)

        self.root.after(120, self._poll)

    def run(self): self.root.mainloop()


# ── Bootstrap ─────────────────────────────────────────────────────
def start_backend(app: App, uid: str):
    """Inicia backend Firebase depois da ativação."""
    if not start_firebase(uid):
        ev("firebase_err"); return

    cfg = load_config()
    load_local_data()
    if ST.local_playlists or ST.local_anuncios:
        ev("fb_data", playlists=ST.local_playlists, anuncios=ST.local_anuncios)

    fb_status(None)
    fb_log(f"PlayAds iniciado — {ST.email}", "ok")
    ev("firebase_ok")

    threading.Thread(target=heartbeat,       args=(cfg,), daemon=True).start()
    threading.Thread(target=check_schedules, args=(cfg,), daemon=True).start()
    threading.Thread(target=setup_listeners, args=(cfg,), daemon=True).start()
    threading.Thread(target=precache_all,    daemon=True).start()

    cfg2 = load_config()
    app._lbl_vol_ad.configure(text=f"{cfg2.get('volume_anuncio',100)}%")
    app._lbl_vol_ot.configure(text=f"{cfg2.get('volume_outros',10)}%")
    app._update_activation_page()

    log.info(f"✅ Backend ativo para: {ST.email}")
    if HAS_PYCAW:  log.info("✅ pycaw — duck habilitado")
    else:          log.warning("⚠ pycaw não instalado")
    if HAS_YTDLP:  log.info("✅ yt-dlp — YouTube habilitado")
    else:          log.warning("⚠ yt-dlp não instalado")


def main():
    activation = load_activation()

    def on_activated(uid, email, codigo):
        ST.uid    = uid
        ST.email  = email
        ST.codigo = codigo
        # Abre o player principal
        app = App()
        threading.Thread(target=start_backend, args=(app, uid), daemon=True).start()
        app.run()

    if activation:
        # Já ativado — vai direto para o player
        on_activated(activation["uid"], activation["email"], activation["codigo"])
    else:
        # Mostra tela de ativação primeiro
        act_screen = ActivationScreen(on_activated)
        act_screen.run()


if __name__ == "__main__":
    main()