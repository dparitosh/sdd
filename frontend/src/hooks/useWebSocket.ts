/**
 * React Hook for WebSocket Integration
 * Provides real-time updates for React components
 */

import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { websocketService, ConnectionStatus } from '../services/websocket';

/**
 * Hook to initialize and manage WebSocket connection
 * @param autoConnect - Automatically connect on mount (default: true)
 * @param url - Backend WebSocket URL (auto-detected if not provided)
 */
export function useWebSocket(autoConnect: boolean = true, url?: string) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ConnectionStatus>(websocketService.getStatus());

  useEffect(() => {
    if (!autoConnect) return;

    // Connect to WebSocket
    websocketService.connect(queryClient, url);

    // Listen for connection status changes
    const handleConnection = (data: any) => {
      setStatus(websocketService.getStatus());
    };

    websocketService.on('connection', handleConnection);
    websocketService.on('error', handleConnection);

    // Cleanup on unmount
    return () => {
      websocketService.off('connection', handleConnection);
      websocketService.off('error', handleConnection);
    };
  }, [autoConnect, url, queryClient]);

  return {
    connected: status.connected,
    lastUpdate: status.lastUpdate,
    error: status.error,
    subscribe: (room: string) => websocketService.subscribe(room),
    unsubscribe: (room: string) => websocketService.unsubscribe(room),
    emit: (event: string, data: any) => websocketService.emit(event, data)
  };
}

/**
 * Hook to listen for specific WebSocket events
 * @param event - Event name to listen for
 * @param callback - Callback function when event occurs
 */
export function useWebSocketEvent<T = any>(
  event: string,
  callback: (data: T) => void
) {
  useEffect(() => {
    websocketService.on(event, callback);

    return () => {
      websocketService.off(event, callback);
    };
  }, [event, callback]);
}

/**
 * Hook to listen for graph updates
 * @param callback - Callback function when graph is updated
 */
export function useGraphUpdates(callback?: (data: any) => void) {
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useWebSocketEvent('graph_update', (data) => {
    setLastUpdate(new Date());
    callback?.(data);
  });

  useWebSocketEvent('node_created', (data) => {
    setLastUpdate(new Date());
    callback?.(data);
  });

  useWebSocketEvent('node_updated', (data) => {
    setLastUpdate(new Date());
    callback?.(data);
  });

  useWebSocketEvent('node_deleted', (data) => {
    setLastUpdate(new Date());
    callback?.(data);
  });

  useWebSocketEvent('relationship_created', (data) => {
    setLastUpdate(new Date());
    callback?.(data);
  });

  useWebSocketEvent('relationship_deleted', (data) => {
    setLastUpdate(new Date());
    callback?.(data);
  });

  return { lastUpdate };
}

/**
 * Hook to listen for requirement updates
 * @param callback - Callback function when requirements are updated
 */
export function useRequirementUpdates(callback?: (data: any) => void) {
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useWebSocketEvent('requirement_updated', (data) => {
    setLastUpdate(new Date());
    callback?.(data);
  });

  return { lastUpdate };
}

/**
 * Hook to listen for part updates
 * @param callback - Callback function when parts are updated
 */
export function usePartUpdates(callback?: (data: any) => void) {
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useWebSocketEvent('part_updated', (data) => {
    setLastUpdate(new Date());
    callback?.(data);
  });

  return { lastUpdate };
}
