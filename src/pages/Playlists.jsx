// src/pages/Playlists.jsx
import { useState, useRef } from "react";
import {
  Plus, Trash2, Play, Edit3, Check, X, Clock, Music2,
  Youtube, ChevronDown, ChevronUp, GripVertical, AlertCircle,
  ToggleLeft, ToggleRight, Repeat, Timer
} from "lucide-react";
import { useAnuncios, usePlaylists } from "../hooks/useFirebase";
import { useToast } from "../components/Toast";

const isYT = url => url && (url.includes("youtube.com") || url.includes("youtu.be"));

// ── Horário picker inline ─────────────────────────────────────────
function TimePicker({ value, onChange }) {
  const hours   = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
  const minutes = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, "0"));

  // Estado interno independente — resolve o problema de hh ou mm vazio
  const [hh, setHh] = useState(() => value ? value.split(":")[0] : "");
  const [mm, setMm] = useState(() => value ? value.split(":")[1] : "");

  const handleHour = (h) => {
    setHh(h);
    const m = mm || "00";
    if (h) { setMm(m); onChange(`${h}:${m}`); }
    else   { onChange(""); }
  };

  const handleMin = (m) => {
    setMm(m);
    if (hh && m) onChange(`${hh}:${m}`);
    else if (!m) onChange("");
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      <select value={hh} onChange={e => handleHour(e.target.value)} style={sel}>
        <option value="">hh</option>
        {hours.map(h => <option key={h} value={h}>{h}</option>)}
      </select>
      <span style={{ color: "#7a7490", fontWeight: 700 }}>:</span>
      <select value={mm} onChange={e => handleMin(e.target.value)} style={sel}>
        <option value="">mm</option>
        {minutes.map(m => <option key={m} value={m}>{m}</option>)}
      </select>
    </div>
  );
}
const sel = {
  background: "#0d0b14", border: "1px solid #332f4d", borderRadius: 6,
  color: "#f0eeff", padding: "5px 7px", fontSize: 12, cursor: "pointer", outline: "none",
};

// ── Card de configuração da mídia (painel lateral/modal) ──────────
function MediaConfigPanel({ item, idx, totalItens, onClose, onSave, onPlay, onRemove, onMove, allHorarios }) {
  const [nome,    setNome]    = useState(item.nome || "");
  const [loops,   setLoops]   = useState(item.loops || 1);
  // horarios: array de strings "HH:MM" (pode ter vários)
  const [horarios, setHorarios] = useState(
    Array.isArray(item.horarios) && item.horarios.length > 0
      ? item.horarios
      : item.horario
        ? [item.horario]
        : [""]
  );

  const DIAS = [
    { key: "dom", label: "Dom" },
    { key: "seg", label: "Seg" },
    { key: "ter", label: "Ter" },
    { key: "qua", label: "Qua" },
    { key: "qui", label: "Qui" },
    { key: "sex", label: "Sex" },
    { key: "sab", label: "Sáb" },
  ];

  const [dias, setDias] = useState(
    Array.isArray(item.dias) && item.dias.length > 0
      ? item.dias
      : ["dom","seg","ter","qua","qui","sex","sab"]  // padrão: todos os dias
  );

  const toggleDia = (key) => {
    setDias(prev =>
      prev.includes(key)
        ? prev.length > 1 ? prev.filter(d => d !== key) : prev  // mínimo 1 dia
        : [...prev, key]
    );
  };

  const yt = isYT(item.url || "");

  const addHorario   = () => setHorarios(h => [...h, ""]);
  const removeHorario = i  => setHorarios(h => h.filter((_, idx2) => idx2 !== i));
  const updateHorario = (i, v) => setHorarios(h => h.map((x, idx2) => idx2 === i ? v : x));

  // Detecta duplicatas entre os horários deste item
  const filled = horarios.filter(Boolean);
  const hasDupe = filled.length !== new Set(filled).size;

  // Detecta conflito com outros itens na playlist (mesmo horário, diferente item)
  const conflitos = filled.filter(h => allHorarios.filter(x => x === h).length > 1);

  const handleSave = () => {
    const horariosLimpos = horarios.filter(Boolean);
    onSave({
      ...item,
      nome,
      loops,
      horarios: horariosLimpos,
      horario:  horariosLimpos[0] || null,
      dias,
    });
    onClose();
  };

  return (
    <div style={mp.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={mp.panel}>
        {/* Header */}
        <div style={mp.header}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, minWidth: 0 }}>
            <div style={{ ...mp.thumb, background: yt ? "rgba(244,63,94,.12)" : "rgba(155,89,245,.12)" }}>
              {yt ? <Youtube size={16} color="#f43f5e" /> : <Music2 size={16} color="#9b59f5" />}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={mp.title}>{item.nome}</div>
              <div style={mp.sub}>{yt ? "YouTube" : (item.tipo?.includes("wav") ? "WAV" : "MP3")}</div>
            </div>
          </div>
          <button style={mp.closeBtn} onClick={onClose}><X size={16} /></button>
        </div>

        <div style={mp.body}>
          {/* Nome */}
          <div style={mp.section}>
            <label style={mp.label}>Nome de exibição</label>
            <input
              style={mp.input}
              value={nome}
              onChange={e => setNome(e.target.value)}
              placeholder="Nome da mídia"
            />
          </div>

          {/* Loops */}
          <div style={mp.section}>
            <label style={mp.label}>
              <Repeat size={11} style={{ marginRight: 5, verticalAlign: "middle" }} />
              Repetições (loops)
            </label>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={mp.loopControl}>
                <button style={mp.loopBtn} onClick={() => setLoops(l => Math.max(1, l - 1))}>−</button>
                <span style={mp.loopVal}>{loops}</span>
                <button style={mp.loopBtn} onClick={() => setLoops(l => Math.min(99, l + 1))}>+</button>
              </div>
              <span style={{ fontSize: 12, color: "#7a7490" }}>
                {loops === 1 ? "1 vez" : `${loops} vezes`} por disparo
              </span>
            </div>
          </div>

          {/* Horários */}
          <div style={mp.section}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <label style={{ ...mp.label, marginBottom: 0 }}>
                <Timer size={11} style={{ marginRight: 5, verticalAlign: "middle" }} />
                Horários de reprodução
              </label>
              <button style={mp.addHorarioBtn} onClick={addHorario}>
                <Plus size={12} /> Adicionar horário
              </button>
            </div>

            {horarios.length === 0 && (
              <div style={mp.noHorario}>Sem horário agendado — toca apenas por comando manual</div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {horarios.map((h, i) => {
                const isDupe = filled.filter(x => x === h && h !== "").length > 1;
                const isConflict = h && conflitos.includes(h);
                return (
                  <div key={i} style={{ ...mp.horarioRow, borderColor: (isDupe || isConflict) ? "rgba(244,63,94,.4)" : "#1a1728" }}>
                    <div style={mp.horarioNum}>{i + 1}</div>
                    <TimePicker value={h} onChange={v => updateHorario(i, v)} />
                    {(isDupe || isConflict) && (
                      <div title={isDupe ? "Horário duplicado" : "Conflito com outro item"}>
                        <AlertCircle size={13} color="#f43f5e" />
                      </div>
                    )}
                    {h && (
                      <span style={mp.horarioBadge}>
                        <Clock size={9} /> {h}
                      </span>
                    )}
                    <button style={mp.removeHorarioBtn} onClick={() => removeHorario(i)}>
                      <X size={12} />
                    </button>
                  </div>
                );
              })}
            </div>

            {hasDupe && (
              <div style={mp.warnBox}>
                <AlertCircle size={13} /> Horários duplicados — remova os repetidos
              </div>
            )}
          </div>

          {/* Dias da semana */}
          <div style={mp.section}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <label style={{ ...mp.label, marginBottom: 0 }}>Dias de reprodução</label>
              <div style={{ display: "flex", gap: 4 }}>
                <button style={mp.diaLinkBtn} onClick={() => setDias(["dom","seg","ter","qua","qui","sex","sab"])}>
                  Todos
                </button>
                <button style={mp.diaLinkBtn} onClick={() => setDias(["seg","ter","qua","qui","sex"])}>
                  Úteis
                </button>
                <button style={mp.diaLinkBtn} onClick={() => setDias(["dom","sab"])}>
                  FDS
                </button>
              </div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              {DIAS.map(d => (
                <button
                  key={d.key}
                  onClick={() => toggleDia(d.key)}
                  style={{
                    flex: 1,
                    padding: "7px 0",
                    border: "1px solid",
                    borderRadius: 7,
                    cursor: "pointer",
                    fontSize: 11,
                    fontWeight: 700,
                    fontFamily: "monospace",
                    transition: "all 0.15s",
                    background: dias.includes(d.key) ? "rgba(155,89,245,.18)" : "#0d0b14",
                    color:      dias.includes(d.key) ? "#b48eff" : "#7a7490",
                    borderColor: dias.includes(d.key) ? "rgba(155,89,245,.4)" : "#221f33",
                  }}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          {/* Posição na playlist */}
          <div style={mp.section}>
            <label style={mp.label}>Posição na playlist</label>
            <div style={{ display: "flex", gap: 6 }}>
              <button style={{ ...mp.moveBtn, opacity: idx === 0 ? 0.3 : 1 }}
                disabled={idx === 0} onClick={() => { onMove(idx, -1); onClose(); }}>
                <ChevronUp size={13} /> Subir
              </button>
              <button style={{ ...mp.moveBtn, opacity: idx === totalItens - 1 ? 0.3 : 1 }}
                disabled={idx === totalItens - 1} onClick={() => { onMove(idx, 1); onClose(); }}>
                <ChevronDown size={13} /> Descer
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={mp.footer}>
          <button style={btn.danger} onClick={() => { onRemove(idx); onClose(); }}>
            <Trash2 size={13} /> Remover
          </button>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={btn.play} onClick={() => { onPlay(item); onClose(); }}>
              <Play size={13} fill="#fff" /> Tocar agora
            </button>
            <button
              style={{ ...btn.primary, opacity: hasDupe ? 0.5 : 1 }}
              disabled={hasDupe}
              onClick={handleSave}
            >
              <Check size={13} /> Salvar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const mp = {
  overlay: {
    position: "fixed", inset: 0, background: "rgba(0,0,0,.65)",
    display: "flex", alignItems: "center", justifyContent: "center",
    zIndex: 1000, backdropFilter: "blur(2px)",
  },
  panel: {
    background: "#13111f", borderRadius: 16, border: "1px solid #221f33",
    width: 480, maxWidth: "95vw", maxHeight: "85vh",
    display: "flex", flexDirection: "column",
    boxShadow: "0 32px 80px rgba(0,0,0,.6)",
  },
  header: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "18px 20px 14px", borderBottom: "1px solid #1a1728",
    gap: 10,
  },
  thumb: {
    width: 42, height: 42, borderRadius: 10, flexShrink: 0,
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  title: { fontSize: 15, fontWeight: 700, color: "#f0eeff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  sub: { fontSize: 11, color: "#7a7490", marginTop: 2 },
  closeBtn: {
    background: "#1a1728", border: "1px solid #221f33", borderRadius: 8,
    color: "#7a7490", cursor: "pointer", width: 30, height: 30,
    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
  },
  body: { flex: 1, overflowY: "auto", padding: "16px 20px" },
  section: { marginBottom: 20 },
  label: {
    display: "block", fontSize: 10, fontWeight: 700, color: "#7a7490",
    textTransform: "uppercase", letterSpacing: 1, marginBottom: 8,
  },
  input: {
    width: "100%", background: "#0d0b14", border: "1px solid #221f33",
    borderRadius: 8, color: "#f0eeff", padding: "9px 12px",
    fontSize: 13, outline: "none", boxSizing: "border-box",
  },
  loopControl: {
    display: "flex", alignItems: "center",
    background: "#1a1728", border: "1px solid #221f33",
    borderRadius: 8, overflow: "hidden",
  },
  loopBtn: {
    background: "transparent", border: "none", color: "#9b59f5",
    width: 34, height: 34, fontSize: 16, fontWeight: 700,
    cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
  },
  loopVal: {
    fontSize: 16, fontWeight: 800, color: "#f0eeff", width: 40, textAlign: "center",
    fontFamily: "monospace", borderLeft: "1px solid #221f33", borderRight: "1px solid #221f33",
    lineHeight: "34px",
  },
  addHorarioBtn: {
    display: "flex", alignItems: "center", gap: 5,
    background: "rgba(155,89,245,.12)", border: "1px solid rgba(155,89,245,.25)",
    borderRadius: 20, color: "#9b59f5", fontSize: 11, fontWeight: 700,
    padding: "5px 12px", cursor: "pointer",
  },
  noHorario: {
    fontSize: 12, color: "#7a7490", padding: "12px",
    background: "#0d0b14", borderRadius: 8, border: "1px dashed #221f33",
    textAlign: "center",
  },
  horarioRow: {
    display: "flex", alignItems: "center", gap: 8,
    background: "#0d0b14", padding: "8px 12px", borderRadius: 8,
    border: "1px solid #1a1728",
  },
  horarioNum: {
    width: 18, height: 18, borderRadius: "50%",
    background: "#1a1728", color: "#7a7490",
    fontSize: 10, fontWeight: 700,
    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
  },
  horarioBadge: {
    display: "flex", alignItems: "center", gap: 3,
    marginLeft: "auto", fontSize: 10, color: "#f59e0b",
    background: "rgba(245,158,11,.1)", padding: "2px 8px",
    borderRadius: 20, fontWeight: 700,
  },
  removeHorarioBtn: {
    background: "rgba(244,63,94,.1)", border: "none", borderRadius: 6,
    color: "#f43f5e", width: 24, height: 24, cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
  },
  warnBox: {
    display: "flex", alignItems: "center", gap: 7, marginTop: 8,
    background: "rgba(244,63,94,.08)", border: "1px solid rgba(244,63,94,.2)",
    borderRadius: 8, padding: "7px 12px", color: "#f43f5e", fontSize: 11, fontWeight: 500,
  },
  moveBtn: {
    display: "flex", alignItems: "center", gap: 5,
    background: "#1a1728", border: "1px solid #221f33",
    borderRadius: 7, color: "#a89ec0", fontSize: 11, fontWeight: 600,
    padding: "6px 12px", cursor: "pointer",
  },
  diaLinkBtn: {
    background: "transparent", border: "none",
    color: "#9b59f5", fontSize: 10, fontWeight: 700,
    cursor: "pointer", padding: "2px 6px", borderRadius: 4,
    textDecoration: "underline",
  },
  footer: {
    padding: "14px 20px", borderTop: "1px solid #1a1728",
    display: "flex", alignItems: "center", justifyContent: "space-between",
    gap: 10,
  },
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
  play: {
    display: "flex", alignItems: "center", gap: 6,
    background: "linear-gradient(135deg,#059669,#10b981)",
    border: "none", borderRadius: 8, color: "#fff",
    fontSize: 12, fontWeight: 700, padding: "8px 16px", cursor: "pointer",
  },
};

// ── Item de mídia na playlist (linha) ─────────────────────────────
function PlaylistItem({ item, idx, total, onClick }) {
  const yt = isYT(item.url || "");
  const horarios = Array.isArray(item.horarios) && item.horarios.length
    ? item.horarios
    : item.horario ? [item.horario] : [];

  return (
    <div
      style={pi.row}
      onClick={onClick}
      onMouseEnter={e => e.currentTarget.style.background = "#1a1728"}
      onMouseLeave={e => e.currentTarget.style.background = "#13111f"}
      title="Clique para configurar"
    >
      <div style={pi.grip}><GripVertical size={13} color="#332f4d" /></div>

      <div style={{ ...pi.thumb, background: yt ? "rgba(244,63,94,.1)" : "rgba(155,89,245,.1)" }}>
        {yt ? <Youtube size={13} color="#f43f5e" /> : <Music2 size={13} color="#9b59f5" />}
      </div>

      <div style={pi.info}>
        <div style={pi.name}>{item.nome || item.url}</div>
        <div style={pi.meta}>
          {item.loops > 1 && (
            <span style={pi.badge}>
              <Repeat size={8} /> {item.loops}×
            </span>
          )}
          {horarios.length > 0 && horarios.map((h, i) => (
            <span key={i} style={{ ...pi.badge, background: "rgba(245,158,11,.1)", color: "#f59e0b" }}>
              <Clock size={8} /> {h}
            </span>
          ))}
          {horarios.length === 0 && (
            <span style={{ ...pi.badge, color: "#7a7490", background: "rgba(122,116,144,.08)" }}>
              sem horário
            </span>
          )}
          {horarios.length > 0 && Array.isArray(item.dias) && item.dias.length < 7 && (
            <span style={{ ...pi.badge, background: "rgba(34,211,238,.08)", color: "#22d3ee" }}>
              {item.dias.map(d => d.charAt(0).toUpperCase() + d.slice(1)).join(" · ")}
            </span>
          )}
        </div>
      </div>

      <div style={pi.editHint}>
        <Edit3 size={12} color="#332f4d" />
      </div>
    </div>
  );
}

const pi = {
  row: {
    display: "flex", alignItems: "center", gap: 10,
    padding: "9px 12px", borderRadius: 8,
    background: "#13111f", marginBottom: 4,
    cursor: "pointer", transition: "background .12s",
    border: "1px solid transparent",
  },
  grip: { flexShrink: 0 },
  thumb: {
    width: 32, height: 32, borderRadius: 6, flexShrink: 0,
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  info: { flex: 1, minWidth: 0 },
  name: {
    fontSize: 13, fontWeight: 600, color: "#f0eeff",
    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
    marginBottom: 3,
  },
  meta: { display: "flex", gap: 5, flexWrap: "wrap" },
  badge: {
    display: "inline-flex", alignItems: "center", gap: 3,
    fontSize: 10, fontWeight: 700,
    background: "rgba(155,89,245,.1)", color: "#9b59f5",
    padding: "2px 7px", borderRadius: 10,
  },
  editHint: { flexShrink: 0, opacity: 0.4 },
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
          <button style={mp.closeBtn} onClick={onClose}><X size={16} /></button>
        </div>
        <div style={{ padding: "10px 20px" }}>
          <input autoFocus style={{ ...mp.input, fontSize: 13 }}
            placeholder="Buscar..." value={q} onChange={e => setQ(e.target.value)} />
        </div>
        <div style={modal.list}>
          {entries.length === 0 && (
            <div style={{ color: "#7a7490", textAlign: "center", padding: 24 }}>Nenhum anúncio encontrado</div>
          )}
          {entries.map(([id, a]) => {
            const yt = isYT(a.url || "");
            return (
              <div key={id} style={modal.item}
                onMouseEnter={e => e.currentTarget.style.background = "#1a1728"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                onClick={() => onSelect(a)}>
                <div style={{ ...pi.thumb, background: yt ? "rgba(244,63,94,.1)" : "rgba(155,89,245,.1)" }}>
                  {yt ? <Youtube size={13} color="#f43f5e" /> : <Music2 size={13} color="#9b59f5" />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#f0eeff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {a.nome}
                  </div>
                  <div style={{ fontSize: 11, color: "#7a7490", marginTop: 1 }}>
                    {yt ? "YouTube" : (a.tipo?.includes("wav") ? "WAV" : "MP3")}
                    {a.tamanho ? ` · ${(a.tamanho/1024/1024).toFixed(1)} MB` : ""}
                  </div>
                </div>
                <Plus size={14} color="#9b59f5" />
              </div>
            );
          })}
        </div>
        <div style={modal.footer}>
          <span style={{ fontSize: 11, color: "#7a7490" }}>
            O mesmo anúncio pode ser adicionado várias vezes com horários diferentes.
          </span>
        </div>
      </div>
    </div>
  );
}

const modal = {
  overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1100 },
  box: { background: "#13111f", borderRadius: 16, border: "1px solid #221f33", width: 480, maxHeight: "70vh", display: "flex", flexDirection: "column", boxShadow: "0 24px 64px rgba(0,0,0,.5)" },
  header: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px 0" },
  title: { fontSize: 15, fontWeight: 700, color: "#f0eeff" },
  list: { overflowY: "auto", flex: 1, padding: "0 20px 10px" },
  item: { display: "flex", alignItems: "center", gap: 12, padding: "10px 8px", borderRadius: 8, cursor: "pointer", transition: "background .12s" },
  footer: { padding: "12px 20px", borderTop: "1px solid #1a1728" },
};

// ── Editor de playlist ────────────────────────────────────────────
function PlaylistEditor({ playlist, plId, anuncios, onSave, onCancel, onPlayItem }) {
  const [nome,    setNome]    = useState(playlist?.nome || "");
  const [ativa,   setAtiva]   = useState(playlist?.ativa ?? true);
  const [itens,   setItens]   = useState(
    (playlist?.itens || []).map(it => ({
      ...it,
      horarios: Array.isArray(it.horarios) && it.horarios.length > 0
        ? it.horarios
        : it.horario ? [it.horario] : [],
    }))
  );
  const [showPicker,  setShowPicker]  = useState(false);
  const [showUrlForm, setShowUrlForm] = useState(false);
  const [urlVal,  setUrlVal]  = useState("");
  const [urlNome, setUrlNome] = useState("");
  const [editingIdx, setEditingIdx] = useState(null);

  // Todos os horários para detectar conflitos entre itens
  const allHorarios = itens.flatMap(it =>
    Array.isArray(it.horarios) ? it.horarios.filter(Boolean) : it.horario ? [it.horario] : []
  );

  const updateItem = (idx, patch) => setItens(prev => prev.map((it, i) => i === idx ? { ...it, ...patch } : it));
  const removeItem = idx => setItens(prev => prev.filter((_, i) => i !== idx));
  const moveItem   = (idx, dir) => {
    setItens(prev => {
      const arr = [...prev]; const nIdx = idx + dir;
      if (nIdx < 0 || nIdx >= arr.length) return arr;
      [arr[idx], arr[nIdx]] = [arr[nIdx], arr[idx]];
      return arr;
    });
  };

  const addFromLibrary = (anuncio) => {
    setItens(prev => [...prev, { nome: anuncio.nome, url: anuncio.url, loops: 1, tipo: anuncio.tipo || "url", horarios: [], horario: null }]);
    setShowPicker(false);
  };

  const addFromUrl = () => {
    if (!urlVal.trim()) return;
    setItens(prev => [...prev, { nome: urlNome.trim() || urlVal.trim(), url: urlVal.trim(), loops: 1, tipo: "url", horarios: [], horario: null }]);
    setUrlVal(""); setUrlNome(""); setShowUrlForm(false);
  };

  // Verifica duplicatas globais
  const filled = allHorarios;
  const hasDupeGlobal = filled.length !== new Set(filled).size;

  const canSave = nome.trim() && !hasDupeGlobal;

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
          <button style={{ ...btn.primary, opacity: canSave ? 1 : 0.5 }} disabled={!canSave}
            onClick={() => onSave({ nome: nome.trim(), ativa, itens })}>
            <Check size={14} /> Salvar
          </button>
        </div>
      </div>

      {/* Nome + ativa */}
      <div style={ed.meta}>
        <div style={ed.fieldWrap}>
          <label style={ed.label}>Nome da Playlist</label>
          <input style={ed.inp} value={nome} onChange={e => setNome(e.target.value)} placeholder="Ex: Comerciais da manhã" />
        </div>
        <label style={ed.toggle}>
          <input type="checkbox" checked={ativa} onChange={e => setAtiva(e.target.checked)} style={{ accentColor: "#9b59f5" }} />
          <span style={{ fontSize: 13, color: "#f0eeff", fontWeight: 500 }}>Playlist ativa</span>
        </label>
      </div>

      {hasDupeGlobal && (
        <div style={ed.warn}>
          <AlertCircle size={14} />
          <span>Horários duplicados entre as faixas. Corrija antes de salvar.</span>
        </div>
      )}

      {/* Lista */}
      <div style={ed.listWrap}>
        <div style={ed.listHeader}>
          <span style={ed.listTitle}>Faixas <span style={{ color: "#7a7490", fontWeight: 400 }}>— clique em uma faixa para configurar</span></span>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={btn.sm} onClick={() => setShowPicker(true)}><Music2 size={12} /> Da Biblioteca</button>
            <button style={btn.sm} onClick={() => setShowUrlForm(v => !v)}><Plus size={12} /> URL Manual</button>
          </div>
        </div>

        {showUrlForm && (
          <div style={ed.urlForm}>
            <input style={{ ...ed.inp, flex: 1 }} placeholder="URL do áudio ou YouTube..." value={urlVal} onChange={e => setUrlVal(e.target.value)} />
            <input style={{ ...ed.inp, width: 180 }} placeholder="Nome (opcional)" value={urlNome} onChange={e => setUrlNome(e.target.value)} />
            <button style={btn.primary} onClick={addFromUrl}><Check size={13} /></button>
            <button style={btn.ghost} onClick={() => setShowUrlForm(false)}><X size={13} /></button>
          </div>
        )}

        <div style={ed.items}>
          {itens.length === 0 && (
            <div style={ed.empty}><Music2 size={28} color="#332f4d" /><p>Adicione faixas da biblioteca ou por URL</p></div>
          )}
          {itens.map((item, idx) => (
            <PlaylistItem
              key={idx}
              item={item}
              idx={idx}
              total={itens.length}
              onClick={() => setEditingIdx(idx)}
            />
          ))}
        </div>
      </div>

      {/* Modal config da mídia */}
      {editingIdx !== null && (
        <MediaConfigPanel
          item={itens[editingIdx]}
          idx={editingIdx}
          totalItens={itens.length}
          allHorarios={allHorarios}
          onClose={() => setEditingIdx(null)}
          onSave={(updated) => updateItem(editingIdx, updated)}
          onPlay={(item) => onPlayItem(item)}
          onRemove={removeItem}
          onMove={moveItem}
        />
      )}

      {showPicker && <AnuncioPickerModal anuncios={anuncios} onSelect={addFromLibrary} onClose={() => setShowPicker(false)} />}
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
  label: { display: "block", fontSize: 11, fontWeight: 700, color: "#7a7490", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 },
  inp: { width: "100%", background: "#0d0b14", border: "1px solid #221f33", borderRadius: 8, color: "#f0eeff", padding: "10px 12px", fontSize: 13, outline: "none", boxSizing: "border-box" },
  toggle: { display: "flex", alignItems: "center", gap: 8, cursor: "pointer", paddingBottom: 10 },
  warn: { display: "flex", alignItems: "center", gap: 8, background: "rgba(244,63,94,.1)", border: "1px solid rgba(244,63,94,.2)", borderRadius: 8, padding: "8px 14px", marginBottom: 12, color: "#f43f5e", fontSize: 12, fontWeight: 500 },
  listWrap: { background: "#0d0b14", borderRadius: 12, border: "1px solid #1a1728", padding: 16 },
  listHeader: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 },
  listTitle: { fontSize: 13, fontWeight: 700, color: "#f0eeff" },
  urlForm: { display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" },
  items: { display: "flex", flexDirection: "column" },
  empty: { display: "flex", flexDirection: "column", alignItems: "center", gap: 8, padding: "32px 0", color: "#7a7490", fontSize: 13 },
};

// ── Modal renomear ────────────────────────────────────────────────
function RenameModal({ nome, onSave, onClose }) {
  const [val, setVal] = useState(nome);
  return (
    <div style={modal.overlay} onClick={onClose}>
      <div style={{ ...modal.box, width: 360, maxHeight: "none", padding: "24px" }} onClick={e => e.stopPropagation()}>
        <div style={{ fontSize: 15, fontWeight: 700, color: "#f0eeff", marginBottom: 16 }}>Renomear Playlist</div>
        <input
          autoFocus style={{ ...mp.input, marginBottom: 16 }}
          value={val} onChange={e => setVal(e.target.value)}
          onKeyDown={e => e.key === "Enter" && val.trim() && onSave(val.trim())}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button style={btn.ghost} onClick={onClose}><X size={13} /> Cancelar</button>
          <button style={btn.primary} onClick={() => val.trim() && onSave(val.trim())}><Check size={13} /> Salvar</button>
        </div>
      </div>
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────
export default function Playlists() {
  const { playlists, criarPlaylist, togglePlaylist, deletePlaylist, salvarPlaylist, playNow } = usePlaylists();
  const { anuncios } = useAnuncios();
  const toast = useToast();

  const [editing,    setEditing]    = useState(null);   // null | "new" | plId
  const [renaming,   setRenaming]   = useState(null);   // null | { id, nome }
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
    } catch (e) { toast("Erro: " + e.message, "error"); }
  };

  const handleDelete = async (id, nome) => {
    if (!window.confirm(`Excluir a playlist "${nome}"?`)) return;
    try { await deletePlaylist(id); toast("Playlist excluída", "success"); }
    catch (e) { toast("Erro: " + e.message, "error"); }
  };

  const handleToggle = async (id, atual) => {
    try { await togglePlaylist(id, atual); }
    catch (e) { toast("Erro: " + e.message, "error"); }
  };

  const handleRename = async (id, novoNome) => {
    try {
      await salvarPlaylist(id, { ...playlists[id], nome: novoNome });
      toast("Renomeado!", "success");
      setRenaming(null);
    } catch (e) { toast("Erro: " + e.message, "error"); }
  };

  // Play de item individual (ad-hoc)
  const handlePlayItem = async (item) => {
    try {
      await playNow(null, { nome: item.nome, url: item.url, tipo: item.tipo || "url", loops: item.loops || 1 });
      toast("Tocando agora!", "success");
    } catch (e) { toast("Erro: " + e.message, "error"); }
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
          onPlayItem={handlePlayItem}
        />
      </div>
    );
  }

  // Lista de playlists
  return (
    <div style={{ overflowY: "auto", flex: 1, paddingBottom: 80 }}>
      {/* Header */}
      <div style={pg.header}>
        <div style={pg.headerGrad} />
        <div style={{ position: "relative", zIndex: 1 }}>
          <h1 style={pg.h1}>Playlists</h1>
          <p style={pg.sub}>{entries.length} playlist{entries.length !== 1 ? "s" : ""}</p>
        </div>
        <button style={{ ...btn.primary, position: "relative", zIndex: 1 }} onClick={() => setEditing("new")}>
          <Plus size={15} /> Nova Playlist
        </button>
      </div>

      {entries.length === 0 && (
        <div style={pg.empty}>
          <Music2 size={48} color="#332f4d" />
          <p style={{ fontSize: 18, fontWeight: 700, color: "#f0eeff", margin: "12px 0 4px" }}>Nenhuma playlist ainda</p>
          <p style={{ fontSize: 13, color: "#7a7490" }}>Clique em "Nova Playlist" para começar</p>
        </div>
      )}

      <div style={pg.list}>
        {entries.map(([id, pl]) => {
          const expanded  = expandedId === id;
          const itens     = pl.itens || [];
          const agendados = itens.filter(it =>
            (Array.isArray(it.horarios) && it.horarios.length > 0) || it.horario
          ).length;

          return (
            <div key={id} style={pg.card}>
              {/* Cabeçalho do card — sem botão play */}
              <div style={pg.cardHead}>
                {/* Toggle ativo/inativo */}
                <button
                  style={pg.toggleBtn}
                  onClick={() => handleToggle(id, pl.ativa)}
                  title={pl.ativa ? "Desativar" : "Ativar"}
                >
                  {pl.ativa
                    ? <ToggleRight size={28} color="#10b981" />
                    : <ToggleLeft  size={28} color="#332f4d" />
                  }
                </button>

                {/* Nome + meta */}
                <div style={{ flex: 1, minWidth: 0, cursor: "pointer" }} onClick={() => setExpandedId(expanded ? null : id)}>
                  <div style={pg.cardNome}>{pl.nome}</div>
                  <div style={pg.cardMeta}>
                    {itens.length} faixa{itens.length !== 1 ? "s" : ""}
                    {agendados > 0 && (
                      <span style={{ color: "#f59e0b", marginLeft: 8 }}>
                        <Clock size={10} style={{ verticalAlign: "middle" }} /> {agendados} agendado{agendados !== 1 ? "s" : ""}
                      </span>
                    )}
                    <span style={{ color: pl.ativa ? "#10b981" : "#7a7490", marginLeft: 8 }}>
                      {pl.ativa ? "● Ativa" : "○ Inativa"}
                    </span>
                  </div>
                </div>

                {/* Ações: só lápis + lixeira + expandir */}
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <button style={btn.ghost} onClick={() => setRenaming({ id, nome: pl.nome })} title="Renomear">
                    <Edit3 size={13} />
                  </button>
                  <button style={btn.ghost} onClick={() => setEditing(id)} title="Editar faixas">
                    <Music2 size={13} />
                  </button>
                  <button style={btn.danger} onClick={() => handleDelete(id, pl.nome)} title="Excluir">
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
                    <div style={{ color: "#7a7490", fontSize: 13, padding: "8px 0" }}>Playlist vazia</div>
                  )}
                  {itens.map((item, idx) => {
                    const yt = isYT(item.url || "");
                    const horarios = Array.isArray(item.horarios) && item.horarios.length > 0
                      ? item.horarios
                      : item.horario ? [item.horario] : [];
                    return (
                      <div key={idx} style={pg.trackRow}>
                        <span style={pg.trackNum}>{idx + 1}</span>
                        <div style={{ width: 26, height: 26, borderRadius: 5, flexShrink: 0, background: yt ? "rgba(244,63,94,.1)" : "rgba(155,89,245,.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          {yt ? <Youtube size={12} color="#f43f5e" /> : <Music2 size={12} color="#9b59f5" />}
                        </div>
                        <span style={pg.trackName}>{item.nome}</span>
                        {item.loops > 1 && <span style={pg.badge}>{item.loops}×</span>}
                        {horarios.map((h, hi) => (
                          <span key={hi} style={{ ...pg.badge, background: "rgba(245,158,11,.12)", color: "#f59e0b" }}>
                            <Clock size={9} style={{ verticalAlign: "middle" }} /> {h}
                          </span>
                        ))}
                        {/* Play só na mídia */}
                        <button
                          style={{ ...btn.play, padding: "4px 10px", fontSize: 11, marginLeft: "auto" }}
                          onClick={() => handlePlayItem(item)}
                          title="Tocar este anúncio agora"
                        >
                          <Play size={11} fill="#fff" /> Tocar
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Modal renomear */}
      {renaming && (
        <RenameModal
          nome={renaming.nome}
          onSave={(novoNome) => handleRename(renaming.id, novoNome)}
          onClose={() => setRenaming(null)}
        />
      )}
    </div>
  );
}

const pg = {
  header: { position: "relative", padding: "36px 32px 24px", display: "flex", alignItems: "flex-end", justifyContent: "space-between" },
  headerGrad: { position: "absolute", inset: 0, background: "linear-gradient(135deg, #1a0a40 0%, #130d38 50%, transparent 100%)" },
  h1: { fontSize: 32, fontWeight: 800, color: "#f0eeff", margin: 0 },
  sub: { fontSize: 13, color: "#7a7490", margin: "4px 0 0" },
  empty: { display: "flex", flexDirection: "column", alignItems: "center", gap: 4, padding: "80px 0" },
  list: { padding: "0 24px" },
  card: { background: "#13111f", borderRadius: 12, border: "1px solid #1a1728", marginBottom: 12, overflow: "hidden" },
  cardHead: { display: "flex", alignItems: "center", gap: 12, padding: "14px 18px" },
  toggleBtn: { background: "none", border: "none", cursor: "pointer", padding: 0, display: "flex", flexShrink: 0 },
  cardNome: { fontSize: 15, fontWeight: 700, color: "#f0eeff" },
  cardMeta: { fontSize: 12, color: "#7a7490", marginTop: 2 },
  expand: { borderTop: "1px solid #1a1728", padding: "12px 18px", background: "#0d0b14" },
  trackRow: { display: "flex", alignItems: "center", gap: 8, padding: "7px 0", borderBottom: "1px solid #13111f", flexWrap: "wrap" },
  trackNum: { fontSize: 11, color: "#7a7490", fontFamily: "monospace", width: 18, textAlign: "right", flexShrink: 0 },
  trackName: { flex: 1, fontSize: 13, color: "#f0eeff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 80 },
  badge: { fontSize: 10, fontWeight: 700, background: "rgba(155,89,245,.12)", color: "#9b59f5", padding: "2px 7px", borderRadius: 10, display: "inline-flex", alignItems: "center", gap: 3 },
};