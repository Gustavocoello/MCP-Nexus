// NUEVO AuthContext.jsx (reemplazo completo)
import React, { createContext, useContext, useMemo } from "react";
import { useUser, useAuth } from "@clerk/clerk-react";

const AuthContext = createContext({
  user: null,
  isAuthenticated: false,
  getToken: async () => null,
});

export const AuthProvider = ({ children }) => {
  const { user } = useUser();
  const { getToken, isSignedIn } = useAuth();

  const value = useMemo(() => ({
    user: user
      ? {
          id: user.id,
          email:
            user.primaryEmailAddress?.emailAddress ||
            user.emailAddresses?.[0]?.emailAddress,
          fullName: user.fullName,
          imageUrl: user.imageUrl,
        }
      : null,
    isAuthenticated: isSignedIn,
    getToken: async (opts) => await getToken(opts),
  }), [user, isSignedIn, getToken]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuthContext = () => useContext(AuthContext);

export { AuthContext };
