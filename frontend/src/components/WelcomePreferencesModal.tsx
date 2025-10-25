import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';

interface WelcomePreferencesModalProps {
  onClose: () => void;
}

export default function WelcomePreferencesModal({ onClose }: WelcomePreferencesModalProps) {
  const { firm, refreshUser } = useAuth();
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
      await refreshUser();
      setMessage({ type: 'success', text: 'Preferences saved successfully!' });
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to save preferences' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkip = () => {
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-indigo-600 mb-2">🎉 Welcome to SNAPPY!</h2>
          <p className="text-gray-600">
            Your account is set up! Let's configure your invoice preferences to get started.
          </p>
        </div>

        {message && (
          <div
            className={`mb-6 p-3 border rounded-md text-sm ${
              message.type === 'success'
                ? 'bg-green-50 border-green-200 text-green-700'
                : 'bg-red-50 border-red-200 text-red-700'
            }`}
          >
            {message.text}
          </div>
        )}

        <div className="space-y-6">
          {/* Invoice Template */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Invoice Template
            </label>
            <select
              value={preferencesData.default_template}
              onChange={(e) =>
                setPreferencesData({ ...preferencesData, default_template: e.target.value })
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="Simple">Simple - Minimalist template</option>
              <option value="LAW_001">LAW_001 - Professional template with branding</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Choose the default template for your invoices. You can change this anytime in Settings.
            </p>
          </div>

          {/* Invoice Prefix */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Invoice Number Prefix
            </label>
            <input
              type="text"
              value={preferencesData.invoice_prefix}
              onChange={(e) =>
                setPreferencesData({ ...preferencesData, invoice_prefix: e.target.value })
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="LAW / INV / etc."
            />
            <p className="text-xs text-gray-500 mt-1">
              This will be used as prefix for invoice numbers (e.g., LAW/2025/001)
            </p>
          </div>

          {/* Tax Rate and Currency */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="18.0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Currency</label>
              <select
                value={preferencesData.currency}
                onChange={(e) =>
                  setPreferencesData({ ...preferencesData, currency: e.target.value })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                <option value="INR">INR (₹)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>

          {/* Info Box */}
          <div className="bg-indigo-50 border border-indigo-200 rounded-md p-4">
            <p className="text-sm text-indigo-800">
              💡 <strong>Tip:</strong> You can always update these preferences later from the Settings page.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 mt-8 pt-6 border-t border-gray-200">
          <button
            onClick={handleSkip}
            disabled={isLoading}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Skip for Now
          </button>
          <button
            onClick={handleSave}
            disabled={isLoading}
            className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
    </div>
  );
}
