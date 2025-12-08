import React, { useEffect, useState } from 'react';
import { FaUserAstronaut, FaGoogle,  FaCalendar } from 'react-icons/fa';
import { useUser, SignOutButton } from "@clerk/clerk-react";
import './GeneralTab.css';

const GeneralTab = () => {
  const { user, isLoaded } = useUser();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (isLoaded) {
      setReady(true);
      if (user) {
      }
    }
  }, [isLoaded, user]);


  if (!ready) return <p>Cargando datos del usuario...</p>;
  if (!user) return <p>⚠️ Debes iniciar sesión para ver esta sección.</p>;

  return (
    <div className="general-tab-container">
      <h3>General Information</h3>

      <div className="profile-section">
        {/* User information aligned to the left */}
        <div className="user-info-left">
          <p><strong>Name:</strong> {user.fullName}</p>
          <p><strong>Email:</strong> {user.primaryEmailAddress.emailAddress}</p>
          <p><strong>Provider:</strong> {user.externalAccounts?.[0]?.provider || "Clerk"}</p>
          <div className="logout-button-wrapper">
            <SignOutButton>
              <button className="logout-btn">
                Sign Out
              </button>
            </SignOutButton>
          </div>
        </div>

        {/* Avatar o ícono a la derecha */}
        <div className="avatar-right">
          {user.imageUrl ? (
            <img src={user.imageUrl} alt="Avatar" className="avatar" />
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
