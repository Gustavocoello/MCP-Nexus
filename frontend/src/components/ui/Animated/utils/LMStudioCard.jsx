import { motion } from "framer-motion";

export default function LMStudioCard() {
  return (
    <motion.div
      className="flex items-center justify-center w-[120px] h-[120px] rounded-xl bg-white/10 shadow-lg backdrop-blur-md"
      initial={{ opacity: 0, x: 50 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.6, ease: "easeInOut" }}
    >
      <motion.img
        src="/icons/lmstudio.svg"
        alt="LLM Studio Logo"
        className="w-16 h-16"
        animate={{ y: [0, -10, 0] }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      />
    </motion.div>
  );
}
