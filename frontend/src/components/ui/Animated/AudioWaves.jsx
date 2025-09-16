// components/AudioWaves.jsx
import React, { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

function Bars() {
  const barsRef = useRef([]);
  
  useFrame(() => {
    barsRef.current.forEach((bar, i) => {
      if (!bar) return;
      // animación de subida/bajada
      const scaleY = Math.abs(Math.sin(Date.now() * 0.002 + i)) * 2 + 0.2;
      bar.scale.y = scaleY;
    });
  });

  return (
    <>
      {Array.from({ length: 12 }).map((_, i) => (
        <mesh
          key={i}
          ref={(el) => (barsRef.current[i] = el)}
          position={[i * 0.5 - 3, 0, 0]}
        >
          <boxGeometry args={[0.3, 1, 0.3]} />
          <meshStandardMaterial color="#00ffff" emissive="#00ffff" />
        </mesh>
      ))}
    </>
  );
}

const AudioWaves = () => {
  return (
    <div style={{ width: "160px", height: "160px" }}>
      <Canvas camera={{ position: [0, 5, 8], fov: 40 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[0, 5, 5]} intensity={1} />
        <Bars />
      </Canvas>
    </div>
  );
};

export default AudioWaves;
