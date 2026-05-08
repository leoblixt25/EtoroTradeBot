import { useState, useEffect, useCallback, useRef } from 'react';
import { wsService } from '../services/websocket';

interface UseWebSocketReturn {
  connected: boolean;
  lastMessage: unknown | null;
  send: (message: unknown) => void;
}

export function useWebSocket(portfolioId: string | null): UseWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<unknown | null>(null);
  const lastMessageRef = useRef<unknown | null>(null);

  useEffect(() => {
    if (!portfolioId) return;

    wsService.connect(portfolioId);

    const unsubConnection = wsService.onMessage('_connection', (data: unknown) => {
      const msg = data as { status: string };
      setConnected(msg.status === 'connected');
    });

    const unsubAll = wsService.onMessage('*', (data: unknown) => {
      lastMessageRef.current = data;
      setLastMessage(data);
    });

    return () => {
      unsubConnection();
      unsubAll();
      wsService.disconnect();
    };
  }, [portfolioId]);

  const send = useCallback((message: unknown) => {
    wsService.send(message);
  }, []);

  return { connected, lastMessage, send };
}
