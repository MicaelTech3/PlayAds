// src/components/Sidebar.jsx
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

const NAV = [
  {
    id: "home",
    label: "Início",
    icon: (active) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H5a1 1 0 01-1-1V9.5z"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8"
          strokeLinejoin="round" fill={active ? "rgba(155,89,245,.15)" : "none"} />
        <path d="M9 21V12h6v9" stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: "all",
    label: "Todas Mídias",
    icon: (active) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="7" height="7" rx="1.5"
          fill={active ? "rgba(155,89,245,.2)" : "none"}
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8" />
        <rect x="14" y="3" width="7" height="7" rx="1.5"
          fill={active ? "rgba(155,89,245,.2)" : "none"}
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8" />
        <rect x="3" y="14" width="7" height="7" rx="1.5"
          fill={active ? "rgba(155,89,245,.2)" : "none"}
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8" />
        <rect x="14" y="14" width="7" height="7" rx="1.5"
          fill={active ? "rgba(155,89,245,.2)" : "none"}
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8" />
      </svg>
    ),
  },
  {
    id: "anuncios",
    label: "Anúncios",
    icon: (active) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="9"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8"
          fill={active ? "rgba(155,89,245,.1)" : "none"} />
        <path d="M9 8.5v7l6-3.5-6-3.5z"
          fill={active ? "#9b59f5" : "#6b6b80"} />
      </svg>
    ),
  },
  {
    id: "playlists",
    label: "Playlists",
    icon: (active) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M3 6h13M3 10h9M3 14h11M3 18h7"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="19" cy="15" r="3"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8"
          fill={active ? "rgba(155,89,245,.15)" : "none"} />
        <path d="M19 12V7l3-1" stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    id: "ativar",
    label: "Ativar Player",
    icon: (active) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <rect x="2" y="4" width="20" height="14" rx="2"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8"
          fill={active ? "rgba(155,89,245,.1)" : "none"} />
        <path d="M8 21h8M12 18v3"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="12" cy="11" r="2.5"
          fill={active ? "#9b59f5" : "#6b6b80"} />
        <path d="M8.5 8.5a5 5 0 017 0M6 6a8.5 8.5 0 0112 0"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.6"
          strokeLinecap="round" fill="none" />
      </svg>
    ),
  },
  {
    id: "players",
    label: "Players",
    icon: (active) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="13" rx="2"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8"
          fill={active ? "rgba(155,89,245,.1)" : "none"} />
        <path d="M7 20h10M12 16v4"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="12" cy="9.5" r="2"
          fill={active ? "#9b59f5" : "none"}
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.6" />
      </svg>
    ),
  },
  {
    id: "logs",
    label: "Logs",
    icon: (active) => (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <rect x="4" y="2" width="16" height="20" rx="2"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.8"
          fill={active ? "rgba(155,89,245,.1)" : "none"} />
        <path d="M8 7h8M8 11h6M8 15h4"
          stroke={active ? "#9b59f5" : "#6b6b80"} strokeWidth="1.7" strokeLinecap="round" />
      </svg>
    ),
  },
];

export default function Sidebar({ view, setView }) {
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  const w = collapsed ? 64 : 220;

  return (
    <div style={{
      width: w, minWidth: w, height: "100vh",
      background: "#0f0d1a",
      borderRight: "1px solid #1a1728",
      display: "flex", flexDirection: "column",
      transition: "width .22s cubic-bezier(.4,0,.2,1)",
      overflow: "hidden", flexShrink: 0,
      userSelect: "none",
    }}>
      {/* Logo */}
      <div style={{
        display: "flex", alignItems: "center",
        gap: 10, padding: collapsed ? "20px 0" : "20px 18px",
        justifyContent: collapsed ? "center" : "flex-start",
        borderBottom: "1px solid #1a1728",
        minHeight: 64,
      }}>
        {/* Logo icon */}
        <div style={{
          width: 32, height: 32, borderRadius: 9,
          background: "linear-gradient(135deg, #7c3aed, #9b59f5)",
          display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0, boxShadow: "0 4px 12px rgba(124,58,237,.4)",
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <polygon points="5,3 5,21 20,12" fill="white" />
          </svg>
        </div>
        {!collapsed && (
          <span style={{
            fontSize: 16, fontWeight: 800, color: "#f0eeff",
            letterSpacing: "-0.3px", whiteSpace: "nowrap",
            fontFamily: "'Figtree', sans-serif",
          }}>
            PlayAds
          </span>
        )}
      </div>

      {/* Nav items */}
      <nav style={{ flex: 1, padding: "10px 8px", display: "flex", flexDirection: "column", gap: 2 }}>
        {NAV.map(item => {
          const active = view === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              title={collapsed ? item.label : ""}
              style={{
                display: "flex", alignItems: "center",
                gap: 10, width: "100%",
                padding: collapsed ? "10px 0" : "9px 12px",
                justifyContent: collapsed ? "center" : "flex-start",
                background: active
                  ? "linear-gradient(90deg, rgba(124,58,237,.18), rgba(155,89,245,.08))"
                  : "transparent",
                border: "none",
                borderRadius: 10,
                cursor: "pointer",
                transition: "background .15s",
                position: "relative",
                overflow: "hidden",
              }}
              onMouseEnter={e => {
                if (!active) e.currentTarget.style.background = "rgba(255,255,255,.04)";
              }}
              onMouseLeave={e => {
                if (!active) e.currentTarget.style.background = "transparent";
              }}
            >
              {/* Active indicator */}
              {active && (
                <div style={{
                  position: "absolute", left: 0, top: "20%", bottom: "20%",
                  width: 3, borderRadius: 2,
                  background: "linear-gradient(180deg, #9b59f5, #7c3aed)",
                }} />
              )}
              <span style={{ flexShrink: 0, display: "flex" }}>
                {item.icon(active)}
              </span>
              {!collapsed && (
                <span style={{
                  fontSize: 13, fontWeight: active ? 600 : 500,
                  color: active ? "#f0eeff" : "#7a7490",
                  whiteSpace: "nowrap",
                  fontFamily: "'Figtree', sans-serif",
                  transition: "color .15s",
                }}>
                  {item.label}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom: user + collapse */}
      <div style={{
        borderTop: "1px solid #1a1728",
        padding: "10px 8px",
        display: "flex", flexDirection: "column", gap: 4,
      }}>
        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(v => !v)}
          title={collapsed ? "Expandir" : "Recolher"}
          style={{
            display: "flex", alignItems: "center",
            gap: 10, width: "100%",
            padding: collapsed ? "9px 0" : "9px 12px",
            justifyContent: collapsed ? "center" : "flex-start",
            background: "transparent", border: "none",
            borderRadius: 10, cursor: "pointer",
            transition: "background .15s",
          }}
          onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,.04)"}
          onMouseLeave={e => e.currentTarget.style.background = "transparent"}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
            style={{ transform: collapsed ? "rotate(180deg)" : "none", transition: "transform .22s", flexShrink: 0 }}>
            <path d="M15 6l-6 6 6 6" stroke="#6b6b80" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {!collapsed && (
            <span style={{ fontSize: 13, color: "#6b6b80", fontFamily: "'Figtree', sans-serif" }}>
              Recolher
            </span>
          )}
        </button>

        {/* User */}
        <button
          onClick={logout}
          title="Sair"
          style={{
            display: "flex", alignItems: "center",
            gap: 10, width: "100%",
            padding: collapsed ? "9px 0" : "9px 12px",
            justifyContent: collapsed ? "center" : "flex-start",
            background: "transparent", border: "none",
            borderRadius: 10, cursor: "pointer",
            transition: "background .15s",
          }}
          onMouseEnter={e => e.currentTarget.style.background = "rgba(244,63,94,.08)"}
          onMouseLeave={e => e.currentTarget.style.background = "transparent"}
        >
          {/* Avatar */}
          <div style={{
            width: 28, height: 28, borderRadius: 8, flexShrink: 0,
            background: "linear-gradient(135deg, #332f4d, #221f33)",
            border: "1px solid #332f4d",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 11, fontWeight: 700, color: "#9b59f5",
          }}>
            {user?.email?.[0]?.toUpperCase() || "?"}
          </div>
          {!collapsed && (
            <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
              <div style={{
                fontSize: 11, fontWeight: 600, color: "#a89ec0",
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                fontFamily: "'Figtree', sans-serif",
              }}>
                {user?.email || "Usuário"}
              </div>
              <div style={{ fontSize: 10, color: "#f43f5e", fontWeight: 500, marginTop: 1 }}>
                Sair
              </div>
            </div>
          )}
        </button>
      </div>
    </div>
  );
}