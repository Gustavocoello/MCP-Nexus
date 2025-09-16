import { motion } from "framer-motion";
import { LmStudio } from "@lobehub/icons";

export default function LMStudioFloating() {
  return (
    <motion.div
      className="flex items-center justify-center w-32 h-32 bg-white rounded-full shadow-lg"
      animate={{ y: [0, -10, 0] }} // sube y baja
      transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
    >
      <LmStudio size={60} className="text-green-500" />
    </motion.div>
  );
}
