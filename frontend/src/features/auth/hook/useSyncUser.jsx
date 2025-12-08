// frontend/src/features/auth/hook/useSyncUser.jsx
import { useEffect, useState } from 'react';
import { useAuthContext } from '@/features/auth/components/context/AuthContext'; // Ajustada ruta de importación
import { authLogger } from '@/components/controller/log/logger.jsx';
import { useUser } from '@clerk/clerk-react';

// variable de entorno
const API_BASE_URL = import.meta.env.VITE_URL

export const useSyncUser = () => {
    // Usamos useUser de Clerk para asegurar que el objeto user esté completamente cargado.
    const { isLoaded, isSignedIn } = useUser();
    const { getToken } = useAuthContext();
    
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

                    // 2. Realizar la llamada a la ruta protegida de sincronización
                    const response = await fetch(`${API_BASE_URL}/api/v1/user/sync`, {
                        method: 'GET',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json',
                        },
                    });

                    if (!response.ok) {
                        // Intentamos leer el error del cuerpo si es un JSON
                        const errorData = await response.json();
                        throw new Error(errorData.error || `Sincronización fallida: ${response.status}`);
                    }

                    authLogger.info("Perfil sincronizado exitosamente.");
                    setIsSynced(true);

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
        }

    }, [isLoaded, isSignedIn, getToken, isSynced]);

    return { isSynced, syncError, isLoadingSync };
};