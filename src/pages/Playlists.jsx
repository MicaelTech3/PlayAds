// src/pages/Playlists.jsx
// Gerenciamento completo de playlists:
// - Adiciona anúncios já importados (biblioteca)
// - Mesmo anúncio pode aparecer várias vezes com horários diferentes
// - Nunca dois no mesmo horário dentro da mesma playlist (validação)
import { useState, useRef } from "react";
import {
  Plus, Trash2, Play, Edit3, Check, X, Clock, Music2,
  Youtube, ChevronDown, ChevronUp, GripVertical, Copy, AlertCircle
} from "lucide-react";
import { useAnuncios, usePlaylists } from "../hooks/useFirebase";
import { useToast } from "../components/Toast";

const isYT = url => url && (url.includes("youtube.com") || url.includes("youtu.be"));

// ── Horário picker ────────────────────────────────────────────────
function TimePicker({ value, onChange, disabled }) {
  const hours   = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
  const minutes = ["00", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55"];
  const [hh, mm] = value ? value.split(":") : ["", ""];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      <select
        value={hh || ""}
        onChange={e => onChange(e.target.value && mm ? `${e.target.value}:${mm || "00"}` : "")}
        disabled={disabled}
        style={sel}
      >
        <option value="">--</option>
        {hours.map(h => <option key={h} value={h}>{h}</option>)}
      </select>
      <span style={{ color: "#7a7490" }}>:</span>
      <select
        value={mm || ""}
        onChange={e => onChange(hh && e.target.value ? `${hh}:${e.target.value}` : "")}
        disabled={disabled}
        style={sel}
      >
        <option value="">--</option>
        {minutes.map(m => <option key={m} value={m}>{m}</option>)}
      </select>
    </div>
  );
}
const sel = {
  background: "#0d0b14", border: "1px solid #332f4d", borderRadius: 6,
  color: "#f0eeff", padding: "4px 6px", fontSize: 12, cursor: "pointer",
  outline: "none",
};

// ── Item de mídia na playlist ─────────────────────────────────────
function PlaylistItem({ item, idx, total, onRemove, onUpdate, onMove, horarioConflito }) {
  const yt = isYT(item.url || "");
  return (
    <div style={{ ...pi.row, borderLeft: horarioConflito ? "3px solid #f43f5e" : "3px solid transparent" }}>
      {/* Grip */}
      <div style={pi.grip}><GripVertical size={14} color="#332f4d" /></div>

      {/* Thumb */}
      <div style={{ ...pi.thumb, background: yt ? "rgba(244,63,94,.1)" : "rgba(155,89,245,.1)" }}>
        {yt ? <Youtube size={14} color="#f43f5e" /> : <Music2 size={14} color="#9b59f5" />}
      </div>

      {/* Nome */}
      <div style={pi.name}>{item.nome || item.url}</div>

      {/* Loops */}
      <div style={pi.loops}>
        <button style={pi.loopBtn}
          onClick={() => onUpdate(idx, { loops: Math.max(1, (item.loops||1) - 1) })}>
          −
        </button>
        <span style={pi.loopVal}>{item.loops || 1}×</span>
        <button style={pi.loopBtn}
          onClick={() => onUpdate(idx, { loops: Math.min(99, (item.loops||1) + 1) })}>
          +
        </button>
      </div>

      {/* Horário */}
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <TimePicker
          value={item.horario || ""}
          onChange={v => onUpdate(idx, { horario: v || null })}
        />
        {horarioConflito && (
          <div title="Horário duplicado na mesma playlist">
            <AlertCircle size={14} color="#f43f5e" />
          </div>
        )}
      </div>

      {/* Mover */}
      <div style={{ display: "flex", gap: 2 }}>
        <button style={pi.mv} onClick={() => onMove(idx, -1)} disabled={idx === 0}>
          <ChevronUp size={13} />
        </button>
        <button style={pi.mv} onClick={() => onMove(idx, 1)} disabled={idx === total - 1}>
          <ChevronDown size={13} />
        </button>
      </div>

      {/* Remover */}
      <button style={pi.del} onClick={() => onRemove(idx)}>
        <X size={14} />
      </button>
    </div>
  );
}
const pi = {
  row: {
    display: "flex", alignItems: "center", gap: 10,
    padding: "8px 12px", borderRadius: 8,
    background: "#13111f", marginBottom: 4,
    transition: "background .15s",
  },
  grip: { color: "#332f4d", cursor: "grab", flexShrink: 0 },
  thumb: {
    width: 32, height: 32, borderRadius: 6, flexShrink: 0,
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  name: {
    flex: 1, fontSize: 13, fontWeight: 500, color: "#f0eeff",
    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
  },
  loops: { display: "flex", alignItems: "center", gap: 2, flexShrink: 0 },
  loopBtn: {
    background: "#221f33", border: "none", color: "#9b59f5",
    width: 22, height: 22, borderRadius: 4, cursor: "pointer",
    fontSize: 14, fontWeight: 700, display: "flex",
    alignItems: "center", justifyContent: "center",
  },
  loopVal: {
    fontSize: 12, fontWeight: 700, color: "#f0eeff",
    fontFamily: "monospace", minWidth: 24, textAlign: "center",
  },
  mv: {
    background: "#221f33", border: "none", color: "#7a7490",
    width: 22, height: 22, borderRadius: 4, cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  del: {
    background: "rgba(244,63,94,.1)", border: "none", color: "#f43f5e",
    width: 28, height: 28, borderRadius: 6, cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center",
    flexShrink: 0,
  },
};

// ── Picker de anúncio da biblioteca ──────────────────────────────
function AnuncioPickerModal({ anuncios, onSelect, onClose }) {
  const [q, setQ] = useState("");
  const entries = Object.entries(anuncios)
    .filter(([, a]) => a.nome?.toLowerCase().includes(q.toLowerCase()))
    .sort(([, a], [, b]) => (a.nome || "").localeCompare(b.nome || ""));
  return (
    <div style={modal.overlay} onClick={onClose}>
      <div style={modal.box} onClick={e => e.stopPropagation()}>
        <div style={modal.header}>
          <span style={modal.title}>Adicionar da Biblioteca</span>
          <button style={modal.close} onClick={onClose}><X size={16} /></button>
        </div>
        <div style={modal.search}>
          <input
            autoFocus
            style={modal.inp}
            placeholder="Buscar anúncio..."
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>
        <div style={modal.list}>
          {entries.length === 0 && (
            <div style={{ color: "#7a7490", textAlign: "center", padding: 24 }}>
              Nenhum anúncio encontrado
            </div>
          )}
          {entries.map(([id, a]) => {
            const yt = isYT(a.url || "");
            return (
              <div
                key={id}
                style={modal.item}
                onMouseEnter={e => e.currentTarget.style.background = "#1a1728"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                onClick={() => onSelect(a)}
              >
                <div style={{
                  width: 30, height: 30, borderRadius: 6, flexShrink: 0,
                  background: yt ? "rgba(244,63,94,.1)" : "rgba(155,89,245,.1)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {yt ? <Youtube size={13} color="#f43f5e" /> : <Music2 size={13} color="#9b59f5" />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#f0eeff",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {a.nome}
                  </div>
                  <div style={{ fontSize: 11, color: "#7a7490", marginTop: 1 }}>
                    {yt ? "YouTube" : (a.tipo?.includes("wav") ? "WAV" : "MP3")}
                    {a.tamanho ? ` · ${(a.tamanho / 1024 / 1024).toFixed(1)} MB` : ""}
                  </div>
                </div>
                <Plus size={14} color="#9b59f5" />
              </div>
            );
          })}
        </div>
        <div style={modal.footer}>
          <span style={{ fontSize: 11, color: "#7a7490" }}>
            Clique para adicionar. O mesmo anúncio pode ser adicionado várias vezes com horários diferentes.
          </span>
        </div>
      </div>
    </div>
  );
}
const modal = {
  overlay: {
    position: "fixed", inset: 0, background: "rgba(0,0,0,.7)",
    display: "flex", alignItems: "center", justifyContent: "center",
    zIndex: 1000,
  },
  box: {
    background: "#13111f", borderRadius: 16, border: "1px solid #221f33",
    width: 480, maxHeight: "70vh", display: "flex", flexDirection: "column",
    boxShadow: "0 24px 64px rgba(0,0,0,.5)",
  },
  header: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "16px 20px 0",
  },
  title: { fontSize: 15, fontWeight: 700, color: "#f0eeff" },
  close: {
    background: "none", border: "none", color: "#7a7490", cursor: "pointer",
    width: 28, height: 28, borderRadius: 6, display: "flex",
    alignItems: "center", justifyContent: "center",
  },
  search: { padding: "12px 20px" },
  inp: {
    width: "100%", background: "#0d0b14", border: "1px solid #221f33",
    borderRadius: 8, color: "#f0eeff", padding: "8px 12px",
    fontSize: 13, outline: "none", boxSizing: "border-box",
  },
  list: { overflowY: "auto", flex: 1, padding: "0 20px" },
  item: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "10px 8px", borderRadius: 8, cursor: "pointer",
    transition: "background .12s",
  },
  footer: { padding: "12px 20px", borderTop: "1px solid #1a1728" },
};

// ── Editor de playlist ────────────────────────────────────────────
function PlaylistEditor({ playlist, plId, anuncios, onSave, onCancel }) {
  const [nome, setNome]   = useState(playlist?.nome || "");
  const [ativa, setAtiva] = useState(playlist?.ativa ?? true);
  const [itens, setItens] = useState(playlist?.itens || []);
  const [showPicker, setShowPicker] = useState(false);
  const [showUrlForm, setShowUrlForm] = useState(false);
  const [urlVal, setUrlVal] = useState("");
  const [urlNome, setUrlNome] = useState("");

  // Detecta horários duplicados dentro da mesma playlist
  const conflitos = new Set();
  const horarios = itens.map(it => it.horario).filter(Boolean);
  horarios.forEach((h, i) => {
    if (horarios.indexOf(h) !== i) {
      // Marca todos os índices com esse horário
      itens.forEach((it, idx) => { if (it.horario === h) conflitos.add(idx); });
    }
  });

  const updateItem = (idx, patch) => {
    setItens(prev => prev.map((it, i) => i === idx ? { ...it, ...patch } : it));
  };
  const removeItem = idx => setItens(prev => prev.filter((_, i) => i !== idx));
  const moveItem = (idx, dir) => {
    setItens(prev => {
      const arr = [...prev];
      const nIdx = idx + dir;
      if (nIdx < 0 || nIdx >= arr.length) return arr;
      [arr[idx], arr[nIdx]] = [arr[nIdx], arr[idx]];
      return arr;
    });
  };

  const addFromLibrary = (anuncio) => {
    setItens(prev => [...prev, {
      nome:    anuncio.nome,
      url:     anuncio.url,
      loops:   1,
      tipo:    anuncio.tipo || "url",
      horario: null,
    }]);
    setShowPicker(false);
  };

  const addFromUrl = () => {
    if (!urlVal.trim()) return;
    setItens(prev => [...prev, {
      nome:    urlNome.trim() || urlVal.trim(),
      url:     urlVal.trim(),
      loops:   1,
      tipo:    "url",
      horario: null,
    }]);
    setUrlVal(""); setUrlNome(""); setShowUrlForm(false);
  };

  const canSave = nome.trim() && conflitos.size === 0;

  return (
    <div style={ed.wrap}>
      {/* Header */}
      <div style={ed.header}>
        <div>
          <div style={ed.title}>{plId ? "Editar Playlist" : "Nova Playlist"}</div>
          <div style={ed.sub}>{itens.length} faixa{itens.length !== 1 ? "s" : ""}</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button style={btn.ghost} onClick={onCancel}><X size={14} /> Cancelar</button>
          <button
            style={{ ...btn.primary, opacity: canSave ? 1 : 0.5 }}
            disabled={!canSave}
            onClick={() => onSave({ nome: nome.trim(), ativa, itens })}
          >
            <Check size={14} /> Salvar
          </button>
        </div>
      </div>

      {/* Nome + ativa */}
      <div style={ed.meta}>
        <div style={ed.fieldWrap}>
          <label style={ed.label}>Nome da Playlist</label>
          <input
            style={ed.inp}
            value={nome}
            onChange={e => setNome(e.target.value)}
            placeholder="Ex: Comerciais da manhã"
          />
        </div>
        <label style={ed.toggle}>
          <input
            type="checkbox" checked={ativa}
            onChange={e => setAtiva(e.target.checked)}
            style={{ accentColor: "#9b59f5" }}
          />
          <span style={{ fontSize: 13, color: "#f0eeff", fontWeight: 500 }}>Playlist ativa</span>
        </label>
      </div>

      {/* Conflito aviso */}
      {conflitos.size > 0 && (
        <div style={ed.warn}>
          <AlertCircle size={14} />
          <span>Horários duplicados detectados (marcados em vermelho). Corrija antes de salvar.</span>
        </div>
      )}

      {/* Lista de itens */}
      <div style={ed.listWrap}>
        <div style={ed.listHeader}>
          <span style={ed.listTitle}>Faixas da Playlist</span>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={btn.sm} onClick={() => setShowPicker(true)}>
              <Music2 size={12} /> Da Biblioteca
            </button>
            <button style={btn.sm} onClick={() => setShowUrlForm(v => !v)}>
              <Plus size={12} /> URL Manual
            </button>
          </div>
        </div>

        {/* URL form */}
        {showUrlForm && (
          <div style={ed.urlForm}>
            <input
              style={{ ...ed.inp, flex: 1 }}
              placeholder="URL do áudio ou YouTube..."
              value={urlVal}
              onChange={e => setUrlVal(e.target.value)}
            />
            <input
              style={{ ...ed.inp, width: 180 }}
              placeholder="Nome (opcional)"
              value={urlNome}
              onChange={e => setUrlNome(e.target.value)}
            />
            <button style={btn.primary} onClick={addFromUrl}><Check size={13} /></button>
            <button style={btn.ghost} onClick={() => setShowUrlForm(false)}><X size={13} /></button>
          </div>
        )}

        {/* Itens */}
        <div style={ed.items}>
          {itens.length === 0 && (
            <div style={ed.empty}>
              <Music2 size={28} color="#332f4d" />
              <p>Adicione faixas da biblioteca ou por URL</p>
            </div>
          )}
          {itens.map((item, idx) => (
            <PlaylistItem
              key={idx}
              item={item}
              idx={idx}
              total={itens.length}
              onRemove={removeItem}
              onUpdate={updateItem}
              onMove={moveItem}
              horarioConflito={conflitos.has(idx)}
            />
          ))}
        </div>
      </div>

      {/* Picker modal */}
      {showPicker && (
        <AnuncioPickerModal
          anuncios={anuncios}
          onSelect={addFromLibrary}
          onClose={() => setShowPicker(false)}
        />
      )}
    </div>
  );
}
const ed = {
  wrap: { padding: "24px 32px", maxWidth: 860, margin: "0 auto" },
  header: { display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 },
  title: { fontSize: 22, fontWeight: 800, color: "#f0eeff" },
  sub: { fontSize: 13, color: "#7a7490", marginTop: 2 },
  meta: { display: "flex", alignItems: "flex-end", gap: 20, marginBottom: 16 },
  fieldWrap: { flex: 1 },
  label: { display: "block", fontSize: 11, fontWeight: 700, color: "#7a7490",
           textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 },
  inp: {
    width: "100%", background: "#0d0b14", border: "1px solid #221f33",
    borderRadius: 8, color: "#f0eeff", padding: "10px 12px",
    fontSize: 13, outline: "none", boxSizing: "border-box",
  },
  toggle: { display: "flex", alignItems: "center", gap: 8, cursor: "pointer", paddingBottom: 10 },
  warn: {
    display: "flex", alignItems: "center", gap: 8,
    background: "rgba(244,63,94,.1)", border: "1px solid rgba(244,63,94,.2)",
    borderRadius: 8, padding: "8px 14px", marginBottom: 12,
    color: "#f43f5e", fontSize: 12, fontWeight: 500,
  },
  listWrap: { background: "#0d0b14", borderRadius: 12, border: "1px solid #1a1728", padding: 16 },
  listHeader: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 },
  listTitle: { fontSize: 13, fontWeight: 700, color: "#f0eeff" },
  urlForm: { display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" },
  items: { display: "flex", flexDirection: "column" },
  empty: { display: "flex", flexDirection: "column", alignItems: "center",
           gap: 8, padding: "32px 0", color: "#7a7490", fontSize: 13 },
};
const btn = {
  primary: {
    display: "flex", alignItems: "center", gap: 6,
    background: "linear-gradient(135deg,#7c3aed,#9b59f5)",
    border: "none", borderRadius: 8, color: "#fff",
    fontSize: 12, fontWeight: 700, padding: "8px 16px", cursor: "pointer",
  },
  ghost: {
    display: "flex", alignItems: "center", gap: 6,
    background: "#13111f", border: "1px solid #221f33",
    borderRadius: 8, color: "#a89ec0",
    fontSize: 12, fontWeight: 600, padding: "8px 14px", cursor: "pointer",
  },
  sm: {
    display: "flex", alignItems: "center", gap: 5,
    background: "#1a1728", border: "1px solid #221f33",
    borderRadius: 6, color: "#9b59f5",
    fontSize: 11, fontWeight: 600, padding: "6px 12px", cursor: "pointer",
  },
  danger: {
    background: "rgba(244,63,94,.1)", border: "1px solid rgba(244,63,94,.2)",
    borderRadius: 6, color: "#f43f5e",
    fontSize: 11, fontWeight: 600, padding: "6px 10px", cursor: "pointer",
    display: "flex", alignItems: "center", gap: 4,
  },
};

// ── Página principal ──────────────────────────────────────────────
export default function Playlists() {
  const {
    playlists, criarPlaylist, togglePlaylist,
    deletePlaylist, salvarPlaylist, playNow,
  } = usePlaylists();
  const { anuncios } = useAnuncios();
  const toast = useToast();
  const [editing, setEditing]       = useState(null);
  const [sendingId, setSendingId]   = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  const entries = Object.entries(playlists)
    .filter(([, pl]) => pl && !pl.temp)
    .sort(([, a], [, b]) => (b.criado_em || 0) - (a.criado_em || 0));

  const handleSave = async (data) => {
    try {
      if (editing === "new") {
        const newId = await criarPlaylist(data.nome);
        await salvarPlaylist(newId, data);
        toast("Playlist criada!", "success");
      } else {
        await salvarPlaylist(editing, data);
        toast("Playlist atualizada!", "success");
      }
      setEditing(null);
    } catch (e) {
      toast("Erro: " + e.message, "error");
    }
  };

const handleDelete = async (id, nome) => {
    // Adicione 'window.' antes do confirm
    if (!window.confirm(`Excluir a playlist "${nome}"? Essa ação não pode ser desfeita.`)) return;
    
    try {
      await deletePlaylist(id);
      toast("Playlist excluída", "success");
    } catch (e) {
      toast("Erro: " + e.message, "error");
    }
};

  const handlePlay = async (id) => {
    setSendingId(id);
    try {
      await playNow(id);
      toast("Comando enviado ao player!", "success");
    } catch (e) {
      toast("Erro: " + e.message, "error");
    } finally {
      setSendingId(null);
    }
  };

  // Modo editor
  if (editing !== null) {
    const pl = editing === "new" ? null : playlists[editing];
    return (
      <div style={{ overflowY: "auto", flex: 1 }}>
        <PlaylistEditor
          playlist={pl}
          plId={editing === "new" ? null : editing}
          anuncios={anuncios}
          onSave={handleSave}
          onCancel={() => setEditing(null)}
        />
      </div>
    );
  }

  // Lista de playlists
  return (
    <div style={{ overflowY: "auto", flex: 1, padding: "0 0 80px" }}>
      {/* Header */}
      <div style={pg.header}>
        <div style={pg.headerGrad} />
        <div style={{ position: "relative", zIndex: 1 }}>
          <h1 style={pg.h1}>Playlists</h1>
          <p style={pg.sub}>{entries.length} playlist{entries.length !== 1 ? "s" : ""}</p>
        </div>
        <button style={{ ...btn.primary, position: "relative", zIndex: 1 }}
                onClick={() => setEditing("new")}>
          <Plus size={15} /> Nova Playlist
        </button>
      </div>

      {/* Empty */}
      {entries.length === 0 && (
        <div style={pg.empty}>
          <Music2 size={48} color="#332f4d" />
          <p style={{ fontSize: 18, fontWeight: 700, color: "#f0eeff", margin: "12px 0 4px" }}>
            Nenhuma playlist ainda
          </p>
          <p style={{ fontSize: 13, color: "#7a7490" }}>
            Clique em "Nova Playlist" para começar
          </p>
        </div>
      )}

      {/* Lista */}
      <div style={pg.list}>
        {entries.map(([id, pl]) => {
          const expanded = expandedId === id;
          const itens = pl.itens || [];
          const agendados = itens.filter(it => it.horario).length;
          const isSending = sendingId === id;

          return (
            <div key={id} style={pg.card}>
              {/* Card header */}
              <div style={pg.cardHead}>
                {/* Status dot */}
                <div style={{
                  width: 10, height: 10, borderRadius: "50%", flexShrink: 0,
                  background: pl.ativa ? "#10b981" : "#332f4d",
                  boxShadow: pl.ativa ? "0 0 6px #10b981" : "none",
                }} />

                {/* Nome + meta */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={pg.cardNome}>{pl.nome}</div>
                  <div style={pg.cardMeta}>
                    {itens.length} faixa{itens.length !== 1 ? "s" : ""}
                    {agendados > 0 && (
                      <span style={{ color: "#f59e0b", marginLeft: 8 }}>
                        <Clock size={10} style={{ verticalAlign: "middle" }} />
                        {" "}{agendados} agendado{agendados !== 1 ? "s" : ""}
                      </span>
                    )}
                    <span style={{ color: pl.ativa ? "#10b981" : "#7a7490", marginLeft: 8 }}>
                      {pl.ativa ? "Ativa" : "Inativa"}
                    </span>
                  </div>
                </div>

                {/* Ações */}
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <button
                    style={{ ...btn.primary, padding: "6px 12px", opacity: isSending ? 0.6 : 1 }}
                    onClick={() => handlePlay(id)}
                    disabled={isSending}
                  >
                    <Play size={12} fill="#fff" />
                    {isSending ? "Enviando..." : "Tocar"}
                  </button>
                  <button style={btn.ghost} onClick={() => setEditing(id)}>
                    <Edit3 size={13} />
                  </button>
                  <button style={btn.danger} onClick={() => handleDelete(id, pl.nome)}>
                    <Trash2 size={13} />
                  </button>
                  <button style={btn.ghost} onClick={() => setExpandedId(expanded ? null : id)}>
                    {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                  </button>
                </div>
              </div>

              {/* Faixas expandidas */}
              {expanded && (
                <div style={pg.expand}>
                  {itens.length === 0 && (
                    <div style={{ color: "#7a7490", fontSize: 13, padding: "8px 0" }}>
                      Playlist vazia
                    </div>
                  )}
                  {itens.map((item, idx) => {
                    const yt = isYT(item.url || "");
                    return (
                      <div key={idx} style={pg.trackRow}>
                        <span style={pg.trackNum}>{idx + 1}</span>
                        <div style={{
                          width: 26, height: 26, borderRadius: 5, flexShrink: 0,
                          background: yt ? "rgba(244,63,94,.1)" : "rgba(155,89,245,.1)",
                          display: "flex", alignItems: "center", justifyContent: "center",
                        }}>
                          {yt ? <Youtube size={12} color="#f43f5e" /> : <Music2 size={12} color="#9b59f5" />}
                        </div>
                        <span style={pg.trackName}>{item.nome}</span>
                        {item.loops > 1 && (
                          <span style={pg.badge}>{item.loops}×</span>
                        )}
                        {item.horario && (
                          <span style={{ ...pg.badge, background: "rgba(245,158,11,.12)",
                            color: "#f59e0b" }}>
                            <Clock size={9} style={{ verticalAlign: "middle" }} />
                            {" "}{item.horario}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const pg = {
  header: {
    position: "relative", padding: "36px 32px 24px",
    display: "flex", alignItems: "flex-end", justifyContent: "space-between",
  },
  headerGrad: {
    position: "absolute", inset: 0,
    background: "linear-gradient(135deg, #1a0a40 0%, #130d38 50%, transparent 100%)",
  },
  h1: { fontSize: 32, fontWeight: 800, color: "#f0eeff", margin: 0 },
  sub: { fontSize: 13, color: "#7a7490", margin: "4px 0 0" },
  empty: {
    display: "flex", flexDirection: "column", alignItems: "center",
    gap: 4, padding: "80px 0",
  },
  list: { padding: "0 24px" },
  card: {
    background: "#13111f", borderRadius: 12, border: "1px solid #1a1728",
    marginBottom: 12, overflow: "hidden",
  },
  cardHead: {
    display: "flex", alignItems: "center", gap: 14,
    padding: "16px 20px",
  },
  cardNome: { fontSize: 15, fontWeight: 700, color: "#f0eeff" },
  cardMeta: { fontSize: 12, color: "#7a7490", marginTop: 2 },
  expand: {
    borderTop: "1px solid #1a1728", padding: "12px 20px",
    background: "#0d0b14",
  },
  trackRow: {
    display: "flex", alignItems: "center", gap: 10,
    padding: "6px 0", borderBottom: "1px solid #13111f",
  },
  trackNum: { fontSize: 11, color: "#7a7490", fontFamily: "monospace", width: 18, textAlign: "right" },
  trackName: {
    flex: 1, fontSize: 13, color: "#f0eeff",
    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
  },
  badge: {
    fontSize: 10, fontWeight: 700,
    background: "rgba(155,89,245,.12)", color: "#9b59f5",
    padding: "2px 7px", borderRadius: 10,
  },
};