// src/context/AuthContext.jsx
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut
} from "firebase/auth";
import { ref, get, set, update } from "firebase/database";
import { auth, db } from "../firebase";

const AuthContext = createContext(null);

// Gera código no formato PLAY-XXXX-XXXX (baseado no uid)
function gerarCodigo(uid) {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let hash = 0;
  for (let i = 0; i < uid.length; i++) {
    hash = ((hash << 5) - hash) + uid.charCodeAt(i);
    hash |= 0;
  }
  const abs = Math.abs(hash);
  let part1 = "", part2 = "";
  let n = abs;
  for (let i = 0; i < 4; i++) {
    part1 = chars[n % chars.length] + part1;
    n = Math.floor(n / chars.length);
  }
  n = abs ^ 0xDEADBEEF;
  for (let i = 0; i < 4; i++) {
    part2 = chars[Math.abs(n) % chars.length] + part2;
    n = Math.floor(n / chars.length);
  }
  return `PLAY-${part1}-${part2}`;
}

export function AuthProvider({ children }) {
  const [user,      setUser]      = useState(undefined); // undefined = carregando
  const [userData,  setUserData]  = useState(null);      // dados do /users/{uid}
  const [loadingUD, setLoadingUD] = useState(false);

  // Carrega dados do usuário e garante que o código existe
  const carregarUserData = useCallback(async (firebaseUser) => {
    if (!firebaseUser) { setUserData(null); return; }
    setLoadingUD(true);
    try {
      const userRef  = ref(db, `users/${firebaseUser.uid}`);
      const snap     = await get(userRef);
      const existing = snap.val();

      if (existing?.codigo) {
        setUserData(existing);
      } else {
        // Primeiro acesso — cria o nó e registra o código
        const codigo = gerarCodigo(firebaseUser.uid);
        const novosDados = {
          email:           firebaseUser.email,
          codigo,
          player_ativo:    false,
          player_last_seen: 0,
          criado_em:       Date.now(),
        };
        await set(userRef, novosDados);
        // Índice reverso: /codigos/{codigo} → uid
        await set(ref(db, `codigos/${codigo}`), { uid: firebaseUser.uid });
        setUserData(novosDados);
      }
    } catch (e) {
      console.error("carregarUserData:", e);
    } finally {
      setLoadingUD(false);
    }
  }, []);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      carregarUserData(u);
    });
    return unsub;
  }, [carregarUserData]);

  const login = async (email, pass) => {
    const cred = await signInWithEmailAndPassword(auth, email, pass);
    return cred;
  };

  const register = async (email, pass) => {
    const cred = await createUserWithEmailAndPassword(auth, email, pass);
    return cred;
  };

  const logout = () => signOut(auth);

  return (
    <AuthContext.Provider value={{ user, userData, loadingUD, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);