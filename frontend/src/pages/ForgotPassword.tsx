import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowLeft, MailCheck } from 'lucide-react';

export default function ForgotPassword() {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);
    setIsLoading(true);
    try {
      await resetPassword(email);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email.');
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
                <MailCheck size={20} strokeWidth={1.5} className="text-status-paid" />
              </div>
              <div className="page-eyebrow">Sent</div>
              <h1 className="page-title !text-3xl mt-1">Check your inbox.</h1>
              <p className="page-subtitle mx-auto">
                We've sent a password reset link to{' '}
                <span className="text-ink font-medium">{email}</span>.
                The link will be valid for one hour.
              </p>
              <Link to="/login" className="btn-secondary mt-8 inline-flex">
                <ArrowLeft size={14} strokeWidth={2} />
                <span>Back to sign in</span>
              </Link>
            </div>
          ) : (
            <>
              <div className="mb-8">
                <div className="page-eyebrow">Reset</div>
                <h1 className="page-title !text-3xl">Forgot your password?</h1>
                <p className="page-subtitle">
                  Enter your email and we'll send you a secure link to set a new one.
                </p>
              </div>

              {error && (
                <div className="alert-error mb-6 animate-fade-in" role="alert">{error}</div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label htmlFor="email" className="field-label">Email</label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="field-input"
                    placeholder="advocate@chambers.in"
                    disabled={isLoading}
                    autoFocus
                    autoComplete="email"
                  />
                </div>

                <button type="submit" disabled={isLoading} className="btn-primary w-full py-3">
                  {isLoading ? (
                    <>
                      <span className="spinner !w-4 !h-4 !border-paper/40 !border-t-paper" />
                      <span>Sending…</span>
                    </>
                  ) : (
                    <span>Send reset link</span>
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
