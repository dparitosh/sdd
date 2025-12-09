"""
WebSocket support for real-time graph updates
Allows clients to receive live notifications when data changes
"""

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
import json


class GraphUpdateNotifier:
    """
    Manages WebSocket connections and broadcasts graph updates
    """
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self._active_connections = {}  # {sid: {user_id, rooms, connected_at}}
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            sid = request.sid
            self._active_connections[sid] = {
                'user_id': None,
                'rooms': [],
                'connected_at': datetime.now(),
                'last_activity': datetime.now()
            }
            logger.info(f"Client connected: {sid}")
            emit('connection_status', {'status': 'connected', 'sid': sid})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            sid = request.sid
            if sid in self._active_connections:
                del self._active_connections[sid]
            logger.info(f"Client disconnected: {sid}")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Subscribe to specific graph updates"""
            sid = request.sid
            room = data.get('room', 'default')
            
            join_room(room)
            
            if sid in self._active_connections:
                self._active_connections[sid]['rooms'].append(room)
                self._active_connections[sid]['last_activity'] = datetime.now()
            
            logger.info(f"Client {sid} subscribed to {room}")
            emit('subscribed', {'room': room, 'status': 'success'})
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """Unsubscribe from graph updates"""
            sid = request.sid
            room = data.get('room', 'default')
            
            leave_room(room)
            
            if sid in self._active_connections:
                if room in self._active_connections[sid]['rooms']:
                    self._active_connections[sid]['rooms'].remove(room)
            
            logger.info(f"Client {sid} unsubscribed from {room}")
            emit('unsubscribed', {'room': room, 'status': 'success'})
    
    def notify_node_created(self, node_data: Dict[str, Any], room: str = 'default'):
        """
        Notify clients that a new node was created
        
        Args:
            node_data: Node details
            room: Room to broadcast to (default: 'default')
        """
        message = {
            'event': 'node_created',
            'timestamp': datetime.now().isoformat(),
            'data': node_data
        }
        
        self.socketio.emit('graph_update', message, room=room)
        logger.debug(f"Broadcasted node_created to {room}")
    
    def notify_node_updated(self, node_data: Dict[str, Any], room: str = 'default'):
        """Notify clients that a node was updated"""
        message = {
            'event': 'node_updated',
            'timestamp': datetime.now().isoformat(),
            'data': node_data
        }
        
        self.socketio.emit('graph_update', message, room=room)
        logger.debug(f"Broadcasted node_updated to {room}")
    
    def notify_node_deleted(self, node_id: str, room: str = 'default'):
        """Notify clients that a node was deleted"""
        message = {
            'event': 'node_deleted',
            'timestamp': datetime.now().isoformat(),
            'data': {'id': node_id}
        }
        
        self.socketio.emit('graph_update', message, room=room)
        logger.debug(f"Broadcasted node_deleted to {room}")
    
    def notify_relationship_created(self, rel_data: Dict[str, Any], room: str = 'default'):
        """Notify clients that a relationship was created"""
        message = {
            'event': 'relationship_created',
            'timestamp': datetime.now().isoformat(),
            'data': rel_data
        }
        
        self.socketio.emit('graph_update', message, room=room)
        logger.debug(f"Broadcasted relationship_created to {room}")
    
    def notify_batch_update(self, updates: List[Dict[str, Any]], room: str = 'default'):
        """Notify clients of multiple updates at once"""
        message = {
            'event': 'batch_update',
            'timestamp': datetime.now().isoformat(),
            'count': len(updates),
            'data': updates
        }
        
        self.socketio.emit('graph_update', message, room=room)
        logger.debug(f"Broadcasted batch_update ({len(updates)} items) to {room}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections"""
        return {
            'active_connections': len(self._active_connections),
            'total_rooms': len(set(
                room
                for conn in self._active_connections.values()
                for room in conn['rooms']
            )),
            'connections': [
                {
                    'sid': sid,
                    'rooms': conn['rooms'],
                    'connected_duration': (datetime.now() - conn['connected_at']).total_seconds(),
                    'last_activity': (datetime.now() - conn['last_activity']).total_seconds()
                }
                for sid, conn in self._active_connections.items()
            ]
        }


# Example integration with Flask app:
"""
from flask import Flask
from flask_socketio import SocketIO
from websocket_handler import GraphUpdateNotifier

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Create notifier
notifier = GraphUpdateNotifier(socketio)

# In your API routes, notify clients of changes:

@app.route('/api/v1/Class', methods=['POST'])
def create_class():
    # Create the class in Neo4j
    new_class = create_class_in_db(request.json)
    
    # Notify all subscribers
    notifier.notify_node_created({
        'id': new_class['id'],
        'type': 'Class',
        'name': new_class['name']
    })
    
    return {'status': 'created', 'id': new_class['id']}

@app.route('/api/v1/Class/<class_id>', methods=['PUT'])
def update_class(class_id):
    # Update the class
    updated_class = update_class_in_db(class_id, request.json)
    
    # Notify subscribers
    notifier.notify_node_updated({
        'id': class_id,
        'type': 'Class',
        'changes': request.json
    })
    
    return {'status': 'updated'}

# Get connection stats
@app.route('/api/ws/stats')
def websocket_stats():
    return notifier.get_connection_stats()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
"""

# Client-side JavaScript example:
"""
// Connect to WebSocket
const socket = io('http://localhost:5000');

// Handle connection
socket.on('connect', () => {
    console.log('Connected to server');
    
    // Subscribe to graph updates
    socket.emit('subscribe', { room: 'default' });
});

// Listen for graph updates
socket.on('graph_update', (data) => {
    console.log('Graph update:', data);
    
    switch(data.event) {
        case 'node_created':
            // Update UI to show new node
            addNodeToGraph(data.data);
            break;
        
        case 'node_updated':
            // Update existing node in UI
            updateNodeInGraph(data.data);
            break;
        
        case 'node_deleted':
            // Remove node from UI
            removeNodeFromGraph(data.data.id);
            break;
        
        case 'relationship_created':
            // Add relationship to graph
            addRelationshipToGraph(data.data);
            break;
    }
});

// Handle disconnection
socket.on('disconnect', () => {
    console.log('Disconnected from server');
});
"""
