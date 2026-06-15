import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { AlertTriangle, X } from 'lucide-react';

export default function OnboardingWarning() {
  const { isOnboarded, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  if (!isAuthenticated || isOnboarded || dismissed) return null;

  return (
    <div className="bg-status-pending-wash border-b border-status-pending/30">
      <div className="max-w-page mx-auto px-8 lg:px-12 py-3 flex items-center gap-4">
        <AlertTriangle size={16} strokeWidth={1.75} className="text-status-pending shrink-0" />
        <div className="flex-1 text-sm text-ink-soft">
          <span className="uppercase tracking-eyebrow text-2xs text-status-pending font-medium">
            Setup pending ·{' '}
          </span>
          Complete your firm profile to enable invoicing and the full feature set.
        </div>
        <button
          onClick={() => navigate('/onboarding')}
          className="text-xs font-medium uppercase tracking-eyebrow text-ink hover:text-oxblood transition-colors"
        >
          Complete now
        </button>
        <button
          onClick={() => setDismissed(true)}
          className="text-ink-faint hover:text-ink-muted transition-colors"
          aria-label="Dismiss"
        >
          <X size={16} strokeWidth={1.5} />
        </button>
      </div>
    </div>
  );
}
