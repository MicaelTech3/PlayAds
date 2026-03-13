// src/pages/Anuncios.jsx
import { useState, useRef } from "react";
import { useAnuncios } from "../hooks/useFirebase";
import { useToast } from "../components/Toast";
import { Upload, Trash2, Music, Plus, Youtube, Link } from "lucide-react";

const isYouTube = url => url && (url.includes("youtube.com") || url.includes("youtu.be"));

export default function Anuncios() {
  const { anuncios, loading, uploadAnuncio, deleteAnuncio, addUrlAnuncio } = useAnuncios();
  const toast    = useToast();
  const fileRef  = useRef(null);
  const [dragging,  setDragging]  = useState(false);
  const [progress,  setProgress]  = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showUrl,   setShowUrl]   = useState(false);
  const [urlInput,  setUrlInput]  = useState("");
  const [urlNome,   setUrlNome]   = useState("");

  const allowed = f => f && (f.name.match(/\.(mp3|wav)$/i) || f.type.startsWith("audio/"));

  const doUpload = async (file) => {
    if (!allowed(file)) { toast("Apenas MP3 ou WAV são aceitos", "error"); return; }
    setUploading(true); setProgress(0);
    try {
      await uploadAnuncio(file, setProgress);
      toast("Upload concluído!", "success");
    } catch (e) {
      toast("Erro no upload: " + e.message, "error");
    } finally { setUploading(false); setProgress(null); }
  };

  const doAddUrl = async () => {
    const url = urlInput.trim();
    if (!url) { toast("Digite uma URL válida", "error"); return; }
    const nome = urlNome.trim() || (isYouTube(url) ? "Vídeo YouTube" : url.split("/").pop()) || "Áudio URL";
    try {
      await addUrlAnuncio({ nome, url, tipo: isYouTube(url) ? "youtube" : "url" });
      toast("Mídia adicionada!", "success");
      setUrlInput(""); setUrlNome(""); setShowUrl(false);
    } catch(e) { toast("Erro: " + e.message, "error"); }
  };

  const handleDrop = e => {
    e.preventDefault(); setDragging(false);
    doUpload(e.dataTransfer.files[0]);
  };

  const handleDelete = async (id, filename) => {
    if (!window.confirm("Excluir este anúncio?")) return;
    await deleteAnuncio(id, filename);
    toast("Anúncio removido", "success");
  };

  const entries = Object.entries(anuncios).sort(([,a],[,b]) => (b.criado_em||0) - (a.criado_em||0));

  return (
    <div style={s.wrap}>
      {/* Header */}
      <div style={s.header}>
        <div style={s.headerGrad} />
        <div style={s.headerContent}>
          <div style={s.headerIcon}><Music size={52} color="rgba(255,255,255,.5)" /></div>
          <div>
            <div style={s.headerSub}>Biblioteca</div>
            <h1 style={s.headerTitle}>Anúncios</h1>
            <div style={s.headerMeta}>{entries.length} faixa{entries.length !== 1 ? "s" : ""}</div>
          </div>
        </div>
      </div>

      <div style={s.content}>
        {/* Upload area */}
        <div style={s.addRow}>
          <div
            style={{ ...s.dropZone, ...(dragging ? s.dropZoneActive : {}) }}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => !uploading && fileRef.current?.click()}
          >
            <input ref={fileRef} type="file" accept=".mp3,.wav,audio/*"
              style={{ display: "none" }} onChange={e => doUpload(e.target.files[0])} />
            {uploading ? (
              <div style={s.uploadingState}>
                <div style={s.progressWrap}>
                  <div style={{ ...s.progressFill, width: `${progress}%` }} />
                </div>
                <span style={s.uploadPct}>{progress}%</span>
              </div>
            ) : (
              <div style={s.dropContent}>
                <div style={s.dropIcon}><Upload size={22} color="#9b59f5" /></div>
                <span style={s.dropTitle}>Arraste MP3 / WAV ou clique</span>
                <span style={s.dropSub}>máx. 50 MB</span>
              </div>
            )}
          </div>

          <button
            style={{ ...s.urlBtn, ...(showUrl ? { borderColor: "#7c3aed", color: "#9b59f5" } : {}) }}
            onClick={() => setShowUrl(v => !v)}
          >
            <Link size={15} /> URL / YouTube
          </button>
        </div>

        {/* URL panel */}
        {showUrl && (
          <div style={s.urlPanel}>
            <div style={s.urlPanelInner}>
              <Youtube size={18} color="#f43f5e" style={{ flexShrink: 0 }} />
              <input type="text" placeholder="Nome (opcional)"
                value={urlNome} onChange={e => setUrlNome(e.target.value)}
                style={{ ...s.urlInput, flex: "0 0 180px" }} />
              <input type="url" placeholder="https://youtube.com/watch?v=... ou URL de áudio"
                value={urlInput} onChange={e => setUrlInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && doAddUrl()}
                style={{ ...s.urlInput, flex: 1 }} />
              <button style={s.urlAddBtn} onClick={doAddUrl}>
                <Plus size={14} /> Adicionar
              </button>
            </div>
            <p style={s.urlHint}>
              ✓ Suporta links do YouTube — o player irá baixar o áudio automaticamente via yt-dlp
            </p>
          </div>
        )}

        {/* Table */}
        {entries.length > 0 && (
          <div style={s.tableWrap}>
            <div style={s.tableHead}>
              <span style={{ ...s.thCell, flex: "0 0 36px" }}>#</span>
              <span style={{ ...s.thCell, flex: 1 }}>Título</span>
              <span style={{ ...s.thCell, flex: "0 0 80px" }}>Tipo</span>
              <span style={{ ...s.thCell, flex: "0 0 80px" }}>Tamanho</span>
              <span style={{ ...s.thCell, flex: "0 0 90px" }}>Ação</span>
            </div>
            <div style={s.divider} />
            {entries.map(([id, a], i) => {
              const yt = isYouTube(a.url || "");
              return (
                <div key={id} style={s.trackRow}
                  onMouseEnter={e => e.currentTarget.style.background = "#1a1728"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  <div style={{ ...s.tdCell, flex: "0 0 36px" }}>
                    <span style={s.trackNum}>{i+1}</span>
                  </div>
                  <div style={{ ...s.tdCell, flex: 1 }}>
                    <div style={{ ...s.trackThumb, background: yt ? "rgba(244,63,94,.15)" : "#1a1728" }}>
                      {yt ? <Youtube size={13} color="#f43f5e" /> : <Music size={13} color="#a89ec0" />}
                    </div>
                    <span style={s.trackName}>{a.nome}</span>
                  </div>
                  <span style={{ ...s.tdCell, flex: "0 0 80px", fontSize: 11 }}>
                    <span style={{
                      background: yt ? "rgba(244,63,94,.12)" : "rgba(155,89,245,.12)",
                      color: yt ? "#f43f5e" : "#9b59f5",
                      padding: "2px 8px", borderRadius: 20, fontWeight: 700, fontSize: 10,
                    }}>
                      {yt ? "YouTube" : a.tipo?.includes("wav") ? "WAV" : "MP3"}
                    </span>
                  </span>
                  <span style={{ ...s.tdCell, flex: "0 0 80px", color: "#7a7490", fontSize: 12, fontFamily: "'DM Mono', monospace" }}>
                    {a.tamanho ? (a.tamanho/1024/1024).toFixed(1)+" MB" : "—"}
                  </span>
                  <div style={{ ...s.tdCell, flex: "0 0 90px" }}>
                    <button style={s.delBtn} onClick={() => handleDelete(id, a.filename)}>
                      <Trash2 size={13} /> Excluir
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!loading && entries.length === 0 && (
          <div style={s.empty}>
            <Music size={44} color="#332f4d" />
            <p style={s.emptyText}>Nenhum anúncio ainda</p>
            <p style={s.emptySub}>Faça upload de MP3/WAV ou adicione um link do YouTube</p>
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
    background: "linear-gradient(135deg, #2d1b69 0%, #1a1040 50%, transparent 100%)",
  },
  headerContent: { position: "relative", zIndex: 1, display: "flex", alignItems: "flex-end", gap: 20 },
  headerIcon: {
    width: 76, height: 76, background: "rgba(124,58,237,.2)",
    borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center",
    border: "1px solid rgba(124,58,237,.3)",
  },
  headerSub:   { fontSize: 11, fontWeight: 700, color: "#9b59f5", textTransform: "uppercase", letterSpacing: 1.5 },
  headerTitle: { fontSize: 36, fontWeight: 800, color: "#f0eeff", marginBottom: 4 },
  headerMeta:  { fontSize: 13, color: "#7a7490" },
  content: { padding: "20px 32px 80px" },
  addRow: { display: "flex", gap: 12, marginBottom: 12, alignItems: "stretch" },
  dropZone: {
    flex: 1, border: "1.5px dashed #332f4d", borderRadius: 10,
    padding: "28px", display: "flex", alignItems: "center", justifyContent: "center",
    cursor: "pointer", transition: "border-color .2s, background .2s", background: "#13111f",
  },
  dropZoneActive: { borderColor: "#7c3aed", background: "rgba(124,58,237,.06)" },
  dropContent: { display: "flex", flexDirection: "column", alignItems: "center", gap: 8 },
  dropIcon: {
    width: 48, height: 48, background: "rgba(155,89,245,.1)", borderRadius: "50%",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  dropTitle: { fontSize: 14, fontWeight: 600, color: "#f0eeff" },
  dropSub:   { fontSize: 12, color: "#7a7490" },
  uploadingState: { display: "flex", flexDirection: "column", alignItems: "center", gap: 8, width: "100%" },
  progressWrap:   { width: "100%", height: 3, background: "#2a2740", borderRadius: 2 },
  progressFill:   { height: "100%", background: "#9b59f5", borderRadius: 2, transition: "width .2s" },
  uploadPct:      { fontSize: 12, color: "#9b59f5", fontFamily: "'DM Mono', monospace" },
  urlBtn: {
    display: "flex", alignItems: "center", gap: 7, flexShrink: 0,
    border: "1.5px dashed #332f4d", borderRadius: 10,
    color: "#7a7490", fontSize: 13, fontWeight: 600,
    padding: "0 20px", cursor: "pointer", background: "transparent",
    fontFamily: "'Figtree', sans-serif", transition: "all .2s",
  },
  urlPanel: {
    background: "#13111f", border: "1px solid #332f4d",
    borderRadius: 10, padding: "14px 16px", marginBottom: 20,
  },
  urlPanelInner: { display: "flex", gap: 10, alignItems: "center" },
  urlInput: {
    background: "#1a1728", border: "1px solid #332f4d", borderRadius: 6,
    color: "#f0eeff", fontSize: 13, padding: "9px 12px", outline: "none",
    fontFamily: "'Figtree', sans-serif",
  },
  urlAddBtn: {
    display: "flex", alignItems: "center", gap: 6, flexShrink: 0,
    background: "linear-gradient(135deg, #7c3aed, #9b59f5)", border: "none",
    borderRadius: 20, color: "#fff", fontSize: 13, fontWeight: 700,
    padding: "9px 16px", cursor: "pointer", fontFamily: "'Figtree', sans-serif",
  },
  urlHint: { fontSize: 11, color: "#7a7490", marginTop: 8 },
  tableWrap: { display: "flex", flexDirection: "column" },
  tableHead: { display: "flex", alignItems: "center", gap: 16, padding: "6px 12px 10px" },
  thCell: { fontSize: 10, fontWeight: 700, color: "#7a7490", letterSpacing: 1, textTransform: "uppercase" },
  divider: { height: 1, background: "#1a1728", marginBottom: 4 },
  trackRow: {
    display: "flex", alignItems: "center", gap: 16,
    padding: "10px 12px", borderRadius: 8, transition: "background .15s",
  },
  tdCell:    { display: "flex", alignItems: "center", gap: 10, overflow: "hidden" },
  trackNum:  { fontSize: 13, color: "#7a7490", width: 20, textAlign: "center", fontFamily: "'DM Mono', monospace" },
  trackThumb: {
    width: 34, height: 34, borderRadius: 6,
    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
  },
  trackName: { fontSize: 14, fontWeight: 500, color: "#f0eeff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  delBtn: {
    display: "flex", alignItems: "center", gap: 5,
    background: "transparent", border: "1px solid rgba(244,63,94,.25)",
    borderRadius: 16, color: "#f43f5e", fontSize: 11, fontWeight: 600,
    padding: "4px 10px", cursor: "pointer", fontFamily: "'Figtree', sans-serif",
  },
  empty: { display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "70px 0" },
  emptyText: { fontSize: 18, fontWeight: 700, color: "#f0eeff" },
  emptySub:  { fontSize: 13, color: "#7a7490" },
};