import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import { ArrowRight, Check } from 'lucide-react';

type Profile = {
  full_name: string;
  designation: string;
  bar_council_number: string;
  personal_phone: string;
};

export default function Onboarding() {
  const navigate = useNavigate();
  const { refreshProfile, isOnboarded, isLoading: isAuthLoading, pendingInvite } = useAuth();

  useEffect(() => {
    if (!isAuthLoading && isOnboarded) navigate('/', { replace: true });
  }, [isAuthLoading, isOnboarded, navigate]);

  const [profile, setProfile] = useState<Profile>({
    full_name: '', designation: '', bar_council_number: '', personal_phone: '',
  });
  const [firmName, setFirmName] = useState('');
  const [isSolo, setIsSolo] = useState(true);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const isInvitee = !!pendingInvite;

  const onProfileChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setProfile((p) => ({ ...p, [e.target.name]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!profile.full_name.trim()) return setError('Your name is required');
    if (!isInvitee && !firmName.trim()) return setError('Firm name is required');

    setIsLoading(true);
    try {
      if (isInvitee) {
        await api.acceptPendingInvite();
        await api.updateProfile(profile);
      } else {
        await api.onboard({ ...profile, firm_name: firmName, is_solo: isSolo });
      }
      try { await refreshProfile(); } catch (err) { console.error(err); }
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Could not complete setup. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper py-12 px-6">
      <div className="max-w-2xl mx-auto animate-fade-up">
        <div className="text-center mb-10">
          <span className="font-display text-4xl text-ink"
            style={{ fontVariationSettings: '"opsz" 144, "wght" 500, "SOFT" 30' }}>
            Snappy
          </span>
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-oxblood mb-1 ml-1.5" />
          <div className="eyebrow text-ink-faint mt-2">
            {isInvitee ? `Join ${pendingInvite!.firm_name}` : 'Establish your chambers'}
          </div>
        </div>

        <div className="card p-10">
          {error && <div className="alert-error mb-6" role="alert">{error}</div>}

          <form onSubmit={submit} className="space-y-5">
            <div className="mb-2">
              <div className="page-eyebrow">{isInvitee ? 'Your details' : 'Step I'}</div>
              <h2 className="section-title">
                {isInvitee
                  ? `Joining as ${pendingInvite!.role_name}`
                  : 'Tell us about you and your firm'}
              </h2>
            </div>

            <div>
              <label className="field-label">Your full name *</label>
              <input name="full_name" value={profile.full_name} onChange={onProfileChange}
                     className="field-input" placeholder="e.g., Adv. Priya Sharma" autoFocus />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="field-label">Designation</label>
                <input name="designation" value={profile.designation} onChange={onProfileChange}
                       className="field-input" placeholder="Advocate" />
              </div>
              <div>
                <label className="field-label">Bar Council / enrolment no.</label>
                <input name="bar_council_number" value={profile.bar_council_number}
                       onChange={onProfileChange} className="field-input font-mono"
                       placeholder="MAH/1234/2020" />
              </div>
            </div>

            <div>
              <label className="field-label">Your phone</label>
              <input name="personal_phone" value={profile.personal_phone} onChange={onProfileChange}
                     className="field-input font-mono" placeholder="+91-XXXXXXXXXX" />
            </div>

            {!isInvitee && (
              <>
                <div className="pt-4 border-t border-rule">
                  <label className="field-label">Firm name *</label>
                  <input value={firmName} onChange={(e) => setFirmName(e.target.value)}
                         className="field-input" placeholder="e.g., Sharma & Associates" />
                </div>

                <div>
                  <label className="field-label">Are you practising solo or as a firm?</label>
                  <div className="flex gap-3 mt-1">
                    {([['Solo', true], ['Firm / team', false]] as [string, boolean][]).map(
                      ([label, val]) => (
                        <button type="button" key={label}
                          onClick={() => setIsSolo(val)}
                          className={`px-4 py-2 rounded-md border text-sm transition-all ${
                            isSolo === val ? 'border-oxblood bg-oxblood/5 text-ink'
                                           : 'border-rule text-ink-muted'}`}>
                          {label}
                        </button>
                      ))}
                  </div>
                </div>
              </>
            )}

            <div className="flex justify-end pt-6 border-t border-rule">
              <button type="submit" disabled={isLoading} className="btn-primary">
                {isLoading ? (
                  <><span className="spinner !w-4 !h-4 !border-paper/40 !border-t-paper" />
                    <span>Setting up…</span></>
                ) : (
                  <><span>{isInvitee ? 'Join firm' : 'Enter Snappy'}</span>
                    {isInvitee ? <Check size={14} strokeWidth={2} />
                               : <ArrowRight size={14} strokeWidth={2} />}</>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
