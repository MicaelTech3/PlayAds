// src/pages/Playlists.jsx
import { useState, useRef } from "react";
import { usePlaylists } from "../hooks/useFirebase";
import { useToast } from "../components/Toast";
import {
  ListMusic, Plus, Trash2, Play, Edit2, Check, X,
  Upload, Link2, Music, Clock, RefreshCw, ChevronLeft,
  ToggleLeft, ToggleRight, Settings2, Youtube
} from "lucide-react";

const isYT = url => url && (url.includes("youtube.com") || url.includes("youtu.be"));

// ── Modal config de item ─────────────────────────────────────────
function ItemConfigModal({ item, itemIndex, playlistId, atualizarItem, onClose }) {
  const toast = useToast();
  const [loops,   setLoops]   = useState(item.loops   || 1);
  const [horario, setHorario] = useState(item.horario || "");

  const salvar = async () => {
    await atualizarItem(playlistId, itemIndex, {
      loops: Math.max(1, parseInt(loops) || 1),
      horario: horario.trim() || null,
    });
    toast("Configurações salvas!", "success");
    onClose();
  };

  return (
    <div style={m.overlay} onClick={onClose}>
      <div style={m.box} onClick={e => e.stopPropagation()}>
        <div style={m.header}>
          <Settings2 size={18} color="#9b59f5" />
          <span style={m.title}>Configurar mídia</span>
          <button style={m.closeBtn} onClick={onClose}><X size={16} /></button>
        </div>
        <div style={m.body}>
          <div style={m.trackName}>{item.nome}</div>
          <div style={m.field}>
            <label style={m.label}><Clock size={13} color="#7a7490" /> Horário (opcional)</label>
            <input type="time" value={horario} onChange={e => setHorario(e.target.value)}
              style={m.input} />
            <span style={m.hint}>Vazio = toca na ordem da playlist</span>
          </div>
          <div style={m.field}>
            <label style={m.label}><RefreshCw size={13} color="#7a7490" /> Loops</label>
            <div style={m.loopRow}>
              <button style={m.loopBtn} onClick={() => setLoops(l => Math.max(1,(parseInt(l)||1)-1))}>−</button>
              <input type="number" min={1} max={99} value={loops}
                onChange={e => setLoops(e.target.value)}
                style={{ ...m.input, width: 70, textAlign: "center" }} />
              <button style={m.loopBtn} onClick={() => setLoops(l => Math.min(99,(parseInt(l)||1)+1))}>+</button>
            </div>
            <span style={m.hint}>{parseInt(loops)===1 ? "Toca 1 vez" : `Toca ${loops} vezes seguidas`}</span>
          </div>
        </div>
        <div style={m.footer}>
          <button style={m.cancelBtn} onClick={onClose}>Cancelar</button>
          <button style={m.saveBtn} onClick={salvar}><Check size={14}/> Salvar</button>
        </div>
      </div>
    </div>
  );
}

// ── Detalhe da playlist ──────────────────────────────────────────
function PlaylistDetail({ playlistId, playlist, onBack }) {
  const { atualizarItem, removerItem, uploadItemPlaylist, adicionarItem,
          renomearPlaylist, togglePlaylist, playNow } = usePlaylists();
  const toast    = useToast();
  const fileRef  = useRef(null);

  const [editingName, setEditingName] = useState(false);
  const [novoNome,    setNovoNome]    = useState(playlist.nome);
  const [uploading,   setUploading]   = useState(false);
  const [uploadPct,   setUploadPct]   = useState(0);
  const [urlInput,    setUrlInput]    = useState("");
  const [urlNome,     setUrlNome]     = useState("");
  const [showUrl,     setShowUrl]     = useState(false);
  const [dragging,    setDragging]    = useState(false);
  const [configItem,  setConfigItem]  = useState(null);

  const itens = playlist.itens || [];

  const salvarNome = async () => {
    if (!novoNome.trim()) return;
    await renomearPlaylist(playlistId, novoNome.trim());
    toast("Playlist renomeada!", "success");
    setEditingName(false);
  };

  const allowed = f => f && (f.name.match(/\.(mp3|wav)$/i) || f.type.startsWith("audio/"));

  const doUpload = async (file) => {
    if (!allowed(file)) { toast("Apenas MP3 ou WAV são aceitos", "error"); return; }
    setUploading(true); setUploadPct(0);
    try {
      await uploadItemPlaylist(playlistId, file, setUploadPct);
      toast("Áudio adicionado!", "success");
    } catch(e) { toast("Erro: " + e.message, "error"); }
    finally { setUploading(false); setUploadPct(0); }
  };

  const adicionarUrl = async () => {
    const url = urlInput.trim();
    if (!url) { toast("Digite uma URL válida", "error"); return; }
    const youtube = isYT(url);
    const nome = urlNome.trim() || (youtube ? "Vídeo YouTube" : url.split("/").pop()) || "Áudio URL";
    await adicionarItem(playlistId, {
      nome, url, tipo: youtube ? "youtube" : "url", loops: 1, horario: null,
    });
    toast(youtube ? "YouTube adicionado!" : "URL adicionada!", "success");
    setUrlInput(""); setUrlNome(""); setShowUrl(false);
  };

  const handleDrop = e => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) doUpload(f);
  };

  const handleDelete = async (i) => {
    if (!window.confirm("Remover esta mídia?")) return;
    await removerItem(playlistId, i);
    toast("Mídia removida", "success");
  };

  const handlePlayNow = async () => {
    if (itens.length === 0) { toast("Playlist vazia!", "error"); return; }
    await playNow(playlistId);
    toast(`▶ "${playlist.nome}" enviada ao player!`, "success");
  };

  return (
    <div style={s.wrap}>
      <div style={{ ...s.header, background: "linear-gradient(135deg, #1e1050 0%, #130d38 50%, transparent 100%)" }}>
        <div style={s.headerGrad} />
        <div style={s.headerContent}>
          <button style={s.backBtn} onClick={onBack}><ChevronLeft size={18}/> Playlists</button>
          <div style={s.headerMain}>
            <div style={s.headerIcon}><ListMusic size={52} color="rgba(155,89,245,.6)" /></div>
            <div style={{ flex: 1 }}>
              <div style={s.headerSub}>Playlist</div>
              {editingName ? (
                <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                  <input autoFocus value={novoNome} onChange={e => setNovoNome(e.target.value)}
                    onKeyDown={e => { if(e.key==="Enter") salvarNome(); if(e.key==="Escape") setEditingName(false); }}
                    style={s.nameInput} />
                  <button style={s.iconBtn} onClick={salvarNome}><Check size={16} color="#9b59f5"/></button>
                  <button style={s.iconBtn} onClick={() => setEditingName(false)}><X size={16} color="#7a7490"/></button>
                </div>
              ) : (
                <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                  <h1 style={s.headerTitle}>{playlist.nome}</h1>
                  <button style={s.iconBtn} onClick={() => { setNovoNome(playlist.nome); setEditingName(true); }}>
                    <Edit2 size={14} color="#7a7490"/>
                  </button>
                </div>
              )}
              <div style={s.headerMeta}>
                {itens.length} faixa{itens.length!==1?"s":""}
                &nbsp;·&nbsp;
                <span style={{ color: playlist.ativa ? "#10b981" : "#7a7490" }}>
                  {playlist.ativa ? "● Ativa" : "○ Inativa"}
                </span>
              </div>
            </div>
            <div style={s.headerActions}>
              <button style={{ ...s.actionBtn, background: playlist.ativa ? "#10b981" : "#1a1728" }}
                onClick={() => togglePlaylist(playlistId, playlist.ativa)}>
                {playlist.ativa ? <><ToggleRight size={14}/> Ativa</> : <><ToggleLeft size={14}/> Inativa</>}
              </button>
              <button style={{ ...s.actionBtn, background: "linear-gradient(135deg,#7c3aed,#9b59f5)", color:"#fff" }}
                onClick={handlePlayNow}>
                <Play size={14} fill="#fff"/> Tocar agora
              </button>
            </div>
          </div>
        </div>
      </div>

      <div style={s.content}>
        {/* Add area */}
        <div style={s.addSection}>
          <div
            style={{ ...s.dropZone, ...(dragging ? s.dropZoneActive : {}) }}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => !uploading && fileRef.current?.click()}
          >
            <input ref={fileRef} type="file" accept=".mp3,.wav,audio/*"
              style={{ display:"none" }} onChange={e => doUpload(e.target.files[0])} />
            {uploading ? (
              <div style={s.uploadingState}>
                <div style={s.progressWrap}><div style={{ ...s.progressFill, width:`${uploadPct}%` }}/></div>
                <span style={s.uploadPct}>{uploadPct}%</span>
              </div>
            ) : (
              <div style={s.dropContent}>
                <Upload size={18} color="#9b59f5"/>
                <span style={s.dropTitle}>Arraste MP3/WAV ou clique</span>
              </div>
            )}
          </div>
          <button style={{ ...s.addUrlBtn, ...(showUrl ? { borderColor:"#7c3aed", color:"#9b59f5" } : {}) }}
            onClick={() => setShowUrl(v=>!v)}>
            <Youtube size={14}/> YouTube / URL
          </button>
        </div>

        {showUrl && (
          <div style={s.urlPanel}>
            <input type="text" placeholder="Nome (opcional)" value={urlNome}
              onChange={e => setUrlNome(e.target.value)} style={s.urlInput} />
            <input type="url" placeholder="https://youtube.com/watch?v=... ou URL do áudio"
              value={urlInput} onChange={e => setUrlInput(e.target.value)}
              onKeyDown={e => e.key==="Enter" && adicionarUrl()} style={{ ...s.urlInput, flex:1 }} />
            <button style={s.urlAddBtn} onClick={adicionarUrl}>
              <Plus size={13}/> Adicionar
            </button>
          </div>
        )}

        {/* Track list */}
        {itens.length > 0 && (
          <div style={s.tableWrap}>
            <div style={s.tableHead}>
              <span style={{ ...s.thCell, flex:"0 0 32px" }}>#</span>
              <span style={{ ...s.thCell, flex:1 }}>Mídia</span>
              <span style={{ ...s.thCell, flex:"0 0 80px" }}>Horário</span>
              <span style={{ ...s.thCell, flex:"0 0 60px" }}>Loops</span>
              <span style={{ ...s.thCell, flex:"0 0 90px" }}>Ações</span>
            </div>
            <div style={s.divider}/>
            {itens.map((item, i) => {
              const youtube = isYT(item.url || "");
              return (
                <div key={item.id||i} style={s.trackRow}
                  onMouseEnter={e => e.currentTarget.style.background="#1a1728"}
                  onMouseLeave={e => e.currentTarget.style.background="transparent"}>
                  <div style={{ ...s.tdCell, flex:"0 0 32px" }}>
                    <span style={s.trackNum}>{i+1}</span>
                  </div>
                  <div style={{ ...s.tdCell, flex:1 }}>
                    <div style={{ ...s.trackThumb, background: youtube ? "rgba(244,63,94,.12)" : "#1a1728" }}>
                      {youtube ? <Youtube size={12} color="#f43f5e"/> : <Music size={12} color="#a89ec0"/>}
                    </div>
                    <div style={{ display:"flex", flexDirection:"column", gap:2, overflow:"hidden" }}>
                      <span style={s.trackName}>{item.nome}</span>
                      {item.tipo==="url"||youtube ? (
                        <span style={{ fontSize:10, color:"#7a7490", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                          {item.url}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div style={{ ...s.tdCell, flex:"0 0 80px" }}>
                    <span style={{ fontSize:11, color: item.horario?"#f59e0b":"#7a7490", fontFamily:"'DM Mono',monospace" }}>
                      {item.horario || "—"}
                    </span>
                  </div>
                  <div style={{ ...s.tdCell, flex:"0 0 60px" }}>
                    <span style={{ fontSize:11, color:"#a89ec0", fontFamily:"'DM Mono',monospace" }}>
                      {item.loops||1}×
                    </span>
                  </div>
                  <div style={{ ...s.tdCell, flex:"0 0 90px", gap:6 }}>
                    <button style={s.itemBtn} onClick={() => setConfigItem({ item, index:i })}>
                      <Settings2 size={12}/>
                    </button>
                    <button style={{ ...s.itemBtn, ...s.itemBtnDanger }} onClick={() => handleDelete(i)}>
                      <Trash2 size={12}/>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {itens.length===0 && (
          <div style={s.empty}>
            <Music size={36} color="#332f4d"/>
            <p style={s.emptyText}>Playlist vazia</p>
            <p style={s.emptySub}>Adicione MP3, WAV, links do YouTube ou URLs de áudio</p>
          </div>
        )}
      </div>

      {configItem && (
        <ItemConfigModal item={configItem.item} itemIndex={configItem.index}
          playlistId={playlistId} atualizarItem={atualizarItem}
          onClose={() => setConfigItem(null)} />
      )}
    </div>
  );
}

// ── Lista de playlists ───────────────────────────────────────────
export default function Playlists() {
  const { playlists, loading, criarPlaylist, deletePlaylist, togglePlaylist, playNow } = usePlaylists();
  const toast = useToast();
  const [openId,   setOpenId]   = useState(null);
  const [criando,  setCriando]  = useState(false);
  const [nomeNovo, setNomeNovo] = useState("");

  const handleCreate = async () => {
    if (!nomeNovo.trim()) { toast("Digite um nome", "error"); return; }
    const id = await criarPlaylist(nomeNovo.trim());
    toast("Playlist criada!", "success");
    setNomeNovo(""); setCriando(false); setOpenId(id);
  };

  const handleDelete = async (id, nome) => {
    if (!window.confirm(`Excluir "${nome}"?`)) return;
    await deletePlaylist(id);
    toast("Playlist removida", "success");
  };

  const entries = Object.entries(playlists).sort(([,a],[,b]) => (b.criado_em||0)-(a.criado_em||0));

  if (openId && playlists[openId]) {
    return <PlaylistDetail playlistId={openId} playlist={playlists[openId]} onBack={() => setOpenId(null)}/>;
  }

  return (
    <div style={s.wrap}>
      <div style={s.header}>
        <div style={{ ...s.headerGrad, background:"linear-gradient(135deg,#1e1050 0%,#130d38 50%,transparent 100%)" }}/>
        <div style={s.headerContent}>
          <div style={s.headerMain}>
            <div style={s.headerIcon}><ListMusic size={52} color="rgba(155,89,245,.6)"/></div>
            <div>
              <div style={s.headerSub}>Biblioteca</div>
              <h1 style={s.headerTitle}>Playlists</h1>
              <div style={s.headerMeta}>{entries.length} playlist{entries.length!==1?"s":""}</div>
            </div>
          </div>
          <div style={s.headerActions}>
            <button style={{ ...s.actionBtn, background:"linear-gradient(135deg,#7c3aed,#9b59f5)", color:"#fff" }}
              onClick={() => setCriando(true)}>
              <Plus size={14}/> Nova playlist
            </button>
          </div>
        </div>
      </div>

      <div style={s.content}>
        {criando && (
          <div style={m.overlay} onClick={() => setCriando(false)}>
            <div style={m.box} onClick={e => e.stopPropagation()}>
              <div style={m.header}>
                <ListMusic size={18} color="#9b59f5"/>
                <span style={m.title}>Nova playlist</span>
                <button style={m.closeBtn} onClick={() => setCriando(false)}><X size={16}/></button>
              </div>
              <div style={m.body}>
                <div style={m.field}>
                  <label style={m.label}>Nome da playlist</label>
                  <input autoFocus type="text" placeholder="Ex: Promoções da manhã"
                    value={nomeNovo} onChange={e => setNomeNovo(e.target.value)}
                    onKeyDown={e => { if(e.key==="Enter") handleCreate(); if(e.key==="Escape") setCriando(false); }}
                    style={m.input}/>
                </div>
              </div>
              <div style={m.footer}>
                <button style={m.cancelBtn} onClick={() => setCriando(false)}>Cancelar</button>
                <button style={m.saveBtn} onClick={handleCreate}><Check size={14}/> Criar</button>
              </div>
            </div>
          </div>
        )}

        {entries.length > 0 ? (
          <div style={s.plGrid}>
            {entries.map(([id, pl]) => {
              const qtd = pl.itens?.length || 0;
              return (
                <div key={id} style={s.plCard}
                  onMouseEnter={e => { e.currentTarget.style.background="#1a1728"; e.currentTarget.style.borderColor="#332f4d"; }}
                  onMouseLeave={e => { e.currentTarget.style.background="#13111f"; e.currentTarget.style.borderColor="#221f33"; }}>
                  <div style={s.plCardThumb} onClick={() => setOpenId(id)}
                    onMouseEnter={e => e.currentTarget.querySelector(".play-btn").style.opacity="1"}
                    onMouseLeave={e => e.currentTarget.querySelector(".play-btn").style.opacity="0"}>
                    <ListMusic size={28} color="#332f4d"/>
                    <button className="play-btn" style={s.plPlayBtn}
                      onClick={async e => {
                        e.stopPropagation();
                        if(!qtd){ toast("Playlist vazia!", "error"); return; }
                        await playNow(id);
                        toast(`▶ "${pl.nome}" enviada!`, "success");
                      }}>▶</button>
                  </div>
                  <div style={{ cursor:"pointer" }} onClick={() => setOpenId(id)}>
                    <div style={s.plCardName}>{pl.nome}</div>
                    <div style={s.plCardMeta}>
                      {qtd} faixa{qtd!==1?"s":""}
                      {pl.ativa ? " · ● Ativa" : ""}
                    </div>
                  </div>
                  <div style={s.plCardActions}>
                    <button style={{ ...s.cardBtn, color: pl.ativa ? "#10b981":"#7a7490" }}
                      onClick={() => togglePlaylist(id, pl.ativa)}>
                      {pl.ativa ? <ToggleRight size={15}/> : <ToggleLeft size={15}/>}
                    </button>
                    <button style={{ ...s.cardBtn, color:"#7a7490" }} onClick={() => setOpenId(id)}>
                      <Edit2 size={13}/>
                    </button>
                    <button style={{ ...s.cardBtn, color:"#f43f5e" }} onClick={() => handleDelete(id, pl.nome)}>
                      <Trash2 size={13}/>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : !loading && (
          <div style={s.empty}>
            <ListMusic size={44} color="#332f4d"/>
            <p style={s.emptyText}>Nenhuma playlist ainda</p>
            <p style={s.emptySub}>Crie sua primeira playlist para organizar os anúncios</p>
            <button style={{ ...s.actionBtn, background:"linear-gradient(135deg,#7c3aed,#9b59f5)", color:"#fff", marginTop:8 }}
              onClick={() => setCriando(true)}>
              <Plus size={14}/> Criar playlist
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

const s = {
  wrap: { overflowY:"auto", flex:1 },
  header: { position:"relative", padding:"44px 32px 24px" },
  headerGrad: { position:"absolute", inset:0 },
  headerContent: { position:"relative", zIndex:1 },
  headerMain: { display:"flex", alignItems:"flex-end", gap:20, marginBottom:14 },
  headerIcon: {
    width:76, height:76, background:"rgba(124,58,237,.15)",
    borderRadius:12, display:"flex", alignItems:"center", justifyContent:"center",
    border:"1px solid rgba(124,58,237,.3)", flexShrink:0,
  },
  headerSub:   { fontSize:11, fontWeight:700, color:"#9b59f5", textTransform:"uppercase", letterSpacing:1.5 },
  headerTitle: { fontSize:32, fontWeight:800, color:"#f0eeff", marginBottom:4 },
  headerMeta:  { fontSize:13, color:"#7a7490" },
  headerActions: { display:"flex", gap:8, marginLeft:"auto" },
  actionBtn: {
    display:"flex", alignItems:"center", gap:6,
    border:"none", borderRadius:20, fontSize:12, fontWeight:600,
    padding:"7px 16px", cursor:"pointer", fontFamily:"'Figtree', sans-serif",
    color:"#f0eeff", background:"#1a1728",
  },
  backBtn: {
    display:"flex", alignItems:"center", gap:4, background:"transparent",
    border:"none", color:"#7a7490", fontSize:12, fontWeight:600,
    cursor:"pointer", marginBottom:14, fontFamily:"'Figtree', sans-serif",
  },
  nameInput: {
    background:"#1a1728", border:"1px solid #332f4d", borderRadius:6,
    color:"#f0eeff", fontSize:26, fontWeight:800, padding:"4px 12px",
    outline:"none", fontFamily:"'Figtree', sans-serif",
  },
  iconBtn: { background:"transparent", border:"none", cursor:"pointer", display:"flex", padding:4 },
  content: { padding:"20px 32px 80px" },
  addSection: { display:"flex", gap:10, marginBottom:12, alignItems:"stretch" },
  dropZone: {
    flex:1, border:"1.5px dashed #332f4d", borderRadius:8,
    padding:"16px 22px", display:"flex", alignItems:"center", justifyContent:"center",
    cursor:"pointer", transition:"all .2s", background:"#13111f",
  },
  dropZoneActive: { borderColor:"#7c3aed", background:"rgba(124,58,237,.06)" },
  dropContent: { display:"flex", alignItems:"center", gap:10 },
  dropTitle: { fontSize:13, color:"#a89ec0" },
  uploadingState: { display:"flex", flexDirection:"column", alignItems:"center", gap:6, width:"100%" },
  progressWrap: { width:"100%", height:3, background:"#2a2740", borderRadius:2 },
  progressFill: { height:"100%", background:"#9b59f5", borderRadius:2, transition:"width .2s" },
  uploadPct: { fontSize:11, color:"#9b59f5", fontFamily:"'DM Mono', monospace" },
  addUrlBtn: {
    display:"flex", alignItems:"center", gap:6, flexShrink:0,
    border:"1.5px dashed #332f4d", borderRadius:8, color:"#7a7490",
    fontSize:12, fontWeight:600, padding:"0 16px", cursor:"pointer",
    background:"transparent", fontFamily:"'Figtree', sans-serif", transition:"all .2s",
  },
  urlPanel: {
    display:"flex", gap:10, marginBottom:16, alignItems:"center",
    background:"#13111f", border:"1px solid #332f4d",
    borderRadius:8, padding:"12px 14px", flexWrap:"wrap",
  },
  urlInput: {
    background:"#1a1728", border:"1px solid #332f4d", borderRadius:6,
    color:"#f0eeff", fontSize:12, padding:"8px 10px", outline:"none",
    fontFamily:"'Figtree', sans-serif", minWidth:0,
  },
  urlAddBtn: {
    display:"flex", alignItems:"center", gap:5, flexShrink:0,
    background:"linear-gradient(135deg,#7c3aed,#9b59f5)", border:"none",
    borderRadius:16, color:"#fff", fontSize:12, fontWeight:700,
    padding:"8px 14px", cursor:"pointer", fontFamily:"'Figtree', sans-serif",
  },
  tableWrap: { display:"flex", flexDirection:"column" },
  tableHead: { display:"flex", alignItems:"center", gap:12, padding:"5px 10px 8px" },
  thCell:    { fontSize:10, fontWeight:700, color:"#7a7490", letterSpacing:1, textTransform:"uppercase" },
  divider:   { height:1, background:"#1a1728", marginBottom:4 },
  trackRow: {
    display:"flex", alignItems:"center", gap:12,
    padding:"9px 10px", borderRadius:6, transition:"background .15s",
  },
  tdCell:    { display:"flex", alignItems:"center", gap:8, overflow:"hidden" },
  trackNum:  { fontSize:12, color:"#7a7490", width:18, textAlign:"center", fontFamily:"'DM Mono', monospace" },
  trackThumb: {
    width:32, height:32, borderRadius:4,
    display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0,
  },
  trackName: { fontSize:13, fontWeight:500, color:"#f0eeff", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" },
  itemBtn: {
    display:"flex", alignItems:"center", justifyContent:"center",
    background:"transparent", border:"1px solid #332f4d", borderRadius:5,
    color:"#a89ec0", padding:"5px 7px", cursor:"pointer", transition:"all .15s",
  },
  itemBtnDanger: { color:"#f43f5e", borderColor:"rgba(244,63,94,.25)" },
  plGrid: { display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(190px, 1fr))", gap:12 },
  plCard: {
    background:"#13111f", borderRadius:10, padding:14,
    display:"flex", flexDirection:"column", gap:8,
    transition:"all .2s", border:"1px solid #221f33",
  },
  plCardThumb: {
    width:"100%", aspectRatio:"1", background:"#1a1728",
    borderRadius:8, display:"flex", alignItems:"center", justifyContent:"center",
    position:"relative", overflow:"hidden", cursor:"pointer",
  },
  plPlayBtn: {
    position:"absolute", bottom:8, right:8,
    width:38, height:38, borderRadius:"50%",
    background:"linear-gradient(135deg,#7c3aed,#9b59f5)",
    border:"none", color:"#fff", fontSize:14, cursor:"pointer",
    display:"flex", alignItems:"center", justifyContent:"center",
    boxShadow:"0 4px 14px rgba(124,58,237,.4)",
    opacity:0, transition:"opacity .2s",
  },
  plCardName:    { fontSize:13, fontWeight:700, color:"#f0eeff" },
  plCardMeta:    { fontSize:11, color:"#7a7490" },
  plCardActions: { display:"flex", gap:4, marginTop:2 },
  cardBtn: {
    background:"transparent", border:"none", cursor:"pointer",
    display:"flex", padding:4, borderRadius:4, transition:"opacity .15s",
  },
  empty: { display:"flex", flexDirection:"column", alignItems:"center", gap:10, padding:"70px 0" },
  emptyText: { fontSize:18, fontWeight:700, color:"#f0eeff" },
  emptySub:  { fontSize:13, color:"#7a7490" },
};

const m = {
  overlay: {
    position:"fixed", inset:0, background:"rgba(0,0,0,.7)",
    display:"flex", alignItems:"center", justifyContent:"center",
    zIndex:1000, backdropFilter:"blur(4px)",
  },
  box: {
    background:"#13111f", borderRadius:12, width:400,
    border:"1px solid #221f33", overflow:"hidden",
    boxShadow:"0 20px 60px rgba(0,0,0,.8)",
  },
  header: { display:"flex", alignItems:"center", gap:8, padding:"16px 18px", borderBottom:"1px solid #1a1728" },
  title:  { fontSize:15, fontWeight:700, color:"#f0eeff", flex:1 },
  closeBtn: { background:"transparent", border:"none", color:"#7a7490", cursor:"pointer", display:"flex", padding:2 },
  body:    { padding:"18px" },
  trackName: {
    fontSize:13, fontWeight:600, color:"#f0eeff", marginBottom:16,
    padding:"8px 10px", background:"#1a1728", borderRadius:6,
  },
  field: { display:"flex", flexDirection:"column", gap:6, marginBottom:16 },
  label: {
    display:"flex", alignItems:"center", gap:5,
    fontSize:11, fontWeight:700, color:"#7a7490", textTransform:"uppercase", letterSpacing:.5,
  },
  input: {
    background:"#1a1728", border:"1px solid #332f4d", borderRadius:6,
    color:"#f0eeff", fontSize:13, padding:"9px 10px",
    outline:"none", fontFamily:"'Figtree', sans-serif",
  },
  hint: { fontSize:10, color:"#7a7490" },
  loopRow: { display:"flex", alignItems:"center", gap:8 },
  loopBtn: {
    width:34, height:34, background:"#1a1728", border:"1px solid #332f4d",
    borderRadius:6, color:"#f0eeff", fontSize:18, cursor:"pointer",
    display:"flex", alignItems:"center", justifyContent:"center",
  },
  footer: { display:"flex", gap:8, justifyContent:"flex-end", padding:"12px 18px", borderTop:"1px solid #1a1728" },
  cancelBtn: {
    background:"transparent", border:"1px solid #332f4d", borderRadius:16,
    color:"#7a7490", fontSize:12, fontWeight:600, padding:"7px 14px",
    cursor:"pointer", fontFamily:"'Figtree', sans-serif",
  },
  saveBtn: {
    display:"flex", alignItems:"center", gap:5,
    background:"linear-gradient(135deg,#7c3aed,#9b59f5)", border:"none", borderRadius:16,
    color:"#fff", fontSize:12, fontWeight:700, padding:"7px 16px",
    cursor:"pointer", fontFamily:"'Figtree', sans-serif",
  },
};