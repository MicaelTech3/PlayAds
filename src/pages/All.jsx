// src/pages/All.jsx
// Aba "All" — lista todas as mídias individualmente com "Tocar Agora" + loop selector
import { useState } from "react";
import { useAnuncios, usePlaylists } from "../hooks/useFirebase";
import { useToast } from "../components/Toast";
import { Music2, Youtube, Play, Layers, Search, Grid3x3, List } from "lucide-react";

const isYT = url => url && (url.includes("youtube.com") || url.includes("youtu.be"));

function LoopStepper({ value, onChange }) {
  return (
    <div style={ls.wrap}>
      <button style={ls.btn} onClick={() => onChange(Math.max(1, value - 1))}>−</button>
      <span style={ls.val}>{value}×</span>
      <button style={ls.btn} onClick={() => onChange(Math.min(99, value + 1))}>+</button>
    </div>
  );
}

const ls = {
  wrap: {
    display: "flex", alignItems: "center", gap: 0,
    background: "#0d0b14", borderRadius: 20,
    border: "1px solid #2a2740", overflow: "hidden",
  },
  btn: {
    background: "transparent", border: "none", color: "#9b59f5",
    fontSize: 16, fontWeight: 700, width: 28, height: 28,
    cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
    fontFamily: "monospace", transition: "background .15s",
  },
  val: {
    fontSize: 12, fontWeight: 700, color: "#f0eeff",
    fontFamily: "'DM Mono', monospace", minWidth: 28, textAlign: "center",
  },
};

export default function All() {
  const { anuncios } = useAnuncios();
  const { playNow, playlists } = usePlaylists();
  const toast = useToast();
  const [loops, setLoops] = useState({});       // { [id]: number }
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState("list"); // "list" | "grid"
  const [sending, setSending] = useState(null);

  const entries = Object.entries(anuncios)
    .sort(([, a], [, b]) => (b.criado_em || 0) - (a.criado_em || 0))
    .filter(([, a]) => a.nome?.toLowerCase().includes(search.toLowerCase()));

  const getLoops = (id) => loops[id] ?? 1;
  const setLoop = (id, n) => setLoops(prev => ({ ...prev, [id]: n }));

  const handlePlay = async (id, anuncio) => {
    setSending(id);
    try {
      await playNow(null, {
        nome:     anuncio.nome,
        url:      anuncio.url,
        loops:    getLoops(id),
        tipo:     anuncio.tipo,
        filename: anuncio.filename || null,
        tamanho:  anuncio.tamanho  || null,
      });
      toast(`▶ "${anuncio.nome}" enviado (${getLoops(id)}×)`, "success");
    } catch (e) {
      toast("Erro ao enviar: " + e.message, "error");
    } finally {
      setSending(null);
    }
  };

  return (
    <div style={s.wrap}>
      {/* Header */}
      <div style={s.header}>
        <div style={s.headerGrad} />
        <div style={s.headerContent}>
          <div style={s.headerIcon}>
            <Layers size={48} color="rgba(155,89,245,.6)" />
          </div>
          <div>
            <div style={s.headerSub}>Biblioteca Completa</div>
            <h1 style={s.headerTitle}>All Medias</h1>
            <div style={s.headerMeta}>
              {entries.length} faixa{entries.length !== 1 ? "s" : ""}
              {search && <span style={{ color: "#9b59f5", marginLeft: 8 }}>filtradas</span>}
            </div>
          </div>
        </div>
      </div>

      <div style={s.content}>
        {/* Toolbar */}
        <div style={s.toolbar}>
          <div style={s.searchWrap}>
            <Search size={14} color="#7a7490" style={{ flexShrink: 0 }} />
            <input
              style={s.searchInput}
              placeholder="Buscar mídia..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div style={s.viewToggle}>
            <button
              style={{ ...s.viewBtn, ...(viewMode === "list" ? s.viewBtnActive : {}) }}
              onClick={() => setViewMode("list")}
            >
              <List size={14} />
            </button>
            <button
              style={{ ...s.viewBtn, ...(viewMode === "grid" ? s.viewBtnActive : {}) }}
              onClick={() => setViewMode("grid")}
            >
              <Grid3x3 size={14} />
            </button>
          </div>
        </div>

        {/* Empty */}
        {entries.length === 0 && (
          <div style={s.empty}>
            <Music2 size={44} color="#332f4d" />
            <p style={s.emptyTitle}>{search ? "Nenhuma mídia encontrada" : "Nenhuma mídia ainda"}</p>
            <p style={s.emptySub}>Adicione anúncios na aba Anúncios para aparecerem aqui</p>
          </div>
        )}

        {/* LIST VIEW */}
        {viewMode === "list" && entries.length > 0 && (
          <div style={s.listWrap}>
            {/* Header row */}
            <div style={s.listHead}>
              <span style={{ ...s.th, flex: "0 0 36px" }}>#</span>
              <span style={{ ...s.th, flex: 1 }}>Título</span>
              <span style={{ ...s.th, flex: "0 0 80px", textAlign: "center" }}>Tipo</span>
              <span style={{ ...s.th, flex: "0 0 80px", textAlign: "center" }}>Tamanho</span>
              <span style={{ ...s.th, flex: "0 0 120px", textAlign: "center" }}>Loops</span>
              <span style={{ ...s.th, flex: "0 0 110px", textAlign: "center" }}>Ação</span>
            </div>
            <div style={s.divider} />

            {entries.map(([id, a], i) => {
              const yt = isYT(a.url || "");
              const isSending = sending === id;
              return (
                <div
                  key={id}
                  style={s.listRow}
                  onMouseEnter={e => e.currentTarget.style.background = "#1a1728"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                >
                  {/* # */}
                  <div style={{ ...s.td, flex: "0 0 36px" }}>
                    <span style={s.num}>{i + 1}</span>
                  </div>
                  {/* Title */}
                  <div style={{ ...s.td, flex: 1 }}>
                    <div style={{
                      ...s.thumb,
                      background: yt ? "rgba(244,63,94,.15)" : "rgba(155,89,245,.1)"
                    }}>
                      {yt
                        ? <Youtube size={13} color="#f43f5e" />
                        : <Music2 size={13} color="#9b59f5" />
                      }
                    </div>
                    <span style={s.trackName}>{a.nome}</span>
                  </div>
                  {/* Type */}
                  <div style={{ ...s.td, flex: "0 0 80px", justifyContent: "center" }}>
                    <span style={{
                      background: yt ? "rgba(244,63,94,.12)" : "rgba(155,89,245,.12)",
                      color: yt ? "#f43f5e" : "#9b59f5",
                      padding: "2px 8px", borderRadius: 20, fontWeight: 700, fontSize: 10,
                    }}>
                      {yt ? "YouTube" : a.tipo?.includes("wav") ? "WAV" : "MP3"}
                    </span>
                  </div>
                  {/* Size */}
                  <div style={{ ...s.td, flex: "0 0 80px", justifyContent: "center" }}>
                    <span style={{ color: "#7a7490", fontSize: 11, fontFamily: "'DM Mono', monospace" }}>
                      {a.tamanho ? (a.tamanho / 1024 / 1024).toFixed(1) + " MB" : "—"}
                    </span>
                  </div>
                  {/* Loops */}
                  <div style={{ ...s.td, flex: "0 0 120px", justifyContent: "center" }}>
                    <LoopStepper value={getLoops(id)} onChange={n => setLoop(id, n)} />
                  </div>
                  {/* Play */}
                  <div style={{ ...s.td, flex: "0 0 110px", justifyContent: "center" }}>
                    <button
                      style={{ ...s.playBtn, ...(isSending ? s.playBtnSending : {}) }}
                      onClick={() => handlePlay(id, a)}
                      disabled={isSending}
                    >
                      <Play size={12} fill={isSending ? "#7a7490" : "#fff"} />
                      {isSending ? "Enviando..." : "Tocar agora"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* GRID VIEW */}
        {viewMode === "grid" && entries.length > 0 && (
          <div style={s.grid}>
            {entries.map(([id, a]) => {
              const yt = isYT(a.url || "");
              const isSending = sending === id;
              return (
                <div key={id} style={s.gridCard}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = "#332f4d";
                    e.currentTarget.style.transform = "translateY(-2px)";
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = "#1a1728";
                    e.currentTarget.style.transform = "translateY(0)";
                  }}
                >
                  {/* Art */}
                  <div style={s.gridArt}>
                    <div style={{
                      width: 48, height: 48, borderRadius: 12,
                      background: yt ? "rgba(244,63,94,.15)" : "rgba(155,89,245,.12)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      {yt
                        ? <Youtube size={22} color="#f43f5e" />
                        : <Music2 size={22} color="#9b59f5" />
                      }
                    </div>
                    <span style={{
                      background: yt ? "rgba(244,63,94,.12)" : "rgba(155,89,245,.12)",
                      color: yt ? "#f43f5e" : "#9b59f5",
                      padding: "2px 8px", borderRadius: 20, fontWeight: 700, fontSize: 9,
                    }}>
                      {yt ? "YouTube" : a.tipo?.includes("wav") ? "WAV" : "MP3"}
                    </span>
                  </div>

                  <div style={s.gridName}>{a.nome}</div>
                  {a.tamanho && (
                    <div style={s.gridSize}>{(a.tamanho / 1024 / 1024).toFixed(1)} MB</div>
                  )}

                  {/* Loop + Play row */}
                  <div style={s.gridBottom}>
                    <LoopStepper value={getLoops(id)} onChange={n => setLoop(id, n)} />
                    <button
                      style={{ ...s.gridPlayBtn, ...(isSending ? s.playBtnSending : {}) }}
                      onClick={() => handlePlay(id, a)}
                      disabled={isSending}
                    >
                      <Play size={11} fill={isSending ? "#7a7490" : "#fff"} />
                      {isSending ? "..." : "Tocar"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

const s = {
  wrap: { overflowY: "auto", flex: 1 },
  header: { position: "relative", padding: "44px 32px 24px" },
  headerGrad: {
    position: "absolute", inset: 0,
    background: "linear-gradient(135deg, #1a0a40 0%, #130d38 50%, transparent 100%)",
  },
  headerContent: { position: "relative", zIndex: 1, display: "flex", alignItems: "flex-end", gap: 20 },
  headerIcon: {
    width: 76, height: 76, background: "rgba(124,58,237,.15)", borderRadius: 12,
    display: "flex", alignItems: "center", justifyContent: "center",
    border: "1px solid rgba(124,58,237,.3)",
  },
  headerSub: { fontSize: 11, fontWeight: 700, color: "#9b59f5", textTransform: "uppercase", letterSpacing: 1.5 },
  headerTitle: { fontSize: 36, fontWeight: 800, color: "#f0eeff", marginBottom: 4 },
  headerMeta: { fontSize: 13, color: "#7a7490" },

  content: { padding: "20px 32px 80px" },

  toolbar: { display: "flex", alignItems: "center", gap: 12, marginBottom: 20 },
  searchWrap: {
    flex: 1, display: "flex", alignItems: "center", gap: 10,
    background: "#13111f", border: "1px solid #221f33", borderRadius: 8,
    padding: "10px 14px",
  },
  searchInput: {
    background: "transparent", border: "none", outline: "none",
    color: "#f0eeff", fontSize: 13, flex: 1,
    fontFamily: "'Figtree', sans-serif",
  },
  viewToggle: {
    display: "flex", background: "#13111f", borderRadius: 8,
    border: "1px solid #221f33", overflow: "hidden",
  },
  viewBtn: {
    background: "transparent", border: "none", color: "#7a7490",
    padding: "8px 12px", cursor: "pointer", display: "flex",
    alignItems: "center", justifyContent: "center", transition: "all .15s",
  },
  viewBtnActive: { background: "rgba(155,89,245,.15)", color: "#9b59f5" },

  listWrap: {
    background: "#13111f", borderRadius: 12,
    border: "1px solid #221f33", overflow: "hidden",
  },
  listHead: {
    display: "flex", alignItems: "center", gap: 16,
    padding: "8px 16px 10px",
  },
  th: { fontSize: 10, fontWeight: 700, color: "#7a7490", letterSpacing: 1, textTransform: "uppercase" },
  divider: { height: 1, background: "#1a1728" },
  listRow: {
    display: "flex", alignItems: "center", gap: 16,
    padding: "10px 16px", borderBottom: "1px solid #13111f",
    transition: "background .15s",
  },
  td: { display: "flex", alignItems: "center", gap: 8, overflow: "hidden" },
  num: { fontSize: 12, color: "#7a7490", width: 22, textAlign: "center", fontFamily: "'DM Mono', monospace" },
  thumb: {
    width: 32, height: 32, borderRadius: 6,
    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
  },
  trackName: {
    fontSize: 13, fontWeight: 500, color: "#f0eeff",
    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
  },
  playBtn: {
    display: "flex", alignItems: "center", gap: 6,
    background: "linear-gradient(135deg, #7c3aed, #9b59f5)",
    border: "none", borderRadius: 20, color: "#fff",
    fontSize: 11, fontWeight: 700, padding: "6px 14px",
    cursor: "pointer", fontFamily: "'Figtree', sans-serif",
    transition: "opacity .15s", whiteSpace: "nowrap",
  },
  playBtnSending: {
    background: "#1a1728", color: "#7a7490",
    border: "1px solid #2a2740",
  },

  // Grid
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
    gap: 12,
  },
  gridCard: {
    background: "#13111f", borderRadius: 12, padding: "16px",
    border: "1px solid #1a1728", display: "flex", flexDirection: "column", gap: 8,
    transition: "border-color .2s, transform .2s", cursor: "default",
  },
  gridArt: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 },
  gridName: {
    fontSize: 13, fontWeight: 700, color: "#f0eeff",
    overflow: "hidden", textOverflow: "ellipsis",
    display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
    lineHeight: 1.4,
  },
  gridSize: { fontSize: 10, color: "#7a7490", fontFamily: "'DM Mono', monospace" },
  gridBottom: { display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 4 },
  gridPlayBtn: {
    display: "flex", alignItems: "center", gap: 5,
    background: "linear-gradient(135deg, #7c3aed, #9b59f5)",
    border: "none", borderRadius: 16, color: "#fff",
    fontSize: 11, fontWeight: 700, padding: "6px 12px",
    cursor: "pointer", fontFamily: "'Figtree', sans-serif",
    transition: "opacity .15s",
  },

  empty: { display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "80px 0" },
  emptyTitle: { fontSize: 18, fontWeight: 700, color: "#f0eeff" },
  emptySub: { fontSize: 13, color: "#7a7490" },
};