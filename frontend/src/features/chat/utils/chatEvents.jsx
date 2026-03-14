// src/services/chatEvents.js

class ChatEventEmitter {
  constructor() {
    this.events = {};
  }

  // Suscribirse a un evento (ej. 'chat-updated')
  on(event, callback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
    
    // Devolvemos una función para desuscribirse fácilmente (limpieza de useEffect)
    return () => {
      this.events[event] = this.events[event].filter(cb => cb !== callback);
    };
  }

  // Emitir un evento
  emit(event, data) {
    if (this.events[event]) {
      this.events[event].forEach(callback => callback(data));
    }
  }
}

// Exportamos una instancia única para el SDK
export const chatEvents = new ChatEventEmitter();