import { useEffect, useRef, useState } from 'react';
import { useParams, useSearchParams, useNavigate, Navigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { CheckCircle2, XCircle, ArrowRight } from 'lucide-react';

type Status = 'working' | 'success' | 'error';

export default function AcceptInvite() {
  const params = useParams();
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, refreshProfile } = useAuth();

  // The email link is /accept-invite/<token>; tolerate ?token= as a fallback.
  const token = params.token || search.get('token') || '';

  const [status, setStatus] = useState<Status>('working');
  const [message, setMessage] = useState('');
  const ranRef = useRef(false);

  useEffect(() => {
    if (isLoading || !isAuthenticated || !token || ranRef.current) return;
    ranRef.current = true; // guard against double-invoke in StrictMode
    (async () => {
      try {
        await api.acceptInvite(token);
        await refreshProfile(); // pick up new firm_id + permissions
        setStatus('success');
        setMessage('You have joined the firm.');
      } catch (e) {
        setStatus('error');
        setMessage(e instanceof Error ? e.message : 'This invitation could not be accepted.');
      }
    })();
  }, [isLoading, isAuthenticated, token, refreshProfile]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-paper">
        <div className="spinner" />
      </div>
    );
  }

  // Logged-out invitee: send them to sign in, then back here to finish.
  if (!isAuthenticated) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(`/accept-invite/${token}`)}`} replace />;
  }

  if (!token) {
    return (
      <Shell>
        <Icon kind="error" />
        <h1 className="page-title !text-2xl mt-4">Invalid invitation link</h1>
        <p className="page-subtitle">This link is missing its invitation token.</p>
      </Shell>
    );
  }

  return (
    <Shell>
      {status === 'working' && (
        <>
          <div className="spinner" />
          <p className="text-sm text-ink-muted mt-4">Accepting your invitation…</p>
        </>
      )}

      {status === 'success' && (
        <>
          <Icon kind="success" />
          <h1 className="page-title !text-2xl mt-4">You're in.</h1>
          <p className="page-subtitle">{message}</p>
          <button onClick={() => navigate('/dashboard')} className="btn-primary mt-6 group">
            <span>Go to dashboard</span>
            <ArrowRight size={16} strokeWidth={2} className="transition-transform group-hover:translate-x-0.5" />
          </button>
        </>
      )}

      {status === 'error' && (
        <>
          <Icon kind="error" />
          <h1 className="page-title !text-2xl mt-4">Invitation not accepted</h1>
          <p className="page-subtitle">{message}</p>
          <button onClick={() => navigate('/')} className="btn-ghost mt-6">Back to app</button>
        </>
      )}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper px-6">
      <div className="card p-10 max-w-md w-full text-center animate-fade-up">
        <div className="page-eyebrow">Invitation</div>
        {children}
      </div>
    </div>
  );
}

function Icon({ kind }: { kind: 'success' | 'error' }) {
  return kind === 'success' ? (
    <CheckCircle2 size={36} strokeWidth={1.5} className="text-oxblood mx-auto" />
  ) : (
    <XCircle size={36} strokeWidth={1.5} className="text-oxblood mx-auto" />
  );
}
