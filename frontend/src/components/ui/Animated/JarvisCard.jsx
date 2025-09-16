import { motion } from "framer-motion";
import LMStudioCard from "./utils/LMStudioCard";
import { useState } from "react";
import './JarvisCard.css';

export default function JarvisCard() {
  const [hovered, setHovered] = useState(false);

  return (
    <motion.div
      className="service-card jarvis-card relative flex items-center justify-start cursor-pointer"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Logo de Jarvis */}
      <motion.img
        src="/icons/jarvis00.png"
        alt="Jarvis Logo"
        className="jarvis-logo03"
        animate={hovered ? { x: -60, scale: 0.7 } : { x: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
      />

      {/* LMStudio flotando, solo al hacer hover */}
      {hovered && (
        <motion.div
          className="absolute right-5 top-1/2 -translate-y-1/2"
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 50 }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
        >
          <LMStudioCard />
        </motion.div>
      )}

      <hr className="service-divider" />
      <h3 className="service-name">Jarvis</h3>
    </motion.div>
  );
}
