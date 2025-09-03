// ReactiveSphere.jsx
import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
  useImperativeHandle,
  forwardRef,
} from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { CiMicrophoneOff, CiMicrophoneOn } from "react-icons/ci";
import "./ReactiveSphere.css";

/* ------------------ useAudioLevel ------------------ */
function useAudioLevel(active) {
  const [level, setLevel] = useState(0);
  const rafRef = useRef(null);
  const analyserRef = useRef(null);
  const dataRef = useRef(null);
  const audioCtxRef = useRef(null);
  const srcRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioCtxRef.current = new (window.AudioContext ||
          window.webkitAudioContext)();
        analyserRef.current = audioCtxRef.current.createAnalyser();
        analyserRef.current.fftSize = 256;

        srcRef.current = audioCtxRef.current.createMediaStreamSource(stream);
        srcRef.current.connect(analyserRef.current);

        const bufferLen = analyserRef.current.frequencyBinCount;
        dataRef.current = new Uint8Array(bufferLen);

        const tick = () => {
          if (!mounted) return;
          analyserRef.current.getByteFrequencyData(dataRef.current);
          const avg =
            dataRef.current.reduce((a, b) => a + b, 0) / dataRef.current.length;
          const normalized = Math.min(1, avg / 180);
          setLevel((prev) => prev * 0.85 + normalized * 0.15);
          rafRef.current = requestAnimationFrame(tick);
        };
        tick();
      } catch (err) {
        console.warn("Audio no disponible:", err);
      }
    }

    if (active) start();

    return () => {
      mounted = false;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (audioCtxRef.current) audioCtxRef.current.close();
    };
  }, [active]);

  return level;
}

/* ------------------ HaloParticles ------------------ */
function HaloParticles({ count = 1500 }) {
  const points = useRef();
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const r = 2.4 + Math.random() * 0.2;
      const theta = Math.acos(2 * Math.random() - 1);
      const phi = Math.random() * Math.PI * 2;
      const x = r * Math.sin(theta) * Math.cos(phi);
      const y = r * Math.sin(theta) * Math.sin(phi);
      const z = r * Math.cos(theta);
      arr.set([x, y, z], i * 3);
    }
    return arr;
  }, [count]);

  useFrame((state, delta) => {
    if (!points.current) return;
    points.current.rotation.y += delta * 0.05;
    points.current.rotation.x += delta * 0.01;
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.01}
        sizeAttenuation
        depthWrite={false}
        color="#bfbfbf"
      />
    </points>
  );
}

/* ------------------ Núcleo (esfera gris) ------------------ */
function CoreSphere({ audioLevel }) {
  const ref = useRef();
  const originalPositions = useRef();

  useEffect(() => {
    if (ref.current) {
      originalPositions.current = ref.current.geometry.attributes.position.array.slice();
    }
  }, []);

  useFrame((state, delta) => {
    const t = state.clock.getElapsedTime();
    const geom = ref.current.geometry;
    const pos = geom.attributes.position.array;
    const orig = originalPositions.current;

    const breathe = 1 + Math.sin(t * 1.5) * 0.02;

    const pulseCycle = (t % 25) / 25;
    const pulse =
      pulseCycle < 0.1
        ? 1 + Math.sin((pulseCycle / 0.1) * Math.PI) * 0.25
        : 1;

    for (let i = 0; i < pos.length; i += 3) {
      const ox = orig[i];
      const oy = orig[i + 1];
      const oz = orig[i + 2];

      // Normalizamos el vector del vértice
      const r = Math.sqrt(ox * ox + oy * oy + oz * oz);
      const nx = ox / r;
      const ny = oy / r;
      const nz = oz / r;

      // Onda en función de dirección + tiempo
      const wave =
        Math.sin(nx * 6 + t * 3) * 0.05 +
        Math.sin(ny * 6 + t * 2) * 0.05 +
        Math.sin(nz * 6 + t * 4) * 0.05 +
        audioLevel * 0.25;

      const scale = breathe * pulse + wave;

      pos[i] = ox * scale;
      pos[i + 1] = oy * scale;
      pos[i + 2] = oz * scale;
    }

    geom.attributes.position.needsUpdate = true;
    //ref.current.rotation.y += delta * 0.15;
  });

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[1, 128, 128]} />
      <meshStandardMaterial
        color="#a6a6a6"
        metalness={0.9}
        roughness={0.25}
        emissive="#4d4d4d"
        emissiveIntensity={0.35}
      />
    </mesh>
  );
}


/* ------------------ Ondas radiales ------------------ */
function JarvisWaves({ level }) {
  const SEGMENTS = 140;
  const R_BASE = 1.2;
  const AMP = 1.0;
  const lineRef = useRef();
  const ringRef = useRef();

  const positions = useMemo(() => new Float32Array(SEGMENTS * 2 * 3), []);
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return g;
  }, [positions]);

  useFrame((state, delta) => {
    const t = state.clock.getElapsedTime();
    const pos = geometry.attributes.position.array;

    const smooth = THREE.MathUtils.lerp(0.0, level, 0.8);

    for (let i = 0; i < SEGMENTS; i++) {
      const a = (i / SEGMENTS) * Math.PI * 2;
      const wobble =
        (Math.sin(t * 2.0 + i * 0.15) +
          Math.sin(t * 1.2 + i * 0.37)) *
        0.25;
      const mag = R_BASE + Math.max(0, smooth * AMP + wobble * 0.08);

      const x0 = Math.cos(a) * (R_BASE * 0.7);
      const y0 = Math.sin(a) * (R_BASE * 0.7);
      const x1 = Math.cos(a) * mag;
      const y1 = Math.sin(a) * mag;

      const idx = i * 2 * 3;
      pos[idx + 0] = x0;
      pos[idx + 1] = y0;
      pos[idx + 2] = 0.0;

      pos[idx + 3] = x1;
      pos[idx + 4] = y1;
      pos[idx + 5] = 0.0;
    }

    geometry.attributes.position.needsUpdate = true;

    if (ringRef.current) {
      //ringRef.current.rotation.z += delta * 0.25;
      const breathe = 1 + Math.sin(t * 1.8) * 0.02;
      ringRef.current.scale.setScalar(breathe);
    }
  });

  return (
    <group ref={ringRef}>
      <lineSegments ref={lineRef} geometry={geometry}>
        <lineBasicMaterial
          color="#d9d9d9"
          transparent
          opacity={0.9}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>
    </group>
  );
}

function Satellites({ audioLevel, count = 6 }) {
  const group = useRef();
  const seeds = useMemo(() => new Array(count).fill(0).map((_, i) => i + Math.random() * 10), [count]);

  useFrame((state, delta) => {
    const t = state.clock.getElapsedTime();
    if (!group.current) return;
    group.current.children.forEach((m, i) => {
      const speed = 0.3 + i * 0.07;
      const r = 1.6 + (i % 3) * 0.2 + audioLevel * 0.3;
      const a = t * speed + seeds[i];
      m.position.set(Math.cos(a) * r, Math.sin(a * 0.9) * 0.2, Math.sin(a) * r);
      m.rotation.y += delta * 0.7;
      const s = 0.05 + (i % 3) * 0.02 + audioLevel * 0.08;
      m.scale.setScalar(s);
    });
  });

  return (
    <group ref={group}>
      {seeds.map((s, i) => (
        <mesh key={i}>
          <icosahedronGeometry args={[1, 0]} />
          <meshStandardMaterial color="#c2c2c2" metalness={0.9} roughness={0.3} emissive="#5e5e5e" emissiveIntensity={0.2} />
        </mesh>
      ))}
    </group>
  );
}
/* ------------------ Scene ------------------ */
function Scene({ listening, externalLevel = 0 }) {
  const micLevel = useAudioLevel(listening);
  const visualLevel = externalLevel > 0 ? externalLevel : micLevel;

  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[3, 5, 2]} intensity={1.2} color="#f0e4b0" />
      <pointLight position={[-3, -2, -3]} intensity={0.8} color="#ffe083" />

      <group>
        <CoreSphere audioLevel={visualLevel} />
        <JarvisWaves level={visualLevel} />
        <HaloParticles count={1600} />
        <Satellites count={6} audioLevel={visualLevel} />
      </group>

      <OrbitControls
        enablePan={false}
        enableZoom={false}
        autoRotate={false}
        //autoRotateSpeed={0.6}
      />
    </>
  );
}


/* ------------------ Componente exportado ------------------ */
const ReactiveSphere = forwardRef(function ReactiveSphere(_, ref) {
  const [listening, setListening] = useState(false);
  const [externalLevel, setExternalLevel] = useState(0);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key.toLowerCase() === "m") setListening((v) => !v);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useImperativeHandle(ref, () => ({
    setExternalLevel: (v) => {
      const clamped = Math.max(0, Math.min(1, Number(v) || 0));
      setExternalLevel(clamped);
    },
    pulse: (strength = 0.8, decayMs = 300) => {
      const s = Math.max(0, Math.min(1, strength));
      setExternalLevel(s);
      const t0 = performance.now();
      const tick = () => {
        const t = performance.now() - t0;
        const k = Math.max(0, 1 - t / decayMs);
        setExternalLevel(s * k);
        if (k > 0) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    },
    toggleMic: () => setListening((v) => !v),
  }));

  return (
    <div className="rs3d-root">
      <Canvas camera={{ position: [0, 0, 5], fov: 60 }} gl={{ alpha: true }}>
        <Scene listening={listening} externalLevel={externalLevel} />
      </Canvas>

      <div className="rs3d-controls">
        <button
          aria-label={listening ? "Detener audio" : "Activar audio"}
          className={`rs3d-mic-btn ${listening ? "listening" : ""}`}
          onClick={() => setListening((v) => !v)}
        >
          {listening ? <CiMicrophoneOff size={22} /> : <CiMicrophoneOn size={22} />}
        </button>
      </div>
    </div>
  );
});

export default ReactiveSphere;
