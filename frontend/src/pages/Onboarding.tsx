import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import ImageUpload from '../components/ImageUpload';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';

export default function Onboarding() {
  const navigate = useNavigate();
  const { refreshProfile, isOnboarded, isLoading: isAuthLoading } = useAuth();

  useEffect(() => {
    if (!isAuthLoading && isOnboarded) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthLoading, isOnboarded, navigate]);

  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);

  const [formData, setFormData] = useState({
    firm_name: '',
    firm_address: '',
    firm_email: '',
    firm_phone: '',
    firm_phone_2: '',
    firm_website: '',
    bank_name: '',
    account_number: '',
    account_holder_name: '',
    ifsc_code: '',
    upi_id: '',
    billing_terms:
      'Payment due within 30 days of invoice date.\n' +
      'Late payments may incur additional charges.\n' +
      'All disputes subject to local jurisdiction.',
    default_template: 'LAW_001',
    invoice_prefix: 'LAW',
    default_tax_rate: 18.0,
    currency: 'INR',
    confirmSetup: false,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'default_tax_rate' ? parseFloat(value) || 0 : value,
    }));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLFormElement>) => {
    if (e.key === 'Enter') {
      const target = e.target as HTMLElement;
      if (target.tagName.toUpperCase() === 'INPUT') {
        e.preventDefault();
        e.stopPropagation();
        if (step < 2) {
          setIsNavigating(true);
          setTimeout(() => { nextStep(); setIsNavigating(false); }, 100);
          return;
        }
        const form = e.currentTarget;
        const focusable = Array.from(form.querySelectorAll(
          'input:not([disabled]), textarea:not([disabled]), select:not([disabled])'
        )) as HTMLElement[];
        const idx = focusable.indexOf(target);
        if (idx > -1 && idx < focusable.length - 1) focusable[idx + 1].focus();
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (isNavigating || step < 2) return;
    if (!formData.firm_name.trim()) return setError('Firm name is required');
    if (!formData.firm_address.trim()) return setError('Firm address is required');

    setIsLoading(true);
    try {
      await api.onboard(formData);
      try { await refreshProfile(); } catch (err) { console.error(err); }
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Onboarding failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const nextStep = () => {
    if (step === 1) {
      if (!formData.firm_name.trim()) return setError('Firm name is required');
      if (!formData.firm_address.trim()) return setError('Firm address is required');
    }
    setError('');
    setStep(step + 1);
  };

  const prevStep = () => { setError(''); setStep(step - 1); };

  return (
    <div className="min-h-screen bg-paper py-12 px-6">
      <div className="max-w-3xl mx-auto animate-fade-up">
        {/* Brand */}
        <div className="text-center mb-10">
          <span
            className="font-display text-4xl text-ink"
            style={{ fontVariationSettings: '"opsz" 144, "wght" 500, "SOFT" 30' }}
          >
            Snappy
          </span>
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-oxblood mb-1 ml-1.5" />
          <div className="eyebrow text-ink-faint mt-2">Establish your chambers</div>
        </div>

        {/* Step indicator */}
        <div className="mb-10 flex items-center justify-center gap-4">
          {[1, 2].map((n) => (
            <div key={n} className="flex items-center gap-3">
              <div className={[
                'flex items-center justify-center font-display text-sm transition-all duration-300',
                'w-9 h-9 rounded-full',
                step > n ? 'bg-oxblood text-paper' :
                step === n ? 'bg-ink text-paper' :
                             'bg-paper-deep text-ink-muted border border-rule',
              ].join(' ')} style={{ fontVariationSettings: '"opsz" 48, "wght" 500' }}>
                {step > n ? <Check size={14} strokeWidth={2.5} /> : n}
              </div>
              <span className={`text-sm font-medium ${step >= n ? 'text-ink' : 'text-ink-faint'}`}>
                {n === 1 ? 'Firm details' : 'Banking & branding'}
              </span>
              {n === 1 && <div className="w-12 h-px bg-rule mx-1" />}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="card p-10">
          {error && (
            <div className="alert-error mb-6 animate-fade-in" role="alert">{error}</div>
          )}

          <form onSubmit={handleSubmit} onKeyDown={handleKeyDown}>
            {step === 1 && (
              <div className="space-y-5">
                <div className="mb-2">
                  <div className="page-eyebrow">Step I</div>
                  <h2 className="section-title">Tell us about your firm</h2>
                </div>

                <div>
                  <label className="field-label">Firm name *</label>
                  <input
                    type="text"
                    name="firm_name"
                    required
                    value={formData.firm_name}
                    onChange={handleChange}
                    className="field-input"
                    placeholder="e.g., Sharma &amp; Associates"
                    autoFocus
                  />
                </div>

                <div>
                  <label className="field-label">Firm address *</label>
                  <textarea
                    name="firm_address"
                    required
                    value={formData.firm_address}
                    onChange={handleChange}
                    rows={3}
                    className="field-textarea"
                    placeholder="Street address, City, State, PIN code"
                  />
                </div>

                <div>
                  <label className="field-label">Email</label>
                  <input
                    type="email"
                    name="firm_email"
                    value={formData.firm_email}
                    onChange={handleChange}
                    className="field-input"
                    placeholder="contact@yourfirm.in"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Phone</label>
                    <input
                      type="tel"
                      name="firm_phone"
                      value={formData.firm_phone}
                      onChange={handleChange}
                      className="field-input font-mono"
                      placeholder="+91-XXXXXXXXXX"
                    />
                  </div>
                  <div>
                    <label className="field-label">Alternate phone</label>
                    <input
                      type="tel"
                      name="firm_phone_2"
                      value={formData.firm_phone_2}
                      onChange={handleChange}
                      className="field-input font-mono"
                      placeholder="+91-XXXXXXXXXX"
                    />
                  </div>
                </div>

                <div>
                  <label className="field-label">Website</label>
                  <input
                    type="url"
                    name="firm_website"
                    value={formData.firm_website}
                    onChange={handleChange}
                    className="field-input"
                    placeholder="https://www.yourfirm.in"
                  />
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-5">
                <div className="mb-2">
                  <div className="page-eyebrow">Step II</div>
                  <h2 className="section-title">Banking &amp; branding</h2>
                  <p className="text-sm text-ink-muted mt-2">
                    These appear on your invoices. You can skip and add them later in Settings.
                  </p>
                </div>

                <div>
                  <label className="field-label">Bank name</label>
                  <input
                    type="text" name="bank_name" value={formData.bank_name}
                    onChange={handleChange}
                    className="field-input"
                    placeholder="State Bank of India"
                  />
                </div>

                <div>
                  <label className="field-label">Account holder name</label>
                  <input
                    type="text" name="account_holder_name" value={formData.account_holder_name}
                    onChange={handleChange}
                    className="field-input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Account number</label>
                    <input
                      type="text" name="account_number" value={formData.account_number}
                      onChange={handleChange}
                      className="field-input font-mono"
                    />
                  </div>
                  <div>
                    <label className="field-label">IFSC code</label>
                    <input
                      type="text" name="ifsc_code" value={formData.ifsc_code}
                      onChange={handleChange}
                      className="field-input font-mono"
                      placeholder="SBIN0001234"
                    />
                  </div>
                </div>

                <div>
                  <label className="field-label">UPI ID</label>
                  <input
                    type="text" name="upi_id" value={formData.upi_id}
                    onChange={handleChange}
                    className="field-input font-mono"
                    placeholder="yourfirm@oksbi"
                  />
                </div>

                <div>
                  <label className="field-label">Billing terms &amp; conditions</label>
                  <textarea
                    name="billing_terms" value={formData.billing_terms}
                    onChange={handleChange}
                    rows={4}
                    className="field-textarea"
                  />
                </div>

                {/* Branding */}
                <div className="pt-6 border-t border-rule">
                  <div className="eyebrow mb-1">Branding</div>
                  <h3 className="section-title !text-xl">Logo, signature, UPI QR</h3>
                  <p className="text-sm text-ink-muted mt-2 mb-5">
                    Optional. These appear on the printed invoice.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <ImageUpload type="logo" label="Firm Logo" description="Top of invoice header" />
                    <ImageUpload type="signature" label="Signature" description="Above the signature line" />
                    <ImageUpload type="qr" label="UPI QR Code" description="In the payment section" />
                  </div>
                </div>

                {/* Confirmation */}
                <div className="pt-6 border-t border-rule">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      name="confirmSetup"
                      checked={formData.confirmSetup}
                      onChange={(e) => setFormData((p) => ({ ...p, confirmSetup: e.target.checked }))}
                      className="w-4 h-4 mt-0.5 accent-oxblood"
                      required
                    />
                    <span className="text-sm text-ink-soft">
                      I confirm the information above is correct and I'm ready to start invoicing.
                      <span className="text-oxblood ml-1">*</span>
                    </span>
                  </label>
                </div>
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between items-center mt-10 pt-6 border-t border-rule">
              <button
                type="button"
                onClick={prevStep}
                disabled={step === 1}
                className="btn-ghost disabled:!opacity-30"
              >
                <ArrowLeft size={14} strokeWidth={2} />
                <span>Previous</span>
              </button>

              {step < 2 ? (
                <button type="button" onClick={nextStep} className="btn-primary">
                  <span>Continue</span>
                  <ArrowRight size={14} strokeWidth={2} />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isLoading || !formData.confirmSetup}
                  className="btn-primary"
                >
                  {isLoading ? (
                    <>
                      <span className="spinner !w-4 !h-4 !border-paper/40 !border-t-paper" />
                      <span>Completing…</span>
                    </>
                  ) : (
                    <>
                      <span>Complete setup</span>
                      <Check size={14} strokeWidth={2} />
                    </>
                  )}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
