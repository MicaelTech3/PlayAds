// src/pages/Login.jsx
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, register } = useAuth();
  const [mode,    setMode]    = useState("login"); // "login" | "register"
  const [email,   setEmail]   = useState("");
  const [pass,    setPass]    = useState("");
  const [pass2,   setPass2]   = useState("");
  const [error,   setError]   = useState("");
  const [loading, setLoading] = useState(false);

  const handle = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      if (mode === "register") {
        if (pass !== pass2) { setError("As senhas não coincidem."); return; }
        if (pass.length < 6) { setError("Senha mínima de 6 caracteres."); return; }
        await register(email, pass);
        // AuthContext cria o código automaticamente no primeiro acesso
      } else {
        await login(email, pass);
      }
    } catch (err) {
      const msg = err.code === "auth/user-not-found" || err.code === "auth/wrong-password"
        ? "E-mail ou senha incorretos."
        : err.code === "auth/email-already-in-use"
        ? "Este e-mail já está cadastrado."
        : "Erro ao entrar. Tente novamente.";
      setError(msg);
    } finally { setLoading(false); }
  };

  return (
    <div style={s.wrap}>
      <div style={s.bg}/>
      <div style={s.orb1}/><div style={s.orb2}/>
      <div style={s.card}>
        {/* Logo */}
        <div style={s.logo}>
          <div style={s.logoIcon}>
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="16" fill="#7c3aed"/>
              <polygon points="12,8 12,24 24,16" fill="white"/>
            </svg>
          </div>
          <span style={s.logoText}>PlayAds</span>
        </div>

        <h1 style={s.title}>
          {mode === "login" ? "Bem‑vindo de volta" : "Criar conta"}
        </h1>
        <p style={s.sub}>
          {mode === "login"
            ? "Painel de controle de anúncios"
            : "Seu código de ativação será gerado automaticamente"}
        </p>

        {error && <div style={s.error}>{error}</div>}

        <form onSubmit={handle} style={s.form}>
          <div style={s.field}>
            <label style={s.label}>E-mail</label>
            <input type="email" value={email} onChange={e=>setEmail(e.target.value)}
              style={s.input} placeholder="admin@empresa.com" required/>
          </div>
          <div style={s.field}>
            <label style={s.label}>Senha</label>
            <input type="password" value={pass} onChange={e=>setPass(e.target.value)}
              style={s.input} placeholder="••••••••" required minLength={6}/>
          </div>
          {mode === "register" && (
            <div style={s.field}>
              <label style={s.label}>Confirmar senha</label>
              <input type="password" value={pass2} onChange={e=>setPass2(e.target.value)}
                style={s.input} placeholder="••••••••" required/>
            </div>
          )}
          <button type="submit"
            style={{ ...s.btn, opacity: loading ? .7 : 1 }} disabled={loading}>
            {loading
              ? (mode==="login" ? "Entrando..." : "Criando conta...")
              : (mode==="login" ? "Entrar" : "Criar conta e ativar")}
          </button>
        </form>

        <div style={s.toggle}>
          {mode === "login" ? (
            <>Não tem conta?&nbsp;
              <button style={s.toggleBtn} onClick={()=>{setMode("register");setError("");}}>
                Cadastre-se
              </button>
            </>
          ) : (
            <>Já tem conta?&nbsp;
              <button style={s.toggleBtn} onClick={()=>{setMode("login");setError("");}}>
                Entrar
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const s = {
  wrap: {
    minHeight:"100vh", display:"flex", alignItems:"center",
    justifyContent:"center", background:"#0d0b14",
    position:"relative", overflow:"hidden",
  },
  bg: {
    position:"absolute", inset:0,
    background:"radial-gradient(ellipse 80% 60% at 50% -10%, rgba(124,58,237,.22) 0%, transparent 60%)",
    pointerEvents:"none",
  },
  orb1: {
    position:"absolute", width:300, height:300, borderRadius:"50%",
    background:"rgba(124,58,237,.06)", top:"10%", left:"5%",
    filter:"blur(60px)", pointerEvents:"none",
  },
  orb2: {
    position:"absolute", width:250, height:250, borderRadius:"50%",
    background:"rgba(155,89,245,.05)", bottom:"10%", right:"8%",
    filter:"blur(50px)", pointerEvents:"none",
  },
  card: {
    width:400, background:"#13111f", borderRadius:16,
    padding:"40px 44px 44px", display:"flex", flexDirection:"column",
    alignItems:"center", position:"relative", zIndex:1,
    border:"1px solid #2a2740", boxShadow:"0 32px 80px rgba(0,0,0,.6)",
  },
  logo: { display:"flex", alignItems:"center", gap:10, marginBottom:24 },
  logoIcon: {
    width:44, height:44, background:"rgba(124,58,237,.15)",
    borderRadius:12, display:"flex", alignItems:"center", justifyContent:"center",
  },
  logoText: {
    fontSize:24, fontWeight:800, color:"#f0eeff",
    letterSpacing:"-0.5px", fontFamily:"'Figtree', sans-serif",
  },
  title: { fontSize:21, fontWeight:700, color:"#f0eeff", marginBottom:5, textAlign:"center" },
  sub:   { fontSize:12, color:"#7a7490", marginBottom:24, textAlign:"center", lineHeight:1.5 },
  error: {
    width:"100%", background:"rgba(244,63,94,.1)",
    border:"1px solid rgba(244,63,94,.3)", color:"#f43f5e",
    fontSize:13, padding:"10px 14px", borderRadius:8,
    marginBottom:14, textAlign:"center",
  },
  form:  { width:"100%", display:"flex", flexDirection:"column", gap:12 },
  field: { display:"flex", flexDirection:"column", gap:5 },
  label: { fontSize:12, fontWeight:600, color:"#a89ec0", letterSpacing:".3px" },
  input: {
    background:"#1a1728", border:"1px solid #332f4d",
    borderRadius:8, color:"#f0eeff", fontSize:14,
    padding:"12px 14px", outline:"none",
    fontFamily:"'Figtree', sans-serif", transition:"border-color .2s",
  },
  btn: {
    marginTop:6,
    background:"linear-gradient(135deg, #7c3aed, #9b59f5)",
    color:"#fff", border:"none", borderRadius:30,
    fontFamily:"'Figtree', sans-serif", fontSize:14, fontWeight:700,
    padding:"13px", cursor:"pointer", letterSpacing:".3px",
    boxShadow:"0 4px 20px rgba(124,58,237,.35)",
    transition:"opacity .15s",
  },
  toggle: {
    marginTop:20, fontSize:13, color:"#7a7490",
    display:"flex", alignItems:"center",
  },
  toggleBtn: {
    background:"transparent", border:"none", color:"#9b59f5",
    fontSize:13, fontWeight:600, cursor:"pointer",
    fontFamily:"'Figtree', sans-serif", padding:0,
  },
};