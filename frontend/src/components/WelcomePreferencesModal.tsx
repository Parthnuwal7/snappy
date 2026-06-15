import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import { Sparkles, X } from 'lucide-react';

interface WelcomePreferencesModalProps {
  onClose: () => void;
}

export default function WelcomePreferencesModal({ onClose }: WelcomePreferencesModalProps) {
  const { firm, refreshProfile } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [preferencesData, setPreferencesData] = useState({
    default_template: firm?.default_template || 'LAW_001',
    invoice_prefix: firm?.invoice_prefix || 'LAW',
    default_tax_rate: firm?.default_tax_rate || 18.0,
    currency: firm?.currency || 'INR',
  });

  const handleSave = async () => {
    setIsLoading(true);
    setMessage(null);
    try {
      await api.updateFirm(preferencesData);
      await refreshProfile();
      setMessage({ type: 'success', text: 'Preferences saved successfully.' });
      setTimeout(onClose, 900);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to save preferences' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={onClose} />

      <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-2xl w-full
                      max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
        {/* Sealed top edge */}
        <div className="h-[3px] bg-oxblood" />

        <div className="p-10">
          <button
            onClick={onClose}
            className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted transition-colors"
            aria-label="Close"
          >
            <X size={20} strokeWidth={1.5} />
          </button>

          <div className="mb-8">
            <div className="flex items-center gap-2 page-eyebrow">
              <Sparkles size={12} strokeWidth={2} />
              <span>Welcome</span>
            </div>
            <h2 className="page-title !text-3xl">Your invoicing preferences.</h2>
            <p className="page-subtitle">
              A few defaults to set the tone of your invoices. You can change all of these
              later from Settings.
            </p>
          </div>

          {message && (
            <div className={message.type === 'success' ? 'alert-success mb-6' : 'alert-error mb-6'}
                 role="alert">
              {message.text}
            </div>
          )}

          <div className="space-y-5">
            <div>
              <label className="field-label">Default invoice template</label>
              <select
                value={preferencesData.default_template}
                onChange={(e) => setPreferencesData({ ...preferencesData, default_template: e.target.value })}
                className="field-select"
              >
                <option value="Simple">Simple — minimalist template</option>
                <option value="LAW_001">LAW_001 — professional template with branding</option>
              </select>
              <p className="field-hint">Used for every new invoice unless overridden.</p>
            </div>

            <div>
              <label className="field-label">Invoice number prefix</label>
              <input
                type="text"
                value={preferencesData.invoice_prefix}
                onChange={(e) => setPreferencesData({ ...preferencesData, invoice_prefix: e.target.value })}
                className="field-input font-mono"
                placeholder="LAW"
              />
              <p className="field-hint">
                Example: <span className="font-mono">{preferencesData.invoice_prefix || 'INV'}/0001</span>
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="field-label">Default tax rate (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={preferencesData.default_tax_rate}
                  onChange={(e) => setPreferencesData({
                    ...preferencesData,
                    default_tax_rate: parseFloat(e.target.value) || 0,
                  })}
                  className="field-input font-mono tabular"
                />
              </div>
              <div>
                <label className="field-label">Currency</label>
                <select
                  value={preferencesData.currency}
                  onChange={(e) => setPreferencesData({ ...preferencesData, currency: e.target.value })}
                  className="field-select"
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>
            </div>

            <div className="alert-info">
              <span className="eyebrow text-ink-soft mr-2">Note ·</span>
              All of these preferences live in Settings → Preferences. Change them anytime.
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-10 pt-6 border-t border-rule">
            <button onClick={onClose} disabled={isLoading} className="btn-ghost">
              Skip for now
            </button>
            <button onClick={handleSave} disabled={isLoading} className="btn-primary">
              {isLoading ? 'Saving…' : 'Save preferences'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
