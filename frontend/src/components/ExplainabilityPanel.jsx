import React from 'react';
import { HelpCircle, BarChart2, BookOpen } from 'lucide-react';

export default function ExplainabilityPanel({ explainability, classification, selectedPlan }) {
  if (!explainability) {
    return (
      <div className="panel-card">
        <div className="panel-title">
          <HelpCircle size={16} color="var(--accent-cyan)" />
          Explainability Engine (SHAP + Rule Reasons)
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic' }}>
          Explainability report will populate after disruption analysis.
        </p>
      </div>
    );
  }

  const maxShap = Math.max(...explainability.shap_top_drivers.map(d => Math.abs(d.shap_value)), 0.01);

  return (
    <div className="panel-card">
      <div className="panel-title">
        <HelpCircle size={16} color="var(--accent-cyan)" />
        Explainability Engine (SHAP + Rule Reasons)
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        {/* SHAP Feature Driver Bar Chart */}
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <BarChart2 size={12} color="var(--accent-cyan)" />
            SHAP Disruption Drivers
          </div>

          {explainability.shap_top_drivers.map(item => {
            const pct = Math.min(100, Math.round((Math.abs(item.shap_value) / maxShap) * 100));
            return (
              <div key={item.feature} className="shap-bar-item">
                <div className="shap-bar-header">
                  <span>{item.feature}</span>
                  <span style={{ fontWeight: '700', color: 'var(--accent-cyan)' }}>
                    {item.shap_value > 0 ? '+' : ''}{item.shap_value}
                  </span>
                </div>
                <div className="shap-bar-track">
                  <div className="shap-bar-fill" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Rule-Based Reasons Narrative */}
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <BookOpen size={12} color="var(--accent-green)" />
            Rule-Based System Reasons
          </div>

          <div style={{ background: 'var(--bg-dark)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {explainability.ml_prediction_reasoning.map((r, i) => (
              <div key={i} style={{ color: 'var(--text-primary)' }}>• {r}</div>
            ))}
            {selectedPlan && selectedPlan.rule_reasons && selectedPlan.rule_reasons.map((r, i) => (
              <div key={`p-${i}`} style={{ color: 'var(--accent-green)' }}>✓ {r}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
