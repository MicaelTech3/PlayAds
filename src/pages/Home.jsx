// src/pages/Home.jsx
import { useAnuncios, usePlaylists, usePlayers } from "../hooks/useFirebase";
import { useToast } from "../components/Toast";
import { Activity, Radio, ListMusic, Zap, StopCircle } from "lucide-react";

function StatCard({ icon: Icon, value, label, color }) {
  return (
    <div style={s.statCard}>
      <div style={{ ...s.statIcon, background: color + "18" }}>
        <Icon size={20} color={color} />
      </div>
      <div style={s.statNum}>{value}</div>
      <div style={s.statLabel}>{label}</div>
    </div>
  );
}

export default function Home({ setView }) {
  const { anuncios  = {} }                   = useAnuncios();
  const { playlists = {}, playNow, stopNow } = usePlaylists();
  const { playerStatus }                     = usePlayers();
  const toast                                = useToast();

  const totalAnuncios  = Object.keys(anuncios).length;
  const totalPlaylists = Object.keys(playlists).length;
  const ativasCount    = Object.values(playlists).filter(p => p?.ativa).length;

  // playerStatus é um objeto único {last_seen, nome, ...} ou null (1 player por conta)
  const now         = Date.now();
  const onlineCount = playerStatus && (now - (playerStatus.last_seen || 0)) < 30000 ? 1 : 0;

  const recentAnuncios = Object.entries(anuncios)
    .sort(([,a],[,b]) => (b.criado_em||0)-(a.criado_em||0)).slice(0,6);
  const ativasArr = Object.entries(playlists).filter(([,p]) => p?.ativa).slice(0,4);

  return (
    <div style={s.wrap}>
      {/* Hero */}
      <div style={s.hero}>
        <div style={s.heroGrad} />
        <div style={s.heroOrb} />
        <div style={s.heroContent}>
          <div style={s.heroBadge}>
            <span style={s.heroBadgeDot} />
            PlayAds — Painel de Controle
          </div>
          <h1 style={s.heroTitle}>Boa tarde 👋</h1>
          <p style={s.heroSub}>Gerencie seus anúncios em tempo real</p>
          <button style={s.stopBtn}
            onClick={async () => { await stopNow(); toast("⏹ Parada enviada ao player!", "info"); }}>
            <StopCircle size={14} /> Parar player
          </button>
        </div>
      </div>

      <div style={s.content}>
        {/* Stats */}
        <div style={s.statsRow}>
          <StatCard icon={Radio}     value={totalAnuncios}  label="Anúncios"        color="#9b59f5" />
          <StatCard icon={ListMusic} value={totalPlaylists} label="Playlists"        color="#06b6d4" />
          <StatCard icon={Zap}       value={ativasCount}    label="Playlists Ativas" color="#f59e0b" />
          <StatCard icon={Activity}  value={onlineCount}    label="Player Online"    color="#10b981" />
        </div>

        {/* Playlists ativas */}
        {ativasArr.length > 0 && (
          <section style={s.section}>
            <div style={s.sectionHeader}>
              <h2 style={s.sectionTitle}>Playlists Ativas</h2>
              <button style={s.seeAll} onClick={() => setView("playlists")}>Ver todas →</button>
            </div>
            <div style={s.plGrid}>
              {ativasArr.map(([id, pl]) => (
                <div key={id} style={s.plCard}
                  onMouseEnter={e => { e.currentTarget.style.background="#1a1728"; e.currentTarget.style.borderColor="#332f4d"; }}
                  onMouseLeave={e => { e.currentTarget.style.background="#13111f"; e.currentTarget.style.borderColor="#221f33"; }}>
                  <div style={s.plCardThumb}
                    onMouseEnter={e => { const b=e.currentTarget.querySelector(".play-btn"); if(b) b.style.opacity="1"; }}
                    onMouseLeave={e => { const b=e.currentTarget.querySelector(".play-btn"); if(b) b.style.opacity="0"; }}>
                    <ListMusic size={28} color="#332f4d" />
                    <button className="play-btn" style={s.plPlayBtn}
                      onClick={async () => { await playNow(id); toast(`▶ "${pl.nome}" enviada!`, "success"); }}>
                      ▶
                    </button>
                  </div>
                  <div style={s.plCardName}>{pl.nome}</div>
                  <div style={s.plCardMeta}>{pl.itens?.length||0} faixas</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Anúncios recentes */}
        {recentAnuncios.length > 0 && (
          <section style={s.section}>
            <div style={s.sectionHeader}>
              <h2 style={s.sectionTitle}>Anúncios Recentes</h2>
              <button style={s.seeAll} onClick={() => setView("anuncios")}>Ver todos →</button>
            </div>
            <div style={s.trackList}>
              {recentAnuncios.map(([id, a], i) => (
                <div key={id} style={s.trackRow}
                  onMouseEnter={e => e.currentTarget.style.background="#1a1728"}
                  onMouseLeave={e => e.currentTarget.style.background="transparent"}>
                  <span style={s.trackNum}>{i+1}</span>
                  <div style={s.trackIcon}><Radio size={13} color="#9b59f5" /></div>
                  <div style={s.trackInfo}>
                    <span style={s.trackName}>{a.nome}</span>
                    <span style={s.trackMeta}>
                      {a.url?.includes("youtube") ? "YouTube" : a.tipo?.includes("wav") ? "WAV" : "MP3"}
                    </span>
                  </div>
                  <span style={s.trackSize}>
                    {a.tamanho ? (a.tamanho/1024/1024).toFixed(1)+" MB" : ""}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Estado vazio */}
        {totalAnuncios === 0 && totalPlaylists === 0 && (
          <div style={s.empty}>
            <div style={s.emptyIcon}>🎙</div>
            <p style={s.emptyTitle}>Nenhum conteúdo ainda</p>
            <p style={s.emptySub}>Adicione anúncios e crie playlists para começar</p>
            <div style={s.emptyBtns}>
              <button style={s.emptyBtn} onClick={() => setView("anuncios")}>+ Anúncio</button>
              <button style={s.emptyBtn} onClick={() => setView("playlists")}>+ Playlist</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const s = {
  wrap: { overflowY:"auto", flex:1 },
  hero: { position:"relative", padding:"44px 32px 28px", overflow:"hidden" },
  heroGrad: {
    position:"absolute", inset:0,
    background:"linear-gradient(135deg, #2d1b69 0%, #1a1040 60%, transparent 100%)", zIndex:0,
  },
  heroOrb: {
    position:"absolute", width:400, height:400, borderRadius:"50%",
    background:"rgba(124,58,237,.08)", top:-100, right:-80,
    filter:"blur(60px)", zIndex:0,
  },
  heroContent: { position:"relative", zIndex:1 },
  heroBadge: {
    display:"inline-flex", alignItems:"center", gap:7,
    background:"rgba(155,89,245,.12)", border:"1px solid rgba(155,89,245,.25)",
    borderRadius:20, color:"#9b59f5", fontSize:11, fontWeight:600,
    padding:"4px 12px", marginBottom:14, letterSpacing:.5,
  },
  heroBadgeDot: { width:6, height:6, borderRadius:"50%", background:"#9b59f5", display:"inline-block" },
  heroTitle: { fontSize:34, fontWeight:800, color:"#f0eeff", marginBottom:6 },
  heroSub:   { fontSize:14, color:"#7a7490", marginBottom:18 },
  stopBtn: {
    display:"inline-flex", alignItems:"center", gap:7,
    background:"rgba(244,63,94,.12)", border:"1px solid rgba(244,63,94,.25)",
    borderRadius:20, color:"#f43f5e", fontSize:12, fontWeight:600,
    padding:"7px 16px", cursor:"pointer", fontFamily:"'Figtree', sans-serif",
  },
  content:  { padding:"20px 32px 40px" },
  statsRow: { display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:12, marginBottom:36 },
  statCard: {
    background:"#13111f", borderRadius:12, padding:"18px",
    border:"1px solid #221f33", display:"flex", flexDirection:"column", gap:6,
  },
  statIcon:  { width:40, height:40, borderRadius:10, display:"flex", alignItems:"center", justifyContent:"center", marginBottom:2 },
  statNum:   { fontSize:28, fontWeight:800, color:"#f0eeff" },
  statLabel: { fontSize:12, color:"#7a7490", fontWeight:500 },
  section:   { marginBottom:36 },
  sectionHeader: { display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 },
  sectionTitle:  { fontSize:20, fontWeight:700, color:"#f0eeff" },
  seeAll: {
    background:"transparent", border:"none", color:"#7a7490",
    fontSize:12, fontWeight:600, cursor:"pointer", fontFamily:"'Figtree', sans-serif",
  },
  plGrid: { display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:12 },
  plCard: {
    background:"#13111f", borderRadius:10, padding:14,
    cursor:"pointer", transition:"background .2s, border-color .2s", border:"1px solid #221f33",
  },
  plCardThumb: {
    width:"100%", aspectRatio:"1", background:"#1a1728",
    borderRadius:8, display:"flex", alignItems:"center", justifyContent:"center",
    marginBottom:10, position:"relative", overflow:"hidden",
  },
  plPlayBtn: {
    position:"absolute", bottom:8, right:8, width:38, height:38, borderRadius:"50%",
    background:"linear-gradient(135deg, #7c3aed, #9b59f5)", border:"none", color:"#fff",
    fontSize:14, cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center",
    boxShadow:"0 4px 16px rgba(124,58,237,.4)", opacity:0, transition:"opacity .2s",
  },
  plCardName: { fontSize:13, fontWeight:700, color:"#f0eeff", marginBottom:3 },
  plCardMeta: { fontSize:11, color:"#7a7490" },
  trackList: {
    display:"flex", flexDirection:"column", background:"#13111f",
    borderRadius:12, overflow:"hidden", border:"1px solid #221f33",
  },
  trackRow: {
    display:"grid", gridTemplateColumns:"32px 36px 1fr 70px",
    alignItems:"center", gap:12, padding:"10px 16px",
    transition:"background .15s", borderBottom:"1px solid #1a1728",
  },
  trackNum:  { fontSize:13, color:"#7a7490", textAlign:"center", fontFamily:"'DM Mono', monospace" },
  trackIcon: { width:32, height:32, background:"rgba(155,89,245,.1)", borderRadius:6, display:"flex", alignItems:"center", justifyContent:"center" },
  trackInfo: { display:"flex", flexDirection:"column", gap:2, overflow:"hidden" },
  trackName: { fontSize:13, fontWeight:500, color:"#f0eeff", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" },
  trackMeta: { fontSize:10, color:"#7a7490" },
  trackSize: { fontSize:11, color:"#7a7490", fontFamily:"'DM Mono', monospace", textAlign:"right" },
  empty: { display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", padding:"60px 0", gap:8 },
  emptyIcon:  { fontSize:48, marginBottom:8 },
  emptyTitle: { fontSize:18, fontWeight:700, color:"#f0eeff" },
  emptySub:   { fontSize:13, color:"#7a7490", marginBottom:12 },
  emptyBtns:  { display:"flex", gap:10 },
  emptyBtn: {
    background:"rgba(155,89,245,.12)", border:"1px solid rgba(155,89,245,.25)",
    borderRadius:20, color:"#9b59f5", fontSize:13, fontWeight:600,
    padding:"8px 20px", cursor:"pointer", fontFamily:"'Figtree', sans-serif",
  },
};