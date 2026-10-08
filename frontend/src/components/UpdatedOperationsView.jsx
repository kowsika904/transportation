import React from 'react';
import { ShieldCheck, ArrowRight, Truck, CheckCircle2 } from 'lucide-react';

export default function UpdatedOperationsView({ lastDecision, currentAnalysis }) {
  if (!lastDecision) return null;

  const plan = lastDecision.active_plan;
  const impact = currentAnalysis?.impact_analysis;

  return (
    <div className="panel-card" style={{ background: 'rgba(16, 185, 129, 0.05)', border: '1px solid var(--accent-green)' }}>
      <div className="panel-title" style={{ color: 'var(--accent-green)' }}>
        <ShieldCheck size={16} />
        Updated Operational State & Dispatch Confirmation
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', textAlign: 'center' }}>
        <div style={{ background: 'var(--bg-dark)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>SLA RISK RESCUE</div>
          <div style={{ fontSize: '1.2rem', fontWeight: '800', color: 'var(--accent-green)' }}>
            {impact ? impact.at_risk_sla_count - plan.sla_violations_count : 0} Resolved
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {plan.sla_violations_count} remaining SLA risk
          </div>
        </div>

        <div style={{ background: 'var(--bg-dark)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>OPTIMIZED DISPATCH DURATION</div>
          <div style={{ fontSize: '1.2rem', fontWeight: '800', color: 'var(--accent-green)' }}>
            {plan.total_duration_minutes} Mins
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {plan.total_distance_miles} miles total fleet travel
          </div>
        </div>

        <div style={{ background: 'var(--bg-dark)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>VEHICLES REROUTED</div>
          <div style={{ fontSize: '1.2rem', fontWeight: '800', color: 'var(--accent-cyan)' }}>
            {plan.rerouted_vehicles_count} Active Units
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {plan.rescheduled_deliveries_count} rescheduled stops
          </div>
        </div>
      </div>
    </div>
  );
}
