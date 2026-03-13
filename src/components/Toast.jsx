// src/components/Toast.jsx
import { createContext, useContext, useState, useCallback } from "react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const toast = useCallback((msg, type = "info") => {
    const id = Date.now();
    setToasts(t => [...t, { id, msg, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500);
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div style={styles.container}>
        {toasts.map(t => (
          <div key={t.id} style={{ ...styles.toast, ...styles[t.type] }}>
            {t.msg}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);

const styles = {
  container: {
    position: "fixed",
    bottom: 100,
    right: 24,
    display: "flex",
    flexDirection: "column",
    gap: 8,
    zIndex: 9999,
    pointerEvents: "none",
  },
  toast: {
    background: "#282828",
    color: "#fff",
    padding: "12px 20px",
    borderRadius: 6,
    fontSize: 13,
    fontWeight: 500,
    fontFamily: "'Figtree', sans-serif",
    boxShadow: "0 4px 20px rgba(0,0,0,.5)",
    animation: "fadeIn .3s ease",
    borderLeft: "3px solid #6a6a6a",
  },
  success: { borderLeftColor: "#1db954" },
  error:   { borderLeftColor: "#ff4444" },
  info:    { borderLeftColor: "#1db954" },
};
