import React, { useEffect, useState } from 'react';
import { FaUserAstronaut } from 'react-icons/fa6';
import LogoutButton from '../../../../auth/components/LogoutButton/LogoutButton';
import useCurrentUser from '../../../../auth/components/context/useCurrentUser';
import './GeneralTab.css';

const GeneralTab = () => {
  const { user, loading } = useCurrentUser();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!loading) {
      setReady(true);
    }
  }, [loading]);

  if (!ready) return <p>Cargando datos del usuario...</p>;
  if (!user) return <p>⚠️ Debes iniciar sesión para ver esta sección.</p>;

  return (
    <div className="general-tab-container">
      <h3>Información general</h3>

      <div className="profile-section">
        {/* Información del usuario alineada a la izquierda */}
        <div className="user-info-left">
          <p><strong>Nombre:</strong> {user.name}</p>
          <p><strong>Email:</strong> {user.email}</p>
          <p><strong>Proveedor:</strong> {user.auth_provider}</p>
          <div className="logout-button-wrapper">
            <LogoutButton />
          </div>
        </div>

        {/* Avatar o ícono a la derecha */}
        <div className="avatar-right">
          {user.picture ? (
            <img src={user.picture} alt="Avatar" className="avatar" />
          ) : (
            <div className="fallback-icon">
              <FaUserAstronaut />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default GeneralTab;
