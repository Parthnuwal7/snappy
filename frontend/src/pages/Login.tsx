import { useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowRight } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Honor a post-login destination (e.g. an invite-accept link). Only allow
  // same-app relative paths so this can't be used as an open redirect.
  const redirectRaw = searchParams.get('redirect') || '/';
  const redirectTo = redirectRaw.startsWith('/') && !redirectRaw.startsWith('//')
    ? redirectRaw
    : '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(email, password);
      navigate(redirectTo);
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-5 bg-paper">
      {/* ---- Left: Brand panel (lg+) ---------------------------------- */}
      <aside className="hidden lg:flex lg:col-span-2 bg-ink text-paper flex-col p-12 relative overflow-hidden">
        {/* Decorative ruled paper overlay, very faint */}
        <div className="absolute inset-0 opacity-[0.04] pointer-events-none"
             style={{
               backgroundImage:
                 'repeating-linear-gradient(to bottom, transparent 0, transparent 31px, #F8F4EC 31px, #F8F4EC 32px)',
             }}
        />

        {/* Top — wordmark */}
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

        {/* Middle — pull quote / value prop */}
        <div className="flex-1 flex items-center relative z-10">
          <blockquote className="max-w-md">
            <div
              className="font-display text-4xl text-paper leading-tight text-balance"
              style={{ fontVariationSettings: '"opsz" 144, "wght" 400, "SOFT" 30' }}
            >
              <span className="text-oxblood-soft">“</span>
              Invoicing built for the practice of law &mdash;{' '}
              <em
                className="not-italic"
                style={{ fontVariationSettings: '"opsz" 144, "wght" 400, "SOFT" 30', fontStyle: 'italic' }}
              >
                briefs, hearings, and the bench.
              </em>
              <span className="text-oxblood-soft">”</span>
            </div>

            <div className="mt-6 flex items-center gap-3">
              <span className="h-px w-8 bg-paper/30" />
              <span className="eyebrow text-paper/50">
                For solo & small firms · India
              </span>
            </div>
          </blockquote>
        </div>

        {/* Bottom — colophon */}
        <div className="relative z-10 grid grid-cols-3 gap-6 text-2xs text-paper/50 tracking-eyebrow uppercase pt-6 border-t border-paper/10">
          <div>
            <div className="text-paper/80 font-mono normal-case tracking-normal text-sm">GST · HSN</div>
            <div className="mt-1">Tax-ready</div>
          </div>
          <div>
            <div className="text-paper/80 font-mono normal-case tracking-normal text-sm">PDF</div>
            <div className="mt-1">Custom templates</div>
          </div>
          <div>
            <div className="text-paper/80 font-mono normal-case tracking-normal text-sm">₹ INR</div>
            <div className="mt-1">Indian numbering</div>
          </div>
        </div>
      </aside>

      {/* ---- Right: Form panel ---------------------------------------- */}
      <section className="lg:col-span-3 flex items-center justify-center px-6 py-12 sm:px-12">
        <div className="w-full max-w-md animate-fade-up">
          {/* Mobile wordmark (lg- only) */}
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
            <div className="page-eyebrow">No. I · Sign in</div>
            <h1 className="page-title">Welcome back, Counsel.</h1>
            <p className="page-subtitle">
              Pick up where you left off — your ledger, your clients, your invoices.
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
                disabled={isLoading}
                autoComplete="email"
                autoFocus
              />
            </div>

            <div>
              <div className="flex items-baseline justify-between mb-1.5">
                <label htmlFor="password" className="field-label !mb-0">Password</label>
                <Link to="/forgot-password" className="text-xs text-ink-muted hover:text-oxblood transition-colors">
                  Forgot it?
                </Link>
              </div>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="field-input"
                placeholder="••••••••••••"
                disabled={isLoading}
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-3 group"
            >
              {isLoading ? (
                <>
                  <span className="spinner !w-4 !h-4 !border-paper/40 !border-t-paper" />
                  <span>Signing in…</span>
                </>
              ) : (
                <>
                  <span>Sign in</span>
                  <ArrowRight size={16} strokeWidth={2}
                              className="transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </form>

          {/* Divider with register link */}
          <div className="mt-10 pt-6 border-t border-rule text-center">
            <p className="text-sm text-ink-muted">
              New to Snappy?{' '}
              <Link to="/register" className="btn-link">
                Register your firm
              </Link>
            </p>
          </div>

          {/* Footer */}
          <div className="mt-12 text-2xs text-ink-faint tracking-eyebrow uppercase text-center">
            © 2026 Snappy · All matters confidential
          </div>
        </div>
      </section>
    </div>
  );
}
