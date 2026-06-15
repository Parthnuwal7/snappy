import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowLeft, CheckCircle2 } from 'lucide-react';

export default function ResetPassword() {
  const navigate = useNavigate();
  const { updatePassword } = useAuth();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    setIsLoading(true);
    try {
      await updatePassword(password);
      setSuccess(true);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper px-6 py-12">
      <div className="w-full max-w-md animate-fade-up">
        <div className="mb-8 text-center">
          <span
            className="font-display text-4xl text-ink"
            style={{ fontVariationSettings: '"opsz" 144, "wght" 500, "SOFT" 30' }}
          >
            Snappy
          </span>
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-oxblood mb-1 ml-1.5" />
        </div>

        <div className="card p-10">
          {success ? (
            <div className="text-center">
              <div className="mx-auto w-12 h-12 rounded-full bg-status-paid-wash border border-status-paid/30
                              flex items-center justify-center mb-5">
                <CheckCircle2 size={20} strokeWidth={1.5} className="text-status-paid" />
              </div>
              <div className="page-eyebrow">Done</div>
              <h1 className="page-title !text-3xl mt-1">Password updated.</h1>
              <p className="page-subtitle mx-auto">
                Redirecting you to sign in&hellip;
              </p>
            </div>
          ) : (
            <>
              <div className="mb-8">
                <div className="page-eyebrow">New password</div>
                <h1 className="page-title !text-3xl">Set a new password.</h1>
                <p className="page-subtitle">
                  Choose something memorable. Minimum six characters.
                </p>
              </div>

              {error && (
                <div className="alert-error mb-6 animate-fade-in" role="alert">{error}</div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label htmlFor="password" className="field-label">New password</label>
                  <input
                    id="password"
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="field-input"
                    placeholder="At least 6 characters"
                    disabled={isLoading}
                    autoFocus
                    autoComplete="new-password"
                  />
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="field-label">Confirm</label>
                  <input
                    id="confirmPassword"
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="field-input"
                    placeholder="Re-enter new password"
                    disabled={isLoading}
                    autoComplete="new-password"
                  />
                </div>

                <button type="submit" disabled={isLoading} className="btn-primary w-full py-3">
                  {isLoading ? (
                    <>
                      <span className="spinner !w-4 !h-4 !border-paper/40 !border-t-paper" />
                      <span>Updating…</span>
                    </>
                  ) : (
                    <span>Update password</span>
                  )}
                </button>
              </form>

              <div className="mt-8 pt-6 border-t border-rule text-center">
                <Link to="/login"
                      className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-oxblood transition-colors">
                  <ArrowLeft size={14} strokeWidth={2} />
                  <span>Back to sign in</span>
                </Link>
              </div>
            </>
          )}
        </div>

        <div className="mt-8 text-2xs text-ink-faint tracking-eyebrow uppercase text-center">
          © 2026 Snappy
        </div>
      </div>
    </div>
  );
}
