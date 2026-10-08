import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import LoginPage from './components/LoginPage';
import DisruptionControl from './components/DisruptionControl';
import LogisticsMap from './components/LogisticsMap';
import ImpactChain from './components/ImpactChain';
import PriorityList from './components/PriorityList';
import RecoveryPlans from './components/RecoveryPlans';
import ExplainabilityPanel from './components/ExplainabilityPanel';
import OperatorAction from './components/OperatorAction';
import UpdatedOperationsView from './components/UpdatedOperationsView';

import {
  fetchHealth,
  fetchDbStatus,
  fetchScenarios,
  analyzeDisruption,
  acceptRecoveryPlan,
  modifyRecoveryPlan,
  getStoredUser,
  logoutUser
} from './services/api';

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    const user = getStoredUser();
    return user ? user.username : null;
  });

  const [dbStatus, setDbStatus] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [statusState, setStatusState] = useState('MONITORING'); // MONITORING, DISRUPTION_DETECTED, ANALYZED, ACCEPTED
  
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [selectedPlanId, setSelectedPlanId] = useState('PLAN_B'); // Default to Fast Recovery Plan B
  const [lastDecision, setLastDecision] = useState(null);

  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Initialize data on mount if authenticated
  useEffect(() => {
    if (currentUser) {
      loadInitialData();
    }
  }, [currentUser]);

  const loadInitialData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [health, dbData, scenarioData] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchDbStatus().catch(() => null),
        fetchScenarios().catch(() => ({ scenarios: [] }))
      ]);

      if (dbData) setDbStatus(dbData);
      if (scenarioData && scenarioData.scenarios) setScenarios(scenarioData.scenarios);

      // Auto-trigger default analysis for seamless hackathon demo on launch
      if (scenarioData && scenarioData.scenarios && scenarioData.scenarios.length > 0) {
        const defaultDisruption = scenarioData.scenarios[0].details;
        const analysis = await analyzeDisruption(defaultDisruption);
        setCurrentAnalysis(analysis);
        setStatusState('ANALYZED');
      }
    } catch (err) {
      console.error('Initialization error:', err);
      setErrorMsg(`Backend Connection Notice: ${err.message}. Ensure FastAPI server is running on http://127.0.0.1:8000.`);
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = (username) => {
    setCurrentUser(username);
  };

  const handleLogout = () => {
    logoutUser();
    setCurrentUser(null);
    setCurrentAnalysis(null);
    setDbStatus(null);
  };

  const handleAnalyzeDisruption = async (disruptionPayload) => {
    setLoading(true);
    setErrorMsg(null);
    setStatusState('DISRUPTION_DETECTED');
    try {
      const res = await analyzeDisruption(disruptionPayload);
      setCurrentAnalysis(res);
      setSelectedPlanId('PLAN_B');
      setLastDecision(null);
      setStatusState('ANALYZED');
    } catch (err) {
      console.error('Analysis error:', err);
      setErrorMsg(`Analysis Failure: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptPlan = async (disruptionId, planId, notes, operatorId) => {
    setActionLoading(true);
    setErrorMsg(null);
    try {
      const res = await acceptRecoveryPlan(disruptionId, planId, notes, operatorId);
      setLastDecision(res);
      setStatusState('ACCEPTED');
      // Refresh DB status
      const updatedDb = await fetchDbStatus().catch(() => null);
      if (updatedDb) setDbStatus(updatedDb);
    } catch (err) {
      console.error('Accept plan error:', err);
      setErrorMsg(`Plan Acceptance Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleModifyPlan = async (disruptionId, planId, overrides, notes, operatorId) => {
    setActionLoading(true);
    setErrorMsg(null);
    try {
      const res = await modifyRecoveryPlan(disruptionId, planId, overrides, notes, operatorId);
      setLastDecision(res);
      setStatusState('MODIFIED_AND_ACCEPTED');
      const updatedDb = await fetchDbStatus().catch(() => null);
      if (updatedDb) setDbStatus(updatedDb);
    } catch (err) {
      console.error('Modify plan error:', err);
      setErrorMsg(`Plan Modification Error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  // If not authenticated, render Login Page
  if (!currentUser) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  const selectedPlanObj = currentAnalysis?.recovery_plans ? currentAnalysis.recovery_plans[selectedPlanId] : null;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-darker)' }}>
      <Header
        status={statusState}
        dbStatus={dbStatus}
        onRefresh={loadInitialData}
        loading={loading}
        currentUser={currentUser}
        onLogout={handleLogout}
      />

      {errorMsg && (
        <div style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#f87171', padding: '10px 24px', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>⚠️ {errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', fontWeight: 'bold' }}>✕</button>
        </div>
      )}

      <main className="dashboard-grid">
        {/* LEFT COLUMN: Controls & Priority Ranking */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <DisruptionControl
            scenarios={scenarios}
            onAnalyze={handleAnalyzeDisruption}
            loading={loading}
            currentAnalysis={currentAnalysis}
          />

          <PriorityList
            priorities={currentAnalysis?.priority_rankings}
          />
        </div>

        {/* MIDDLE COLUMN: Interactive Map & Impact Chain */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <LogisticsMap
            summary={null}
            currentAnalysis={currentAnalysis}
            selectedPlan={selectedPlanObj}
          />

          <ImpactChain
            impact={currentAnalysis?.impact_analysis}
          />

          <UpdatedOperationsView
            lastDecision={lastDecision}
            currentAnalysis={currentAnalysis}
          />
        </div>

        {/* RIGHT COLUMN: Recovery Plans A/B/C, Explainability & Operator Decision */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <RecoveryPlans
            plans={currentAnalysis?.recovery_plans}
            selectedPlanId={selectedPlanId}
            onSelectPlan={setSelectedPlanId}
          />

          <ExplainabilityPanel
            explainability={currentAnalysis?.explainability}
            classification={currentAnalysis?.classification}
            selectedPlan={selectedPlanObj}
          />

          <OperatorAction
            disruptionId={currentAnalysis?.disruption_input?.disruption_id}
            selectedPlanId={selectedPlanId}
            selectedPlan={selectedPlanObj}
            onAccept={handleAcceptPlan}
            onModify={handleModifyPlan}
            actionLoading={actionLoading}
            lastDecision={lastDecision}
          />
        </div>
      </main>
    </div>
  );
}
