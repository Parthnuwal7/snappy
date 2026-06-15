import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import ImageUpload from '../components/ImageUpload';
import { Download, Trash2, X } from 'lucide-react';

type Tab = 'account' | 'preferences';

export default function Settings() {
  const { firm, refreshProfile } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('account');
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');

  const [accountData, setAccountData] = useState({
    firm_name: '',
    firm_address: '',
    firm_email: '',
    firm_phone: '',
    firm_phone_2: '',
    firm_website: '',
  });

  const [preferencesData, setPreferencesData] = useState({
    bank_name: '',
    account_number: '',
    account_holder_name: '',
    ifsc_code: '',
    upi_id: '',
    billing_terms: '',
    default_template: 'Simple',
    invoice_prefix: '',
    use_invoice_prefix: true,
    default_tax_rate: 18.0,
    currency: 'INR',
    show_due_date: true,
  });

  useEffect(() => {
    if (firm) {
      setAccountData({
        firm_name: firm.firm_name || '',
        firm_address: firm.firm_address || '',
        firm_email: firm.firm_email || '',
        firm_phone: firm.firm_phone || '',
        firm_phone_2: firm.firm_phone_2 || '',
        firm_website: firm.firm_website || '',
      });

      setPreferencesData({
        bank_name: firm.bank_name || '',
        account_number: firm.account_number || '',
        account_holder_name: firm.account_holder_name || '',
        ifsc_code: firm.ifsc_code || '',
        upi_id: firm.upi_id || '',
        billing_terms: firm.billing_terms || '',
        default_template: firm.default_template || 'Simple',
        invoice_prefix: firm.invoice_prefix || '',
        use_invoice_prefix: firm.use_invoice_prefix ?? true,
        default_tax_rate: firm.default_tax_rate ?? 18.0,
        currency: firm.currency || 'INR',
        show_due_date: firm.show_due_date ?? true,
      });
    }
  }, [firm]);

  const handleAccountSave = async () => {
    setIsLoading(true);
    setMessage(null);
    try {
      await api.updateFirm(accountData);
      try { await refreshProfile(); } catch (err) { console.error(err); }
      setMessage({ type: 'success', text: 'Account details updated.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update account details' });
    } finally {
      setIsLoading(false);
    }
  };

  const handlePreferencesSave = async () => {
    setIsLoading(true);
    setMessage(null);
    try {
      await api.updateFirm(preferencesData);
      try { await refreshProfile(); } catch (err) { console.error(err); }
      setMessage({ type: 'success', text: 'Preferences updated.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update preferences' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportData = async () => {
    setIsExporting(true);
    setMessage(null);
    try {
      await api.exportData();
      setMessage({ type: 'success', text: 'Backup downloaded. Keep it somewhere safe.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to export data' });
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== 'confirm') {
      setMessage({ type: 'error', text: 'Please type "confirm" to delete your account' });
      return;
    }
    setIsLoading(true);
    setMessage(null);
    try {
      await api.deleteAccount(deleteConfirmation);
      localStorage.removeItem('hasSeenWelcome');
      navigate('/login');
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to delete account' });
      setIsLoading(false);
    }
  };

  const Toggle = ({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) => (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={[
        'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border transition-colors duration-150',
        value ? 'bg-oxblood border-oxblood' : 'bg-paper-deep border-rule-strong',
      ].join(' ')}
    >
      <span
        className={[
          'pointer-events-none inline-block h-3.5 w-3.5 transform rounded-full bg-paper shadow-sm transition-transform duration-150',
          value ? 'translate-x-4' : 'translate-x-0.5',
        ].join(' ')}
        style={{ marginTop: '1px' }}
      />
    </button>
  );

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10 max-w-4xl">
      {/* Header */}
      <header className="mb-10">
        <div className="page-eyebrow">Folio VI · Chambers</div>
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Firm profile, banking, preferences, and account.</p>
        {firm?.updated_at && (
          <p className="text-xs text-ink-faint mt-2 uppercase tracking-eyebrow">
            Last saved · <span className="font-mono normal-case tracking-normal">
              {new Date(firm.updated_at).toLocaleString('en-IN')}
            </span>
          </p>
        )}
      </header>

      {/* Tabs */}
      <div className="border-b border-rule mb-8">
        <nav className="flex gap-8 -mb-px">
          {(['account', 'preferences'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={[
                'py-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab
                  ? 'border-oxblood text-ink'
                  : 'border-transparent text-ink-muted hover:text-ink',
              ].join(' ')}
            >
              {tab === 'account' ? 'Account details' : 'Preferences'}
            </button>
          ))}
        </nav>
      </div>

      {/* Message */}
      {message && (
        <div className={message.type === 'success' ? 'alert-success mb-6' : 'alert-error mb-6'}>
          {message.text}
        </div>
      )}

      {/* Account tab */}
      {activeTab === 'account' && (
        <div className="card p-8 space-y-5">
          <div className="mb-2">
            <div className="page-eyebrow">Firm details</div>
            <h2 className="section-title mt-1">Identifying information</h2>
          </div>

          <div>
            <label className="field-label">Firm name *</label>
            <input
              type="text"
              value={accountData.firm_name}
              onChange={(e) => setAccountData({ ...accountData, firm_name: e.target.value })}
              className="field-input"
            />
          </div>

          <div>
            <label className="field-label">Firm address *</label>
            <textarea
              value={accountData.firm_address}
              onChange={(e) => setAccountData({ ...accountData, firm_address: e.target.value })}
              rows={3}
              className="field-textarea"
            />
          </div>

          <div>
            <label className="field-label">Email</label>
            <input
              type="email"
              value={accountData.firm_email}
              onChange={(e) => setAccountData({ ...accountData, firm_email: e.target.value })}
              className="field-input"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="field-label">Phone</label>
              <input
                type="tel"
                value={accountData.firm_phone}
                onChange={(e) => setAccountData({ ...accountData, firm_phone: e.target.value })}
                className="field-input font-mono"
              />
            </div>
            <div>
              <label className="field-label">Alternate phone</label>
              <input
                type="tel"
                value={accountData.firm_phone_2}
                onChange={(e) => setAccountData({ ...accountData, firm_phone_2: e.target.value })}
                className="field-input font-mono"
              />
            </div>
          </div>

          <div>
            <label className="field-label">Website</label>
            <input
              type="url"
              value={accountData.firm_website}
              onChange={(e) => setAccountData({ ...accountData, firm_website: e.target.value })}
              className="field-input"
            />
          </div>

          <div className="pt-4 border-t border-rule flex justify-end">
            <button onClick={handleAccountSave} disabled={isLoading} className="btn-primary">
              {isLoading ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </div>
      )}

      {/* Preferences tab */}
      {activeTab === 'preferences' && (
        <div className="space-y-6">
          {/* Templates + Invoice settings */}
          <div className="card p-8 space-y-5">
            <div className="mb-2">
              <div className="page-eyebrow">Invoicing</div>
              <h2 className="section-title mt-1">Template and numbering</h2>
            </div>

            <div>
              <label className="field-label">Default template</label>
              <select
                value={preferencesData.default_template}
                onChange={(e) => setPreferencesData({ ...preferencesData, default_template: e.target.value })}
                className="field-select"
              >
                <option value="Simple">Simple — Minimalist</option>
                <option value="LAW_001">LAW_001 — Professional, full-page</option>
                <option value="HALF_PAGE">HALF_PAGE — Compact horizontal</option>
              </select>
              <p className="field-hint">
                {preferencesData.default_template === 'HALF_PAGE'
                  ? 'Compact template with logo, bank details, QR code, and signature.'
                  : preferencesData.default_template === 'LAW_001'
                    ? 'Full-page professional template with firm branding.'
                    : 'Clean and simple invoice template.'}
              </p>
            </div>

            <div>
              <label className="field-label">Invoice prefix</label>
              <input
                type="text"
                value={preferencesData.invoice_prefix}
                onChange={(e) => setPreferencesData({ ...preferencesData, invoice_prefix: e.target.value })}
                className="field-input font-mono"
                placeholder="LAW"
                disabled={!preferencesData.use_invoice_prefix}
              />
              <p className="field-hint">
                Example: <span className="font-mono">
                  {preferencesData.use_invoice_prefix
                    ? `${preferencesData.invoice_prefix || 'INV'}/0001`
                    : '0001'}
                </span>
              </p>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div>
                <div className="text-sm text-ink font-medium">Use invoice prefix</div>
                <div className="text-xs text-ink-muted mt-0.5">Add prefix before invoice numbers</div>
              </div>
              <Toggle
                value={preferencesData.use_invoice_prefix}
                onChange={(v) => setPreferencesData({ ...preferencesData, use_invoice_prefix: v })}
              />
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

            <div className="flex items-center justify-between pt-2 border-t border-rule-soft mt-4">
              <div>
                <div className="text-sm text-ink font-medium">Show due date on invoices</div>
                <div className="text-xs text-ink-muted mt-0.5">Adds a "Due Date" field on creation</div>
              </div>
              <Toggle
                value={preferencesData.show_due_date}
                onChange={(v) => setPreferencesData({ ...preferencesData, show_due_date: v })}
              />
            </div>
          </div>

          {/* Banking */}
          <div className="card p-8 space-y-5">
            <div className="mb-2">
              <div className="page-eyebrow">Payment</div>
              <h2 className="section-title mt-1">Banking details</h2>
            </div>

            <div>
              <label className="field-label">Bank name</label>
              <input
                type="text"
                value={preferencesData.bank_name}
                onChange={(e) => setPreferencesData({ ...preferencesData, bank_name: e.target.value })}
                className="field-input"
              />
            </div>

            <div>
              <label className="field-label">Account holder name</label>
              <input
                type="text"
                value={preferencesData.account_holder_name}
                onChange={(e) => setPreferencesData({ ...preferencesData, account_holder_name: e.target.value })}
                className="field-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="field-label">Account number</label>
                <input
                  type="text"
                  value={preferencesData.account_number}
                  onChange={(e) => setPreferencesData({ ...preferencesData, account_number: e.target.value })}
                  className="field-input font-mono"
                />
              </div>
              <div>
                <label className="field-label">IFSC code</label>
                <input
                  type="text"
                  value={preferencesData.ifsc_code}
                  onChange={(e) => setPreferencesData({ ...preferencesData, ifsc_code: e.target.value })}
                  className="field-input font-mono"
                />
              </div>
            </div>

            <div>
              <label className="field-label">UPI ID</label>
              <input
                type="text"
                value={preferencesData.upi_id}
                onChange={(e) => setPreferencesData({ ...preferencesData, upi_id: e.target.value })}
                className="field-input font-mono"
              />
            </div>

            <div>
              <label className="field-label">Billing terms &amp; conditions</label>
              <textarea
                value={preferencesData.billing_terms}
                onChange={(e) => setPreferencesData({ ...preferencesData, billing_terms: e.target.value })}
                rows={4}
                className="field-textarea"
              />
            </div>
          </div>

          {/* Branding */}
          <div className="card p-8">
            <div className="mb-5">
              <div className="page-eyebrow">Branding</div>
              <h2 className="section-title mt-1">Logo, signature, UPI QR</h2>
              <p className="text-sm text-ink-muted mt-2 max-w-prose">
                These appear on the printed invoice.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <ImageUpload type="logo" label="Firm Logo" description="Top of invoice header" />
              <ImageUpload type="signature" label="Signature" description="Above signature line" />
              <ImageUpload type="qr" label="UPI QR Code" description="In payment section" />
            </div>
          </div>

          <div className="flex justify-end">
            <button onClick={handlePreferencesSave} disabled={isLoading} className="btn-primary">
              {isLoading ? 'Saving…' : 'Save preferences'}
            </button>
          </div>
        </div>
      )}

      {/* Data Export */}
      <div className="card p-8 mt-8">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="page-eyebrow">Export</div>
            <h2 className="section-title mt-1">Your data, in a single archive</h2>
            <p className="text-sm text-ink-muted mt-2 max-w-prose">
              Download a complete backup of your account as a ZIP archive — firm profile, banking,
              clients, items, invoices (with line items), settings, and uploaded images. Keep the
              file somewhere safe; it contains business and banking information.
            </p>
          </div>
          <button onClick={handleExportData} disabled={isExporting} className="btn-secondary shrink-0">
            <Download size={14} strokeWidth={2} />
            <span>{isExporting ? 'Preparing…' : 'Download full backup'}</span>
          </button>
        </div>
      </div>

      {/* Danger zone */}
      <div className="card border-oxblood/30 p-8 mt-8">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="eyebrow text-oxblood">Danger</div>
            <h2 className="section-title mt-1 text-oxblood">Delete account</h2>
            <p className="text-sm text-ink-muted mt-2 max-w-prose">
              Permanently delete your firm, clients, items, invoices, and all uploaded images.
              This cannot be undone. Take a backup first.
            </p>
          </div>
          <button onClick={() => setShowDeleteModal(true)}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2
                             bg-oxblood text-paper text-sm font-medium rounded-DEFAULT
                             hover:bg-oxblood-deep transition-colors shrink-0">
            <Trash2 size={14} strokeWidth={2} />
            <span>Delete account</span>
          </button>
        </div>
      </div>

      {/* Delete modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]"
               onClick={() => { setShowDeleteModal(false); setDeleteConfirmation(''); setMessage(null); }} />

          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-md w-full
                          shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />

            <div className="p-8">
              <button
                onClick={() => { setShowDeleteModal(false); setDeleteConfirmation(''); setMessage(null); }}
                className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted transition-colors"
                aria-label="Close"
              >
                <X size={20} strokeWidth={1.5} />
              </button>

              <div className="eyebrow text-oxblood">Irreversible</div>
              <h3 className="page-title !text-2xl">Delete this account?</h3>

              <div className="alert-error mt-6">
                <div className="font-medium mb-2">This will permanently destroy:</div>
                <ul className="text-xs space-y-1 list-disc list-inside text-oxblood-deep/90">
                  <li>All invoices and their line items</li>
                  <li>All clients</li>
                  <li>All items in your catalog</li>
                  <li>Firm profile and banking</li>
                  <li>All uploaded images (logo, signature, UPI QR)</li>
                </ul>
              </div>

              <p className="text-sm text-ink-soft mt-6">
                Type <span className="font-mono bg-paper-deep px-1.5 py-0.5 border border-rule rounded-sm">confirm</span> below
                to proceed.
              </p>

              <input
                type="text"
                value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)}
                className="field-input mt-3 font-mono"
                placeholder="confirm"
                autoFocus
              />

              {message && message.type === 'error' && (
                <div className="alert-error mt-4">{message.text}</div>
              )}

              <div className="flex justify-end gap-3 mt-6 pt-6 border-t border-rule">
                <button
                  onClick={() => { setShowDeleteModal(false); setDeleteConfirmation(''); setMessage(null); }}
                  disabled={isLoading}
                  className="btn-ghost"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteAccount}
                  disabled={isLoading || deleteConfirmation !== 'confirm'}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2
                             bg-oxblood text-paper text-sm font-medium rounded-DEFAULT
                             hover:bg-oxblood-deep disabled:opacity-40 transition-colors"
                >
                  {isLoading ? 'Deleting…' : 'Delete my account'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
