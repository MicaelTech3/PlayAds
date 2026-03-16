// src/hooks/useFirebase.js
// Estrutura: users/{email,com}/playlists, anuncios, logs, etc.
import { useEffect, useState, useCallback } from "react";
import { ref, onValue, push, remove, update, set, get } from "firebase/database";
import { ref as sRef, uploadBytesResumable, getDownloadURL, deleteObject } from "firebase/storage";
import { db, storage } from "../firebase";
import { useAuth, emailToKey } from "../context/AuthContext";

// Pega a chave do usuário (email com . → ,)
const useUserKey = () => {
  const { user, userData } = useAuth();
  // Usa _key do userData se disponível, senão gera do email
  return userData?._key ?? (user?.email ? emailToKey(user.email) : null);
};

// ── Sanitiza item antes de salvar ─────────────────────────────────
function sanitizeItem(item) {
  const horarios = Array.isArray(item.horarios)
    ? item.horarios.filter(h => h && typeof h === "string" && h.match(/^\d{2}:\d{2}$/))
    : item.horario
      ? [item.horario]
      : [];

  const diasValidos = ["dom","seg","ter","qua","qui","sex","sab"];
  const dias = Array.isArray(item.dias) && item.dias.length > 0
    ? item.dias.filter(d => diasValidos.includes(d))
    : diasValidos;

  return {
    nome:     item.nome     || "",
    url:      item.url      || "",
    tipo:     item.tipo     || "url",
    loops:    Number(item.loops) || 1,
    filename: item.filename || null,
    tamanho:  item.tamanho  || null,
    horarios: horarios,
    horario:  horarios[0] || null,
    dias,
  };
}

// ── Anúncios ──────────────────────────────────────────────────────
export function useAnuncios() {
  const key = useUserKey();
  const [anuncios, setAnuncios] = useState({});
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    if (!key) return;
    return onValue(ref(db, `users/${key}/anuncios`), snap => {
      setAnuncios(snap.val() || {});
      setLoading(false);
    });
  }, [key]);

  const deleteAnuncio = useCallback(async (id, filename) => {
    if (filename) {
      try { await deleteObject(sRef(storage, `users/${key}/audios/${filename}`)); } catch (_) {}
    }
    await remove(ref(db, `users/${key}/anuncios/${id}`));
  }, [key]);

  const uploadAnuncio = useCallback((file, onProgress) => {
    return new Promise((resolve, reject) => {
      const filename   = `${Date.now()}_${file.name.replace(/\s+/g, "_")}`;
      const storageRef = sRef(storage, `users/${key}/audios/${filename}`);
      const task       = uploadBytesResumable(storageRef, file);
      task.on("state_changed",
        snap => onProgress?.(Math.round(snap.bytesTransferred / snap.totalBytes * 100)),
        reject,
        async () => {
          const url  = await getDownloadURL(task.snapshot.ref);
          const novo = {
            nome: file.name.replace(/\.(mp3|wav)$/i, ""),
            filename, url, tamanho: file.size,
            tipo: file.type, criado_em: Date.now(),
          };
          await push(ref(db, `users/${key}/anuncios`), novo);
          resolve(novo);
        }
      );
    });
  }, [key]);

  const addUrlAnuncio = useCallback(async ({ nome, url, tipo = "url" }) => {
    const isYT = url.includes("youtube.com") || url.includes("youtu.be");
    const novo = {
      nome: nome || (isYT ? "Vídeo YouTube" : url.split("/").pop()),
      url, filename: null, tamanho: null,
      tipo: isYT ? "youtube" : tipo,
      criado_em: Date.now(),
    };
    await push(ref(db, `users/${key}/anuncios`), novo);
    return novo;
  }, [key]);

  return { anuncios, loading, deleteAnuncio, uploadAnuncio, addUrlAnuncio };
}

// ── Playlists ─────────────────────────────────────────────────────
export function usePlaylists() {
  const key = useUserKey();
  const [playlists, setPlaylists] = useState({});
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    if (!key) return;
    return onValue(ref(db, `users/${key}/playlists`), snap => {
      setPlaylists(snap.val() || {});
      setLoading(false);
    });
  }, [key]);

  const criarPlaylist = useCallback(async (nome) => {
    const r = await push(ref(db, `users/${key}/playlists`), {
      nome, ativa: false, itens: [], criado_em: Date.now(),
    });
    return r.key;
  }, [key]);

  const renomearPlaylist = useCallback(async (id, novoNome) => {
    await update(ref(db, `users/${key}/playlists/${id}`), { nome: novoNome });
  }, [key]);

  const togglePlaylist = useCallback(async (id, atual) => {
    await update(ref(db, `users/${key}/playlists/${id}`), { ativa: !atual });
  }, [key]);

  const deletePlaylist = useCallback(async (id) => {
    await remove(ref(db, `users/${key}/playlists/${id}`));
  }, [key]);

  const salvarPlaylist = useCallback(async (id, data) => {
    const itens = (data.itens || []).map(sanitizeItem);
    console.log("💾 salvarPlaylist:", id, JSON.stringify({ nome: data.nome, ativa: data.ativa, itens }, null, 2));
    await update(ref(db, `users/${key}/playlists/${id}`), {
      nome:  data.nome,
      ativa: data.ativa ?? false,
      itens,
    });
  }, [key]);

  const adicionarItem = useCallback(async (playlistId, item) => {
    const snap  = await get(ref(db, `users/${key}/playlists/${playlistId}/itens`));
    const itens = snap.val() || [];
    itens.push(sanitizeItem(item));
    await update(ref(db, `users/${key}/playlists/${playlistId}`), { itens });
  }, [key]);

  const atualizarItem = useCallback(async (playlistId, itemIndex, dados) => {
    const snap  = await get(ref(db, `users/${key}/playlists/${playlistId}/itens`));
    const itens = snap.val() || [];
    if (itens[itemIndex]) {
      itens[itemIndex] = sanitizeItem({ ...itens[itemIndex], ...dados });
      await update(ref(db, `users/${key}/playlists/${playlistId}`), { itens });
    }
  }, [key]);

  const removerItem = useCallback(async (playlistId, itemIndex) => {
    const snap  = await get(ref(db, `users/${key}/playlists/${playlistId}/itens`));
    const itens = snap.val() || [];
    itens.splice(itemIndex, 1);
    await update(ref(db, `users/${key}/playlists/${playlistId}`), { itens });
  }, [key]);

  const uploadItemPlaylist = useCallback((playlistId, file, onProgress) => {
    return new Promise((resolve, reject) => {
      const filename   = `${Date.now()}_${file.name.replace(/\s+/g, "_")}`;
      const storageRef = sRef(storage, `users/${key}/audios/${filename}`);
      const task       = uploadBytesResumable(storageRef, file);
      task.on("state_changed",
        snap => onProgress?.(Math.round(snap.bytesTransferred / snap.totalBytes * 100)),
        reject,
        async () => {
          const url   = await getDownloadURL(task.snapshot.ref);
          const item  = sanitizeItem({ nome: file.name.replace(/\.(mp3|wav)$/i, ""), url, filename, tipo: file.type, tamanho: file.size, loops: 1, horarios: [] });
          const snap2 = await get(ref(db, `users/${key}/playlists/${playlistId}/itens`));
          const itens = snap2.val() || [];
          itens.push(item);
          await update(ref(db, `users/${key}/playlists/${playlistId}`), { itens });
          resolve(item);
        }
      );
    });
  }, [key]);

  const playNow = useCallback(async (playlistId, singleItem = null) => {
    const ts = Date.now();
    if (singleItem) {
      const tempRef = await push(ref(db, `users/${key}/playlists`), {
        nome: `Ad-Hoc: ${singleItem.nome}`, ativa: false,
        criado_em: ts, temp: true,
        itens: [sanitizeItem({ ...singleItem, loops: singleItem.loops || 1, horarios: [], horario: null })],
      });
      await set(ref(db, `users/${key}/comandos/play_now`), {
        playlist_id: tempRef.key, timestamp: ts,
        executado: false, temp_playlist_id: tempRef.key,
      });
    } else {
      await set(ref(db, `users/${key}/comandos/play_now`), {
        playlist_id: playlistId, timestamp: ts, executado: false,
      });
    }
  }, [key]);

  const stopNow = useCallback(async () => {
    await set(ref(db, `users/${key}/comandos/stop`), { timestamp: Date.now(), executado: false });
  }, [key]);

  return {
    playlists, loading,
    criarPlaylist, renomearPlaylist, togglePlaylist, deletePlaylist,
    adicionarItem, atualizarItem, removerItem, uploadItemPlaylist,
    salvarPlaylist, playNow, stopNow,
  };
}

// ── Players ───────────────────────────────────────────────────────
export function usePlayers() {
  const key = useUserKey();
  const [playerStatus, setPlayerStatus] = useState(null);
  const [players,      setPlayers]      = useState({});

  useEffect(() => {
    if (!key) return;
    return onValue(ref(db, `users/${key}/player_status`), snap => {
      const data = snap.val();
      setPlayerStatus(data);
      if (data) setPlayers({ [key]: data });
      else      setPlayers({});
    });
  }, [key]);

  return { playerStatus, players };
}

// ── Logs ──────────────────────────────────────────────────────────
export function useLogs() {
  const key = useUserKey();
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (!key) return;
    return onValue(ref(db, `users/${key}/logs`), snap => {
      const raw = snap.val() || {};
      setLogs(
        Object.entries(raw)
          .map(([id, l]) => ({ id, ...l }))
          .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
          .slice(0, 150)
      );
    });
  }, [key]);

  return { logs };
}