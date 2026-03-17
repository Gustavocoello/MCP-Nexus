// frontend/src/features/auth/hook/useSyncUser.jsx
import { useEffect, useState } from 'react';
import { useAuthContext } from '@/features/auth/components/context/AuthContext'; // Ajustada ruta de importación
import { authLogger } from '@/components/controller/log/logger.jsx';
import { useUser } from '@clerk/clerk-react';
import { storageAdapter, USER_ID_KEY } from '@/features/chat/utils/storageAdapter';

// variable de entorno
const API_BASE_URL = import.meta.env.VITE_URL
const TOKEN_KEY = 'jarvis_token';

export const useSyncUser = () => {
    // Usamos useUser de Clerk para asegurar que el objeto user esté completamente cargado.
    const { isLoaded, isSignedIn } = useUser();
    const { getToken } = useAuthContext();
    const [dbUserId, setDbUserId] = useState(null);
    
    // Estado para controlar si el usuario ya fue sincronizado en esta sesión
    const [isSynced, setIsSynced] = useState(false);
    const [syncError, setSyncError] = useState(null);
    const [isLoadingSync, setIsLoadingSync] = useState(false);

    useEffect(() => {
        // Solo proceder si Clerk ha terminado de cargar, el usuario está logueado, y aún no hemos sincronizado
        if (isLoaded && isSignedIn && !isSynced) {
            const syncProfile = async () => {
                setIsLoadingSync(true);
                setSyncError(null);

                try {
                    authLogger.info("Iniciando sincronización de perfil con backend...");
                    
                    // 1. Obtener el JWT
                    const token = await getToken({ template: 'backend-api-jarvis' }); 

                    if (token) {
                        // GUARDAR EN LOCALSTORAGE: Para que esté disponible al recargar
                        storageAdapter.setItem(token, TOKEN_KEY);
                        authLogger.info("✅ Token guardado en LocalStorage.");
                    }

                    // 2. Realizar la llamada a la ruta protegida de sincronización
                    const response = await fetch(`${API_BASE_URL}/api/v1/user/sync`, {
                        method: 'GET',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json',
                        },
                    });

                    if (response.ok) {
                        const data = await response.json();
                        // Guardamos el UUID usando el adpatador
                        setDbUserId(data.user_id);
                        storageAdapter.setItem(data.user_id, USER_ID_KEY);
                        setIsSynced(true);
                        authLogger.info("Perfil sincronizado exitosamente. User ID en DB:", data.user_id);
                    } else {
                        const errorData = await response.json();
                        throw new Error(`Error ${response.status}: ${errorData.message || 'Error desconocido'}`);
                    }

                    authLogger.info("Perfil sincronizado exitosamente.");

                } catch (error) {
                    authLogger.error("Error de Sincronización:", error);
                    setSyncError(error.message);
                } finally {
                    setIsLoadingSync(false);
                }
            };

            syncProfile();
        } 
        
        // Si el usuario se desloguea, reseteamos el estado de sincronización.
        if (isLoaded && !isSignedIn) {
            setIsSynced(false);
            setDbUserId(null);
            storageAdapter.removeItem(TOKEN_KEY);
            storageAdapter.removeItem(USER_ID_KEY);
            storageAdapter.removeItem(); // Limpia activeChatId por defecto
            authLogger.info("Sesión cerrada: Datos eliminados del storage.");
        }

    }, [isLoaded, isSignedIn, getToken, isSynced]);

    return { isSynced, dbUserId, syncError, isLoadingSync };
};