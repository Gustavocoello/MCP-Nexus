import { pingBackend } from '../service/ping_backend';

export default async function handler(req, res) {
  const result = await pingBackend();
  res.status(200).json(result);
}
