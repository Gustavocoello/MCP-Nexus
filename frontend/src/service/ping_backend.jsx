// api/ping-backend.js
import { apiLogger } from '@/components/controller/log/logger.jsx';

const VITE_APP = import.meta.env.VITE_URL;

export default async function handler(req, res) {
  try {
    const response = await fetch(`${VITE_APP}/v2/ping`);
    if (response.ok) {
      res.status(200).json({ status: "Ping OK" });
      apiLogger.info(`Ping enviado con exito a ${VITE_APP}/v2/ping`);

    } else {
      res.status(500).json({ status: "Ping failed", code: response.status });
    }
  } catch (err) {
    res.status(500).json({ status: "Error", error: err.message });
  }
}
