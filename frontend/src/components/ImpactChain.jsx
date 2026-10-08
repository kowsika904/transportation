import React from 'react';
import { Activity, Clock, Truck, Route, AlertCircle, ArrowRight } from 'lucide-react';

export default function ImpactChain({ impact }) {
  if (!impact) {
    return (
      <div className="panel-card">
        <div className="panel-title">
          <Activity size={16} color="var(--accent-cyan)" />
          Operational Impact Chain
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic' }}>
          Select a scenario and click "Analyze Disruption Impact" to evaluate network cascade effects.
        </p>
      </div>
    );
  }

  return (
    <div className="panel-card">
      <div className="panel-title">
        <Activity size={16} color="var(--accent-cyan)" />
        Operational Impact Chain
      </div>

      <div className="impact-chain-container">
        <div className="chain-step">
          <span className="chain-step-val" style={{ color: '#ef4444' }}>
            {impact.affected_routes_count}
          </span>
          <span className="chain-step-lbl">Routes</span>
        </div>
        <ArrowRight size={14} color="var(--text-muted)" />

        <div className="chain-step">
          <span className="chain-step-val" style={{ color: '#8b5cf6' }}>
            {impact.affected_vehicles_count}
          </span>
          <span className="chain-step-lbl">Vehicles</span>
        </div>
        <ArrowRight size={14} color="var(--text-muted)" />

        <div className="chain-step">
          <span className="chain-step-val" style={{ color: '#f59e0b' }}>
            {impact.affected_deliveries_count}
          </span>
          <span className="chain-step-lbl">Deliveries</span>
        </div>
        <ArrowRight size={14} color="var(--text-muted)" />

        <div className="chain-step">
          <span className="chain-step-val" style={{ color: '#ef4444' }}>
            {impact.at_risk_sla_count}
          </span>
          <span className="chain-step-lbl">SLA Risks</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '4px' }}>
        <div style={{ background: 'var(--bg-dark)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock size={20} color="#f59e0b" />
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>TOTAL FLEET DELAY</div>
            <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#f59e0b' }}>
              +{impact.total_expected_delay_minutes} mins
            </div>
          </div>
        </div>

        <div style={{ background: 'var(--bg-dark)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={20} color="#ef4444" />
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>AT-RISK CUSTOMER SLAs</div>
            <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#ef4444' }}>
              {impact.at_risk_sla_count} Critical Breach
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
