// src/firebase.js
// ─────────────────────────────────────────────────────────────
//  SUBSTITUA COM AS SUAS CREDENCIAIS DO FIREBASE
//  Console Firebase → Projeto → Configurações → Seus apps → Web
// ─────────────────────────────────────────────────────────────
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getDatabase } from "firebase/database";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: "AIzaSyBgwB_2syWdyK5Wc0E9rJIlDnXjwTf1OWE",
  authDomain: "anucio-web.firebaseapp.com",
  // ADICIONE ESTA LINHA ABAIXO:
  databaseURL: "https://anucio-web-default-rtdb.firebaseio.com",
  projectId: "anucio-web",
  storageBucket: "anucio-web.firebasestorage.app",
  messagingSenderId: "389219921149",
  appId: "1:389219921149:web:247f583c8c045001eaa294"
};

const app = initializeApp(firebaseConfig);

export const auth    = getAuth(app);
export const db      = getDatabase(app);
export const storage = getStorage(app);
export default app;
