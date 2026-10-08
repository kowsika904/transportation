import React from 'react';
import { ShieldAlert, Database, Server, RefreshCw, LogOut, UserCheck } from 'lucide-react';

export default function Header({ status, dbStatus, onRefresh, loading, currentUser, onLogout }) {
  const getStatusBadge = () => {
    switch (status) {
      case 'ACCEPTED':
        return <span className="badge badge-green">OPERATIONS UPDATED</span>;
      case 'MODIFIED_AND_ACCEPTED':
        return <span className="badge badge-green">CUSTOM PLAN DISPATCHED</span>;
      case 'ANALYZED':
        return <span className="badge badge-amber">RECOVERY PLANS READY</span>;
      case 'DISRUPTION_DETECTED':
        return <span className="badge badge-red">DISRUPTION ACTIVE</span>;
      default:
        return <span className="badge badge-blue">NORMAL MONITORING</span>;
    }
  };

  return (
    <header className="app-header">
      <div className="brand-title">
        <ShieldAlert size={24} color="#ef4444" />
        <div>
          <h1>DISRUPTION RESPONSE CENTER</h1>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            HACKNEXT'26 PS02 — Disruption-Aware Logistics System
          </span>
        </div>
      </div>

      <div className="header-badges">
        {getStatusBadge()}

        <span className="badge badge-blue" title="FastAPI API Connection">
          <Server size={12} /> API CONNECTED
        </span>

        {dbStatus && (
          <span className="badge badge-green" title="PostgreSQL + PostGIS Live Database">
            <Database size={12} /> {dbStatus.backend || 'PostgreSQL + PostGIS'} ({dbStatus.depots_count} Depots, {dbStatus.routes_count} Routes)
          </span>
        )}

        {currentUser && (
          <span className="badge badge-green" title="Authenticated Operator">
            <UserCheck size={12} /> {currentUser}
          </span>
        )}

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
    </header>
  );
}
