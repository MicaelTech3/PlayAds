// src/hooks/useFirebase.js
// Todos os dados ficam em /users/{uid}/ — isolado por conta
import { useEffect, useState, useCallback } from "react";
import {
  ref, onValue, push, remove, update, set, get
} from "firebase/database";
import {
  ref as sRef, uploadBytesResumable, getDownloadURL, deleteObject
} from "firebase/storage";
import { db, storage } from "../firebase";
import { useAuth } from "../context/AuthContext";

const useUid = () => {
  const { user } = useAuth();
  return user?.uid ?? null;
};

// ── Anúncios ─────────────────────────────────────────────────────
export function useAnuncios() {
  const uid = useUid();
  const [anuncios, setAnuncios] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!uid) return;
    const unsub = onValue(ref(db, `users/${uid}/anuncios`), snap => {
      setAnuncios(snap.val() || {});
      setLoading(false);
    });
    return unsub;
  }, [uid]);

  const deleteAnuncio = useCallback(async (id, filename) => {
    if (filename) {
      try { await deleteObject(sRef(storage, `users/${uid}/audios/${filename}`)); } catch (_) { }
    }
    await remove(ref(db, `users/${uid}/anuncios/${id}`));
  }, [uid]);

  const uploadAnuncio = useCallback((file, onProgress) => {
    return new Promise((resolve, reject) => {
      const filename = `${Date.now()}_${file.name.replace(/\s+/g, "_")}`;
      const storageRef = sRef(storage, `users/${uid}/audios/${filename}`);
      const task = uploadBytesResumable(storageRef, file);

      task.on("state_changed",
        snap => onProgress?.(Math.round(snap.bytesTransferred / snap.totalBytes * 100)),
        reject,
        async () => {
          const url = await getDownloadURL(task.snapshot.ref);
          const novo = {
            nome: file.name.replace(/\.(mp3|wav)$/i, ""),
            filename, url,
            tamanho: file.size,
            tipo: file.type,
            criado_em: Date.now(),
          };
          await push(ref(db, `users/${uid}/anuncios`), novo);
          resolve(novo);
        }
      );
    });
  }, [uid]);

  const addUrlAnuncio = useCallback(async ({ nome, url, tipo = "url" }) => {
    const isYT = url.includes("youtube.com") || url.includes("youtu.be");
    const novo = {
      nome: nome || (isYT ? "Vídeo YouTube" : url.split("/").pop()),
      url,
      filename: null,
      tamanho: null,
      tipo: isYT ? "youtube" : tipo,
      criado_em: Date.now(),
    };
    await push(ref(db, `users/${uid}/anuncios`), novo);
    return novo;
  }, [uid]);

  return { anuncios, loading, deleteAnuncio, uploadAnuncio, addUrlAnuncio };
}

// ── Playlists ─────────────────────────────────────────────────────
export function usePlaylists() {
  const uid = useUid();
  const [playlists, setPlaylists] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!uid) return;
    // Listener em tempo real — sempre sincronizado
    const unsub = onValue(ref(db, `users/${uid}/playlists`), snap => {
      setPlaylists(snap.val() || {});
      setLoading(false);
    });
    return unsub;
  }, [uid]);

  const criarPlaylist = useCallback(async (nome) => {
    const r = await push(ref(db, `users/${uid}/playlists`), {
      nome, ativa: false, itens: [], criado_em: Date.now(),
    });
    return r.key;
  }, [uid]);

  const renomearPlaylist = useCallback(async (id, novoNome) => {
    await update(ref(db, `users/${uid}/playlists/${id}`), { nome: novoNome });
  }, [uid]);

  const togglePlaylist = useCallback(async (id, atual) => {
    await update(ref(db, `users/${uid}/playlists/${id}`), { ativa: !atual });
  }, [uid]);

  const deletePlaylist = useCallback(async (id) => {
    await remove(ref(db, `users/${uid}/playlists/${id}`));
  }, [uid]);

  const adicionarItem = useCallback(async (playlistId, item) => {
    const snap = await get(ref(db, `users/${uid}/playlists/${playlistId}/itens`));
    const itens = snap.val() || [];
    const novoItem = {
      id: `item_${Date.now()}`,
      nome: item.nome,
      url: item.url,
      filename: item.filename || null,
      tipo: item.tipo || "url",
      tamanho: item.tamanho || null,
      loops: item.loops || 1,
      horario: item.horario || null,
    };
    itens.push(novoItem);
    await update(ref(db, `users/${uid}/playlists/${playlistId}`), { itens });
    return novoItem;
  }, [uid]);

  const atualizarItem = useCallback(async (playlistId, itemIndex, dados) => {
    const snap = await get(ref(db, `users/${uid}/playlists/${playlistId}/itens`));
    const itens = snap.val() || [];
    if (itens[itemIndex]) {
      itens[itemIndex] = { ...itens[itemIndex], ...dados };
      await update(ref(db, `users/${uid}/playlists/${playlistId}`), { itens });
    }
  }, [uid]);

  const removerItem = useCallback(async (playlistId, itemIndex) => {
    const snap = await get(ref(db, `users/${uid}/playlists/${playlistId}/itens`));
    const itens = snap.val() || [];
    itens.splice(itemIndex, 1);
    await update(ref(db, `users/${uid}/playlists/${playlistId}`), { itens });
  }, [uid]);

  const uploadItemPlaylist = useCallback((playlistId, file, onProgress) => {
    return new Promise((resolve, reject) => {
      const filename = `${Date.now()}_${file.name.replace(/\s+/g, "_")}`;
      const storageRef = sRef(storage, `users/${uid}/audios/${filename}`);
      const task = uploadBytesResumable(storageRef, file);

      task.on("state_changed",
        snap => onProgress?.(Math.round(snap.bytesTransferred / snap.totalBytes * 100)),
        reject,
        async () => {
          const url = await getDownloadURL(task.snapshot.ref);
          const item = {
            nome: file.name.replace(/\.(mp3|wav)$/i, ""),
            url, filename, tipo: file.type, tamanho: file.size,
            loops: 1, horario: null,
          };
          const novoItem = await adicionarItem(playlistId, item);
          resolve(novoItem);
        }
      );
    });
  }, [uid, adicionarItem]);

  /**
   * playNow — envia comando de reprodução ao software.
   * 
   * Modo 1: playNow(playlistId)
   *   → toca a playlist existente pelo ID.
   *
   * Modo 2: playNow(null, { nome, url, loops, tipo })
   *   → cria uma playlist temporária de um único item e envia o comando.
   *   O software vai tocar esse item com o número de loops especificado.
   */
  const playNow = useCallback(async (playlistId, singleItem = null) => {
    const ts = Date.now();

    if (singleItem) {
      // Cria uma playlist temporária "Ad-Hoc" no Firebase com o item único
      const tempPlaylist = {
        nome: `Ad-Hoc: ${singleItem.nome}`,
        ativa: false,
        criado_em: ts,
        temp: true, // flag para o software saber que é temporária
        itens: [{
          id: `adhoc_${ts}`,
          nome: singleItem.nome,
          url: singleItem.url,
          tipo: singleItem.tipo || "url",
          loops: singleItem.loops || 1,
          horario: null,
          filename: singleItem.filename || null,
          tamanho: singleItem.tamanho || null,
        }],
      };

      // Salva temporariamente e obtém o ID
      const tempRef = await push(ref(db, `users/${uid}/playlists`), tempPlaylist);
      const tempId = tempRef.key;

      // Envia o comando de play
      await set(ref(db, `users/${uid}/comandos/play_now`), {
        playlist_id: tempId,
        timestamp: ts,
        executado: false,
        temp_playlist_id: tempId, // o software pode deletar depois de tocar
      });
    } else {
      // Toca playlist existente
      await set(ref(db, `users/${uid}/comandos/play_now`), {
        playlist_id: playlistId,
        timestamp: ts,
        executado: false,
      });
    }
  }, [uid]);

  const stopNow = useCallback(async () => {
    await set(ref(db, `users/${uid}/comandos/stop`), {
      timestamp: Date.now(), executado: false,
    });
  }, [uid]);

  // salvarPlaylist: reescreve nome, ativa e itens de uma vez
  const salvarPlaylist = useCallback(async (id, data) => {
    await update(ref(db, `users/${uid}/playlists/${id}`), {
      nome:  data.nome,
      ativa: data.ativa ?? false,
      itens: data.itens || [],
    });
  }, [uid]);

  return {
    playlists, loading,
    criarPlaylist, renomearPlaylist, togglePlaylist, deletePlaylist,
    adicionarItem, atualizarItem, removerItem, uploadItemPlaylist,
    salvarPlaylist, playNow, stopNow,
  };
}

// ── Players ───────────────────────────────────────────────────────
export function usePlayers() {
  const uid = useUid();
  const [playerStatus, setPlayerStatus] = useState(null);
  // Objeto completo de players (compatível com página Players.jsx)
  const [players, setPlayers] = useState({});

  useEffect(() => {
    if (!uid) return;
    // Player único por conta — lê /users/{uid}/player_status em tempo real
    const unsub = onValue(ref(db, `users/${uid}/player_status`), snap => {
      const data = snap.val();
      setPlayerStatus(data);
      // Mantém compatibilidade com a página Players que espera um objeto { id: {...} }
      if (data) {
        setPlayers({ [uid]: data });
      } else {
        setPlayers({});
      }
    });
    return unsub;
  }, [uid]);

  return { playerStatus, players };
}

// ── Logs ──────────────────────────────────────────────────────────
export function useLogs() {
  const uid = useUid();
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (!uid) return;
    const unsub = onValue(ref(db, `users/${uid}/logs`), snap => {
      const raw = snap.val() || {};
      const arr = Object.entries(raw)
        .map(([id, l]) => ({ id, ...l }))
        .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
        .slice(0, 150);
      setLogs(arr);
    });
    return unsub;
  }, [uid]);

  return { logs };
}