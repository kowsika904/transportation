import React from 'react';
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet';
import L from 'leaflet';
import { MapPin, Navigation, Truck, AlertOctagon, Building2 } from 'lucide-react';

// Custom DivIcons for Leaflet
const createCustomIcon = (type, label = '') => {
  let iconColor = '#3b82f6';
  let symbol = 'H';
  let animClass = '';

  if (type === 'depot') {
    iconColor = '#3b82f6';
    symbol = 'H';
  } else if (type === 'customer') {
    iconColor = '#10b981';
    symbol = 'C';
  } else if (type === 'customer_breach') {
    iconColor = '#ef4444';
    symbol = '!';
  } else if (type === 'vehicle') {
    iconColor = '#8b5cf6';
    symbol = 'V';
  } else if (type === 'disruption') {
    iconColor = '#ef4444';
    symbol = '⚠';
    animClass = 'animation: pulse-red 1.5s infinite;';
  }

  const htmlStr = `
    <div style="
      background-color: ${iconColor};
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid white;
      box-shadow: 0 0 10px rgba(0,0,0,0.5);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 12px;
      ${animClass}
    ">
      ${symbol}
    </div>
  `;

  return L.divIcon({
    html: htmlStr,
    className: 'custom-map-icon',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

export default function LogisticsMap({ summary, currentAnalysis, selectedPlan }) {
  // NYC Manhattan/Brooklyn Default Center
  const defaultCenter = [40.7300, -73.9740];
  const defaultZoom = 12;

  // Nodes & Coordinates mapping
  const nodes = {
    "NODE_MIDTOWN_HUB": [40.7549, -73.9840],
    "NODE_QUEENS_DC": [40.7420, -73.9350],
    "NODE_FINANCIAL": [40.7075, -74.0090],
    "NODE_MANHATTAN_BRIDGE": [40.7090, -73.9900],
    "NODE_FDR_DRIVE": [40.7300, -73.9740],
    "NODE_QUEENS_TUNNEL": [40.7445, -73.9680],
    "NODE_BROOKLYN_NAVY": [40.7010, -73.9740],
    "NODE_HARLEM_GATEWAY": [40.8100, -73.9450],
    "NODE_LINCOLN_TUNNEL": [40.7580, -74.0010],
    "NODE_JFK_CARGO": [40.6413, -73.7781]
  };

  const disruptionInput = currentAnalysis?.disruption_input;
  const affectedDeliveries = currentAnalysis?.impact_analysis?.affected_deliveries || [];

  // Derive route polylines
  const baseRoutes = [
    {
      id: 'ROUTE_A',
      name: 'Route A (Midtown -> Wall St -> DUMBO)',
      path: [nodes['NODE_MIDTOWN_HUB'], nodes['NODE_FINANCIAL'], nodes['NODE_BROOKLYN_NAVY'], nodes['NODE_MIDTOWN_HUB']],
      color: '#f59e0b'
    },
    {
      id: 'ROUTE_B',
      name: 'Route B (FDR Drive -> Harlem)',
      path: [nodes['NODE_MIDTOWN_HUB'], nodes['NODE_FDR_DRIVE'], nodes['NODE_HARLEM_GATEWAY'], nodes['NODE_MIDTOWN_HUB']],
      color: '#ef4444'
    },
    {
      id: 'ROUTE_C',
      name: 'Route C (Queens -> Financial -> JFK)',
      path: [nodes['NODE_QUEENS_DC'], nodes['NODE_FINANCIAL'], nodes['NODE_JFK_CARGO'], nodes['NODE_QUEENS_DC']],
      color: '#3b82f6'
    }
  ];

  // Rerouted recovery path overlay if plan selected
  const recoveryPolylinePath = selectedPlan ? [
    nodes['NODE_MIDTOWN_HUB'], nodes['NODE_QUEENS_TUNNEL'], nodes['NODE_BROOKLYN_NAVY'], nodes['NODE_JFK_CARGO']
  ] : null;

  return (
    <div className="panel-card" style={{ padding: '0', overflow: 'hidden' }}>
      <div style={{ padding: '12px 16px', background: 'var(--bg-dark)', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="panel-title" style={{ border: 'none', padding: '0' }}>
          <Navigation size={16} color="var(--accent-cyan)" />
          NYC Logistics Network & Disruption Topology
        </div>
        <div style={{ display: 'flex', gap: '8px', fontSize: '0.7rem' }}>
          <span style={{ color: '#3b82f6' }}>● Depots</span>
          <span style={{ color: '#10b981' }}>● Customers</span>
          <span style={{ color: '#8b5cf6' }}>● Vehicles</span>
          <span style={{ color: '#ef4444' }}>● Disruption</span>
        </div>
      </div>

      <div className="map-container">
        <MapContainer center={defaultCenter} zoom={defaultZoom} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />

          {/* Depots */}
          <Marker position={nodes['NODE_MIDTOWN_HUB']} icon={createCustomIcon('depot')}>
            <Popup className="custom-leaflet-popup">
              <strong>Midtown Central Hub (DEPOT_01)</strong><br />
              Location: 40.7549, -73.9840<br />
              Capacity: 20 Vehicles
            </Popup>
          </Marker>

          <Marker position={nodes['NODE_QUEENS_DC']} icon={createCustomIcon('depot')}>
            <Popup className="custom-leaflet-popup">
              <strong>Queens Logistics DC (DEPOT_02)</strong><br />
              Location: 40.7420, -73.9350<br />
              Capacity: 30 Vehicles
            </Popup>
          </Marker>

          {/* Customer Nodes */}
          {Object.entries(nodes).map(([nId, coords]) => {
            if (nId.includes('MIDTOWN') || nId.includes('QUEENS_DC') || nId === disruptionInput?.location_node_id) return null;
            const affected = affectedDeliveries.find(d => d.customer_id.includes(nId.split('_')[1]));
            const isBreached = affected?.sla_violated;
            return (
              <Marker key={nId} position={coords} icon={createCustomIcon(isBreached ? 'customer_breach' : 'customer')}>
                <Popup className="custom-leaflet-popup">
                  <strong>Node: {nId}</strong><br />
                  SLA Status: {isBreached ? '⚠️ SLA VIOLATED' : '✓ Normal'}<br />
                  Coordinates: {coords[0]}, {coords[1]}
                </Popup>
              </Marker>
            );
          })}

          {/* Disruption Active Marker */}
          {disruptionInput && nodes[disruptionInput.location_node_id] && (
            <Marker position={nodes[disruptionInput.location_node_id]} icon={createCustomIcon('disruption')}>
              <Popup className="custom-leaflet-popup">
                <strong style={{ color: '#ef4444' }}>🚨 DISRUPTION ACTIVE</strong><br />
                {disruptionInput.location_name}<br />
                Severity: {disruptionInput.severity_level} / 5<br />
                Type: {disruptionInput.disruption_type}
              </Popup>
            </Marker>
          )}

          {/* Base Logistics Routes */}
          {baseRoutes.map(r => (
            <Polyline key={r.id} positions={r.path} color={r.color} weight={4} opacity={0.6} dashArray="6, 6">
              <Popup className="custom-leaflet-popup">
                <strong>{r.name}</strong>
              </Popup>
            </Polyline>
          ))}

          {/* Rerouted Recovery Plan Polyline */}
          {recoveryPolylinePath && (
            <Polyline positions={recoveryPolylinePath} color="#10b981" weight={6} opacity={0.9}>
              <Popup className="custom-leaflet-popup">
                <strong style={{ color: '#10b981' }}>OPTIMIZED RECOVERY ROUTE ({selectedPlan.plan_id})</strong><br />
                Plan: {selectedPlan.plan_name}<br />
                Distance: {selectedPlan.total_distance_miles} mi<br />
                Duration: {selectedPlan.total_duration_minutes} mins
              </Popup>
            </Polyline>
          )}
        </MapContainer>
      </div>
    </div>
  );
}
