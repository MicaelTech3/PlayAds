// src/components/Sidebar.jsx
import { useAuth } from "../context/AuthContext";
import { Home, Radio, ListMusic, Monitor, ScrollText, LogOut } from "lucide-react";

const NAV = [
  { id:"home",      icon:Home,       label:"Início" },
  { id:"anuncios",  icon:Radio,      label:"Anúncios" },
  { id:"playlists", icon:ListMusic,  label:"Playlists" },
  { id:"ativar",    icon:Monitor,    label:"Ativar Player" },
  { id:"logs",      icon:ScrollText, label:"Logs" },
];

export default function Sidebar({ view, setView }) {
  const { user, userData, logout } = useAuth();

  return (
    <div style={s.sidebar}>
      {/* Logo */}
      <div style={s.logo}>
        <div style={s.logoIcon}>
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <circle cx="11" cy="11" r="11" fill="#7c3aed"/>
            <polygon points="8,5 8,17 17,11" fill="white"/>
          </svg>
        </div>
        <span style={s.logoText}>PlayAds</span>
      </div>

      <div style={s.divider}/>

      {/* Nav */}
      <nav style={s.nav}>
        {NAV.map(({ id, icon:Icon, label }) => {
          const active = view === id;
          return (
            <button key={id} style={{ ...s.navItem, ...(active ? s.navActive : {}) }}
              onClick={() => setView(id)}>
              <Icon size={16} color={active ? "#9b59f5" : "#7a7490"}/>
              <span style={{ ...s.navLabel, color: active ? "#f0eeff" : "#7a7490" }}>
                {label}
              </span>
              {active && <div style={s.navIndicator}/>}

              {/* Badge "Ativar" se não tiver player */}
              {id === "ativar" && !userData?.player_ativo && (
                <div style={s.badge}>!</div>
              )}
            </button>
          );
        })}
      </nav>

      <div style={s.spacer}/>
      <div style={s.divider}/>

      {/* Usuário */}
      <div style={s.userSection}>
        <div style={s.avatar}>
          {user?.email?.[0]?.toUpperCase() ?? "U"}
        </div>
        <div style={s.userInfo}>
          <div style={s.userEmail}>{user?.email}</div>
          <div style={s.userCode}>
            {userData?.codigo
              ? <><span style={s.codeLabel}>Código</span> {userData.codigo}</>
              : "Carregando..."}
          </div>
        </div>
        <button style={s.logoutBtn} onClick={logout} title="Sair">
          <LogOut size={14} color="#7a7490"/>
        </button>
      </div>
    </div>
  );
}

const s = {
  sidebar: {
    width: 220,
    background: "#0d0b14",
    borderRight: "1px solid #1a1728",
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
  },
  logo: {
    display: "flex", alignItems: "center", gap: 10,
    padding: "20px 18px 16px",
  },
  logoIcon: {
    width: 32, height: 32, background: "rgba(124,58,237,.15)",
    borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center",
    border: "1px solid rgba(124,58,237,.2)",
  },
  logoText: {
    fontSize: 16, fontWeight: 800, color: "#f0eeff",
    letterSpacing: "-0.3px", fontFamily: "'Figtree', sans-serif",
  },
  divider: { height: 1, background: "#1a1728", margin: "0 14px" },
  nav: { display: "flex", flexDirection: "column", gap: 2, padding: "12px 10px" },
  navItem: {
    display: "flex", alignItems: "center", gap: 10,
    padding: "9px 10px", borderRadius: 8, cursor: "pointer",
    background: "transparent", border: "none",
    position: "relative", transition: "background .15s",
    fontFamily: "'Figtree', sans-serif", width: "100%",
    textAlign: "left",
  },
  navActive: { background: "rgba(155,89,245,.1)" },
  navLabel:  { fontSize: 13, fontWeight: 500, flex: 1 },
  navIndicator: {
    position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)",
    width: 3, height: 20, background: "#9b59f5", borderRadius: 2,
  },
  badge: {
    width: 16, height: 16, background: "#f43f5e",
    borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 10, fontWeight: 800, color: "#fff",
  },
  spacer: { flex: 1 },

  // Usuário
  userSection: {
    display: "flex", alignItems: "center", gap: 10,
    padding: "14px 14px",
  },
  avatar: {
    width: 30, height: 30, background: "rgba(155,89,245,.2)",
    borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 12, fontWeight: 700, color: "#9b59f5",
    flexShrink: 0, border: "1px solid rgba(155,89,245,.3)",
  },
  userInfo:  { flex: 1, overflow: "hidden", minWidth: 0 },
  userEmail: {
    fontSize: 11, color: "#a89ec0", fontWeight: 500,
    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
  },
  userCode: {
    fontSize: 10, color: "#7a7490", marginTop: 2,
    fontFamily: "'DM Mono', monospace",
    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
  },
  codeLabel: { color: "#332f4d", marginRight: 2 },
  logoutBtn: {
    background: "transparent", border: "none", cursor: "pointer",
    display: "flex", padding: 4, flexShrink: 0,
    borderRadius: 6, transition: "background .15s",
  },
};