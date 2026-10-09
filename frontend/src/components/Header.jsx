import React, { useState, useEffect } from 'react';
import { ShieldAlert, Database, Server, RefreshCw, LogOut, UserCheck, Bell, Radio, CheckCircle, AlertTriangle, Info, X } from 'lucide-react';
import { fetchNotifications, markNotificationRead, subscribeNotificationsStream } from '../services/api';

export default function Header({ status, dbStatus, onRefresh, loading, currentUser, userRole, onLogout }) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showDrawer, setShowDrawer] = useState(false);
  const [sseConnected, setSseConnected] = useState(false);

  const loadNotifications = async () => {
    try {
      const data = await fetchNotifications(userRole);
      if (data && data.notifications) {
        setNotifications(data.notifications);
        setUnreadCount(data.unread_count || 0);
      }
    } catch (err) {
      console.warn('Failed to load notifications:', err);
    }
  };

  useEffect(() => {
    loadNotifications();

    // Subscribe to SSE stream
    const unsubscribe = subscribeNotificationsStream(
      (newNotifs) => {
        setSseConnected(true);
        loadNotifications();
      },
      (err) => {
        setSseConnected(false);
      }
    );

    // Polling fallback every 10s
    const pollInterval = setInterval(() => {
      loadNotifications();
    }, 10000);

    return () => {
      unsubscribe();
      clearInterval(pollInterval);
    };
  }, [userRole]);

  const handleMarkAsRead = async (id) => {
    try {
      await markNotificationRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to mark notification read:', err);
    }
  };

  const getStatusBadge = () => {
    switch (status) {
      case 'ACCEPTED':
      case 'RECOVERY_APPROVED':
        return <span className="badge badge-green">RECOVERY APPROVED</span>;
      case 'MODIFIED_AND_ACCEPTED':
        return <span className="badge badge-green">CUSTOM PLAN DISPATCHED</span>;
      case 'ANALYZED':
      case 'RECOVERY_PROPOSED':
        return <span className="badge badge-amber">RECOVERY PLANS READY</span>;
      case 'RESOLVED':
        return <span className="badge badge-green">INCIDENT RESOLVED</span>;
      case 'DISMISSED':
        return <span className="badge badge-blue">INCIDENT DISMISSED</span>;
      case 'DISRUPTION_DETECTED':
      case 'REPORTED':
        return <span className="badge badge-red">DISRUPTION REPORTED</span>;
      default:
        return <span className="badge badge-blue">NORMAL MONITORING</span>;
    }
  };

  return (
    <header className="app-header" style={{ position: 'relative' }}>
      <div className="brand-title">
        <ShieldAlert size={24} color="#ef4444" />
        <div>
          <h1>DISRUPTION RESPONSE CENTER</h1>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Logistics Disruption Recovery System — Phase 6 Integration
          </span>
        </div>
      </div>

      <div className="header-badges">
        {getStatusBadge()}

        <span className="badge badge-blue" title="FastAPI API Connection">
          <Server size={12} /> API ONLINE
        </span>

        <span className={`badge ${sseConnected ? 'badge-green' : 'badge-amber'}`} title={sseConnected ? 'Server-Sent Events Live updates active' : 'Periodic polling refresh active'}>
          <Radio size={12} className={sseConnected ? 'spin' : ''} /> {sseConnected ? 'LIVE STREAM' : 'POLLING REFRESH'}
        </span>

        {dbStatus && (
          <span className="badge badge-green" title="PostgreSQL + PostGIS Live Database">
            <Database size={12} /> {dbStatus.backend || 'PostgreSQL + PostGIS'} ({dbStatus.depots_count} Depots, {dbStatus.routes_count} Routes)
          </span>
        )}

        {currentUser && (
          <span className="badge badge-green" title="Authenticated Operator">
            <UserCheck size={12} /> {currentUser} ({userRole || 'logistics_operator'})
          </span>
        )}

        {/* Notifications Bell Drawer Trigger */}
        <button
          className="btn-secondary"
          onClick={() => setShowDrawer(!showDrawer)}
          style={{ position: 'relative', padding: '4px 10px', fontSize: '0.75rem', cursor: 'pointer', background: unreadCount > 0 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255,255,255,0.05)', borderColor: unreadCount > 0 ? '#ef4444' : 'var(--border-color)' }}
          title="View Notifications"
        >
          <Bell size={13} color={unreadCount > 0 ? '#ef4444' : 'currentColor'} />
          <span style={{ marginLeft: 4 }}>Alerts</span>
          {unreadCount > 0 && (
            <span style={{
              marginLeft: 6,
              background: '#ef4444',
              color: '#fff',
              fontSize: '0.65rem',
              fontWeight: 'bold',
              borderRadius: '10px',
              padding: '1px 6px',
            }}>
              {unreadCount}
            </span>
          )}
        </button>

        <button 
          className="btn-secondary" 
          onClick={onRefresh} 
          disabled={loading}
          style={{ padding: '4px 10px', fontSize: '0.75rem', cursor: 'pointer' }}
        >
          <RefreshCw size={12} className={loading ? 'spin' : ''} /> Refresh
        </button>

        {onLogout && (
          <button 
            className="btn-secondary" 
            onClick={onLogout}
            title="Sign out of Disruption Response Center"
            style={{ padding: '4px 10px', fontSize: '0.75rem', cursor: 'pointer', background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)', color: '#f87171' }}
          >
            <LogOut size={12} /> Sign Out
          </button>
        )}
      </div>

      {/* Notification Drawer Dropdown */}
      {showDrawer && (
        <div style={{
          position: 'absolute',
          top: '100%',
          right: '20px',
          width: '380px',
          maxHeight: '480px',
          overflowY: 'auto',
          background: '#0f172a',
          border: '1px solid #334155',
          borderRadius: '8px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
          zIndex: 1000,
          padding: '12px',
          marginTop: '8px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
            <h4 style={{ margin: 0, fontSize: '0.9rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Bell size={14} color="#38bdf8" /> Persistent Cross-Portal Notifications ({notifications.length})
            </h4>
            <button onClick={() => setShowDrawer(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
              <X size={14} />
            </button>
          </div>

          {notifications.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem' }}>
              No notifications yet. Real-time updates will appear here.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {notifications.map((n) => (
                <div
                  key={n.id}
                  style={{
                    background: n.is_read ? 'rgba(30, 41, 59, 0.4)' : 'rgba(30, 41, 59, 0.95)',
                    borderLeft: `3px solid ${n.is_read ? '#475569' : '#38bdf8'}`,
                    borderRadius: '4px',
                    padding: '8px 10px',
                    fontSize: '0.8rem',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <span style={{ fontWeight: '600', color: n.is_read ? '#cbd5e1' : '#f8fafc' }}>
                      {n.title}
                    </span>
                    {!n.is_read && (
                      <button
                        onClick={() => handleMarkAsRead(n.id)}
                        style={{ background: 'none', border: 'none', color: '#38bdf8', fontSize: '0.7rem', cursor: 'pointer', textDecoration: 'underline' }}
                      >
                        Mark Read
                      </button>
                    )}
                  </div>
                  <p style={{ margin: '4px 0 6px 0', color: '#94a3b8', fontSize: '0.75rem', lineHeight: '1.3' }}>
                    {n.message}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: '#64748b' }}>
                    <span>Role: {n.recipient_role || 'all'}</span>
                    <span>{n.created_at ? new Date(n.created_at).toLocaleTimeString() : 'Just now'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </header>
  );
}

