import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet';
import L from 'leaflet';
import {
  Truck, Navigation, AlertTriangle, LogOut, CheckCircle2, UserCheck,
  RefreshCw, MapPin, Send, AlertCircle, Info, ShieldAlert
} from 'lucide-react';
import { fetchActiveIncident, reportDisruption } from '../services/api';

// Custom DivIcons for Leaflet Map
const createCustomIcon = (type, label = '') => {
  let iconColor = '#8b5cf6';
  let symbol = 'V';
  let animStyle = '';

  if (type === 'depot') {
    iconColor = '#3b82f6';
    symbol = 'H';
  } else if (type === 'customer') {
    iconColor = '#64748b';
    symbol = 'C';
  } else if (type === 'disruption') {
    iconColor = '#ef4444';
    symbol = '⚠';
    animStyle = 'animation: pulse-red 1.5s infinite;';
  } else if (type === 'vehicle') {
    iconColor = '#8b5cf6';
    symbol = 'V';
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
      ${animStyle}
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

const NODE_LOCATIONS = {
  "NODE_MIDTOWN_HUB": { name: "Midtown Central Hub", coords: [40.7549, -73.9840], type: "depot" },
  "NODE_QUEENS_DC": { name: "Queens Logistics DC", coords: [40.7420, -73.9350], type: "depot" },
  "NODE_MANHATTAN_BRIDGE": { name: "Manhattan Bridge Corridor", coords: [40.7090, -73.9900], type: "bridge" },
  "NODE_BROOKLYN_BRIDGE": { name: "Brooklyn Bridge Corridor", coords: [40.7061, -73.9969], type: "bridge" },
  "NODE_WILLIAMSBURG_BRIDGE": { name: "Williamsburg Bridge Corridor", coords: [40.7135, -73.9725], type: "bridge" },
  "NODE_FDR_DRIVE": { name: "FDR Drive Northbound", coords: [40.7300, -73.9740], type: "highway" },
  "NODE_LINCOLN_TUNNEL": { name: "Lincoln Tunnel Access", coords: [40.7580, -74.0010], type: "tunnel" },
  "NODE_QUEENS_TUNNEL": { name: "Queens Midtown Tunnel", coords: [40.7445, -73.9680], type: "tunnel" },
  "NODE_BROOKLYN_NAVY": { name: "Brooklyn Navy Yard", coords: [40.7010, -73.9740], type: "hub" },
  "NODE_HARLEM_GATEWAY": { name: "Harlem Gateway", coords: [40.8100, -73.9450], type: "junction" },
  "NODE_FINANCIAL": { name: "Financial District Hub", coords: [40.7075, -74.0090], type: "hub" },
  "NODE_JFK_CARGO": { name: "JFK Cargo Terminal", coords: [40.6413, -73.7781], type: "cargo" }
};

export default function TransportDashboard({ currentUser, onLogout }) {
  const [activeIncident, setActiveIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success'|'error', text: '' }

  // Disruption reporting form state
  const [disruptionType, setDisruptionType] = useState('severe_congestion');
  const [selectedNode, setSelectedNode] = useState('NODE_MANHATTAN_BRIDGE');
  const [locationName, setLocationName] = useState(NODE_LOCATIONS['NODE_MANHATTAN_BRIDGE'].name);
  const [severityLevel, setSeverityLevel] = useState(4.0);
  const [description, setDescription] = useState('');

  useEffect(() => {
    loadActiveIncident();
  }, []);

  const loadActiveIncident = async () => {
    setLoading(true);
    try {
      const data = await fetchActiveIncident();
      setActiveIncident(data);
    } catch (err) {
      console.error('Failed to load active incident:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNodeSelect = (nodeId) => {
    setSelectedNode(nodeId);
    if (NODE_LOCATIONS[nodeId]) {
      setLocationName(NODE_LOCATIONS[nodeId].name);
    }
  };

  const handleSubmitDisruption = async (e) => {
    e.preventDefault();
    setFeedback(null);

    const trimmedMsg = description.trim();
    if (!trimmedMsg) {
      setFeedback({
        type: 'error',
        text: 'Incident Message / Operator Notes cannot be empty. Please describe the incident before sharing.'
      });
      return;
    }

    setSubmitting(true);

    const payload = {
      disruption_id: `DISR_TRP_${Date.now().toString().slice(-6)}`,
      disruption_type: disruptionType,
      location_node_id: selectedNode,
      location_name: locationName || NODE_LOCATIONS[selectedNode]?.name || selectedNode,
      severity_level: parseFloat(severityLevel),
      wind_speed_mph: 15.0,
      precipitation_inches: disruptionType === 'blizzard' ? 2.5 : 0.0,
      visibility_miles: disruptionType === 'blizzard' ? 1.0 : 8.0,
      temperature_f: disruptionType === 'blizzard' ? 28.0 : 58.0,
      road_capacity_reduction_pct: parseFloat(severityLevel) * 18.0,
      average_speed_mph: Math.max(5.0, 45.0 - parseFloat(severityLevel) * 7.5),
      normal_speed_mph: 45.0,
      active_vehicle_incident: disruptionType === 'vehicle_breakdown',
      description: trimmedMsg
    };

    try {
      await reportDisruption(payload);
      setFeedback({
        type: 'success',
        text: `Incident reported successfully at ${locationName}. Published to Shared Incident Feed across portals.`
      });
      setDescription('');
      await loadActiveIncident();
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err.message || 'Failed to submit disruption report.'
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Derive alternative path geometries from active incident recovery plans
  const plans = activeIncident?.all_recovery_plans || {};
  const planA = plans.PLAN_A;
  const planB = plans.PLAN_B;

  const disruptionInput = activeIncident?.disruption_input;
  const disruptionNode = disruptionInput?.location_node_id || 'NODE_MANHATTAN_BRIDGE';
  const disruptionCoords = NODE_LOCATIONS[disruptionNode]?.coords || [40.7090, -73.9900];

  // Dynamic Route Coordinates calculated by Dijkstra from backend
  const pathACoords = planA?.route_coords && planA.optimization_status === 'FEASIBLE' ? planA.route_coords : [];
  const pathBCoords = planB?.route_coords && planB.optimization_status === 'FEASIBLE' ? planB.route_coords : [];

  // Blocked Disrupted Segment
  const blockedSegmentCoords = [
    NODE_LOCATIONS['NODE_MIDTOWN_HUB'].coords,
    disruptionCoords
  ];

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-darker)', color: 'var(--text-primary)' }}>
      {/* Header */}
      <header className="app-header">
        <div className="brand-title">
          <Truck size={24} color="#8b5cf6" />
          <div>
            <h1>TRANSPORT TEAM PORTAL</h1>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Fleet Operations & Alternative Route Dispatching
            </span>
          </div>
        </div>

        <div className="header-badges">
          <span className="badge badge-blue">
            <Truck size={12} /> TRANSPORT FLEET
          </span>
          {currentUser && (
            <span className="badge badge-green">
              <UserCheck size={12} /> {currentUser}
            </span>
          )}
          {onLogout && (
            <button
              className="btn-secondary"
              onClick={onLogout}
              style={{
                padding: '4px 10px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                background: 'rgba(239, 68, 68, 0.1)',
                borderColor: 'rgba(239, 68, 68, 0.3)',
                color: '#f87171'
              }}
            >
              <LogOut size={12} /> Sign Out
            </button>
          )}
        </div>
      </header>

      {/* Main Grid Layout */}
      <main style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto', display: 'grid', gridTemplateColumns: '400px 1fr', gap: '20px' }}>
        
        {/* Left Column: Shared Incident Feed & Reporting Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          {/* Shared Active Incident Feed Card */}
          <div className="panel-card" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div className="panel-title" style={{ border: 'none', padding: 0 }}>
                <ShieldAlert size={18} color="#ef4444" /> Shared Incident Feed
              </div>
              <button
                onClick={loadActiveIncident}
                disabled={loading}
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-secondary)',
                  borderRadius: '6px',
                  padding: '4px 8px',
                  fontSize: '0.72rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <RefreshCw size={12} className={loading ? 'spin' : ''} /> Refresh
              </button>
            </div>

            {loading ? (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Syncing active incidents...
              </div>
            ) : activeIncident && activeIncident.status === 'ACTIVE' && activeIncident.disruption_input ? (
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span className="badge badge-red" style={{ fontSize: '0.7rem' }}>
                    🚨 {activeIncident.disruption_input?.disruption_type?.toUpperCase().replace('_', ' ')}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                    Status: <strong style={{ color: '#10b981' }}>{activeIncident.status}</strong>
                  </span>
                </div>

                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f8fafc', marginBottom: '4px' }}>
                  {activeIncident.disruption_input?.location_name}
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Severity Level: <strong>{activeIncident.disruption_input?.severity_level}/5.0</strong> &bull; Reported by: <strong style={{ color: '#38bdf8' }}>{activeIncident.disruption_input?.reported_by || currentUser || 'Transport Team'}</strong>
                </div>

                {activeIncident.disruption_input?.description && (
                  <div style={{
                    background: 'rgba(30, 41, 59, 0.7)',
                    borderLeft: '3px solid #ef4444',
                    borderRadius: '4px',
                    padding: '8px 10px',
                    margin: '8px 0',
                    fontSize: '0.8rem',
                    color: '#e2e8f0',
                    lineHeight: '1.4'
                  }}>
                    <strong>Transport Message:</strong> "{activeIncident.disruption_input.description}"
                  </div>
                )}

                {activeIncident.llm_team_notification && (
                  <div style={{
                    background: 'rgba(59, 130, 246, 0.1)',
                    border: '1px solid rgba(59, 130, 246, 0.3)',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    fontSize: '0.75rem',
                    color: '#93c5fd',
                    marginBottom: '8px'
                  }}>
                    📢 <strong>Team Alert:</strong> {activeIncident.llm_team_notification}
                  </div>
                )}

                <div style={{ fontSize: '0.7rem', color: '#64748b', textAlign: 'right' }}>
                  Updated: {activeIncident.updated_at ? new Date(activeIncident.updated_at).toLocaleTimeString() : 'Just now'}
                </div>
              </div>
            ) : (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', border: '1px dashed var(--border-color)', borderRadius: '8px' }}>
                No incident has been reported by the Transport Team yet. Use the form below to report a new disruption.
              </div>
            )}
          </div>

          {/* Disruption Reporting Form Card */}
          <div className="panel-card" style={{ padding: '16px' }}>
            <div className="panel-title" style={{ marginBottom: '14px' }}>
              <AlertTriangle size={18} color="#f59e0b" /> Report Road Disruption
            </div>

            {feedback && (
              <div style={{
                padding: '10px 12px',
                borderRadius: '6px',
                fontSize: '0.78rem',
                marginBottom: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: feedback.type === 'success' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                border: feedback.type === 'success' ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(239, 68, 68, 0.4)',
                color: feedback.type === 'success' ? '#34d399' : '#f87171'
              }}>
                {feedback.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                <span>{feedback.text}</span>
              </div>
            )}

            <form onSubmit={handleSubmitDisruption} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#cbd5e1', marginBottom: '4px' }}>
                  INCIDENT TYPE
                </label>
                <select
                  value={disruptionType}
                  onChange={(e) => setDisruptionType(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    color: '#f8fafc',
                    fontSize: '0.82rem'
                  }}
                >
                  <option value="severe_congestion">Severe Traffic Congestion</option>
                  <option value="blizzard">Blizzard / Severe Weather</option>
                  <option value="bridge_closure">Bridge / Road Closure</option>
                  <option value="vehicle_breakdown">Vehicle Breakdown Incident</option>
                  <option value="flooding">Flash Flooding</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#cbd5e1', marginBottom: '4px' }}>
                  LOCATION NODE
                </label>
                <select
                  value={selectedNode}
                  onChange={(e) => handleNodeSelect(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    color: '#f8fafc',
                    fontSize: '0.82rem'
                  }}
                >
                  {Object.entries(NODE_LOCATIONS).map(([key, loc]) => (
                    <option key={key} value={key}>
                      {loc.name} ({key})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#cbd5e1', marginBottom: '4px' }}>
                  CORRIDOR NAME
                </label>
                <input
                  type="text"
                  value={locationName}
                  onChange={(e) => setLocationName(e.target.value)}
                  required
                  placeholder="e.g. Manhattan Bridge Corridor"
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    color: '#f8fafc',
                    fontSize: '0.82rem',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', fontWeight: 700, color: '#cbd5e1', marginBottom: '4px' }}>
                  <span>SEVERITY RATING</span>
                  <span style={{ color: '#ef4444' }}>{severityLevel} / 5.0</span>
                </div>
                <input
                  type="range"
                  min="1.0"
                  max="5.0"
                  step="0.1"
                  value={severityLevel}
                  onChange={(e) => setSeverityLevel(e.target.value)}
                  style={{ width: '100%', accentColor: '#ef4444', cursor: 'pointer' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#cbd5e1', marginBottom: '4px' }}>
                  WRITE INCIDENT REPORT / MESSAGE TO DELIVERY TEAM *
                </label>
                <textarea
                  rows="3"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  placeholder="Describe the road disruption, affected area, expected delay, and instructions for the delivery team..."
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    color: '#f8fafc',
                    fontSize: '0.82rem',
                    resize: 'vertical',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                style={{
                  padding: '10px',
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: submitting ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  marginTop: '4px',
                  opacity: submitting ? 0.7 : 1
                }}
              >
                {submitting ? 'Sharing Incident Report...' : (
                  <>
                    <Send size={16} /> SHARE INCIDENT REPORT
                  </>
                )}
              </button>
            </form>
          </div>

        </div>

        {/* Right Column: Interactive Leaflet Map & Alternative Routes Visualization */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          {/* Route Distance & Estimated Duration Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            
            {/* Path A Stats */}
            <div style={{
              background: 'rgba(16, 185, 129, 0.08)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: '8px',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#34d399', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Navigation size={14} /> PATH A (Shortest Distance)
              </div>
              {planA && planA.optimization_status !== 'NO_FEASIBLE_ROUTE' ? (
                <>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc' }}>
                    {planA.total_distance_km !== undefined ? `${planA.total_distance_km} km` : 'N/A'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Est. Duration: <strong style={{ color: '#34d399' }}>{planA.total_duration_minutes !== undefined ? `${planA.total_duration_minutes} mins` : 'N/A'}</strong> &bull; Cost: ${planA.total_cost_usd !== undefined ? planA.total_cost_usd.toFixed(2) : 'N/A'}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: '0.85rem', color: '#ef4444', fontWeight: 600, marginTop: '4px' }}>
                  No feasible alternative route found
                </div>
              )}
            </div>

            {/* Path B Stats */}
            <div style={{
              background: 'rgba(6, 182, 212, 0.08)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              borderRadius: '8px',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#22d3ee', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Navigation size={14} /> PATH B (Fastest Travel Time)
              </div>
              {planB && planB.optimization_status !== 'NO_FEASIBLE_ROUTE' ? (
                <>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc' }}>
                    {planB.total_distance_km !== undefined ? `${planB.total_distance_km} km` : 'N/A'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Est. Duration: <strong style={{ color: '#22d3ee' }}>{planB.total_duration_minutes !== undefined ? `${planB.total_duration_minutes} mins` : 'N/A'}</strong> &bull; Cost: ${planB.total_cost_usd !== undefined ? planB.total_cost_usd.toFixed(2) : 'N/A'}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: '0.85rem', color: '#ef4444', fontWeight: 600, marginTop: '4px' }}>
                  No feasible alternative route found
                </div>
              )}
            </div>

          </div>

          {/* Leaflet Interactive Map Container */}
          <div className="panel-card" style={{ padding: 0, overflow: 'hidden', height: '540px', display: 'flex', flexDirection: 'column' }}>
            {/* Map Header & Matching Legend */}
            <div style={{
              padding: '10px 16px',
              background: 'var(--bg-dark)',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div className="panel-title" style={{ border: 'none', padding: 0, fontSize: '0.85rem' }}>
                <MapPin size={16} color="#8b5cf6" /> NYC Transport Network & Rerouted Vectors
              </div>
              <div style={{ display: 'flex', gap: '12px', fontSize: '0.72rem', fontWeight: 600 }}>
                <span style={{ color: '#ef4444' }}>● Disrupted Corridor</span>
                <span style={{ color: '#10b981' }}>━ Path A (Shortest Distance)</span>
                <span style={{ color: '#06b6d4' }}>━ Path B (Fastest Travel Time)</span>
                <span style={{ color: '#3b82f6' }}>■ Depots</span>
              </div>
            </div>

            {/* Leaflet Map */}
            <div style={{ flex: 1, width: '100%', position: 'relative' }}>
              <MapContainer center={[40.7300, -73.9740]} zoom={12} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; OpenStreetMap contributors'
                />

                {/* Node Markers */}
                {Object.entries(NODE_LOCATIONS).map(([key, loc]) => {
                  const isDisrupted = key === disruptionNode;
                  return (
                    <Marker
                      key={key}
                      position={loc.coords}
                      icon={createCustomIcon(isDisrupted ? 'disruption' : (loc.type === 'depot' ? 'depot' : 'customer'))}
                    >
                      <Popup className="custom-leaflet-popup">
                        <strong style={{ color: isDisrupted ? '#ef4444' : '#f8fafc' }}>
                          {loc.name} ({key})
                        </strong><br />
                        Type: {loc.type.toUpperCase()}<br />
                        Status: {isDisrupted ? '🚨 DISRUPTED' : '✓ Normal'}
                      </Popup>
                    </Marker>
                  );
                })}

                {/* Disrupted Segment Line */}
                <Polyline positions={blockedSegmentCoords} color="#ef4444" weight={5} opacity={0.8} dashArray="8, 8">
                  <Popup className="custom-leaflet-popup">
                    <strong style={{ color: '#ef4444' }}>DISRUPTED ROAD SEGMENT</strong><br />
                    Corridor: {locationName}
                  </Popup>
                </Polyline>

                {/* Alternative Path A Polyline */}
                <Polyline positions={pathACoords} color="#10b981" weight={5} opacity={0.95}>
                  <Popup className="custom-leaflet-popup">
                    <strong style={{ color: '#10b981' }}>PATH A (Minimal Cost Reroute)</strong><br />
                    Distance: {planA?.total_distance_miles || 'Calculated'} mi<br />
                    Duration: {planA?.total_duration_minutes || 'Calculated'} mins
                  </Popup>
                </Polyline>

                {/* Alternative Path B Polyline */}
                <Polyline positions={pathBCoords} color="#06b6d4" weight={5} opacity={0.95} dashArray="4, 4">
                  <Popup className="custom-leaflet-popup">
                    <strong style={{ color: '#06b6d4' }}>PATH B (Speed Recovery Reroute)</strong><br />
                    Distance: {planB?.total_distance_miles || 'Calculated'} mi<br />
                    Duration: {planB?.total_duration_minutes || 'Calculated'} mins
                  </Popup>
                </Polyline>
              </MapContainer>
            </div>
          </div>

        </div>

      </main>
    </div>
  );
}
