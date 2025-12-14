/**
 * WebSocket Service for Real-time Updates
 * Connects to Flask-SocketIO backend for live graph updates
 */

import { io, Socket } from 'socket.io-client';
import { QueryClient } from '@tanstack/react-query';
import logger from '../utils/logger';

interface GraphUpdate {
  type: 'node_created' | 'node_updated' | 'node_deleted' | 'relationship_created' | 'relationship_deleted';
  data: any;
  timestamp: string;
}

interface ConnectionStatus {
  connected: boolean;
  lastUpdate: Date | null;
  error: string | null;
}

class WebSocketService {
  private socket: Socket | null = null;
  private queryClient: QueryClient | null = null;
  private status: ConnectionStatus = {
    connected: false,
    lastUpdate: null,
    error: null
  };
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  /**
   * Initialize WebSocket connection
   * @param queryClient - React Query client for cache invalidation
   * @param url - Backend WebSocket URL (auto-detected if not provided)
   */
  connect(queryClient: QueryClient, url?: string) {
    if (this.socket?.connected) {
      logger.log('[WebSocket] Already connected');
      return;
    }

    this.queryClient = queryClient;

    // WebSocket through Codespaces doesn't work well - disable for now
    // In production, API calls will handle updates
    logger.warn('[WebSocket] Skipping connection - not supported in Codespaces environment');
    this.status.error = 'WebSocket disabled in Codespaces environment';
    return;

    // Auto-detect WebSocket URL based on environment
    const wsUrl = url || window.location.origin;

    logger.log('[WebSocket] Connecting to', wsUrl);
    this.socket = io(wsUrl, {
      path: '/socket.io',
      transports: ['polling', 'websocket'], // Try polling first, then websocket
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 3, // Reduced attempts to fail faster
    });

    // Connection event handlers
    this.socket.on('connect', () => {
      logger.log('[WebSocket] ✓ Connected to backend');
      this.status.connected = true;
      this.status.error = null;
      
      // Subscribe to default room for graph updates
      this.socket?.emit('subscribe', { room: 'default' });
      
      // Notify listeners
      this.notifyListeners('connection', { connected: true });
    });

    this.socket.on('disconnect', (reason) => {
      logger.log('[WebSocket] ✗ Disconnected:', reason);
      this.status.connected = false;
      this.notifyListeners('connection', { connected: false, reason });
    });

    this.socket.on('connect_error', (error) => {
      logger.warn('[WebSocket] Connection error (graceful degradation):', error.message);
      this.status.error = error.message;
      this.status.connected = false;
      // Don't notify listeners on every retry to reduce noise
    });

    this.socket.on('reconnect', (attemptNumber) => {
      logger.log('[WebSocket] ✓ Reconnected after', attemptNumber, 'attempts');
      this.status.connected = true;
      this.status.error = null;
    });

    // Graph update event handlers
    this.socket.on('graph_update', (data: GraphUpdate) => {
      logger.log('[WebSocket] Graph update received:', data.type);
      this.handleGraphUpdate(data);
    });

    this.socket.on('node_created', (data) => {
      logger.log('[WebSocket] Node created:', data);
      this.invalidateQueries(['nodes', 'graph', 'stats']);
      this.notifyListeners('node_created', data);
    });

    this.socket.on('node_updated', (data) => {
      logger.log('[WebSocket] Node updated:', data);
      this.invalidateQueries(['nodes', 'graph']);
      this.notifyListeners('node_updated', data);
    });

    this.socket.on('node_deleted', (data) => {
      logger.log('[WebSocket] Node deleted:', data);
      this.invalidateQueries(['nodes', 'graph', 'stats']);
      this.notifyListeners('node_deleted', data);
    });

    this.socket.on('relationship_created', (data) => {
      logger.log('[WebSocket] Relationship created:', data);
      this.invalidateQueries(['relationships', 'graph', 'traceability']);
      this.notifyListeners('relationship_created', data);
    });

    this.socket.on('relationship_deleted', (data) => {
      logger.log('[WebSocket] Relationship deleted:', data);
      this.invalidateQueries(['relationships', 'graph', 'traceability']);
      this.notifyListeners('relationship_deleted', data);
    });

    // Requirements-specific updates
    this.socket.on('requirement_updated', (data) => {
      logger.log('[WebSocket] Requirement updated:', data);
      this.invalidateQueries(['requirements', 'ap239-requirements', 'traceability']);
      this.notifyListeners('requirement_updated', data);
    });

    // Parts-specific updates
    this.socket.on('part_updated', (data) => {
      logger.log('[WebSocket] Part updated:', data);
      this.invalidateQueries(['parts', 'ap242-parts', 'traceability']);
      this.notifyListeners('part_updated', data);
    });
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.socket) {
      logger.log('[WebSocket] Disconnecting...');
      this.socket.disconnect();
      this.socket = null;
      this.status.connected = false;
    }
  }

  /**
   * Handle generic graph update
   */
  private handleGraphUpdate(update: GraphUpdate) {
    this.status.lastUpdate = new Date();
    
    // Invalidate relevant React Query caches
    switch (update.type) {
      case 'node_created':
      case 'node_updated':
      case 'node_deleted':
        this.invalidateQueries(['nodes', 'graph', 'stats']);
        break;
      case 'relationship_created':
      case 'relationship_deleted':
        this.invalidateQueries(['relationships', 'graph', 'traceability']);
        break;
    }

    // Notify registered listeners
    this.notifyListeners('graph_update', update);
  }

  /**
   * Invalidate React Query caches
   */
  private invalidateQueries(queryKeys: string[]) {
    if (!this.queryClient) {
      logger.warn('[WebSocket] QueryClient not initialized');
      return;
    }

    queryKeys.forEach(key => {
      this.queryClient!.invalidateQueries({ 
        queryKey: [key],
        refetchType: 'active' // Only refetch active queries
      });
    });
  }

  /**
   * Subscribe to specific room
   */
  subscribe(room: string) {
    if (!this.socket?.connected) {
      logger.warn('[WebSocket] Not connected, cannot subscribe to room:', room);
      return;
    }

    logger.log('[WebSocket] Subscribing to room:', room);
    this.socket.emit('subscribe', { room });
  }

  /**
   * Unsubscribe from room
   */
  unsubscribe(room: string) {
    if (!this.socket?.connected) {
      return;
    }

    logger.log('[WebSocket] Unsubscribing from room:', room);
    this.socket.emit('unsubscribe', { room });
  }

  /**
   * Register event listener
   */
  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  /**
   * Unregister event listener
   */
  off(event: string, callback: (data: any) => void) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(callback);
    }
  }

  /**
   * Notify all listeners for an event
   */
  private notifyListeners(event: string, data: any) {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(callback => callback(data));
    }
  }

  /**
   * Get connection status
   */
  getStatus(): ConnectionStatus {
    return { ...this.status };
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.status.connected && !!this.socket?.connected;
  }

  /**
   * Emit custom event to server
   */
  emit(event: string, data: any) {
    if (!this.socket?.connected) {
      logger.warn('[WebSocket] Not connected, cannot emit event:', event);
      return;
    }

    this.socket.emit(event, data);
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();

// Export types
export type { GraphUpdate, ConnectionStatus };
