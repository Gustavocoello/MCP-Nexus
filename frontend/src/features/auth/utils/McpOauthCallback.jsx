// mcp-scratch/frontend/src/features/auth/utils/McpOauthCallback.js
// OAuthCallback.js
import React, { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { onMcpAuthorization } from 'use-mcp';

export default function OAuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    onMcpAuthorization();

    const target = location.state?.returnTo ?? '/';
    navigate(target, { replace: true });
  }, [navigate, location.state?.returnTo]);

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Conectando con MCP…</h1>
      <p>Cerrando esta ventana automáticamente.</p>
    </div>
  );
}
