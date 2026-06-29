import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import { Check } from 'lucide-react';

export default function InviteeProfile() {
  const navigate = useNavigate();
  const { refreshProfile } = useAuth();
  const [form, setForm] = useState({
    full_name: '', designation: '', bar_council_number: '', personal_phone: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.full_name.trim()) return setError('Your name is required');
    setIsLoading(true);
    try {
      await api.updateProfile(form);
      try { await refreshProfile(); } catch (err) { console.error(err); }
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Could not save your profile.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper py-12 px-6">
      <div className="max-w-2xl mx-auto animate-fade-up">
        <div className="text-center mb-10">
          <div className="page-eyebrow">Welcome aboard</div>
          <h1 className="page-title">Complete your profile</h1>
        </div>
        <div className="card p-10">
          {error && <div className="alert-error mb-6" role="alert">{error}</div>}
          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="field-label">Your full name *</label>
              <input name="full_name" value={form.full_name} onChange={onChange}
                     className="field-input" placeholder="e.g., Adv. Priya Sharma" autoFocus />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="field-label">Designation</label>
                <input name="designation" value={form.designation} onChange={onChange}
                       className="field-input" placeholder="Associate" />
              </div>
              <div>
                <label className="field-label">Bar Council / enrolment no.</label>
                <input name="bar_council_number" value={form.bar_council_number}
                       onChange={onChange} className="field-input font-mono"
                       placeholder="MAH/1234/2020" />
              </div>
            </div>
            <div>
              <label className="field-label">Your phone</label>
              <input name="personal_phone" value={form.personal_phone} onChange={onChange}
                     className="field-input font-mono" placeholder="+91-XXXXXXXXXX" />
            </div>
            <div className="flex justify-end pt-6 border-t border-rule">
              <button type="submit" disabled={isLoading} className="btn-primary">
                {isLoading ? (
                  <><span className="spinner !w-4 !h-4 !border-paper/40 !border-t-paper" />
                    <span>Saving…</span></>
                ) : (
                  <><span>Go to dashboard</span><Check size={14} strokeWidth={2} /></>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
