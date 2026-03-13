// src/pages/Players.jsx
import { usePlayers } from "../hooks/useFirebase";
import { Activity, Wifi, WifiOff, Music2, Monitor } from "lucide-react";

export default function Players() {
  const { players } = usePlayers();
  const now = Date.now();
  const entries = Object.entries(players).sort(([,a],[,b]) => (b.last_seen||0)-(a.last_seen||0));
  const onlineCount  = entries.filter(([,p]) => (now-(p.last_seen||0)) < 30000).length;
  const offlineCount = entries.length - onlineCount;

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <div style={s.headerGrad}/>
        <div style={s.headerContent}>
          <div style={s.headerIcon}><Activity size={48} color="rgba(155,89,245,.6)"/></div>
          <div>
            <div style={s.headerSub}>Status</div>
            <h1 style={s.headerTitle}>Players</h1>
            <div style={s.headerMeta}>
              <span style={{ color:"#10b981" }}>● {onlineCount} online</span>
              {offlineCount > 0 && <span style={{ color:"#7a7490", marginLeft:12 }}>○ {offlineCount} offline</span>}
            </div>
          </div>
        </div>
      </div>

      <div style={s.content}>
        {entries.length === 0 && (
          <div style={s.empty}>
            <Monitor size={44} color="#332f4d"/>
            <p style={s.emptyTitle}>Nenhum player conectado</p>
            <p style={s.emptySub}>Execute o PlayAds (player.py) para ver o status aqui</p>
          </div>
        )}
        <div style={s.grid}>
          {entries.map(([id, p]) => {
            const online  = (now-(p.last_seen||0)) < 30000;
            const lastSeen = p.last_seen ? new Date(p.last_seen).toLocaleString("pt-BR") : "—";
            return (
              <div key={id} style={{ ...s.card, ...(online ? s.cardOnline : s.cardOffline) }}>
                <div style={s.cardHeader}>
                  <div style={s.cardIcon}>
                    <Monitor size={20} color={online ? "#9b59f5" : "#7a7490"}/>
                  </div>
                  <div style={{ ...s.badge, background: online ? "rgba(155,89,245,.15)":"rgba(122,116,144,.1)", color: online ? "#9b59f5":"#7a7490" }}>
                    {online ? <><Wifi size={11}/> Online</> : <><WifiOff size={11}/> Offline</>}
                  </div>
                </div>
                <div style={s.cardName}>{p.nome || id}</div>
                <div style={s.cardId}>{id}</div>
                <div style={s.divider}/>
                <div style={s.detail}>
                  <Music2 size={12} color={p.reproducao_atual ? "#9b59f5":"#7a7490"}/>
                  <span style={{ color: p.reproducao_atual?"#f0eeff":"#7a7490", fontSize:12 }}>
                    {p.reproducao_atual || "Aguardando..."}
                  </span>
                </div>
                <div style={s.detail}>
                  <Monitor size={12} color="#7a7490"/>
                  <span style={{ color:"#a89ec0", fontSize:11, fontFamily:"'DM Mono', monospace" }}>
                    {p.plataforma || "—"} · v{p.versao || "?"}
                  </span>
                </div>
                <div style={s.lastSeen}>Último contato: {lastSeen}</div>
                {online && <div style={s.pulse}/>}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const s = {
  wrap: { overflowY:"auto", flex:1 },
  header: { position:"relative", padding:"44px 32px 24px" },
  headerGrad: {
    position:"absolute", inset:0,
    background:"linear-gradient(135deg, #1e1050 0%, #130d38 50%, transparent 100%)",
  },
  headerContent: { position:"relative", zIndex:1, display:"flex", alignItems:"flex-end", gap:20 },
  headerIcon: {
    width:76, height:76, background:"rgba(124,58,237,.15)",
    borderRadius:12, display:"flex", alignItems:"center", justifyContent:"center",
    border:"1px solid rgba(124,58,237,.3)",
  },
  headerSub:   { fontSize:11, fontWeight:700, color:"#9b59f5", textTransform:"uppercase", letterSpacing:1.5 },
  headerTitle: { fontSize:32, fontWeight:800, color:"#f0eeff", marginBottom:4 },
  headerMeta:  { fontSize:13, display:"flex", alignItems:"center" },
  content: { padding:"28px 32px 80px" },
  grid: { display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(270px, 1fr))", gap:14 },
  card: {
    background:"#13111f", borderRadius:12, padding:"18px 20px",
    position:"relative", overflow:"hidden",
    display:"flex", flexDirection:"column", gap:8,
    border:"1px solid #221f33", transition:"border-color .2s",
  },
  cardOnline:  { borderColor:"rgba(155,89,245,.3)" },
  cardOffline: { opacity:.65 },
  cardHeader:  { display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:4 },
  cardIcon: {
    width:42, height:42, background:"#1a1728",
    borderRadius:10, display:"flex", alignItems:"center", justifyContent:"center",
  },
  badge: {
    display:"flex", alignItems:"center", gap:5,
    fontSize:11, fontWeight:600, padding:"3px 10px", borderRadius:20,
  },
  cardName: { fontSize:17, fontWeight:700, color:"#f0eeff" },
  cardId:   { fontSize:10, color:"#7a7490", fontFamily:"'DM Mono', monospace" },
  divider:  { height:1, background:"#1a1728", margin:"4px 0" },
  detail:   { display:"flex", alignItems:"center", gap:7 },
  lastSeen: { fontSize:10, color:"#7a7490", marginTop:4, fontFamily:"'DM Mono', monospace" },
  pulse: {
    position:"absolute", top:18, right:20,
    width:8, height:8, borderRadius:"50%", background:"#9b59f5",
    animation:"pulse-purple 2s infinite",
  },
  empty: { display:"flex", flexDirection:"column", alignItems:"center", gap:10, padding:"70px 0" },
  emptyTitle: { fontSize:18, fontWeight:700, color:"#f0eeff" },
  emptySub:   { fontSize:13, color:"#7a7490", textAlign:"center", maxWidth:400 },
};