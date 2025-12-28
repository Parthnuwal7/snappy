import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import ImageUpload from '../components/ImageUpload';

export default function Settings() {
  const { firm, refreshProfile } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'account' | 'preferences'>('account');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Delete account modal
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');

  // Account form
  const [accountData, setAccountData] = useState({
    firm_name: '',
    firm_address: '',
    firm_email: '',
    firm_phone: '',
    firm_phone_2: '',
    firm_website: '',
  });

  // Preferences form
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
      // Refresh user data silently (don't throw on error)
      try {
        await refreshProfile();
      } catch (err) {
        console.error('Failed to refresh user data after save:', err);
        // Continue anyway - the save was successful
      }
      setMessage({ type: 'success', text: 'Account details updated successfully!' });
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
      // Refresh user data silently (don't throw on error)
      try {
        await refreshProfile();
      } catch (err) {
        console.error('Failed to refresh user data after save:', err);
        // Continue anyway - the save was successful
      }
      setMessage({ type: 'success', text: 'Preferences updated successfully!' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update preferences' });
    } finally {
      setIsLoading(false);
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
      // Clear localStorage flags
      localStorage.removeItem('hasSeenWelcome');
      // Account deleted, redirect to login
      navigate('/login');
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to delete account' });
      setIsLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">Manage your firm profile and preferences</p>
        {firm?.updated_at && (
          <p className="text-xs text-gray-500 mt-2">
            Last saved: {new Date(firm.updated_at).toLocaleString()}
          </p>
        )}
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('account')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'account'
              ? 'border-indigo-500 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            Account Details
          </button>
          <button
            onClick={() => setActiveTab('preferences')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'preferences'
              ? 'border-indigo-500 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            Preferences
          </button>
        </nav>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`mb-6 p-4 rounded-md ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
            }`}
        >
          {message.text}
        </div>
      )}


      {/* Account Details Tab */}
      {activeTab === 'account' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-6">Firm Details</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Firm Name *</label>
              <input
                type="text"
                value={accountData.firm_name}
                onChange={(e) => setAccountData({ ...accountData, firm_name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Firm Address *</label>
              <textarea
                value={accountData.firm_address}
                onChange={(e) => setAccountData({ ...accountData, firm_address: e.target.value })}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={accountData.firm_email}
                onChange={(e) => setAccountData({ ...accountData, firm_email: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input
                  type="tel"
                  value={accountData.firm_phone}
                  onChange={(e) => setAccountData({ ...accountData, firm_phone: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone 2</label>
                <input
                  type="tel"
                  value={accountData.firm_phone_2}
                  onChange={(e) => setAccountData({ ...accountData, firm_phone_2: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Website</label>
              <input
                type="url"
                value={accountData.firm_website}
                onChange={(e) => setAccountData({ ...accountData, firm_website: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="pt-4">
              <button
                onClick={handleAccountSave}
                disabled={isLoading}
                className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preferences Tab */}
      {activeTab === 'preferences' && (
        <div className="space-y-6">
          {/* Template Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Invoice Template</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Default Template</label>
              <select
                value={preferencesData.default_template}
                onChange={(e) =>
                  setPreferencesData({ ...preferencesData, default_template: e.target.value })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
              >
                <option value="Simple">Simple - Minimalist template</option>
                <option value="LAW_001">LAW_001 - Professional full-page template</option>
                <option value="HALF_PAGE">HALF_PAGE - Compact horizontal layout</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                {preferencesData.default_template === 'HALF_PAGE'
                  ? 'Compact template with logo, bank details, QR code, and signature'
                  : preferencesData.default_template === 'LAW_001'
                    ? 'Full-page professional template with firm branding'
                    : 'Clean and simple invoice template'}
              </p>
            </div>
          </div>

          {/* Invoice Settings */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Invoice Settings</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Invoice Prefix</label>
                <input
                  type="text"
                  value={preferencesData.invoice_prefix}
                  onChange={(e) =>
                    setPreferencesData({ ...preferencesData, invoice_prefix: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                  placeholder="LAW"
                  disabled={!preferencesData.use_invoice_prefix}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {preferencesData.use_invoice_prefix
                    ? `Example: ${preferencesData.invoice_prefix || 'INV'}/0001`
                    : 'Example: 0001'}
                </p>
              </div>

              {/* Use Prefix Toggle */}
              <div className="flex items-center justify-between py-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Use Invoice Prefix
                  </label>
                  <p className="text-xs text-gray-500">
                    Enable to add prefix before invoice numbers
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setPreferencesData({ ...preferencesData, use_invoice_prefix: !preferencesData.use_invoice_prefix })}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${preferencesData.use_invoice_prefix ? 'bg-indigo-600' : 'bg-gray-200'
                    }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${preferencesData.use_invoice_prefix ? 'translate-x-5' : 'translate-x-0'
                      }`}
                  />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Default Tax Rate (%)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={preferencesData.default_tax_rate}
                    onChange={(e) =>
                      setPreferencesData({
                        ...preferencesData,
                        default_tax_rate: parseFloat(e.target.value) || 0,
                      })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
                  <select
                    value={preferencesData.currency}
                    onChange={(e) => setPreferencesData({ ...preferencesData, currency: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="INR">INR (₹)</option>
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                  </select>
                </div>
              </div>

              {/* Due Date Toggle */}
              <div className="flex items-center justify-between py-4 border-t mt-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Show Due Date on Invoices
                  </label>
                  <p className="text-xs text-gray-500">
                    Enable to display due date field when creating invoices
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setPreferencesData({ ...preferencesData, show_due_date: !preferencesData.show_due_date })}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${preferencesData.show_due_date ? 'bg-indigo-600' : 'bg-gray-200'
                    }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${preferencesData.show_due_date ? 'translate-x-5' : 'translate-x-0'
                      }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* Banking Details */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Banking Details</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Bank Name</label>
                <input
                  type="text"
                  value={preferencesData.bank_name}
                  onChange={(e) => setPreferencesData({ ...preferencesData, bank_name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Account Holder Name</label>
                <input
                  type="text"
                  value={preferencesData.account_holder_name}
                  onChange={(e) =>
                    setPreferencesData({ ...preferencesData, account_holder_name: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Account Number</label>
                  <input
                    type="text"
                    value={preferencesData.account_number}
                    onChange={(e) =>
                      setPreferencesData({ ...preferencesData, account_number: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">IFSC Code</label>
                  <input
                    type="text"
                    value={preferencesData.ifsc_code}
                    onChange={(e) =>
                      setPreferencesData({ ...preferencesData, ifsc_code: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">UPI ID</label>
                <input
                  type="text"
                  value={preferencesData.upi_id}
                  onChange={(e) => setPreferencesData({ ...preferencesData, upi_id: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Billing Terms & Conditions
                </label>
                <textarea
                  value={preferencesData.billing_terms}
                  onChange={(e) =>
                    setPreferencesData({ ...preferencesData, billing_terms: e.target.value })
                  }
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Branding & Assets */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Branding & Assets</h2>
            <p className="text-sm text-gray-600 mb-4">
              Upload your firm logo, signature, and UPI QR code for invoices.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <ImageUpload
                type="logo"
                label="Firm Logo"
                description="Appears on invoice header"
              />

              <ImageUpload
                type="signature"
                label="Signature"
                description="Appears on invoice footer"
              />

              <ImageUpload
                type="qr"
                label="UPI QR Code"
                description="Payment QR code"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={handlePreferencesSave}
              disabled={isLoading}
              className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        </div>
      )}

      {/* Danger Zone - Delete Account */}
      <div className="mt-8 bg-white rounded-lg shadow-md p-6 border-2 border-red-200">
        <h2 className="text-xl font-semibold text-red-600 mb-4">Danger Zone</h2>
        <p className="text-sm text-gray-600 mb-4">
          Once you delete your account, there is no going back. Please be certain.
        </p>

        <button
          onClick={() => setShowDeleteModal(true)}
          className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
        >
          Delete Account
        </button>
      </div>

      {/* Delete Account Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
            <h3 className="text-2xl font-bold text-red-600 mb-4">Delete Account</h3>

            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800 font-semibold mb-2">⚠️ Warning: This action is permanent!</p>
              <ul className="text-sm text-red-700 space-y-1 list-disc list-inside">
                <li>All your invoices will be deleted</li>
                <li>All your clients will be deleted</li>
                <li>All your firm data will be deleted</li>
                <li>All analytics data will be lost</li>
                <li>This action cannot be undone</li>
              </ul>
            </div>

            <p className="text-sm text-gray-700 mb-4">
              Please type <strong className="font-mono bg-gray-100 px-2 py-1 rounded">confirm</strong> to delete your account:
            </p>

            <input
              type="text"
              value={deleteConfirmation}
              onChange={(e) => setDeleteConfirmation(e.target.value)}
              placeholder="Type 'confirm' here"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500 focus:border-transparent mb-4"
              autoFocus
            />

            {message && message.type === 'error' && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
                {message.text}
              </div>
            )}

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteConfirmation('');
                  setMessage(null);
                }}
                disabled={isLoading}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={isLoading || deleteConfirmation !== 'confirm'}
                className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Deleting...' : 'Delete My Account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
