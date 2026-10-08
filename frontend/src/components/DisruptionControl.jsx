import React, { useState, useEffect } from 'react';
import { AlertTriangle, Cpu, Play, Thermometer, Wind, CloudRain, Eye } from 'lucide-react';

export default function DisruptionControl({ scenarios, onAnalyze, loading, currentAnalysis }) {
  const [selectedKey, setSelectedKey] = useState('NYC_BLIZZARD');
  const [activePayload, setActivePayload] = useState(null);

  useEffect(() => {
    if (scenarios && scenarios.length > 0) {
      const match = scenarios.find(s => s.key === selectedKey) || scenarios[0];
      if (match) setActivePayload(match.details);
    }
  }, [scenarios, selectedKey]);

  const handleKeyChange = (e) => {
    const key = e.target.value;
    setSelectedKey(key);
    const match = scenarios.find(s => s.key === key);
    if (match) setActivePayload(match.details);
  };

  const handleSubmit = () => {
    if (activePayload) {
      onAnalyze(activePayload);
    }
  };

  const clf = currentAnalysis?.classification;

  return (
    <div className="panel-card">
      <div className="panel-title">
        <AlertTriangle size={16} color="#ef4444" />
        Disruption Scenario Control
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          Select Preconfigured Scenario:
        </label>
        <select
          value={selectedKey}
          onChange={handleKeyChange}
          style={{
            background: 'var(--bg-dark)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.85rem',
            fontWeight: '600'
          }}
        >
          {scenarios.map(s => (
            <option key={s.key} value={s.key}>
              {s.key.replace(/_/g, ' ')} — {s.details.location_name}
            </option>
          ))}
        </select>
      </div>

      {activePayload && (
        <div style={{ background: 'var(--bg-dark)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', fontSize: '0.8rem' }}>
          <div style={{ fontWeight: '700', color: '#f87171', marginBottom: '4px' }}>
            {activePayload.disruption_type.toUpperCase().replace(/_/g, ' ')} (Severity {activePayload.severity_level}/5)
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '8px' }}>
            {activePayload.description}
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.7rem' }}>
            <div><CloudRain size={10} /> Precip: <strong>{activePayload.precipitation_inches} in</strong></div>
            <div><Wind size={10} /> Wind: <strong>{activePayload.wind_speed_mph} mph</strong></div>
            <div><Eye size={10} /> Visibility: <strong>{activePayload.visibility_miles} mi</strong></div>
            <div><Thermometer size={10} /> Temp: <strong>{activePayload.temperature_f}°F</strong></div>
            <div>Cap. Reduction: <strong style={{ color: '#ef4444' }}>{activePayload.road_capacity_reduction_pct}%</strong></div>
            <div>Speed: <strong>{activePayload.average_speed_mph} / {activePayload.normal_speed_mph} mph</strong></div>
          </div>
        </div>
      )}

      <button className="btn-action" onClick={handleSubmit} disabled={loading}>
        <Play size={16} /> {loading ? 'Analyzing Impact...' : 'ANALYZE DISRUPTION IMPACT'}
      </button>

      {clf && (
        <div style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', padding: '10px', borderRadius: 'var(--radius-sm)', marginTop: '4px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={14} /> XGBoost Classifier Output
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
            <span style={{ fontSize: '0.9rem', fontWeight: '800', color: '#f87171' }}>
              {clf.predicted_class}
            </span>
            <span className="badge badge-green">
              {(clf.confidence * 100).toFixed(1)}% Confidence
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
