// src/context/PlayerContext.jsx
import { createContext, useContext, useRef, useState, useCallback } from "react";

const PlayerContext = createContext(null);

export function PlayerProvider({ children }) {
  const audioRef = useRef(new Audio());
  const [nowPlaying, setNowPlaying]   = useState(null);   // { nome, url, filename }
  const [isPlaying,  setIsPlaying]    = useState(false);
  const [progress,   setProgress]     = useState(0);       // 0-100
  const [duration,   setDuration]     = useState(0);
  const [volume,     setVolumeState]  = useState(80);
  const intervalRef = useRef(null);

  const _startProgress = useCallback(() => {
    clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      const a = audioRef.current;
      if (a.duration) setProgress((a.currentTime / a.duration) * 100);
    }, 500);
  }, []);

  const play = useCallback((track) => {
    const a = audioRef.current;
    if (nowPlaying?.url === track.url && !a.paused) return;

    a.pause();
    a.src = track.url;
    a.volume = volume / 100;
    a.play().then(() => {
      setNowPlaying(track);
      setIsPlaying(true);
      _startProgress();
    }).catch(() => {});

    a.onloadedmetadata = () => setDuration(a.duration);
    a.onended = () => {
      setIsPlaying(false);
      setProgress(0);
      clearInterval(intervalRef.current);
    };
  }, [nowPlaying, volume, _startProgress]);

  const togglePlay = useCallback(() => {
    const a = audioRef.current;
    if (!nowPlaying) return;
    if (a.paused) { a.play(); setIsPlaying(true); _startProgress(); }
    else           { a.pause(); setIsPlaying(false); clearInterval(intervalRef.current); }
  }, [nowPlaying, _startProgress]);

  const seek = useCallback((pct) => {
    const a = audioRef.current;
    if (a.duration) a.currentTime = (pct / 100) * a.duration;
    setProgress(pct);
  }, []);

  const setVolume = useCallback((v) => {
    audioRef.current.volume = v / 100;
    setVolumeState(v);
  }, []);

  const stop = useCallback(() => {
    audioRef.current.pause();
    audioRef.current.currentTime = 0;
    setIsPlaying(false);
    setProgress(0);
    setNowPlaying(null);
    clearInterval(intervalRef.current);
  }, []);

  return (
    <PlayerContext.Provider value={{
      nowPlaying, isPlaying, progress, duration, volume,
      play, togglePlay, seek, setVolume, stop
    }}>
      {children}
    </PlayerContext.Provider>
  );
}

export const usePlayer = () => useContext(PlayerContext);
