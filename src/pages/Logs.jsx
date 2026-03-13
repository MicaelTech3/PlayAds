// src/pages/Logs.jsx
import { useLogs } from "../hooks/useFirebase";
import { ScrollText, CheckCircle, XCircle, Info } from "lucide-react";

const StatusIcon = ({ status }) => {
  if (status === "ok")    return <CheckCircle size={13} color="#10b981"/>;
  if (status === "error") return <XCircle     size={13} color="#f43f5e"/>;
  return <Info size={13} color="#7a7490"/>;
};

export default function Logs() {
  const { logs } = useLogs();

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <div style={s.headerGrad}/>
        <div style={s.headerContent}>
          <div style={s.headerIcon}><ScrollText size={48} color="rgba(155,89,245,.6)"/></div>
          <div>
            <div style={s.headerSub}>Histórico</div>
            <h1 style={s.headerTitle}>Logs</h1>
            <div style={s.headerMeta}>{logs.length} registro{logs.length!==1?"s":""}</div>
          </div>
        </div>
      </div>

      <div style={s.content}>
        {logs.length === 0 && (
          <div style={s.empty}>
            <ScrollText size={44} color="#332f4d"/>
            <p style={s.emptyTitle}>Sem registros ainda</p>
            <p style={s.emptySub}>As execuções dos players aparecerão aqui em tempo real</p>
          </div>
        )}
        <div style={s.table}>
          {logs.map(l => (
            <div key={l.id} style={s.row}
              onMouseEnter={e => e.currentTarget.style.background="#13111f"}
              onMouseLeave={e => e.currentTarget.style.background="transparent"}>
              <StatusIcon status={l.status}/>
              <span style={s.time}>
                {l.timestamp ? new Date(l.timestamp).toLocaleString("pt-BR") : "—"}
              </span>
              <span style={s.player}>[{l.player_id||"player"}]</span>
              <span style={s.msg}>{l.mensagem}</span>
              <span style={{
                ...s.badge,
                color:      l.status==="ok" ? "#10b981" : l.status==="error" ? "#f43f5e" : "#7a7490",
                background: l.status==="ok" ? "rgba(16,185,129,.1)" : l.status==="error" ? "rgba(244,63,94,.1)" : "rgba(122,116,144,.1)",
              }}>
                {l.status || "info"}
              </span>
            </div>
          ))}
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
  headerMeta:  { fontSize:13, color:"#7a7490" },
  content: { padding:"20px 32px 80px" },
  table:   { display:"flex", flexDirection:"column", background:"#13111f", borderRadius:12, overflow:"hidden", border:"1px solid #221f33" },
  row: {
    display:"grid", gridTemplateColumns:"18px 155px 125px 1fr 55px",
    alignItems:"center", gap:14, padding:"11px 18px",
    borderBottom:"1px solid #1a1728", transition:"background .15s",
  },
  time:   { fontSize:11, color:"#7a7490", fontFamily:"'DM Mono', monospace", whiteSpace:"nowrap" },
  player: { fontSize:11, color:"#9b59f5", fontFamily:"'DM Mono', monospace", overflow:"hidden", textOverflow:"ellipsis" },
  msg:    { fontSize:12, color:"#f0eeff", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" },
  badge:  {
    fontSize:9, fontWeight:700, textTransform:"uppercase",
    padding:"2px 7px", borderRadius:20, fontFamily:"'DM Mono', monospace",
  },
  empty:      { display:"flex", flexDirection:"column", alignItems:"center", gap:10, padding:"70px 0" },
  emptyTitle: { fontSize:18, fontWeight:700, color:"#f0eeff" },
  emptySub:   { fontSize:13, color:"#7a7490", textAlign:"center" },
};