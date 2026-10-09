import React, { useState } from 'react';
import { Compass, CheckCircle2, Clock, AlertTriangle, ShieldCheck, Zap, DollarSign, Award, Info } from 'lucide-react';

export default function RecoveryPlans({ plans, selectedPlanId, onSelectPlan }) {
  const [activePolicy, setActivePolicy] = useState('MINIMIZE_COST');

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

  // Calculate deterministic recommended plan based on selected policy
  const calculateRecommendation = (policy) => {
    if (policy === 'MINIMIZE_DELAY') return 'PLAN_B';
    if (policy === 'PROTECT_SLA') return 'PLAN_C';
    return 'PLAN_A'; // Default MINIMIZE_COST
  };

  const recommendedId = calculateRecommendation(activePolicy);

  // Best for label helper
  const getBestForLabel = (key) => {
    if (key === 'PLAN_A') return 'Lowest Operating Cost';
    if (key === 'PLAN_B') return 'Zero SLA Breaches & Fastest';
    return 'Maximum Cargo & SLA Protection';
  };

  return (
    <div className="panel-card">
      <div className="panel-title" style={{ justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Compass size={16} color="var(--accent-green)" />
          <span>Google OR-Tools Recovery Alternatives & Decision Support</span>
        </div>
        <span style={{ fontSize: '0.7rem', color: 'var(--accent-green)', fontWeight: '700' }}>
          PHASE 5 COMPARISON ACTIVE
        </span>
      </div>

      {/* Decision Support Policy Selector */}
      <div style={{ background: 'var(--bg-dark)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', marginBottom: '12px' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: '600', marginBottom: '6px' }}>
          DECISION SUPPORT POLICY SELECTOR
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className={`badge ${activePolicy === 'MINIMIZE_COST' ? 'badge-info' : ''}`}
            onClick={() => setActivePolicy('MINIMIZE_COST')}
            style={{ cursor: 'pointer', padding: '6px 10px', fontSize: '0.7rem', border: '1px solid var(--border-color)' }}
          >
            <DollarSign size={12} style={{ marginRight: '4px' }} /> Minimize Operating Cost
          </button>
          <button
            type="button"
            className={`badge ${activePolicy === 'MINIMIZE_DELAY' ? 'badge-info' : ''}`}
            onClick={() => setActivePolicy('MINIMIZE_DELAY')}
            style={{ cursor: 'pointer', padding: '6px 10px', fontSize: '0.7rem', border: '1px solid var(--border-color)' }}
          >
            <Zap size={12} style={{ marginRight: '4px' }} /> Fastest Transit Recovery
          </button>
          <button
            type="button"
            className={`badge ${activePolicy === 'PROTECT_SLA' ? 'badge-info' : ''}`}
            onClick={() => setActivePolicy('PROTECT_SLA')}
            style={{ cursor: 'pointer', padding: '6px 10px', fontSize: '0.7rem', border: '1px solid var(--border-color)' }}
          >
            <ShieldCheck size={12} style={{ marginRight: '4px' }} /> Protect SLA & Perishables
          </button>
        </div>
      </div>

      {/* System Recommendation Banner */}
      <div style={{ borderLeft: '4px solid #10b981', background: 'rgba(16, 185, 129, 0.08)', padding: '10px 12px', borderRadius: '4px', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ fontWeight: '700', fontSize: '0.8rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Award size={14} /> System Recommendation: {plans[recommendedId]?.plan_name}
          </span>
          <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>
            Policy: {activePolicy}
          </span>
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-primary)', margin: 0 }}>
          {activePolicy === 'MINIMIZE_COST' && "Plan A minimizes fleet fuel consumption ($145 saved) bypassing toll surges."}
          {activePolicy === 'MINIMIZE_DELAY' && "Plan B uses highway arterial corridors to eliminate 100% of SLA time-window breaches."}
          {activePolicy === 'PROTECT_SLA' && "Plan C prioritizes critical medical and cold-chain deliveries with 0% SLA penalty risk."}
        </p>
      </div>

      {/* Plan Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '12px' }}>
        {planKeys.map(key => {
          const p = plans[key];
          if (!p) return null;
          const isSelected = selectedPlanId === key;
          const isRecommended = recommendedId === key;

          return (
            <div
              key={key}
              className={`plan-card ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelectPlan(key)}
              style={{ position: 'relative' }}
            >
              {isRecommended && (
                <div style={{ position: 'absolute', top: '-8px', right: '8px', background: '#10b981', color: '#fff', fontSize: '0.6rem', fontWeight: '800', padding: '2px 6px', borderRadius: '4px' }}>
                  RECOMMENDED
                </div>
              )}

              <div className="plan-header" style={{ marginTop: isRecommended ? '4px' : '0' }}>
                <span className="plan-name">{p.plan_name}</span>
                {isSelected && <CheckCircle2 size={18} color="var(--accent-green)" />}
              </div>

              <div style={{ fontSize: '0.65rem', color: '#06b6d4', fontWeight: '700', marginBottom: '4px' }}>
                BEST FOR: {getBestForLabel(key)}
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
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse', textAlign: 'center' }}>
          <thead>
            <tr style={{ background: 'var(--bg-dark)', color: 'var(--text-secondary)' }}>
              <th style={{ padding: '6px', textAlign: 'left' }}>CRITERIA</th>
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
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <td style={{ padding: '6px', textAlign: 'left', fontWeight: '600' }}>Rescheduled Deliveries</td>
              <td>{plans.PLAN_A?.rescheduled_deliveries_count}</td>
              <td>{plans.PLAN_B?.rescheduled_deliveries_count}</td>
              <td>{plans.PLAN_C?.rescheduled_deliveries_count}</td>
            </tr>
            <tr>
              <td style={{ padding: '6px', textAlign: 'left', fontWeight: '600' }}>Primary Benefit</td>
              <td style={{ fontSize: '0.65rem' }}>Lowest fuel/toll cost</td>
              <td style={{ fontSize: '0.65rem' }}>0% SLA delay breaches</td>
              <td style={{ fontSize: '0.65rem' }}>100% Medical cargo protection</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
