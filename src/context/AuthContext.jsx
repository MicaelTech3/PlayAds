// src/context/AuthContext.jsx
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut
} from "firebase/auth";
import { ref, get, set } from "firebase/database";
import { auth, db } from "../firebase";

const AuthContext = createContext(null);

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
  for (let i = 0; i < 4; i++) { part1 = chars[n % chars.length] + part1; n = Math.floor(n / chars.length); }
  n = abs ^ 0xDEADBEEF;
  for (let i = 0; i < 4; i++) { part2 = chars[Math.abs(n) % chars.length] + part2; n = Math.floor(n / chars.length); }
  return `PLAY-${part1}-${part2}`;
}

// Converte email para chave Firebase-safe (. → ,)
export function emailToKey(email) {
  return email.replace(/\./g, ",");
}

export function AuthProvider({ children }) {
  const [user,      setUser]      = useState(undefined);
  const [userData,  setUserData]  = useState(null);
  const [loadingUD, setLoadingUD] = useState(false);

  const carregarUserData = useCallback(async (firebaseUser) => {
    if (!firebaseUser) { setUserData(null); return; }
    setLoadingUD(true);
    try {
      const emailKey = emailToKey(firebaseUser.email);

      // Tenta ler por email primeiro (nova estrutura)
      const emailRef  = ref(db, `users/${emailKey}`);
      const emailSnap = await get(emailRef);

      if (emailSnap.val()?.codigo) {
        setUserData({ ...emailSnap.val(), _key: emailKey });
        setLoadingUD(false);
        return;
      }

      // Fallback: tenta ler por uid (estrutura antiga)
      const uidRef  = ref(db, `users/${firebaseUser.uid}`);
      const uidSnap = await get(uidRef);
      const existing = uidSnap.val();

      if (existing?.codigo) {
        // Migra para estrutura de email
        await set(emailRef, { ...existing, email: firebaseUser.email });
        setUserData({ ...existing, _key: emailKey });
        setLoadingUD(false);
        return;
      }

      // Primeiro acesso — cria nó por email
      const codigo = gerarCodigo(firebaseUser.uid);
      const novosDados = {
        email:            firebaseUser.email,
        codigo,
        player_ativo:     false,
        player_last_seen: 0,
        criado_em:        Date.now(),
      };
      await set(emailRef, novosDados);
      await set(ref(db, `codigos/${codigo}`), { uid: firebaseUser.uid, email: firebaseUser.email, emailKey });
      setUserData({ ...novosDados, _key: emailKey });
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

  const login    = (email, pass) => signInWithEmailAndPassword(auth, email, pass);
  const register = (email, pass) => createUserWithEmailAndPassword(auth, email, pass);
  const logout   = () => signOut(auth);

  return (
    <AuthContext.Provider value={{ user, userData, loadingUD, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);