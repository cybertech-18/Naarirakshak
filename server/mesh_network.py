"""
Mesh Network Simulator
Simulates offline mesh networking for alert propagation
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
import uuid
import json


class MeshNetworkSimulator:
    """Simulates mesh network for offline alert propagation"""
    
    def __init__(self):
        """Initialize mesh network simulator"""
        self.nodes = {}  # {node_id: node_data}
        self.message_cache = {}  # {message_id: message_data}
        self.propagation_paths = {}  # {alert_id: [node_ids]}
        
    def add_node(self, node_id: str, node_type: str, latitude: float, 
                 longitude: float, properties: Dict[str, Any] = None):
        """
        Add a node to the mesh network
        
        Args:
            node_id: Unique node identifier
            node_type: Type (smart_pole, bus, phone, beacon)
            latitude, longitude: GPS coordinates
            properties: Additional properties
        """
        self.nodes[node_id] = {
            'node_id': node_id,
            'type': node_type,
            'latitude': latitude,
            'longitude': longitude,
            'is_active': True,
            'last_seen': datetime.utcnow(),
            'messages_relayed': 0,
            'connected_nodes': [],
            'properties': properties or {}
        }
        
        # Find nearby nodes and establish connections
        self._update_connections(node_id)
    
    def _update_connections(self, node_id: str):
        """Update connections for a node based on proximity"""
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        node['connected_nodes'] = []
        
        # Find nodes within range
        for other_id, other_node in self.nodes.items():
            if other_id == node_id or not other_node['is_active']:
                continue
            
            distance = self._calculate_distance(
                node['latitude'], node['longitude'],
                other_node['latitude'], other_node['longitude']
            )
            
            # Connection range based on node type
            max_range = self._get_node_range(node['type'])
            
            if distance <= max_range:
                node['connected_nodes'].append(other_id)
    
    def _get_node_range(self, node_type: str) -> float:
        """
        Get transmission range for node type (km)
        
        Args:
            node_type: Type of node
            
        Returns:
            Range in kilometers
        """
        ranges = {
            'smart_pole': 0.5,    # 500m BLE range
            'bus': 1.0,           # 1km with better antenna
            'phone': 0.1,         # 100m standard BLE
            'beacon': 0.2,        # 200m low-power beacon
            'lora': 5.0,          # 5km LoRaWAN
            'satellite': 1000.0   # Satellite coverage
        }
        return ranges.get(node_type, 0.1)
    
    def _calculate_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """Calculate distance between coordinates (km)"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def propagate_alert(self, alert_data: Dict[str, Any], 
                       source_node: str = None, ttl: int = 300,
                       max_hops: int = 10) -> Dict[str, Any]:
        """
        Propagate alert through mesh network
        
        Args:
            alert_data: Alert information to propagate
            source_node: Starting node ID (or use user location)
            ttl: Time-to-live in seconds
            max_hops: Maximum hops before stopping
            
        Returns:
            Propagation statistics
        """
        alert_id = alert_data.get('alert_id')
        message_id = str(uuid.uuid4())
        
        # Create message
        message = {
            'message_id': message_id,
            'alert_id': alert_id,
            'alert_data': alert_data,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(seconds=ttl),
            'priority': self._calculate_priority(alert_data),
            'hops': 0,
            'max_hops': max_hops,
            'path': []
        }
        
        # Store in cache
        self.message_cache[message_id] = message
        
        # Find starting node (nearest to alert location)
        if source_node is None:
            latitude = alert_data.get('latitude')
            longitude = alert_data.get('longitude')
            if latitude and longitude:
                source_node = self._find_nearest_node(latitude, longitude)
        
        if source_node is None or source_node not in self.nodes:
            return {
                'success': False,
                'reason': 'No starting node found',
                'nodes_reached': 0
            }
        
        # Start propagation using flood algorithm with optimization
        reached_nodes = self._flood_propagate(message, source_node, set())
        
        # Store propagation path
        self.propagation_paths[alert_id] = list(reached_nodes)
        
        return {
            'success': True,
            'message_id': message_id,
            'nodes_reached': len(reached_nodes),
            'path': list(reached_nodes),
            'hops': message['hops'],
            'estimated_latency_ms': self._estimate_latency(len(reached_nodes))
        }
    
    def _calculate_priority(self, alert_data: Dict[str, Any]) -> int:
        """
        Calculate message priority (1-5, 5 being highest)
        
        Args:
            alert_data: Alert information
            
        Returns:
            Priority level
        """
        threat_level = alert_data.get('threat_level', 'moderate')
        
        priority_map = {
            'critical': 5,
            'high': 4,
            'moderate': 3,
            'low': 2
        }
        
        priority = priority_map.get(threat_level, 3)
        
        # Increase priority for unacknowledged alerts
        if alert_data.get('status') == 'triggered':
            priority = min(priority + 1, 5)
        
        return priority
    
    def _find_nearest_node(self, latitude: float, longitude: float) -> str:
        """
        Find nearest active node to coordinates
        
        Args:
            latitude, longitude: GPS coordinates
            
        Returns:
            Node ID or None
        """
        nearest_node = None
        min_distance = float('inf')
        
        for node_id, node in self.nodes.items():
            if not node['is_active']:
                continue
            
            distance = self._calculate_distance(
                latitude, longitude,
                node['latitude'], node['longitude']
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest_node = node_id
        
        return nearest_node
    
    def _flood_propagate(self, message: Dict[str, Any], current_node: str, 
                        visited: set) -> set:
        """
        Propagate message using controlled flooding
        
        Args:
            message: Message to propagate
            current_node: Current node ID
            visited: Set of visited nodes
            
        Returns:
            Set of reached nodes
        """
        # Check if already visited
        if current_node in visited:
            return visited
        
        # Check hop limit
        if message['hops'] >= message['max_hops']:
            return visited
        
        # Check TTL
        if datetime.utcnow() > message['expires_at']:
            return visited
        
        # Mark as visited
        visited.add(current_node)
        message['path'].append(current_node)
        message['hops'] += 1
        
        # Update node stats
        if current_node in self.nodes:
            self.nodes[current_node]['messages_relayed'] += 1
            self.nodes[current_node]['last_seen'] = datetime.utcnow()
        
        # Get connected nodes
        node = self.nodes.get(current_node)
        if not node:
            return visited
        
        # Propagate to connected nodes
        for neighbor_id in node['connected_nodes']:
            if neighbor_id not in visited:
                # Check if neighbor should receive based on priority
                if self._should_relay(message, neighbor_id):
                    visited = self._flood_propagate(message, neighbor_id, visited)
        
        return visited
    
    def _should_relay(self, message: Dict[str, Any], node_id: str) -> bool:
        """
        Determine if node should relay message
        
        Args:
            message: Message data
            node_id: Target node ID
            
        Returns:
            True if should relay
        """
        node = self.nodes.get(node_id)
        if not node or not node['is_active']:
            return False
        
        # Always relay high-priority messages
        if message['priority'] >= 4:
            return True
        
        # Check node type - some nodes are always relay
        if node['type'] in ['smart_pole', 'bus', 'lora']:
            return True
        
        # For lower priority, relay with probability based on priority
        import random
        relay_probability = message['priority'] / 5.0
        return random.random() < relay_probability
    
    def _estimate_latency(self, num_nodes: int) -> int:
        """
        Estimate propagation latency
        
        Args:
            num_nodes: Number of nodes reached
            
        Returns:
            Estimated latency in milliseconds
        """
        # Simplified model: ~50ms per hop
        base_latency = 50
        hop_latency = num_nodes * base_latency
        
        # Add network jitter
        import random
        jitter = random.randint(0, 100)
        
        return hop_latency + jitter
    
    def get_coverage_area(self, latitude: float, longitude: float, 
                         radius_km: float = 1.0) -> List[str]:
        """
        Get nodes covering an area
        
        Args:
            latitude, longitude: Center coordinates
            radius_km: Coverage radius
            
        Returns:
            List of node IDs in area
        """
        nodes_in_area = []
        
        for node_id, node in self.nodes.items():
            if not node['is_active']:
                continue
            
            distance = self._calculate_distance(
                latitude, longitude,
                node['latitude'], node['longitude']
            )
            
            if distance <= radius_km:
                nodes_in_area.append(node_id)
        
        return nodes_in_area
    
    def simulate_node_failure(self, node_id: str):
        """Simulate node going offline"""
        if node_id in self.nodes:
            self.nodes[node_id]['is_active'] = False
            
            # Update connections for all nodes
            for nid in self.nodes:
                self._update_connections(nid)
    
    def simulate_node_recovery(self, node_id: str):
        """Simulate node coming back online"""
        if node_id in self.nodes:
            self.nodes[node_id]['is_active'] = True
            self.nodes[node_id]['last_seen'] = datetime.utcnow()
            
            # Update connections
            self._update_connections(node_id)
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        active_nodes = sum(1 for n in self.nodes.values() if n['is_active'])
        total_messages = sum(n['messages_relayed'] for n in self.nodes.values())
        
        return {
            'total_nodes': len(self.nodes),
            'active_nodes': active_nodes,
            'total_messages_relayed': total_messages,
            'cached_messages': len(self.message_cache),
            'network_density': active_nodes / max(len(self.nodes), 1)
        }
    
    def clear_expired_messages(self):
        """Remove expired messages from cache"""
        current_time = datetime.utcnow()
        expired = [
            msg_id for msg_id, msg in self.message_cache.items()
            if msg['expires_at'] < current_time
        ]
        
        for msg_id in expired:
            del self.message_cache[msg_id]
        
        return len(expired)
