// features/mcp/calendar/components/CalendarList.js

import React, { useEffect, useState } from 'react';
import { createMcpService } from '../service/mcp_service';

const CalendarsList = ({ userId }) => {
  const [calendars, setCalendars] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const svc = createMcpService(userId);
    svc.listUserCalendars()
      .then(list => setCalendars(list))
      .catch(err => setError(err.message));
  }, [userId]);

  if (error) return <div>Error: {error}</div>;
  if (calendars.length === 0) return <div>Cargando calendarios...</div>;

  return (
    <ul>
      {calendars.map(c => (
        <li key={c.id}>{c.nombre} ({c.id})</li>
      ))}
    </ul>
  );
};

export default CalendarsList;
