import React from 'react';
import { Compass, CheckCircle2, Clock, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function RecoveryPlans({ plans, selectedPlanId, onSelectPlan }) {
  if (!plans) {
    return (
      <div className="panel-card">
        <div className="panel-title">
          <Compass size={16} color="var(--accent-green)" />
          Google OR-Tools Recovery Plans (A / B / C)
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic' }}>
          No recovery plans generated yet.
        </p>
      </div>
    );
  }

  const planKeys = ['PLAN_A', 'PLAN_B', 'PLAN_C'];

  return (
    <div className="panel-card">
      <div className="panel-title">
        <Compass size={16} color="var(--accent-green)" />
        Google OR-Tools Recovery Alternatives (Plan A / Plan B / Plan C)
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
        {planKeys.map(key => {
          const p = plans[key];
          if (!p) return null;
          const isSelected = selectedPlanId === key;

          return (
            <div
              key={key}
              className={`plan-card ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelectPlan(key)}
            >
              <div className="plan-header">
                <span className="plan-name">{p.plan_name}</span>
                {isSelected && <CheckCircle2 size={18} color="var(--accent-green)" />}
              </div>

              <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', margin: '4px 0 8px 0', minHeight: '32px' }}>
                {p.strategy_summary}
              </p>

              <div className="plan-metrics-grid">
                <div className="metric-box">
                  <div className="metric-box-num">{p.total_duration_minutes}m</div>
                  <div className="metric-box-lbl">DURATION</div>
                </div>

                <div className="metric-box">
                  <div className="metric-box-num">{p.total_distance_miles}mi</div>
                  <div className="metric-box-lbl">DISTANCE</div>
                </div>

                <div className="metric-box">
                  <div className="metric-box-num" style={{ color: p.sla_violations_count > 0 ? '#ef4444' : '#10b981' }}>
                    {p.sla_violations_count}
                  </div>
                  <div className="metric-box-lbl">SLA RISK</div>
                </div>
              </div>

              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                Trade-off: {p.trade_offs[0] || 'Standard routing.'}
              </div>
            </div>
          );
        })}
      </div>

      {/* Plan Comparison Matrix Table */}
      <div style={{ marginTop: '8px', overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse', textAlign: 'center' }}>
          <thead>
            <tr style={{ background: 'var(--bg-dark)', color: 'var(--text-secondary)' }}>
              <th style={{ padding: '6px', textAlign: 'left' }}>METRIC</th>
              <th style={{ padding: '6px', color: selectedPlanId === 'PLAN_A' ? 'var(--accent-green)' : 'inherit' }}>PLAN A</th>
              <th style={{ padding: '6px', color: selectedPlanId === 'PLAN_B' ? 'var(--accent-green)' : 'inherit' }}>PLAN B (FAST)</th>
              <th style={{ padding: '6px', color: selectedPlanId === 'PLAN_C' ? 'var(--accent-green)' : 'inherit' }}>PLAN C (SLA)</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '6px', textAlign: 'left', fontWeight: '600' }}>Travel Duration</td>
              <td>{plans.PLAN_A?.total_duration_minutes} mins</td>
              <td>{plans.PLAN_B?.total_duration_minutes} mins</td>
              <td>{plans.PLAN_C?.total_duration_minutes} mins</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '6px', textAlign: 'left', fontWeight: '600' }}>SLA Violations</td>
              <td style={{ color: plans.PLAN_A?.sla_violations_count > 0 ? '#ef4444' : '#10b981' }}>{plans.PLAN_A?.sla_violations_count}</td>
              <td style={{ color: plans.PLAN_B?.sla_violations_count > 0 ? '#ef4444' : '#10b981' }}>{plans.PLAN_B?.sla_violations_count}</td>
              <td style={{ color: plans.PLAN_C?.sla_violations_count > 0 ? '#ef4444' : '#10b981' }}>{plans.PLAN_C?.sla_violations_count}</td>
            </tr>
            <tr>
              <td style={{ padding: '6px', textAlign: 'left', fontWeight: '600' }}>Rescheduled Deliveries</td>
              <td>{plans.PLAN_A?.rescheduled_deliveries_count}</td>
              <td>{plans.PLAN_B?.rescheduled_deliveries_count}</td>
              <td>{plans.PLAN_C?.rescheduled_deliveries_count}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
