// src/pages/Players.jsx
// Página unificada: Ativar Player + Status do Player
import { useState } from "react";
import { Monitor, Wifi, WifiOff, Activity, Copy, Check, Music2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { usePlayers } from "../hooks/useFirebase";

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button onClick={copy} style={s.copyBtn} title="Copiar código">
      {copied
        ? <Check size={14} color="#10b981" />
        : <Copy size={14} />
      }
      {copied ? "Copiado!" : "Copiar"}
    </button>
  );
}

function OfflineCard({ codigo }) {
  return (
    <div style={s.offlineCard}>
      {/* Ícone */}
      <div style={s.offlineIcon}>
        <Monitor size={36} color="rgba(155,89,245,.5)" />
      </div>

      <div style={s.offlineTitle}>Player não conectado</div>
      <div style={s.offlineSub}>
        Para ativar o PlayAds neste dispositivo, abra o software e insira o código abaixo.
      </div>

      {/* Código */}
      <div style={s.codeWrap}>
        <div style={s.codeLabel}>Código de Ativação</div>
        <div style={s.codeBox}>
          <span style={s.codeText}>{codigo || "—"}</span>
          {codigo && <CopyButton text={codigo} />}
        </div>
      </div>

      {/* Passos */}
      <div style={s.steps}>
        {[
          ["1", "Baixe e abra o", "PlayAds.exe"],
          ["2", "Digite o código acima na tela de", "ativação"],
          ["3", "O player aparecerá aqui como", "online"],
        ].map(([num, txt, bold]) => (
          <div key={num} style={s.step}>
            <div style={s.stepNum}>{num}</div>
            <span style={s.stepTxt}>
              {txt} <strong style={{ color: "#f0eeff" }}>{bold}</strong>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function OnlineCard({ player, codigo }) {
  const now        = Date.now();
  const lastSeen   = player.last_seen || 0;
  const online     = (now - lastSeen) < 35000;
  const lastSeenStr = lastSeen
    ? new Date(lastSeen).toLocaleString("pt-BR", {
        day: "2-digit", month: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      })
    : "—";

  return (
    <div style={s.onlineWrap}>
      {/* Header com código no canto */}
      <div style={s.onlineHeader}>
        <div style={s.onlineHeaderLeft}>
          <div style={{
            ...s.statusDot,
            background: online ? "#10b981" : "#332f4d",
            boxShadow: online ? "0 0 10px rgba(16,185,129,.5)" : "none",
          }} />
          <span style={s.onlineHeaderTitle}>
            {online ? "Player Online" : "Player Offline"}
          </span>
        </div>
        {/* Código pequeno no canto */}
        <div style={s.codeChip}>
          <span style={s.codeChipLabel}>Código:</span>
          <span style={s.codeChipVal}>{codigo}</span>
          <CopyButton text={codigo || ""} />
        </div>
      </div>

      {/* Card principal */}
      <div style={{ ...s.deviceCard, borderColor: online ? "rgba(155,89,245,.3)" : "#221f33" }}>
        {/* Cabeçalho do card */}
        <div style={s.deviceCardHead}>
          <div style={s.deviceIcon}>
            <Monitor size={22} color={online ? "#9b59f5" : "#7a7490"} />
          </div>
          <div style={s.deviceBadge(online)}>
            {online
              ? <><Wifi size={11} /> Online</>
              : <><WifiOff size={11} /> Offline</>
            }
          </div>
          {online && <div style={s.pulse} />}
        </div>

        {/* Nome */}
        <div style={s.deviceName}>{player.nome || "Player"}</div>
        <div style={s.deviceSub}>
          {player.plataforma || "—"} · v{player.versao || "?"}
        </div>

        <div style={s.divider} />

        {/* Reprodução atual */}
        <div style={s.deviceRow}>
          <Music2 size={13} color={player.reproducao_atual ? "#9b59f5" : "#7a7490"} />
          <span style={{
            fontSize: 13,
            color: player.reproducao_atual ? "#f0eeff" : "#7a7490",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {player.reproducao_atual || "Aguardando..."}
          </span>
        </div>

        {/* Último contato */}
        <div style={s.lastSeen}>
          Último contato: {lastSeenStr}
        </div>

        {/* Stats */}
        <div style={s.statsRow}>
          <div style={s.statBox}>
            <div style={s.statLabel}>Status</div>
            <div style={{ ...s.statVal, color: online ? "#10b981" : "#7a7490" }}>
              {online ? "● Ativo" : "○ Inativo"}
            </div>
          </div>
          <div style={s.statBox}>
            <div style={s.statLabel}>Versão</div>
            <div style={s.statVal}>{player.versao || "—"}</div>
          </div>
          <div style={s.statBox}>
            <div style={s.statLabel}>Sistema</div>
            <div style={{ ...s.statVal, fontSize: 11 }}>
              {(player.plataforma || "—").split(" ")[0]}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Players() {
  const { userData } = useAuth();
  const { playerStatus } = usePlayers();

  const codigo  = userData?.codigo || "";
  const hasPlayer = !!playerStatus;

  return (
    <div style={s.wrap}>
      {/* Page header */}
      <div style={s.pageHeader}>
        <div style={s.pageHeaderGrad} />
        <div style={{ position: "relative", zIndex: 1, display: "flex", alignItems: "flex-end", gap: 20 }}>
          <div style={s.headerIcon}>
            <Activity size={40} color="rgba(155,89,245,.6)" />
          </div>
          <div>
            <div style={s.headerSub}>Gerenciamento</div>
            <h1 style={s.headerTitle}>Player</h1>
            <div style={s.headerMeta}>
              <span style={{ color: hasPlayer ? "#10b981" : "#7a7490" }}>
                {hasPlayer ? "● Conectado" : "○ Aguardando conexão"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div style={s.content}>
        {hasPlayer
          ? <OnlineCard player={playerStatus} codigo={codigo} />
          : <OfflineCard codigo={codigo} />
        }
      </div>
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────────
const s = {
  wrap:    { overflowY: "auto", flex: 1 },
  content: { padding: "28px 32px 80px" },

  pageHeader: { position: "relative", padding: "44px 32px 24px" },
  pageHeaderGrad: {
    position: "absolute", inset: 0,
    background: "linear-gradient(135deg, #1e1050 0%, #130d38 50%, transparent 100%)",
  },
  headerIcon: {
    width: 72, height: 72,
    background: "rgba(124,58,237,.15)",
    borderRadius: 12,
    display: "flex", alignItems: "center", justifyContent: "center",
    border: "1px solid rgba(124,58,237,.3)",
  },
  headerSub:   { fontSize: 11, fontWeight: 700, color: "#9b59f5", textTransform: "uppercase", letterSpacing: 1.5 },
  headerTitle: { fontSize: 32, fontWeight: 800, color: "#f0eeff", margin: "4px 0" },
  headerMeta:  { fontSize: 13 },

  // ── Offline ──────────────────────────────────────────────────
  offlineCard: {
    background: "#13111f",
    border: "1px solid #221f33",
    borderRadius: 16,
    padding: "40px 36px",
    maxWidth: 500,
    display: "flex", flexDirection: "column", alignItems: "center",
    gap: 16, textAlign: "center",
  },
  offlineIcon: {
    width: 80, height: 80,
    background: "rgba(124,58,237,.1)",
    borderRadius: 20,
    display: "flex", alignItems: "center", justifyContent: "center",
    border: "1px solid rgba(124,58,237,.2)",
    marginBottom: 4,
  },
  offlineTitle: { fontSize: 20, fontWeight: 800, color: "#f0eeff" },
  offlineSub:   { fontSize: 13, color: "#7a7490", lineHeight: 1.6, maxWidth: 380 },

  codeWrap: { width: "100%", marginTop: 8 },
  codeLabel: {
    fontSize: 10, fontWeight: 700, color: "#7a7490",
    textTransform: "uppercase", letterSpacing: 1.5,
    marginBottom: 8, textAlign: "left",
  },
  codeBox: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    background: "#0d0b14",
    border: "1px solid rgba(155,89,245,.3)",
    borderRadius: 10, padding: "14px 16px",
  },
  codeText: {
    fontFamily: "'DM Mono', monospace",
    fontSize: 22, fontWeight: 700,
    color: "#b48eff", letterSpacing: 3,
  },

  steps: { width: "100%", display: "flex", flexDirection: "column", gap: 10, marginTop: 8 },
  step: {
    display: "flex", alignItems: "center", gap: 12,
    background: "#0d0b14", border: "1px solid #1a1728",
    borderRadius: 8, padding: "10px 14px", textAlign: "left",
  },
  stepNum: {
    width: 24, height: 24, borderRadius: "50%",
    background: "rgba(155,89,245,.15)",
    border: "1px solid rgba(155,89,245,.3)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 11, fontWeight: 800, color: "#9b59f5", flexShrink: 0,
  },
  stepTxt: { fontSize: 13, color: "#a89ec0" },

  copyBtn: {
    display: "flex", alignItems: "center", gap: 5,
    background: "rgba(155,89,245,.12)",
    border: "1px solid rgba(155,89,245,.25)",
    borderRadius: 20, color: "#9b59f5",
    fontSize: 11, fontWeight: 700,
    padding: "5px 12px", cursor: "pointer",
    whiteSpace: "nowrap",
  },

  // ── Online ───────────────────────────────────────────────────
  onlineWrap:  { maxWidth: 520 },
  onlineHeader: {
    display: "flex", alignItems: "center",
    justifyContent: "space-between", marginBottom: 16,
  },
  onlineHeaderLeft: { display: "flex", alignItems: "center", gap: 10 },
  onlineHeaderTitle: { fontSize: 16, fontWeight: 700, color: "#f0eeff" },
  statusDot: {
    width: 10, height: 10, borderRadius: "50%", transition: "all 0.3s",
  },

  codeChip: {
    display: "flex", alignItems: "center", gap: 8,
    background: "#13111f", border: "1px solid #221f33",
    borderRadius: 99, padding: "5px 12px",
  },
  codeChipLabel: { fontSize: 10, color: "#7a7490", fontWeight: 600 },
  codeChipVal: {
    fontFamily: "'DM Mono', monospace",
    fontSize: 12, fontWeight: 700, color: "#b48eff", letterSpacing: 1.5,
  },

  deviceCard: {
    background: "#13111f",
    borderRadius: 14, padding: "20px 22px",
    border: "1px solid",
    position: "relative", overflow: "hidden",
    display: "flex", flexDirection: "column", gap: 10,
    transition: "border-color .3s",
  },
  deviceCardHead: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
  },
  deviceIcon: {
    width: 44, height: 44, background: "#1a1728",
    borderRadius: 10,
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  deviceBadge: (online) => ({
    display: "flex", alignItems: "center", gap: 5,
    fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 20,
    background: online ? "rgba(155,89,245,.15)" : "rgba(122,116,144,.1)",
    color: online ? "#9b59f5" : "#7a7490",
  }),
  deviceName: { fontSize: 18, fontWeight: 700, color: "#f0eeff" },
  deviceSub:  { fontSize: 11, color: "#7a7490", fontFamily: "'DM Mono', monospace" },

  divider: { height: 1, background: "#1a1728", margin: "4px 0" },

  deviceRow: {
    display: "flex", alignItems: "center", gap: 8,
    overflow: "hidden",
  },
  lastSeen: {
    fontSize: 10, color: "#7a7490",
    fontFamily: "'DM Mono', monospace",
  },

  statsRow: { display: "flex", gap: 10, marginTop: 4 },
  statBox: {
    flex: 1, background: "#0d0b14",
    border: "1px solid #1a1728",
    borderRadius: 8, padding: "10px 12px",
    textAlign: "center",
  },
  statLabel: {
    fontSize: 9, fontWeight: 700, color: "#7a7490",
    textTransform: "uppercase", letterSpacing: 1, marginBottom: 5,
  },
  statVal: { fontSize: 13, fontWeight: 700, color: "#f0eeff" },

  pulse: {
    position: "absolute", top: 20, right: 20,
    width: 8, height: 8, borderRadius: "50%",
    background: "#9b59f5",
    animation: "pulse-purple 2s infinite",
  },
};