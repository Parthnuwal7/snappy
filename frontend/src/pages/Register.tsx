import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowRight } from 'lucide-react';

export default function Register() {
  const navigate = useNavigate();
  const { register, isAuthenticated, isOnboarded, isLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate(isOnboarded ? '/dashboard' : '/onboarding', { replace: true });
    }
  }, [isAuthenticated, isOnboarded, isLoading, navigate]);

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
    setIsSubmitting(true);
    try {
      await register(email, password);
      navigate('/onboarding');
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-5 bg-paper">
      <aside className="hidden lg:flex lg:col-span-2 bg-ink text-paper flex-col p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-[0.04] pointer-events-none"
             style={{
               backgroundImage:
                 'repeating-linear-gradient(to bottom, transparent 0, transparent 31px, #F8F4EC 31px, #F8F4EC 32px)',
             }}
        />

        <div className="relative z-10 flex items-baseline gap-2">
          <span
            className="font-display text-5xl text-paper"
            style={{ fontVariationSettings: '"opsz" 144, "wght" 500, "SOFT" 30' }}
          >
            Snappy
          </span>
          <span className="h-2 w-2 rounded-full bg-oxblood-soft translate-y-[-4px]" />
        </div>
        <div className="eyebrow text-paper/50 mt-1 relative z-10">Counsel's Ledger</div>

        <div className="flex-1 flex items-center relative z-10">
          <blockquote className="max-w-md">
            <div
              className="font-display text-4xl text-paper leading-tight text-balance"
              style={{ fontVariationSettings: '"opsz" 144, "wght" 400, "SOFT" 30' }}
            >
              <span className="text-oxblood-soft">“</span>
              Set up your chambers in minutes &mdash;{' '}
              <em
                className="not-italic"
                style={{ fontStyle: 'italic' }}
              >
                start invoicing the same afternoon.
              </em>
              <span className="text-oxblood-soft">”</span>
            </div>

            <div className="mt-6 flex items-center gap-3">
              <span className="h-px w-8 bg-paper/30" />
              <span className="eyebrow text-paper/50">Two steps · then your ledger</span>
            </div>
          </blockquote>
        </div>

        <div className="relative z-10 grid grid-cols-3 gap-6 text-2xs text-paper/50 tracking-eyebrow uppercase pt-6 border-t border-paper/10">
          <div>
            <div className="text-paper/80 font-display normal-case tracking-normal text-base">01</div>
            <div className="mt-1">Account</div>
          </div>
          <div>
            <div className="text-paper/80 font-display normal-case tracking-normal text-base">02</div>
            <div className="mt-1">Firm details</div>
          </div>
          <div>
            <div className="text-paper/80 font-display normal-case tracking-normal text-base">03</div>
            <div className="mt-1">First invoice</div>
          </div>
        </div>
      </aside>

      <section className="lg:col-span-3 flex items-center justify-center px-6 py-12 sm:px-12">
        <div className="w-full max-w-md animate-fade-up">
          <div className="lg:hidden mb-10 text-center">
            <span
              className="font-display text-4xl text-ink"
              style={{ fontVariationSettings: '"opsz" 144, "wght" 500, "SOFT" 30' }}
            >
              Snappy
            </span>
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-oxblood mb-1 ml-1.5" />
          </div>

          <div className="mb-8">
            <div className="page-eyebrow">Step I · Register</div>
            <h1 className="page-title">Open your ledger.</h1>
            <p className="page-subtitle">
              We'll create your account, then walk you through the firm profile.
            </p>
          </div>

          {error && (
            <div className="alert-error mb-6 animate-fade-in" role="alert">
              {error}
            </div>
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
                disabled={isSubmitting}
                autoComplete="email"
                autoFocus
              />
            </div>

            <div>
              <label htmlFor="password" className="field-label">Password</label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="field-input"
                placeholder="At least 6 characters"
                disabled={isSubmitting}
                autoComplete="new-password"
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="field-label">Confirm password</label>
              <input
                id="confirmPassword"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="field-input"
                placeholder="Re-enter password"
                disabled={isSubmitting}
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary w-full py-3 group mt-2"
            >
              {isSubmitting ? (
                <>
                  <span className="spinner !w-4 !h-4 !border-paper/40 !border-t-paper" />
                  <span>Creating account…</span>
                </>
              ) : (
                <>
                  <span>Create account</span>
                  <ArrowRight size={16} strokeWidth={2}
                              className="transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </form>

          <div className="mt-10 pt-6 border-t border-rule text-center">
            <p className="text-sm text-ink-muted">
              Already registered?{' '}
              <Link to="/login" className="btn-link">Sign in</Link>
            </p>
          </div>

          <div className="mt-12 text-2xs text-ink-faint tracking-eyebrow uppercase text-center">
            © 2026 Snappy · All matters confidential
          </div>
        </div>
      </section>
    </div>
  );
}
