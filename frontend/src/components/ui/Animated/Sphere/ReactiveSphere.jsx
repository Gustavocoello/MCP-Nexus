/**
 * ReactiveSphere v3.0 - Esfera Abstracta Interactiva
 * - Red exterior tipo planeta (dispersa)
 * - Núcleo neuronal denso interior
 * - Colores: blanco
 * - Audio interactivo con botón micrófono
 */

import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
  useImperativeHandle,
  forwardRef,
} from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { CiMicrophoneOff, CiMicrophoneOn } from "react-icons/ci";
import "./ReactiveSphere.css";

/* ==================== AUDIO HOOK ==================== */
function useAudioLevel(active) {
  const [level, setLevel] = useState(0);
  const rafRef = useRef(null);
  const analyserRef = useRef(null);
  const audioCtxRef = useRef(null);
  const srcRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: { echoCancellation: true } 
        });
        audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
        analyserRef.current = audioCtxRef.current.createAnalyser();
        analyserRef.current.fftSize = 512;
        analyserRef.current.smoothingTimeConstant = 0.8;

        srcRef.current = audioCtxRef.current.createMediaStreamSource(stream);
        srcRef.current.connect(analyserRef.current);

        const bufferLen = analyserRef.current.frequencyBinCount;
        const dataRef = new Uint8Array(bufferLen);

        const tick = () => {
          if (!mounted) return;
          analyserRef.current.getByteFrequencyData(dataRef);
          const avg = dataRef.reduce((a, b) => a + b, 0) / dataRef.length;
          const normalized = Math.min(1, avg / 200);
          setLevel((prev) => prev * 0.82 + normalized * 0.18);
          rafRef.current = requestAnimationFrame(tick);
        };
        tick();
      } catch (err) {
        console.warn("Micrófono no disponible:", err);
      }
    }

    if (active) start();

    return () => {
      mounted = false;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (srcRef.current) srcRef.current.disconnect();
      if (audioCtxRef.current) audioCtxRef.current.close();
    };
  }, [active]);

  return level;
}

/* ==================== NEURAL NODES GENERATOR ==================== */
function generateNeuralNodes(count, radiusBase = 3.5) {
  const positions = new Float32Array(count * 3);
  const originalPositions = new Float32Array(count * 3);
  const seeds = new Float32Array(count);
  const energies = new Float32Array(count);

  for (let i = 0; i < count; i++) {
    const t = Math.random();
    const u = Math.random();
    
    // Esfera más redonda con menor distorsión
    const radiusNoise = Math.sin(t * Math.PI * 2) * 0.08 + Math.cos(u * Math.PI) * 0.06;
    const r = radiusBase + radiusNoise;

    const theta = Math.acos(2 * t - 1);
    const phi = u * Math.PI * 2;

    const x = r * Math.sin(theta) * Math.cos(phi);
    const y = r * Math.sin(theta) * Math.sin(phi);
    const z = r * Math.cos(theta);

    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;

    originalPositions[i * 3] = x;
    originalPositions[i * 3 + 1] = y;
    originalPositions[i * 3 + 2] = z;

    seeds[i] = Math.random();
    energies[i] = 0;
  }

  return { positions, originalPositions, seeds, energies };
}

/* ==================== OUTER PLANET NETWORK ==================== */
function OuterPlanetNetwork({ audioLevel }) {
  const pointsRef = useRef();
  const linesRef = useRef();
  const count = 500;

  const neuralData = useMemo(() => generateNeuralNodes(count, 3.5), [count]);
  const lineGeometryRef = useRef(null);
  const linePositionsRef = useRef(new Float32Array(count * 200 * 3));

  useEffect(() => {
    if (!lineGeometryRef.current) {
      lineGeometryRef.current = new THREE.BufferGeometry();
    }
    const posAttr = new THREE.BufferAttribute(linePositionsRef.current, 3);
    lineGeometryRef.current.setAttribute("position", posAttr);
  }, []);

  useFrame((state) => {
    if (!pointsRef.current) return;

    const t = state.clock.getElapsedTime();
    const particles = pointsRef.current.geometry.attributes.position.array;
    const { originalPositions, seeds, energies } = neuralData;

    for (let i = 0; i < count; i++) {
      const wave1 = Math.sin(t * 0.3 + seeds[i] * Math.PI * 2) * 0.12;
      const wave2 = Math.cos(t * 0.25 + seeds[i] * Math.PI) * 0.1;
      const wave3 = Math.sin(t * 0.35 + seeds[i] * Math.PI * 1.5) * 0.11;

      energies[i] = Math.max(0, energies[i] * 0.92 + audioLevel * 0.08);
      const movementAmp = 0.25 + energies[i] * 0.4;

      particles[i * 3] = originalPositions[i * 3] + wave1 * movementAmp;
      particles[i * 3 + 1] = originalPositions[i * 3 + 1] + wave2 * movementAmp;
      particles[i * 3 + 2] = originalPositions[i * 3 + 2] + wave3 * movementAmp;
    }

    pointsRef.current.geometry.attributes.position.needsUpdate = true;

    if (lineGeometryRef.current) {
      const linePos = linePositionsRef.current;
      let lineIdx = 0;
      const CONNECTION_DISTANCE = 1.4;
      const maxLines = count * 12;

      for (let i = 0; i < count && lineIdx < maxLines; i++) {
        for (let j = i + 1; j < count && lineIdx < maxLines; j++) {
          const dx = particles[i * 3] - particles[j * 3];
          const dy = particles[i * 3 + 1] - particles[j * 3 + 1];
          const dz = particles[i * 3 + 2] - particles[j * 3 + 2];
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

          if (dist < CONNECTION_DISTANCE) {
            linePos[lineIdx * 3] = particles[i * 3];
            linePos[lineIdx * 3 + 1] = particles[i * 3 + 1];
            linePos[lineIdx * 3 + 2] = particles[i * 3 + 2];
            lineIdx++;

            linePos[lineIdx * 3] = particles[j * 3];
            linePos[lineIdx * 3 + 1] = particles[j * 3 + 1];
            linePos[lineIdx * 3 + 2] = particles[j * 3 + 2];
            lineIdx++;
          }
        }
      }

      lineGeometryRef.current.attributes.position.needsUpdate = true;
      lineGeometryRef.current.setDrawRange(0, lineIdx);
    }
  });

  const pointSize = 0.04 + audioLevel * 0.06;

  return (
    <>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={count}
            array={neuralData.positions}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={pointSize}
          sizeAttenuation
          depthWrite={true}
          color="#ffffff"
          transparent
          opacity={0.7}
          fog={false}
        />
      </points>

      {lineGeometryRef.current && (
        <lineSegments geometry={lineGeometryRef.current} ref={linesRef}>
          <lineBasicMaterial
            color="#ffffff"
            transparent
            opacity={0.15 + audioLevel * 0.3}
            blending={THREE.AdditiveBlending}
            linewidth={1}
            fog={false}
          />
        </lineSegments>
      )}
    </>
  );
}

/* ==================== DENSE INNER NEURAL NETWORK ==================== */
function InnerNeuralNetwork({ audioLevel }) {
  const pointsRef = useRef();
  const linesRef = useRef();
  const coreRef = useRef();
  const count = 800;

  const neuralData = useMemo(() => generateNeuralNodes(count, 1.2), [count]);
  const lineGeometryRef = useRef(null);
  const linePositionsRef = useRef(new Float32Array(count * 120 * 3));

  useEffect(() => {
    if (!lineGeometryRef.current) {
      lineGeometryRef.current = new THREE.BufferGeometry();
    }
    const posAttr = new THREE.BufferAttribute(linePositionsRef.current, 3);
    lineGeometryRef.current.setAttribute("position", posAttr);
  }, []);

  useFrame((state) => {
    if (!pointsRef.current) return;

    const t = state.clock.getElapsedTime();
    const particles = pointsRef.current.geometry.attributes.position.array;
    const { originalPositions, seeds, energies } = neuralData;

    // Pulso sincronizado para núcleo y nodos
    const basePulse = Math.sin(t * 0.6) * 0.08 + 1;
    const audioBoost = audioLevel * 0.12;
    const globalScale = basePulse + audioBoost;

    for (let i = 0; i < count; i++) {
      const wave1 = Math.sin(t * 0.4 + seeds[i] * Math.PI * 2) * 0.06;
      const wave2 = Math.cos(t * 0.3 + seeds[i] * Math.PI) * 0.05;
      const wave3 = Math.sin(t * 0.5 + seeds[i] * Math.PI * 1.5) * 0.06;

      energies[i] = Math.max(0, energies[i] * 0.92 + audioLevel * 0.1);
      const movementAmp = 0.12 + energies[i] * 0.2;

      // Aplicar escala global de respiración + ondas individuales
      particles[i * 3] = (originalPositions[i * 3] + wave1 * movementAmp) * globalScale;
      particles[i * 3 + 1] = (originalPositions[i * 3 + 1] + wave2 * movementAmp) * globalScale;
      particles[i * 3 + 2] = (originalPositions[i * 3 + 2] + wave3 * movementAmp) * globalScale;
    }

    pointsRef.current.geometry.attributes.position.needsUpdate = true;

    // Animar núcleo con respiración controlada
    if (coreRef.current) {
      coreRef.current.scale.setScalar(globalScale);

      const glowIntensity = 0.5 + audioLevel * 0.8;
      if (coreRef.current.material.emissiveIntensity !== undefined) {
        coreRef.current.material.emissiveIntensity = glowIntensity;
      }
    }

    if (lineGeometryRef.current) {
      const linePos = linePositionsRef.current;
      let lineIdx = 0;
      const CONNECTION_DISTANCE = 1.2;
      const maxLines = count * 25;

      for (let i = 0; i < count && lineIdx < maxLines; i++) {
        for (let j = i + 1; j < count && lineIdx < maxLines; j++) {
          const dx = particles[i * 3] - particles[j * 3];
          const dy = particles[i * 3 + 1] - particles[j * 3 + 1];
          const dz = particles[i * 3 + 2] - particles[j * 3 + 2];
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

          if (dist < CONNECTION_DISTANCE) {
            linePos[lineIdx * 3] = particles[i * 3];
            linePos[lineIdx * 3 + 1] = particles[i * 3 + 1];
            linePos[lineIdx * 3 + 2] = particles[i * 3 + 2];
            lineIdx++;

            linePos[lineIdx * 3] = particles[j * 3];
            linePos[lineIdx * 3 + 1] = particles[j * 3 + 1];
            linePos[lineIdx * 3 + 2] = particles[j * 3 + 2];
            lineIdx++;
          }
        }
      }

      lineGeometryRef.current.attributes.position.needsUpdate = true;
      lineGeometryRef.current.setDrawRange(0, lineIdx);
    }
  });

  const pointSize = 0.035 + audioLevel * 0.05;

  return (
    <>
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={count}
            array={neuralData.positions}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={pointSize}
          sizeAttenuation
          depthWrite={true}
          color="#00bfff"
          transparent
          opacity={0.95}
          fog={false}
        />
      </points>

      {lineGeometryRef.current && (
        <lineSegments geometry={lineGeometryRef.current} ref={linesRef}>
          <lineBasicMaterial
            color="#00bfff"
            transparent
            opacity={0.4 + audioLevel * 0.5}
            blending={THREE.AdditiveBlending}
            linewidth={1}
            fog={false}
          />
        </lineSegments>
      )}

      <mesh ref={coreRef}>
        <sphereGeometry args={[0.95, 128, 128]} />
        <meshStandardMaterial
          color="#00bfff"
          metalness={0.95}
          roughness={0.05}
          emissive="#00bfff"
          emissiveIntensity={0.6}
          transparent
          opacity={0.15}
        />
      </mesh>

      <pointLight intensity={0.8} color="#00bfff" distance={12} />
    </>
  );
}

/* ==================== 3D SCENE ==================== */
function Scene3D({ audioLevel }) {
  const groupRef = useRef();

  useFrame(() => {
    if (!groupRef.current) return;
    groupRef.current.rotation.x += 0.0002;
    groupRef.current.rotation.y += 0.0003;
  });

  return (
    <>
      <color attach="background" args={["#000000"]} />
      <ambientLight intensity={0.2} color="#ffffff" />
      <directionalLight position={[8, 6, 5]} intensity={0.4} color="#ffffff" />
      <pointLight position={[5, 5, 5]} intensity={0.8} color="#ffffff" distance={30} />
      <pointLight position={[-5, -5, -5]} intensity={0.5} color="#ffffff" distance={25} />

      <group ref={groupRef}>
        <OuterPlanetNetwork audioLevel={audioLevel} />
        <InnerNeuralNetwork audioLevel={audioLevel} />
      </group>
    </>
  );
}

/* ==================== MAIN COMPONENT ==================== */
const ReactiveSphere = forwardRef(function ReactiveSphere(props, ref) {
  const [listening, setListening] = useState(false);
  const audioLevel = useAudioLevel(listening);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key.toLowerCase() === "m") {
        setListening((v) => !v);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useImperativeHandle(ref, () => ({
    toggleMic: () => setListening((v) => !v),
    isListening: () => listening,
  }));

  return (
    <div className="rs3d-root">
      <Canvas
        camera={{ position: [0, 0, 8], fov: 60 }}
        gl={{ alpha: true, antialias: true, precision: "highp" }}
        dpr={Math.min(window.devicePixelRatio, 2)}
      >
        <Scene3D audioLevel={audioLevel} />
      </Canvas>

      {/* Botón micrófono */}
      <div className="rs3d-controls">
        <button
          aria-label={listening ? "Detener audio" : "Activar audio"}
          className={`rs3d-mic-btn ${listening ? "listening" : ""}`}
          onClick={() => setListening((v) => !v)}
          title="Presiona M para alternar"
        >
          {listening ? <CiMicrophoneOff size={22} /> : <CiMicrophoneOn size={22} />}
        </button>
      </div>
    </div>
  );
});

ReactiveSphere.displayName = "ReactiveSphere";

export default ReactiveSphere;
