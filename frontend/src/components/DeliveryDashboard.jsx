import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, Popup } from 'react-leaflet';
import L from 'leaflet';
import {
  Package, Clock, ShieldCheck, AlertCircle, LogOut, CheckCircle2,
  UserCheck, RefreshCw, MapPin, Search, Filter, AlertTriangle, ShieldAlert
} from 'lucide-react';
import { fetchAffectedDeliveries, acknowledgeDelivery } from '../services/api';

// Custom DivIcons for Leaflet Map
const createCustomIcon = (type, label = '') => {
  let iconColor = '#10b981';
  let symbol = 'C';
  let animStyle = '';

  if (type === 'depot') {
    iconColor = '#3b82f6';
    symbol = 'H';
  } else if (type === 'customer_normal') {
    iconColor = '#10b981';
    symbol = '✓';
  } else if (type === 'customer_breach') {
    iconColor = '#ef4444';
    symbol = '!';
    animStyle = 'animation: pulse-red 1.5s infinite;';
  } else if (type === 'disruption') {
    iconColor = '#ef4444';
    symbol = '⚠';
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
  "NODE_FDR_DRIVE": { name: "FDR Drive North Segment", coords: [40.7300, -73.9740], type: "highway" },
  "NODE_LINCOLN_TUNNEL": { name: "Lincoln Tunnel Access", coords: [40.7580, -74.0010], type: "tunnel" },
  "NODE_QUEENS_TUNNEL": { name: "Queens Midtown Tunnel", coords: [40.7445, -73.9680], type: "tunnel" },
  "NODE_FINANCIAL": { name: "Financial District Hub", coords: [40.7075, -74.0090], type: "customer" },
  "NODE_BROOKLYN_NAVY": { name: "Brooklyn Navy Yard", coords: [40.7010, -73.9740], type: "customer" },
  "NODE_HARLEM_GATEWAY": { name: "Harlem Medical Center", coords: [40.8100, -73.9450], type: "customer" },
  "NODE_JFK_CARGO": { name: "JFK Cold Storage DC", coords: [40.6413, -73.7781], type: "customer" }
};

export default function DeliveryDashboard({ currentUser, onLogout }) {
  const [portalData, setPortalData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTierFilter, setSelectedTierFilter] = useState('ALL');
  const [acknowledgedMap, setAcknowledgedMap] = useState({});

  useEffect(() => {
    loadDeliveryData();
    const interval = setInterval(() => {
      loadDeliveryData(false);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const loadDeliveryData = async (showLoadingSpinner = true) => {
    if (showLoadingSpinner) setLoading(true);
    try {
      const data = await fetchAffectedDeliveries();
      setPortalData(data);
      if (data.acknowledged_deliveries) {
        const ackObj = {};
        data.acknowledged_deliveries.forEach(item => {
          ackObj[item.delivery_id] = true;
        });
        setAcknowledgedMap(ackObj);
      }
    } catch (err) {
      console.error('Failed to load affected deliveries:', err);
    } finally {
      if (showLoadingSpinner) setLoading(false);
    }
  };

  const handleAcknowledge = async (deliveryId) => {
    try {
      await acknowledgeDelivery(deliveryId, currentUser || 'delivery_team');
      setAcknowledgedMap((prev) => ({ ...prev, [deliveryId]: true }));
    } catch (err) {
      console.error('Failed to acknowledge delivery:', err);
    }
  };

  const affectedDeliveries = portalData?.affected_deliveries || [];
  const priorityRankings = portalData?.priority_rankings || [];

  // Filter deliveries based on search & tier filter
  const filteredDeliveries = affectedDeliveries.filter((item) => {
    const matchesSearch =
      item.delivery_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.customer_name.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (selectedTierFilter === 'ALL') return matchesSearch;
    
    const rankInfo = priorityRankings.find(r => r.delivery_id === item.delivery_id);
    return matchesSearch && rankInfo?.priority_tier === selectedTierFilter;
  });

  const getPriorityBadgeClass = (tier) => {
    switch (tier) {
      case 'CRITICAL': return 'badge-red';
      case 'HIGH': return 'badge-orange';
      case 'MEDIUM': return 'badge-blue';
      default: return 'badge-gray';
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-darker)', color: 'var(--text-primary)' }}>
      {/* Header */}
      <header className="app-header">
        <div className="brand-title">
          <Package size={24} color="#3b82f6" />
          <div>
            <h1>DELIVERY MANAGEMENT PORTAL</h1>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Order Tracking, Customer Priority Rankings & SLA Monitoring
            </span>
          </div>
        </div>

        <div className="header-badges">
          <span className="badge badge-blue">
            <Package size={12} /> DELIVERY MANAGEMENT
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

      {/* Main Grid */}
      <main style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Top Summary Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px' }}>
          <div className="panel-card" style={{ padding: '16px' }}>
            <div className="panel-title" style={{ border: 'none', padding: 0, marginBottom: '6px' }}>
              <Package size={18} color="#3b82f6" /> Active Deliveries
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#3b82f6' }}>48</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>12 high-priority medical & perishable loads</div>
          </div>

          <div className="panel-card" style={{ padding: '16px' }}>
            <div className="panel-title" style={{ border: 'none', padding: 0, marginBottom: '6px' }}>
              <AlertTriangle size={18} color="#f59e0b" /> Affected Orders
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#f59e0b' }}>
              {portalData?.affected_deliveries_count || 0}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Delay: +{portalData?.total_expected_delay_minutes?.toFixed(1) || 0} mins across routes
            </div>
          </div>

          <div className="panel-card" style={{ padding: '16px' }}>
            <div className="panel-title" style={{ border: 'none', padding: 0, marginBottom: '6px' }}>
              <AlertCircle size={18} color="#ef4444" /> SLA At-Risk Windows
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#ef4444' }}>
              {portalData?.at_risk_sla_count || 0}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Endangered target delivery windows</div>
          </div>

          <div className="panel-card" style={{ padding: '16px' }}>
            <div className="panel-title" style={{ border: 'none', padding: 0, marginBottom: '6px' }}>
              <Clock size={18} color="#10b981" /> SLA Compliance Rate
            </div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#10b981' }}>94.2%</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>On-time delivery performance rate</div>
          </div>
        </div>

        {/* Shared Incident Feed Alert Banner or Neutral Empty State */}
        {portalData?.status === 'NO_ACTIVE_INCIDENT' || !portalData || portalData.disruption_id === 'NONE' ? (
          <div style={{
            background: 'rgba(30, 41, 59, 0.4)',
            border: '1px dashed rgba(148, 163, 184, 0.3)',
            borderRadius: '8px',
            padding: '14px 18px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <ShieldAlert size={22} color="#64748b" />
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#e2e8f0' }}>
                  No incident has been reported by the Transport Team.
                </div>
                <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
                  All delivery operations and fleet routes are running on normal baseline schedules.
                </div>
              </div>
            </div>
            <button
              onClick={() => loadDeliveryData(true)}
              disabled={loading}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-color)',
                color: '#94a3b8',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <RefreshCw size={13} className={loading ? 'spin' : ''} /> Refresh Sync
            </button>
          </div>
        ) : (
          <div style={{
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            borderRadius: '8px',
            padding: '16px 20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: '16px'
          }}>
            <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start', flex: 1 }}>
              <ShieldAlert size={24} color="#ef4444" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.88rem', fontWeight: 800, color: '#f8fafc' }}>
                    SHARED INCIDENT FEED — MESSAGE FROM TRANSPORT TEAM &bull; {portalData.location_name}
                  </span>
                  <span className="badge badge-red" style={{ fontSize: '0.7rem' }}>
                    🚨 {portalData.disruption_type?.toUpperCase().replace('_', ' ')}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: '#f59e0b' }}>
                    Severity: <strong>{portalData.severity_level}/5.0</strong>
                  </span>
                  <span style={{ fontSize: '0.72rem', color: '#38bdf8' }}>
                    Reported by: <strong>{portalData.reported_by || 'Transport Team'}</strong>
                  </span>
                </div>

                {portalData.description && (
                  <div style={{
                    background: 'rgba(15, 23, 42, 0.7)',
                    borderLeft: '3px solid #ef4444',
                    borderRadius: '4px',
                    padding: '8px 12px',
                    margin: '6px 0 8px 0',
                    fontSize: '0.82rem',
                    color: '#f1f5f9',
                    lineHeight: '1.4'
                  }}>
                    <strong>Transport Message:</strong> "{portalData.description}"
                  </div>
                )}

                {portalData.llm_team_notification && (
                  <div style={{ fontSize: '0.78rem', color: '#cbd5e1', marginTop: '4px' }}>
                    📢 <strong>Delivery Guidance:</strong> {portalData.llm_team_notification}
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={() => loadDeliveryData(true)}
              disabled={loading}
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#f8fafc',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                flexShrink: 0
              }}
            >
              <RefreshCw size={13} className={loading ? 'spin' : ''} /> Refresh Sync
            </button>
          </div>
        )}

        {/* Middle Section: Deliveries Table + Interactive Map Split */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 500px', gap: '20px' }}>

          {/* Delivery Orders & Customer SLA Table */}
          <div className="panel-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            
            {/* Table Search & Priority Filter Controls */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ position: 'relative', width: '240px' }}>
                <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
                <input
                  type="text"
                  placeholder="Search Order ID or Customer..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px 10px 6px 30px',
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    color: '#f8fafc',
                    fontSize: '0.78rem',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Filter size={12} /> Tier:
                </span>
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((tier) => (
                  <button
                    key={tier}
                    onClick={() => setSelectedTierFilter(tier)}
                    style={{
                      padding: '4px 8px',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      borderRadius: '4px',
                      cursor: 'pointer',
                      background: selectedTierFilter === tier ? 'var(--accent-blue)' : 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-color)',
                      color: selectedTierFilter === tier ? '#ffffff' : '#94a3b8'
                    }}
                  >
                    {tier}
                  </button>
                ))}
              </div>
            </div>

            {/* Table */}
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table" style={{ width: '100%', fontSize: '0.78rem' }}>
                <thead>
                  <tr>
                    <th>ORDER ID</th>
                    <th>CUSTOMER</th>
                    <th>PRIORITY TIER</th>
                    <th>ORIGINAL ETA</th>
                    <th>PROJECTED ETA</th>
                    <th>DELAY</th>
                    <th>SLA WINDOW</th>
                    <th>STATUS</th>
                    <th>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDeliveries.length > 0 ? (
                    filteredDeliveries.map((item) => {
                      const rank = priorityRankings.find(r => r.delivery_id === item.delivery_id);
                      const tier = rank?.priority_tier || 'MEDIUM';
                      const isAck = acknowledgedMap[item.delivery_id];

                      return (
                        <tr key={item.delivery_id} style={{ background: item.sla_violated ? 'rgba(239, 68, 68, 0.05)' : 'transparent' }}>
                          <td style={{ fontWeight: 700, color: '#f8fafc' }}>{item.delivery_id}</td>
                          <td>
                            <div style={{ fontWeight: 600, color: '#f8fafc' }}>{item.customer_name}</div>
                            {item.is_perishable && (
                              <span style={{ fontSize: '0.65rem', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '1px 5px', borderRadius: '3px' }}>
                                ❄️ Cold Chain / Medical
                              </span>
                            )}
                          </td>
                          <td>
                            <span className={`badge ${getPriorityBadgeClass(tier)}`} style={{ fontSize: '0.68rem' }}>
                              {tier} ({rank ? rank.priority_score.toFixed(0) : '50'})
                            </span>
                          </td>
                          <td style={{ color: '#94a3b8' }}>{item.original_eta}</td>
                          <td style={{ fontWeight: 700, color: item.sla_violated ? '#f87171' : '#34d399' }}>
                            {item.projected_eta}
                          </td>
                          <td style={{ color: item.delay_minutes > 0 ? '#f59e0b' : '#94a3b8' }}>
                            +{item.delay_minutes.toFixed(0)}m
                          </td>
                          <td style={{ color: '#94a3b8' }}>{item.sla_window_end}</td>
                          <td>
                            {item.sla_violated ? (
                              <span className="badge badge-red" style={{ fontSize: '0.68rem' }}>
                                ⚠️ SLA BREACH
                              </span>
                            ) : (
                              <span className="badge badge-green" style={{ fontSize: '0.68rem' }}>
                                ✓ ON TIME
                              </span>
                            )}
                          </td>
                          <td>
                            {isAck ? (
                              <span style={{ fontSize: '0.7rem', color: '#34d399', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <CheckCircle2 size={12} /> ACK
                              </span>
                            ) : (
                              <button
                                onClick={() => handleAcknowledge(item.delivery_id)}
                                style={{
                                  padding: '3px 8px',
                                  fontSize: '0.7rem',
                                  background: 'rgba(59, 130, 246, 0.15)',
                                  border: '1px solid rgba(59, 130, 246, 0.4)',
                                  color: '#60a5fa',
                                  borderRadius: '4px',
                                  cursor: 'pointer'
                                }}
                              >
                                Acknowledge
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="9" style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>
                        No affected deliveries found matching filter criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

          </div>

          {/* Interactive Leaflet Map showing Customer Delivery Locations & Route Optimization */}
          <div className="panel-card" style={{ padding: 0, overflow: 'hidden', height: '540px', display: 'flex', flexDirection: 'column' }}>
            <div style={{
              padding: '10px 14px',
              background: 'var(--bg-dark)',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div className="panel-title" style={{ border: 'none', padding: 0, fontSize: '0.85rem' }}>
                <MapPin size={16} color="#3b82f6" /> Delivery Destinations & Reroute Visualization Map
              </div>
              <div style={{ display: 'flex', gap: '10px', fontSize: '0.7rem', fontWeight: 600 }}>
                <span style={{ color: '#ef4444' }}>● Disrupted Road</span>
                <span style={{ color: '#ef4444' }}>● Disrupted Corridor</span>
                <span style={{ color: '#10b981' }}>━ Path A (Shortest Distance)</span>
                <span style={{ color: '#06b6d4' }}>╍ Path B (Fastest Travel Time)</span>
                <span style={{ color: '#3b82f6' }}>■ Depot</span>
              </div>
            </div>

            {/* Route Optimization Summary Overlay */}
            {portalData?.status === 'ACTIVE' && (
              <div style={{
                background: portalData.optimization_status === 'NO_FEASIBLE_ROUTE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(15, 23, 42, 0.85)',
                borderBottom: '1px solid var(--border-color)',
                padding: '8px 14px',
                fontSize: '0.78rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                {portalData.optimization_status === 'NO_FEASIBLE_ROUTE' ? (
                  <div style={{ color: '#f87171', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertTriangle size={14} /> NO FEASIBLE ALTERNATIVE ROUTE AVAILABLE: All network paths are blocked or exceed capacity constraints.
                  </div>
                ) : portalData.optimized_route ? (
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'center', color: '#f8fafc', width: '100%', justifyContent: 'space-between' }}>
                    <div>
                      <span className="badge badge-green" style={{ fontSize: '0.7rem', marginRight: '8px' }}>
                        ✓ {portalData.optimized_route.plan_name || 'Fastest Feasible Route'}
                      </span>
                      <span style={{ color: '#94a3b8' }}>{portalData.optimized_route.strategy_summary}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', fontWeight: 700 }}>
                      <span>Path A (Distance): <strong style={{ color: '#10b981' }}>{portalData.path_a?.total_distance_km ? `${portalData.path_a.total_distance_km} km` : 'N/A'}</strong></span>
                      <span>Path B (Duration): <strong style={{ color: '#06b6d4' }}>{portalData.path_b?.total_duration_minutes ? `${portalData.path_b.total_duration_minutes} mins` : 'N/A'}</strong></span>
                      <span>Affected Orders: <strong style={{ color: '#f59e0b' }}>{portalData.affected_deliveries_count}</strong></span>
                    </div>
                  </div>
                ) : null}
              </div>
            )}

            <div style={{ flex: 1, width: '100%', position: 'relative' }}>
              <MapContainer center={[40.7300, -73.9740]} zoom={12} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; OpenStreetMap contributors'
                />

                {/* Node Locations & Customer Status */}
                {Object.entries(NODE_LOCATIONS).map(([key, loc]) => {
                  const affectedItem = affectedDeliveries.find(d => key.includes(d.customer_name.split(' ')[0].toUpperCase()) || key.includes(d.customer_id));
                  const isBreached = affectedItem?.sla_violated;
                  const isDisruptedNode = portalData?.disrupted_segment?.v_node === key || portalData?.location_name?.includes(loc.name.split(' ')[0]);
                  const iconType = isDisruptedNode ? 'disruption' : (loc.type === 'depot' ? 'depot' : (isBreached ? 'customer_breach' : 'customer_normal'));

                  return (
                    <Marker key={key} position={loc.coords} icon={createCustomIcon(iconType)}>
                      <Popup className="custom-leaflet-popup">
                        <strong style={{ color: isDisruptedNode ? '#ef4444' : (isBreached ? '#ef4444' : '#f8fafc') }}>
                          {loc.name} {isDisruptedNode ? '🚨 DISRUPTED' : ''}
                        </strong><br />
                        Type: {loc.type.toUpperCase()}<br />
                        {isDisruptedNode ? (
                          <>
                            Severity: {portalData.severity_level}/5.0<br />
                            Incident Msg: "{portalData.description}"<br />
                            Status: {portalData.status}
                          </>
                        ) : affectedItem ? (
                          <>
                            Order: <code>{affectedItem.delivery_id}</code><br />
                            ETA: {affectedItem.projected_eta} (+{affectedItem.delay_minutes.toFixed(0)}m)<br />
                            SLA Window: {affectedItem.sla_window_end}<br />
                            SLA Status: {isBreached ? '⚠️ SLA VIOLATED' : '✓ On Time'}
                          </>
                        ) : 'Status: Normal Dispatch'}
                      </Popup>
                    </Marker>
                  );
                })}

                {/* Disrupted Road Segment (RED) */}
                {portalData?.disrupted_segment?.coords && (
                  <Polyline
                    positions={portalData.disrupted_segment.coords}
                    color="#ef4444"
                    weight={6}
                    opacity={0.9}
                    dashArray="8, 8"
                  >
                    <Popup className="custom-leaflet-popup">
                      <strong style={{ color: '#ef4444' }}>🚨 DISRUPTED ROAD SEGMENT</strong><br />
                      Corridor: {portalData.disrupted_segment.location_name}<br />
                      Severity: {portalData.severity_level}/5.0
                    </Popup>
                  </Polyline>
                )}

                {/* Path A — Shortest Distance (Solid GREEN) */}
                {portalData?.path_a?.route_coords && portalData.path_a.optimization_status !== 'NO_FEASIBLE_ROUTE' && (
                  <Polyline
                    positions={portalData.path_a.route_coords}
                    color="#10b981"
                    weight={5}
                    opacity={0.95}
                  >
                    <Popup className="custom-leaflet-popup">
                      <strong style={{ color: '#10b981' }}>PATH A (SHORTEST DISTANCE ROUTE)</strong><br />
                      Distance: {portalData.path_a.total_distance_km} km<br />
                      Duration: {portalData.path_a.total_duration_minutes} mins
                    </Popup>
                  </Polyline>
                )}

                {/* Path B — Fastest Travel Time (Dashed CYAN) */}
                {portalData?.path_b?.route_coords && portalData.path_b.optimization_status !== 'NO_FEASIBLE_ROUTE' && (
                  <Polyline
                    positions={portalData.path_b.route_coords}
                    color="#06b6d4"
                    weight={4}
                    opacity={0.90}
                    dashArray="4, 4"
                  >
                    <Popup className="custom-leaflet-popup">
                      <strong style={{ color: '#06b6d4' }}>PATH B (FASTEST TRAVEL TIME ROUTE)</strong><br />
                      Distance: {portalData.path_b.total_distance_km} km<br />
                      Duration: {portalData.path_b.total_duration_minutes} mins
                    </Popup>
                  </Polyline>
                )}
              </MapContainer>
            </div>
          </div>

        </div>

      </main>
    </div>
  );
}
