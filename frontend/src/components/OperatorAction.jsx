import React, { useState } from 'react';
import { UserCheck, CheckCircle, Edit3, ShieldAlert } from 'lucide-react';

export default function OperatorAction({
  disruptionId,
  selectedPlanId,
  selectedPlan,
  onAccept,
  onModify,
  actionLoading,
  lastDecision
}) {
  const [operatorId, setOperatorId] = useState('OPERATOR_01');
  const [operatorNotes, setOperatorNotes] = useState('Fast recovery plan approved for fleet dispatch.');
  const [showModify, setShowModify] = useState(false);
  const [extraDuration, setExtraDuration] = useState('15');
  const [overrideNotes, setOverrideNotes] = useState('Added mandatory driver rest stop');

  if (!selectedPlan) {
    return (
      <div className="panel-card">
        <div className="panel-title">
          <UserCheck size={16} color="var(--accent-blue)" />
          Operator Decision & Dispatch Controls
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic' }}>
          Select a recovery plan (Plan A, B, or C) above to enable operator decision controls.
        </p>
      </div>
    );
  }

  const handleAcceptClick = () => {
    onAccept(disruptionId, selectedPlanId, operatorNotes, operatorId);
  };

  const handleModifyClick = () => {
    onModify(
      disruptionId,
      selectedPlanId,
      { extra_duration_mins: parseFloat(extraDuration) || 0, notes: overrideNotes },
      operatorNotes,
      operatorId
    );
  };

  return (
    <div className="panel-card" style={{ border: '2px solid var(--accent-blue)' }}>
      <div className="panel-title">
        <UserCheck size={16} color="var(--accent-blue)" />
        Human Operator Decision Controls ({selectedPlan.plan_name})
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Operator ID:</label>
          <input
            type="text"
            value={operatorId}
            onChange={e => setOperatorId(e.target.value)}
            style={{
              width: '100%',
              background: 'var(--bg-dark)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem',
              marginTop: '4px'
            }}
          />
        </div>

        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Operator Notes:</label>
          <input
            type="text"
            value={operatorNotes}
            onChange={e => setOperatorNotes(e.target.value)}
            style={{
              width: '100%',
              background: 'var(--bg-dark)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem',
              marginTop: '4px'
            }}
          />
        </div>
      </div>

      {showModify && (
        <div style={{ background: 'var(--bg-dark)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--accent-amber)' }}>
            Custom Operator Parameters Overrides
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Extra Duration (mins):</label>
              <input
                type="number"
                value={extraDuration}
                onChange={e => setExtraDuration(e.target.value)}
                style={{ width: '100%', background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', padding: '4px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Custom Route Note:</label>
              <input
                type="text"
                value={overrideNotes}
                onChange={e => setOverrideNotes(e.target.value)}
                style={{ width: '100%', background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', padding: '4px 8px', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem' }}
              />
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
        <button
          className="btn-action btn-success"
          onClick={handleAcceptClick}
          disabled={actionLoading}
        >
          <CheckCircle size={16} /> ACCEPT & DISPATCH PLAN
        </button>

        <button
          className="btn-action btn-secondary"
          onClick={() => {
            if (showModify) handleModifyClick();
            else setShowModify(true);
          }}
          disabled={actionLoading}
        >
          <Edit3 size={16} /> {showModify ? 'CONFIRM CUSTOMIZATIONS' : 'MODIFY PARAMETERS'}
        </button>
      </div>

      {lastDecision && (
        <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--accent-green)', padding: '10px', borderRadius: 'var(--radius-sm)', marginTop: '8px' }}>
          <div style={{ color: 'var(--accent-green)', fontWeight: '700', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle size={16} /> Decision Persisted in PostgreSQL Database
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {lastDecision.message} (Applied Plan: <strong>{lastDecision.applied_plan_id}</strong>)
          </div>
        </div>
      )}
    </div>
  );
}
