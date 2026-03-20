// hooks/useAudioAnalyser.js
import { useEffect, useRef } from "react";

export default function useAudioAnalyser(htmlAudioElement, onLevel) {
  const rafId = useRef(null);

  useEffect(() => {
    if (!htmlAudioElement) return;

    const ctx = new AudioContext();
    const src = ctx.createMediaElementSource(htmlAudioElement);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;

    src.connect(analyser);
    analyser.connect(ctx.destination);

    const data = new Uint8Array(analyser.frequencyBinCount);

    function loop() {
      analyser.getByteFrequencyData(data);
      const avg = data.reduce((a, b) => a + b, 0) / data.length;
      const level = Math.min(1, avg / 180); // normalización
      onLevel(level);
      rafId.current = requestAnimationFrame(loop);
    }

    htmlAudioElement.onplay = () => loop();
    htmlAudioElement.onpause = htmlAudioElement.onended = () => {
      cancelAnimationFrame(rafId.current);
      onLevel(0);
    };

    return () => {
      cancelAnimationFrame(rafId.current);
      ctx.close();
    };
  }, [htmlAudioElement, onLevel]);
}
