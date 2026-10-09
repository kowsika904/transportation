import React, { useState } from 'react';
import { ShieldCheck, Lock, User, AlertCircle, ArrowRight, ArrowLeft, Package, Truck, Activity, Sparkles, Sliders } from 'lucide-react';
import { loginUser } from '../services/api';

const ROLES = [
  {
    id: 'logistics_operator',
    title: 'Logistics Operator',
    description: 'Monitor disruptions and manage recovery decisions.',
    icon: ShieldCheck,
    badgeColor: '#10b981',
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    defaultUsername: 'admin',
    demoHint: 'User ID: admin | Password: admin123'
  },
  {
    id: 'delivery_team',
    title: 'Delivery Team',
    description: 'Track affected deliveries and delivery priorities.',
    icon: Package,
    badgeColor: '#3b82f6',
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
    defaultUsername: 'delivery',
    demoHint: 'User ID: delivery | Password: delivery123'
  },
  {
    id: 'transport_team',
    title: 'Transport Team',
    description: 'Monitor vehicles, routes and transportation operations.',
    icon: Truck,
    badgeColor: '#8b5cf6',
    gradient: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
    defaultUsername: 'transport',
    demoHint: 'User ID: transport | Password: transport123'
  }
];

export default function LoginPage({ onLoginSuccess }) {
  // Navigation states: 'WELCOME' | 'ROLE_SELECTION' | 'LOGIN_FORM' | 'AUTHENTICATING'
  const [step, setStep] = useState('WELCOME');
  const [selectedRole, setSelectedRole] = useState(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleStartLogin = () => {
    setError('');
    setStep('ROLE_SELECTION');
  };

  const handleSelectRole = (role) => {
    setSelectedRole(role);
    setUsername(role.defaultUsername || '');
    setPassword('');
    setError('');
    setStep('LOGIN_FORM');
  };

  const handleBackToRoleSelection = () => {
    setError('');
    setStep('ROLE_SELECTION');
  };

  const handleBackToWelcome = () => {
    setError('');
    setSelectedRole(null);
    setStep('WELCOME');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!username.trim() || !password.trim()) {
      setError('Invalid User ID or Password.');
      return;
    }

    setLoading(true);
    setStep('AUTHENTICATING');

    try {
      const data = await loginUser(username, password, selectedRole?.id || 'logistics_operator');
      onLoginSuccess({
        username: data.username,
        role: data.role || selectedRole?.id || 'logistics_operator',
        access_token: data.access_token
      });
    } catch (err) {
      setError(err.message || 'Invalid User ID or Password.');
      setStep('LOGIN_FORM');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at top, #1e293b 0%, #0f172a 100%)',
      padding: '24px',
      color: '#f8fafc',
      fontFamily: "'Inter', system-ui, -apple-system, sans-serif"
    }}>
      {/* 1. WELCOME PAGE STEP */}
      {step === 'WELCOME' && (
        <div style={{
          width: '100%',
          maxWidth: '560px',
          background: 'rgba(30, 41, 59, 0.75)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '20px',
          padding: '44px 36px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
          textAlign: 'center'
        }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '64px',
            height: '64px',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)',
            boxShadow: '0 10px 20px rgba(239, 68, 68, 0.3)',
            marginBottom: '20px'
          }}>
            <Activity size={36} color="#ffffff" />
          </div>

          <h1 style={{
            fontSize: '1.85rem',
            fontWeight: '800',
            margin: '0 0 10px 0',
            letterSpacing: '-0.025em',
            background: 'linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            Transportation Disruption Recovery
          </h1>

          <p style={{
            fontSize: '0.95rem',
            color: '#94a3b8',
            lineHeight: '1.6',
            margin: '0 0 28px 0',
            fontWeight: '400'
          }}>
            AI-powered logistics disruption analysis and recovery
          </p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            gap: '12px',
            marginBottom: '32px',
            textAlign: 'left'
          }}>
            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '12px',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <ShieldCheck size={20} color="#10b981" />
              <div style={{ fontSize: '0.78rem', fontWeight: '700', color: '#f8fafc' }}>Real-time Detection</div>
              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>XGBoost Disruption Radar</div>
            </div>

            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '12px',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <Sliders size={20} color="#3b82f6" />
              <div style={{ fontSize: '0.78rem', fontWeight: '700', color: '#f8fafc' }}>OR-Tools Optimization</div>
              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Plans A / B / C Strategies</div>
            </div>

            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '12px',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              <Sparkles size={20} color="#8b5cf6" />
              <div style={{ fontSize: '0.78rem', fontWeight: '700', color: '#f8fafc' }}>SLA Defense</div>
              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Dynamic Priority Engine</div>
            </div>
          </div>

          <button
            id="welcome-login-btn"
            onClick={handleStartLogin}
            style={{
              width: '100%',
              padding: '14px 24px',
              background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
              border: 'none',
              borderRadius: '10px',
              color: '#ffffff',
              fontWeight: '700',
              fontSize: '1rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              boxShadow: '0 4px 14px rgba(59, 130, 246, 0.4)',
              transition: 'transform 0.15s ease, filter 0.15s ease'
            }}
          >
            LOGIN <ArrowRight size={20} />
          </button>

          <div style={{ marginTop: '24px', fontSize: '0.75rem', color: '#64748b' }}>
            Authorized Personnel Access Only &bull; Disruption Control System
          </div>
        </div>
      )}

      {/* 2. ROLE SELECTION STEP */}
      {step === 'ROLE_SELECTION' && (
        <div style={{
          width: '100%',
          maxWidth: '520px',
          background: 'rgba(30, 41, 59, 0.75)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '20px',
          padding: '36px 32px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)'
        }}>
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: '800', margin: '0 0 6px 0', letterSpacing: '-0.02em' }}>
              Select Your Role
            </h2>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', margin: 0 }}>
              Choose your operational domain to access the workspace
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '24px' }}>
            {ROLES.map((r) => {
              const RoleIcon = r.icon;
              return (
                <div
                  key={r.id}
                  id={`role-card-${r.id}`}
                  onClick={() => handleSelectRole(r)}
                  style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '12px',
                    padding: '16px 20px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    transition: 'all 0.2s ease',
                    boxSizing: 'border-box'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = r.badgeColor;
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.background = 'rgba(15, 23, 42, 0.85)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.background = 'rgba(15, 23, 42, 0.6)';
                  }}
                >
                  <div style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '10px',
                    background: r.gradient,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}>
                    <RoleIcon size={22} color="#ffffff" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.98rem', fontWeight: '700', color: '#f8fafc', marginBottom: '2px' }}>
                      {r.title}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: '1.4' }}>
                      {r.description}
                    </div>
                  </div>
                  <ArrowRight size={18} color="#64748b" />
                </div>
              );
            })}
          </div>

          <button
            onClick={handleBackToWelcome}
            style={{
              width: '100%',
              padding: '10px',
              background: 'transparent',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '8px',
              color: '#94a3b8',
              fontWeight: '600',
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <ArrowLeft size={16} /> Back to Welcome
          </button>
        </div>
      )}

      {/* 3. LOGIN FORM STEP (Includes AUTHENTICATING state handling) */}
      {(step === 'LOGIN_FORM' || step === 'AUTHENTICATING') && selectedRole && (
        <div style={{
          width: '100%',
          maxWidth: '440px',
          background: 'rgba(30, 41, 59, 0.75)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '20px',
          padding: '36px 32px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)'
        }}>
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '52px',
              height: '52px',
              borderRadius: '14px',
              background: selectedRole.gradient,
              boxShadow: `0 8px 16px ${selectedRole.badgeColor}40`,
              marginBottom: '12px'
            }}>
              {React.createElement(selectedRole.icon, { size: 26, color: '#ffffff' })}
            </div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: '800', margin: '0 0 4px 0', letterSpacing: '-0.02em' }}>
              {selectedRole.title} Login
            </h2>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0 }}>
              Enter credentials to access {selectedRole.title.toLowerCase()} controls
            </p>
          </div>

          {error && (
            <div id="login-error-alert" style={{
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#f87171',
              padding: '12px 14px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              marginBottom: '20px',
              fontWeight: '500'
            }}>
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px', letterSpacing: '0.5px' }}>
                USER ID / EMAIL
              </label>
              <div style={{ position: 'relative' }}>
                <User size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
                <input
                  id="login-username-input"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="Enter User ID or Email"
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '12px 12px 12px 40px',
                    background: 'rgba(15, 23, 42, 0.65)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '8px',
                    color: '#f8fafc',
                    fontSize: '0.9rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px', letterSpacing: '0.5px' }}>
                PASSWORD
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
                <input
                  id="login-password-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="Enter password"
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '12px 12px 12px 40px',
                    background: 'rgba(15, 23, 42, 0.65)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    borderRadius: '8px',
                    color: '#f8fafc',
                    fontSize: '0.9rem',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </div>

            <button
              id="login-submit-btn"
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '12px',
                background: selectedRole.gradient,
                border: 'none',
                borderRadius: '8px',
                color: '#ffffff',
                fontWeight: '700',
                fontSize: '0.9rem',
                cursor: loading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                boxShadow: `0 4px 12px ${selectedRole.badgeColor}40`,
                opacity: loading ? 0.7 : 1,
                marginBottom: '12px'
              }}
            >
              {loading ? 'Authenticating...' : (
                <>
                  LOGIN <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <button
            id="back-to-role-selection-btn"
            onClick={handleBackToRoleSelection}
            disabled={loading}
            style={{
              width: '100%',
              padding: '10px',
              background: 'transparent',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '8px',
              color: '#94a3b8',
              fontWeight: '600',
              fontSize: '0.85rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <ArrowLeft size={16} /> Back to Role Selection
          </button>

          {selectedRole.demoHint && (
            <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.72rem', color: '#64748b', background: 'rgba(15, 23, 42, 0.4)', padding: '6px 10px', borderRadius: '6px' }}>
              💡 Demo credentials: {selectedRole.demoHint}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

