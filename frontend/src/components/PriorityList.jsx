import React from 'react';
import { Award, AlertTriangle, ShieldCheck, Thermometer, DollarSign } from 'lucide-react';

export default function PriorityList({ priorities }) {
  if (!priorities || priorities.length === 0) {
    return (
      <div className="panel-card">
        <div className="panel-title">
          <Award size={16} color="var(--accent-amber)" />
          SLA Priority Ranking (0-100 Score)
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic' }}>
          No affected operations to prioritize.
        </p>
      </div>
    );
  }

  const getBadgeClass = (tier) => {
    switch (tier) {
      case 'CRITICAL': return 'badge-red';
      case 'HIGH': return 'badge-amber';
      case 'MEDIUM': return 'badge-blue';
      default: return 'badge-green';
    }
  };

  return (
    <div className="panel-card">
      <div className="panel-title">
        <Award size={16} color="var(--accent-amber)" />
        SLA Priority Ranking (0-100 Score)
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '320px', overflowY: 'auto' }}>
        {priorities.map((item, idx) => (
          <div
            key={item.delivery_id}
            style={{
              background: 'var(--bg-dark)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-sm)',
              padding: '10px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: '800', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  #{idx + 1}
                </span>
                <span style={{ fontWeight: '700', fontSize: '0.9rem' }}>
                  {item.customer_name}
                </span>
              </div>
              <span className={`badge ${getBadgeClass(item.priority_tier)}`}>
                Score {item.priority_score} — {item.priority_tier}
              </span>
            </div>

            <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              <span>Delivery ID: <strong>{item.delivery_id}</strong></span>
              <span>SLA End: <strong style={{ color: '#ef4444' }}>{item.sla_end_time}</strong></span>
              <span>Delay: <strong style={{ color: '#f59e0b' }}>+{item.delay_minutes}m</strong></span>
              {item.is_perishable && (
                <span style={{ color: '#10b981', display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                  <Thermometer size={10} /> Perishable
                </span>
              )}
              {item.item_value_usd >= 20000 && (
                <span style={{ color: 'var(--accent-cyan)', display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                  <DollarSign size={10} /> High Value (${(item.item_value_usd / 1000).toFixed(0)}k)
                </span>
              )}
            </div>

            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Reason: {item.reasoning}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
