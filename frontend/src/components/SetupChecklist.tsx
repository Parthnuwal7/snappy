import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import { Check, Circle, X } from 'lucide-react';

type Row = { key: 'bank' | 'branding' | 'billing' | 'team'; label: string; to: string };

const ROWS: Row[] = [
  { key: 'bank', label: 'Add bank / UPI details', to: '/settings' },
  { key: 'branding', label: 'Upload logo & signature', to: '/settings' },
  { key: 'billing', label: 'Set billing terms & tax', to: '/settings' },
  { key: 'team', label: 'Invite your team', to: '/team' },
];

export default function SetupChecklist() {
  const navigate = useNavigate();
  const { setup, profile, refreshProfile } = useAuth();

  if (!setup || setup.dismissed || setup.complete) return null;

  const dismiss = async () => {
    try { await api.dismissChecklist(); await refreshProfile(); }
    catch (e) { console.error(e); }
  };

  // Solo practitioners: push the team row to the end and mute it.
  const rows = profile?.is_solo
    ? [...ROWS.filter((r) => r.key !== 'team'), ...ROWS.filter((r) => r.key === 'team')]
    : ROWS;

  const doneCount = ROWS.filter((r) => setup[r.key]).length;

  return (
    <div className="card p-6 mb-6 relative">
      <button onClick={dismiss} aria-label="Dismiss checklist"
              className="absolute top-4 right-4 text-ink-faint hover:text-ink">
        <X size={16} />
      </button>
      <div className="page-eyebrow">Finish setting up</div>
      <h3 className="section-title !text-lg mb-1">
        {doneCount} of {ROWS.length} done
      </h3>
      <p className="text-sm text-ink-muted mb-4">
        Complete these to get the most out of Snappy. You can do them anytime.
      </p>
      <ul className="space-y-1">
        {rows.map((r) => {
          const done = setup[r.key];
          const muted = profile?.is_solo && r.key === 'team';
          return (
            <li key={r.key}>
              <button onClick={() => navigate(r.to)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-left
                            hover:bg-paper-deep transition-colors ${muted ? 'opacity-60' : ''}`}>
                {done
                  ? <Check size={16} className="text-oxblood shrink-0" strokeWidth={2.5} />
                  : <Circle size={16} className="text-ink-faint shrink-0" />}
                <span className={`text-sm ${done ? 'text-ink-muted line-through' : 'text-ink'}`}>
                  {r.label}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
