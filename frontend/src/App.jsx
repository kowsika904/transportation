import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import LoginPage from './components/LoginPage';
import DeliveryDashboard from './components/DeliveryDashboard';
import TransportDashboard from './components/TransportDashboard';
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

  const [currentRole, setCurrentRole] = useState(() => {
    const user = getStoredUser();
    return user ? user.role : 'logistics_operator';
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

  // Initialize data on mount and set up polling interval for Transport Agent incident broadcasts
  useEffect(() => {
    if (currentUser && currentRole === 'logistics_operator') {
      loadInitialData();
      const interval = setInterval(() => {
        pollActiveIncident();
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [currentUser, currentRole]);

  const pollActiveIncident = async () => {
    try {
      const activeInc = await fetchActiveIncident();
      if (activeInc && activeInc.status === 'ACTIVE' && activeInc.disruption_input) {
        setCurrentAnalysis({
          disruption_input: activeInc.disruption_input,
          classification: activeInc.classification,
          impact_analysis: activeInc.impact_analysis,
          priority_rankings: activeInc.impact_analysis?.affected_deliveries || [],
          recovery_plans: activeInc.all_recovery_plans || {},
          explainability: {
            llm_executive_summary: activeInc.llm_executive_summary,
            llm_team_notification: activeInc.llm_team_notification,
            llm_provider_info: activeInc.llm_provider_info
          },
          timestamp: activeInc.updated_at
        });
        setStatusState(activeInc.applied_plan_id ? 'ACCEPTED' : 'ANALYZED');
      }
    } catch (err) {
      console.warn('Polling active incident notice:', err);
    }
  };

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

      // Fetch active incident reported by Transport Agent (no hardcoded auto-analysis on launch)
      await pollActiveIncident();
    } catch (err) {
      console.error('Initialization error:', err);
      setErrorMsg(`Backend Connection Notice: ${err.message}. Ensure FastAPI server is running on http://127.0.0.1:8000.`);
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = (userData) => {
    if (typeof userData === 'object' && userData !== null) {
      setCurrentUser(userData.username);
      setCurrentRole(userData.role || 'logistics_operator');
    } else {
      setCurrentUser(userData);
      setCurrentRole('logistics_operator');
    }
  };

  const handleLogout = () => {
    logoutUser();
    setCurrentUser(null);
    setCurrentRole('logistics_operator');
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

  // Role-based routing
  if (currentRole === 'delivery_team') {
    return <DeliveryDashboard currentUser={currentUser} onLogout={handleLogout} />;
  }

  if (currentRole === 'transport_team') {
    return <TransportDashboard currentUser={currentUser} onLogout={handleLogout} />;
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
        userRole={currentRole}
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
