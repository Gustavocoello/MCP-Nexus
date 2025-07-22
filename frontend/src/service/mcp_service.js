// src/service/mcp_service.js

const MCP_URL = "http://localhost:8000/mcp/";

async function callTool(tool, args = {}, userId) {
  if (!userId) {
    throw new Error("MCP: Se requiere userId en el contexto del usuario.");
  }

  const body = {
    jsonrpc: "2.0",
    id: Date.now(),
    method: "mcp.call_tool",
    params: {
      tool,
      arguments: {
        context: { user_id: userId },
        ...args,
      },
    },
  };

  const res = await fetch(MCP_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json, text/event-stream",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) throw new Error(`MCP HTTP error ${res.status}`);
  const json = await res.json();
  if (json.error) throw new Error(`MCP JSON error: ${json.error.message}`);
  return json.result;
}

export function createMcpService(userId) {
  return {
    getDailySummary: (calendarId = null) =>
      callTool("resumen_diario", calendarId ? { calendar_id: calendarId } : {}, userId),

    getWeeklySummary: (calendarId = null) =>
      callTool("resumen_semanal", calendarId ? { calendar_id: calendarId } : {}, userId),

    getFreeSlots: (date, calendarId = null, dur = 60) =>
      callTool("slots_libres", { date, duracion_minutos: dur, ...(calendarId && { calendar_id: calendarId }) }, userId),

    filterEventsByTitle: (keyword, calendarId = null) =>
      callTool("Filtro de eventos por titulo", { keyword, ...(calendarId && { calendar_id: calendarId }) }, userId),

    listUserCalendars: () =>
      callTool("Listar calendarios del usuario", {}, userId),

    createEvent: (summary, description, startTime, endTime, calendarId = "primary") =>
      callTool("crear_evento", { summary, description, start_time: startTime, end_time: endTime, calendar_id: calendarId }, userId),

    deleteEvent: (calendarId, eventId) =>
      callTool("eliminar_evento", { calendar_id: calendarId, event_id: eventId }, userId),

    updateEvent: (calendarId, eventId, updates = {}) =>
      callTool("actualizar_evento", { calendar_id: calendarId, event_id: eventId, ...updates }, userId),

    getEventsByRange: (calendarId, startDate, endDate) =>
      callTool("Eventos por rango", { calendar_id: calendarId, start_date: startDate, end_date: endDate }, userId),

    getEventsAllCalendars: (startDate, endDate) =>
      callTool("Eventos de todos los calendarios por rango", { start_date: startDate, end_date: endDate }, userId),

    createEventFromText: (texto, calendarId = "primary") =>
      callTool("Crear evento desde texto natural", { texto_usuario: texto, calendar_id: calendarId }, userId),
  };
}
