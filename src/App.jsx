// src/App.jsx  — PAINEL WEB
import { useState } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { PlayerProvider } from "./context/PlayerContext";
import { ToastProvider } from "./components/Toast";
import Login     from "./pages/Login";
import Sidebar   from "./components/Sidebar";
import Home      from "./pages/Home";
import All       from "./pages/All";
import Anuncios  from "./pages/Anuncios";
import Playlists from "./pages/Playlists";
import Players   from "./pages/Players";   // ← única aba (ativar + status)
import Logs      from "./pages/Logs";
import "./index.css";

function MainApp() {
  const { user, loadingUD } = useAuth();
  const [view, setView] = useState("home");

  if (user === undefined || loadingUD) {
    return (
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        height: "100vh", background: "#0d0b14", flexDirection: "column", gap: 16,
      }}>
        <div style={{
          width: 36, height: 36, border: "3px solid #221f33",
          borderTopColor: "#9b59f5", borderRadius: "50%",
          animation: "spin 1s linear infinite",
        }} />
        <span style={{ color: "#7a7490", fontSize: 13 }}>Carregando PlayAds...</span>
      </div>
    );
  }

  if (!user) return <Login />;

  const VIEWS = {
    home:      Home,
    all:       All,
    anuncios:  Anuncios,
    playlists: Playlists,
    players:   Players,   // ← "ativar" e "players" viram uma só rota
    logs:      Logs,
  };
  const Page = VIEWS[view] || Home;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar view={view} setView={setView} />
      <div style={{
        flex: 1, display: "flex", flexDirection: "column",
        overflow: "hidden", background: "#0d0b14",
      }}>
        <div style={{ flex: 1, overflowY: "auto" }}>
          <Page setView={setView} />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <PlayerProvider>
        <ToastProvider>
          <MainApp />
        </ToastProvider>
      </PlayerProvider>
    </AuthProvider>
  );
}