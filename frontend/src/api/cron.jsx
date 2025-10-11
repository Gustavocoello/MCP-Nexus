import { pingBackend } from '@/service/ping_backend';

const VITE_APP = import.meta.env.VITE_CRON_SECRET;

export async function cronJob(params) {
  return await pingBackend();
}

export default async function handler(req, res) {
  const auth = req.headers.authorization || req.headers.Authorization;

  if (auth !== `Bearer ${VITE_APP}`) {
    return res.status(401).end('Unauthorized');
  }

  try {
    const result = await pingBackend();
    res.status(200).json({ status: 'ok', data: result });
    console.log('Cron job executed successfully:', result);
  } catch (error) {
    console.error('Error en cron job:', error);
    res.status(500).json({ status: 'error', message: error.message });
  }
}
