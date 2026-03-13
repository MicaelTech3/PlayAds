// src/components/PlayerBar.jsx
import { usePlayer } from "../context/PlayerContext";
import {
  Play, Pause, Square, Volume2, VolumeX, Music2
} from "lucide-react";

function fmt(secs) {
  if (!secs || isNaN(secs)) return "0:00";
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function PlayerBar() {
  const { nowPlaying, isPlaying, progress, duration, volume,
          togglePlay, seek, setVolume, stop } = usePlayer();

  const elapsed = duration ? (progress / 100) * duration : 0;

  return (
    <div style={styles.bar}>
      {/* Track info */}
      <div style={styles.trackInfo}>
        <div style={styles.thumb}>
          {nowPlaying
            ? <Music2 size={18} color="#1db954" />
            : <Music2 size={18} color="#6a6a6a" />
          }
        </div>
        <div style={styles.trackText}>
          <span style={styles.trackName}>
            {nowPlaying ? nowPlaying.nome : "Nenhum anúncio"}
          </span>
          <span style={styles.trackSub}>
            {nowPlaying ? "Reproduzindo agora" : "Selecione um anúncio"}
          </span>
        </div>
      </div>

      {/* Controls */}
      <div style={styles.controls}>
        <div style={styles.btnRow}>
          <button
            style={{ ...styles.ctrlBtn, ...styles.playBtn }}
            onClick={togglePlay}
            disabled={!nowPlaying}
          >
            {isPlaying
              ? <Pause size={20} fill="#000" color="#000" />
              : <Play  size={20} fill="#000" color="#000" />
            }
          </button>
          <button
            style={styles.ctrlBtn}
            onClick={stop}
            disabled={!nowPlaying}
          >
            <Square size={16} color={nowPlaying ? "#b3b3b3" : "#4a4a4a"} />
          </button>
        </div>

        {/* Progress */}
        <div style={styles.progressRow}>
          <span style={styles.time}>{fmt(elapsed)}</span>
          <div
            style={styles.progressTrack}
            onClick={e => {
              const rect = e.currentTarget.getBoundingClientRect();
              seek(((e.clientX - rect.left) / rect.width) * 100);
            }}
          >
            <div style={{ ...styles.progressFill, width: `${progress}%` }}>
              <div style={styles.progressThumb} />
            </div>
          </div>
          <span style={styles.time}>{fmt(duration)}</span>
        </div>
      </div>

      {/* Volume */}
      <div style={styles.volArea}>
        <button style={styles.volBtn} onClick={() => setVolume(volume > 0 ? 0 : 80)}>
          {volume === 0
            ? <VolumeX size={18} color="#b3b3b3" />
            : <Volume2 size={18} color="#b3b3b3" />
          }
        </button>
        <div
          style={styles.volTrack}
          onClick={e => {
            const rect = e.currentTarget.getBoundingClientRect();
            setVolume(Math.round(((e.clientX - rect.left) / rect.width) * 100));
          }}
        >
          <div style={{ ...styles.volFill, width: `${volume}%` }} />
        </div>
        <span style={styles.volLabel}>{volume}%</span>
      </div>
    </div>
  );
}

const styles = {
  bar: {
    height: 90,
    background: "#181818",
    borderTop: "1px solid #282828",
    display: "grid",
    gridTemplateColumns: "1fr 2fr 1fr",
    alignItems: "center",
    padding: "0 20px",
    flexShrink: 0,
    zIndex: 50,
  },
  trackInfo: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  thumb: {
    width: 52,
    height: 52,
    background: "#282828",
    borderRadius: 4,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  trackText: {
    display: "flex",
    flexDirection: "column",
    gap: 3,
    overflow: "hidden",
  },
  trackName: {
    fontSize: 13,
    fontWeight: 600,
    color: "#fff",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  trackSub: {
    fontSize: 11,
    color: "#b3b3b3",
  },
  controls: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    padding: "0 20px",
  },
  btnRow: {
    display: "flex",
    alignItems: "center",
    gap: 16,
  },
  ctrlBtn: {
    background: "transparent",
    border: "none",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 4,
    borderRadius: "50%",
    transition: "transform .1s",
  },
  playBtn: {
    width: 36,
    height: 36,
    background: "#fff",
    borderRadius: "50%",
  },
  progressRow: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    width: "100%",
  },
  time: {
    fontSize: 11,
    color: "#b3b3b3",
    fontFamily: "'DM Mono', monospace",
    minWidth: 32,
    textAlign: "center",
  },
  progressTrack: {
    flex: 1,
    height: 4,
    background: "#3e3e3e",
    borderRadius: 2,
    cursor: "pointer",
    position: "relative",
    overflow: "visible",
  },
  progressFill: {
    height: "100%",
    background: "#fff",
    borderRadius: 2,
    position: "relative",
    transition: "width .3s linear",
  },
  progressThumb: {
    width: 12,
    height: 12,
    background: "#fff",
    borderRadius: "50%",
    position: "absolute",
    right: -6,
    top: "50%",
    transform: "translateY(-50%)",
  },
  volArea: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    justifyContent: "flex-end",
  },
  volBtn: {
    background: "transparent",
    border: "none",
    cursor: "pointer",
    display: "flex",
    padding: 4,
  },
  volTrack: {
    width: 90,
    height: 4,
    background: "#3e3e3e",
    borderRadius: 2,
    cursor: "pointer",
  },
  volFill: {
    height: "100%",
    background: "#1db954",
    borderRadius: 2,
  },
  volLabel: {
    fontSize: 11,
    color: "#b3b3b3",
    fontFamily: "'DM Mono', monospace",
    minWidth: 28,
  },
};
