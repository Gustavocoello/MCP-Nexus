/**
 * src/components/controller/log/logger.jsx
 * Sistema de logs con niveles y modo debug
 * @file logger.js
 */

// ===================================
// 1. CONFIGURACIÓN
// ===================================

const LOG_LEVELS = {
  NONE: -1,
  ERROR: 0,
  WARN: 1,
  INFO: 2,
  DEBUG: 3
};

const getDebugMode = () => {
  try {
    return import.meta.env.VITE_DEBUG === 'true';
  } catch (error) {
    return false; 
  }
};

const DEBUG_MODE = getDebugMode();

// Configura el nivel mínimo
const CURRENT_LEVEL = DEBUG_MODE ? LOG_LEVELS.DEBUG : LOG_LEVELS.NONE;
// ===================================
// 2. CLASE LOGGER
// ===================================

class Logger {
  constructor(prefix = '') {
    this.prefix = prefix;
  }

  /**
   * Método interno para formatear y mostrar logs
   */
  _log(level, color, emoji, ...args) {
    if (LOG_LEVELS[level] > CURRENT_LEVEL) {
      return; // No mostrar si el nivel es mayor al configurado
    }

    const timestamp = new Date().toLocaleTimeString('es-EC');
    const formattedPrefix = `[${timestamp}] ${this.prefix}`;

    // Mostrar en consola
    console.log(
      `%c${formattedPrefix}`,
      `color: ${color}; font-weight: bold`,
      emoji,
      ...args
    );

    // Si es ERROR, también usar console.error para stack trace
    if (level === 'ERROR') {
      console.error(...args);
    }
  }

  // ===================================
  // 3. MÉTODOS PÚBLICOS
  // ===================================

  error(...args) {
    this._log('ERROR', '#ef4444', '❌', ...args);
  }

  warn(...args) {
    this._log('WARN', '#f59e0b', '⚠️', ...args);
  }

  info(...args) {
    this._log('INFO', '#3b82f6', 'ℹ️', ...args);
  }

  debug(...args) {
    this._log('DEBUG', '#8b5cf6', '🔍', ...args);
  }

  /**
   * Log para operaciones exitosas
   */
  success(...args) {
    this._log('INFO', '#22c55e', '✅', ...args);
  }

  /**
   * Log de grupo (para operaciones relacionadas)
   */
  group(label, callback) {
    if (LOG_LEVELS.DEBUG <= CURRENT_LEVEL) {
      console.group(`${this.prefix} ${label}`);
      try {
        callback();
      } finally {
        console.groupEnd();
      }
    }
  }

  /**
   * Medir tiempo de ejecución
   */
  time(label) {
    if (DEBUG_MODE) {
      console.time(`${this.prefix} ${label}`);
    }
  }

  timeEnd(label) {
    if (DEBUG_MODE) {
      console.timeEnd(`${this.prefix} ${label}`);
    }
  }

  /**
   * Log de tabla (para arrays/objetos)
   */
  table(data) {
    if (LOG_LEVELS.DEBUG <= CURRENT_LEVEL) {
      console.log(`%c${this.prefix}`, 'color: #8b5cf6; font-weight: bold');
      console.table(data);
    }
  }
}

// ===================================
// 4. LOGGERS PREDEFINIDOS
// ===================================

export const apiLogger = new Logger('[API]');
export const streamLogger = new Logger('[STREAM]');
export const hookLogger = new Logger('[HOOK]');
export const dbLogger = new Logger('[DB]');
export const authLogger = new Logger('[AUTH]');
export const routerLogger = new Logger('[ROUTER]');
export const stateLogger = new Logger('[STATE]');
export const mcpLogger = new Logger('[MCP]');

// Logger general (por defecto)
export default Logger;

// ===================================
// 5. INICIALIZACIÓN (MEJORADA)
// ===================================

// Solo mostrar el mensaje UNA VEZ en toda la aplicación
if (DEBUG_MODE && !window.__JARVIS_LOGGER_INITIALIZED__) {
  // Marcamos que ya se inicializó un logger en el objeto global 'window'
  window.__JARVIS_LOGGER_INITIALIZED__ = true;

  console.log(
    '%c🚀 JARVIS SYSTEM READY',
    'background: #8b5cf6; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold; font-size: 14px'
  );
  
  // Detectar si venimos del SDK o del Frontend para el sub-mensaje
  const origin = import.meta.url.includes('jarvis-sdk') ? 'SDK' : 'Frontend';
  
  console.log(
    `%c[${origin}] Debug activo. Para desactivar: .env ("VITE_DEBUG", "false")`,
    'color: #8b5cf6; font-style: italic'
  );
}