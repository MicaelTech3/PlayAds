// src/pages/AtivarPlayer.jsx
import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { usePlayers } from "../hooks/useFirebase";
import { Monitor, Copy, CheckCircle, RefreshCw, Wifi, WifiOff, Music2 } from "lucide-react";

export default function AtivarPlayer() {
  const { userData }     = useAuth();
  const { playerStatus } = usePlayers();
  const [copied, setCopied]   = useState(false);
  const [now, setNow]         = useState(Date.now());

  // Atualiza "online há X segundos" em tempo real
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(t);
  }, []);

  const codigo  = userData?.codigo  ?? "—";
  const online  = playerStatus?.last_seen
    ? (now - playerStatus.last_seen) < 30000
    : false;

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(codigo);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch(_) {}
  };

  const lastSeenStr = playerStatus?.last_seen
    ? new Date(playerStatus.last_seen).toLocaleString("pt-BR")
    : "Nunca conectou";

  return (
    <div style={s.wrap}>
      {/* Header */}
      <div style={s.header}>
        <div style={s.headerGrad}/>
        <div style={s.headerContent}>
          <div style={s.headerIcon}><Monitor size={48} color="rgba(155,89,245,.6)"/></div>
          <div>
            <div style={s.headerSub}>Configuração</div>
            <h1 style={s.headerTitle}>Ativar Player</h1>
            <div style={s.headerMeta}>Pareie o software PlayAds com sua conta</div>
          </div>
        </div>
      </div>

      <div style={s.content}>
        <div style={s.grid}>

          {/* Card: Código */}
          <div style={s.card}>
            <div style={s.cardHeader}>
              <div style={s.cardIconWrap}>
                <Monitor size={18} color="#9b59f5"/>
              </div>
              <span style={s.cardTitle}>Seu Código de Ativação</span>
            </div>

            <div style={s.codigoWrap}>
              <div style={s.codigoBox}>
                <span style={s.codigoText}>{codigo}</span>
              </div>
              <button style={{ ...s.copyBtn, ...(copied ? s.copyBtnOk : {}) }} onClick={copiar}>
                {copied
                  ? <><CheckCircle size={14}/> Copiado!</>
                  : <><Copy size={14}/> Copiar</>
                }
              </button>
            </div>

            <div style={s.steps}>
              <p style={s.stepsTitle}>Como ativar:</p>
              {[
                ["1", "Abra o software PlayAds no computador"],
                ["2", "Clique no ícone  🔑  na sidebar"],
                ["3", "Cole o código acima e clique em Ativar"],
                ["4", "O player ficará online e pronto para receber playlists"],
              ].map(([n, t]) => (
                <div key={n} style={s.step}>
                  <div style={s.stepNum}>{n}</div>
                  <span style={s.stepText}>{t}</span>
                </div>
              ))}
            </div>

            <div style={s.infoBox}>
              <span style={s.infoIcon}>🔒</span>
              <p style={s.infoText}>
                Este código é único e vinculado à sua conta.<br/>
                Ele não expira — mas um código só pode ativar um player por vez.
              </p>
            </div>
          </div>

          {/* Card: Status do player */}
          <div style={s.card}>
            <div style={s.cardHeader}>
              <div style={s.cardIconWrap}>
                {online
                  ? <Wifi size={18} color="#10b981"/>
                  : <WifiOff size={18} color="#7a7490"/>
                }
              </div>
              <span style={s.cardTitle}>Status do Player</span>
              <div style={{
                ...s.statusBadge,
                background: online ? "rgba(16,185,129,.12)" : "rgba(122,116,144,.1)",
                color:      online ? "#10b981" : "#7a7490",
              }}>
                {online ? "● Online" : "○ Offline"}
              </div>
            </div>

            {playerStatus ? (
              <div style={s.statusContent}>
                <div style={s.statusRow}>
                  <span style={s.statusLabel}>Nome</span>
                  <span style={s.statusValue}>{playerStatus.nome || "—"}</span>
                </div>
                <div style={s.statusRow}>
                  <span style={s.statusLabel}>Versão</span>
                  <span style={s.statusValue}>v{playerStatus.versao || "?"}</span>
                </div>
                <div style={s.statusRow}>
                  <span style={s.statusLabel}>Sistema</span>
                  <span style={s.statusValue}>{playerStatus.plataforma || "—"}</span>
                </div>
                <div style={s.statusRow}>
                  <span style={s.statusLabel}>Último contato</span>
                  <span style={s.statusValue}>{lastSeenStr}</span>
                </div>
                <div style={s.divider}/>
                <div style={s.nowPlaying}>
                  <Music2 size={14} color={playerStatus.reproducao_atual ? "#9b59f5" : "#7a7490"}/>
                  <span style={{
                    color: playerStatus.reproducao_atual ? "#f0eeff" : "#7a7490",
                    fontSize: 13,
                  }}>
                    {playerStatus.reproducao_atual || "Aguardando reprodução..."}
                  </span>
                </div>

                {online && (
                  <div style={s.onlinePulse}>
                    <div style={s.pulseRing}/>
                    <span style={s.onlineText}>Conectado e sincronizando em tempo real</span>
                  </div>
                )}
              </div>
            ) : (
              <div style={s.noPlayer}>
                <Monitor size={40} color="#332f4d"/>
                <p style={s.noPlayerTitle}>Nenhum player ativado</p>
                <p style={s.noPlayerSub}>
                  Siga os passos ao lado para parear o software com sua conta
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Download section */}
        <div style={s.downloadCard}>
          <div style={s.downloadLeft}>
            <div style={s.downloadIcon}>📦</div>
            <div>
              <div style={s.downloadTitle}>Software PlayAds</div>
              <div style={s.downloadSub}>
                Requer Python 3.9+ · Windows 10/11<br/>
                Dependências: <code style={s.code}>pip install pygame firebase-admin requests yt-dlp pycaw</code>
              </div>
            </div>
          </div>
          <div style={s.downloadRight}>
            <div style={s.reqItem}><span style={s.reqDot}>●</span> Python 3.9+</div>
            <div style={s.reqItem}><span style={s.reqDot}>●</span> yt-dlp (YouTube)</div>
            <div style={s.reqItem}><span style={s.reqDot}>●</span> pycaw (duck de volume)</div>
          </div>
        </div>
      </div>
    </div>
  );
}

const s = {
  wrap: { overflowY: "auto", flex: 1 },
  header: { position: "relative", padding: "44px 32px 24px" },
  headerGrad: {
    position: "absolute",
    inset: 0,
    background: "linear-gradient(135deg, #1e1050 0%, #130d38 50%, transparent 100%)",
  },
  headerContent: { position: "relative", zIndex: 1, display: "flex", alignItems: "flex-end", gap: 20 },
  headerIcon: {
    width: 76,
    height: 76,
    background: "rgba(124,58,237,.15)",
    borderRadius: 12,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    // CORREÇÃO AQUI:
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "rgba(124,58,237,.3)",
  },
  headerSub: { fontSize: 11, fontWeight: 700, color: "#9b59f5", textTransform: "uppercase", letterSpacing: 1.5 },
  headerTitle: { fontSize: 32, fontWeight: 800, color: "#f0eeff", marginBottom: 4 },
  headerMeta: { fontSize: 13, color: "#7a7490" },

  content: { padding: "24px 32px 60px" },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 },

  card: {
    background: "#13111f",
    borderRadius: 14,
    padding: "24px",
    // CORREÇÃO AQUI:
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "#221f33",
    display: "flex",
    flexDirection: "column",
    gap: 20,
  },
  cardHeader: { display: "flex", alignItems: "center", gap: 10 },
  cardIconWrap: {
    width: 36,
    height: 36,
    background: "rgba(155,89,245,.1)",
    borderRadius: 10,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  cardTitle: { fontSize: 15, fontWeight: 700, color: "#f0eeff", flex: 1 },
  statusBadge: {
    fontSize: 11,
    fontWeight: 700,
    padding: "3px 10px",
    borderRadius: 20,
    letterSpacing: .3,
  },

  // Código
  codigoWrap: { display: "flex", flexDirection: "column", alignItems: "center", gap: 14, padding: "8px 0" },
  codigoBox: {
    background: "linear-gradient(135deg, #1e1050, #2a1b6e)",
    // CORREÇÃO AQUI:
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "rgba(155,89,245,.4)",
    borderRadius: 12,
    padding: "18px 32px",
    boxShadow: "0 0 40px rgba(124,58,237,.2)",
  },
  codigoText: {
    fontSize: 28,
    fontWeight: 800,
    color: "#f0eeff",
    fontFamily: "'DM Mono', monospace",
    letterSpacing: 4,
  },
  copyBtn: {
    display: "flex",
    alignItems: "center",
    gap: 7,
    background: "rgba(155,89,245,.12)",
    // CORREÇÃO AQUI:
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "rgba(155,89,245,.3)",
    borderRadius: 20,
    color: "#9b59f5",
    fontSize: 13,
    fontWeight: 600,
    padding: "8px 20px",
    cursor: "pointer",
    fontFamily: "'Figtree', sans-serif",
    transition: "all .2s",
  },
  copyBtnOk: {
    background: "rgba(16,185,129,.12)",
    borderColor: "rgba(16,185,129,.3)",
    color: "#10b981",
  },

  // Steps
  steps: { display: "flex", flexDirection: "column", gap: 10 },
  stepsTitle: { fontSize: 11, fontWeight: 700, color: "#7a7490", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 },
  step: { display: "flex", alignItems: "center", gap: 12 },
  stepNum: {
    width: 24,
    height: 24,
    background: "rgba(155,89,245,.15)",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 11,
    fontWeight: 800,
    color: "#9b59f5",
    flexShrink: 0,
  },
  stepText: { fontSize: 13, color: "#a89ec0" },

  infoBox: {
    display: "flex",
    gap: 12,
    background: "rgba(155,89,245,.06)",
    // CORREÇÃO AQUI:
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "rgba(155,89,245,.15)",
    borderRadius: 10,
    padding: "12px 14px",
  },
  infoIcon: { fontSize: 16, flexShrink: 0 },
  infoText: { fontSize: 12, color: "#7a7490", lineHeight: 1.6 },

  // Status
  statusContent: { display: "flex", flexDirection: "column", gap: 12 },
  statusRow: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  statusLabel: { fontSize: 12, color: "#7a7490" },
  statusValue: { fontSize: 13, color: "#f0eeff", fontWeight: 500 },
  divider: { height: 1, background: "#1a1728" },
  nowPlaying: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    background: "#1a1728",
    borderRadius: 8,
    padding: "10px 12px",
  },
  onlinePulse: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    background: "rgba(16,185,129,.06)",
    // CORREÇÃO AQUI:
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "rgba(16,185,129,.15)",
    borderRadius: 8,
    padding: "10px 14px",
  },
  pulseRing: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#10b981",
    flexShrink: 0,
    animation: "pulse-purple 2s infinite",
  },
  onlineText: { fontSize: 12, color: "#10b981", fontWeight: 500 },

  noPlayer: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 10,
    padding: "30px 0",
    flex: 1,
    justifyContent: "center",
  },
  noPlayerTitle: { fontSize: 16, fontWeight: 700, color: "#f0eeff" },
  noPlayerSub: { fontSize: 13, color: "#7a7490", textAlign: "center", maxWidth: 280, lineHeight: 1.5 },

  // Download
  downloadCard: {
    background: "#13111f",
    borderRadius: 14,
    padding: "20px 24px",
    // CORREÇÃO AQUI:
    borderWidth: "1px",
    borderStyle: "solid",
    borderColor: "#221f33",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 20,
  },
  downloadLeft: { display: "flex", alignItems: "center", gap: 16 },
  downloadIcon: { fontSize: 32, flexShrink: 0 },
  downloadTitle: { fontSize: 15, fontWeight: 700, color: "#f0eeff", marginBottom: 4 },
  downloadSub: { fontSize: 12, color: "#7a7490", lineHeight: 1.6 },
  downloadRight: { display: "flex", flexDirection: "column", gap: 6, flexShrink: 0 },
  reqItem: { display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#a89ec0" },
  reqDot: { color: "#9b59f5", fontSize: 8 },
  code: {
    background: "#1a1728",
    color: "#9b59f5",
    padding: "1px 6px",
    borderRadius: 4,
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
  },
};