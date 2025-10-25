import { useState } from 'react';
import { X, Copy, CheckCircle, AlertCircle, Upload } from 'lucide-react';
import { paymentAPI } from '../api/client';

interface UPIPaymentModalProps {
  plan: 'starter' | 'pro' | 'enterprise';
  onClose: () => void;
  onSuccess: () => void;
}

const UPIPaymentModal = ({ plan, onClose, onSuccess }: UPIPaymentModalProps) => {
  const [upiTransactionId, setUpiTransactionId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [paymentDetails, setPaymentDetails] = useState<any>(null);
  const [copiedUPI, setCopiedUPI] = useState(false);

  // Fetch UPI details on mount
  useState(() => {
    const fetchUPIDetails = async () => {
      try {
        const response = await paymentAPI.getUPIDetails(plan);
        setPaymentDetails(response.data);
      } catch (err: any) {
        setError(err.response?.data?.error || 'Failed to load payment details');
      }
    };
    fetchUPIDetails();
  });

  const handleCopyUPI = () => {
    if (paymentDetails?.upiId) {
      navigator.clipboard.writeText(paymentDetails.upiId);
      setCopiedUPI(true);
      setTimeout(() => setCopiedUPI(false), 2000);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!upiTransactionId.trim()) {
      setError('Please enter your UPI Transaction ID');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await paymentAPI.submitUPIPayment(plan, upiTransactionId.trim());
      setSuccess(true);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 3000);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to submit payment. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!paymentDetails) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg p-6 max-w-md w-full">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading payment details...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-lg max-w-2xl w-full my-8">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Complete Payment</h2>
            <p className="text-sm text-gray-600 mt-1">
              {plan.charAt(0).toUpperCase() + plan.slice(1)} Plan - ₹{paymentDetails.amount}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Success Message */}
        {success && (
          <div className="m-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start space-x-3">
            <CheckCircle className="text-green-600 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-green-900">Payment Submitted!</h3>
              <p className="text-sm text-green-700 mt-1">
                Your payment has been submitted for verification. You will receive your license key via email within 24 hours after admin approval.
              </p>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="m-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
            <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-red-900">Error</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        <div className="p-6 space-y-6">
          {/* Payment Instructions */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">Payment Instructions</h3>
            <ol className="space-y-2 text-sm text-blue-800">
              {paymentDetails.instructions.map((instruction: string, index: number) => (
                <li key={index} className="flex items-start">
                  <span className="font-bold mr-2">{index + 1}.</span>
                  <span>{instruction}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* QR Code Section */}
          <div className="border rounded-lg p-6 text-center">
            <h3 className="font-semibold text-gray-900 mb-4">Scan QR Code to Pay</h3>
            <div className="bg-gray-100 p-4 rounded-lg inline-block">
              <img
                src={paymentDetails.qrCodeUrl}
                alt={`UPI QR Code for ${plan} plan`}
                className="w-64 h-64 mx-auto"
                onError={(e) => {
                  // Fallback if QR code image not found
                  (e.target as HTMLImageElement).style.display = 'none';
                  (e.target as HTMLImageElement).parentElement!.innerHTML = `
                    <div class="w-64 h-64 flex items-center justify-center bg-gray-200 text-gray-600">
                      <div class="text-center">
                        <p class="font-semibold">QR Code Not Available</p>
                        <p class="text-sm mt-2">Please use UPI ID below</p>
                      </div>
                    </div>
                  `;
                }}
              />
            </div>
            
            {/* UPI ID */}
            <div className="mt-4">
              <p className="text-sm text-gray-600 mb-2">Or pay directly to UPI ID:</p>
              <div className="flex items-center justify-center space-x-2">
                <code className="bg-gray-100 px-4 py-2 rounded text-lg font-mono">
                  {paymentDetails.upiId}
                </code>
                <button
                  onClick={handleCopyUPI}
                  className="p-2 hover:bg-gray-100 rounded transition-colors"
                  title="Copy UPI ID"
                >
                  {copiedUPI ? (
                    <CheckCircle className="text-green-600" size={20} />
                  ) : (
                    <Copy className="text-gray-600" size={20} />
                  )}
                </button>
              </div>
            </div>

            {/* Amount */}
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">Amount to Pay</p>
              <p className="text-3xl font-bold text-blue-600">₹{paymentDetails.amount}</p>
            </div>
          </div>

          {/* Transaction ID Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="transactionId" className="block text-sm font-medium text-gray-700 mb-2">
                UPI Transaction ID / UTR Number *
              </label>
              <input
                type="text"
                id="transactionId"
                value={upiTransactionId}
                onChange={(e) => setUpiTransactionId(e.target.value)}
                placeholder="Enter 12-digit transaction ID (e.g., 123456789012)"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading || success}
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                You can find this in your UPI app's transaction history
              </p>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || success}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Submitting...</span>
                </>
              ) : success ? (
                <>
                  <CheckCircle size={20} />
                  <span>Submitted Successfully</span>
                </>
              ) : (
                <>
                  <Upload size={20} />
                  <span>Submit for Verification</span>
                </>
              )}
            </button>
          </form>

          {/* Help Text */}
          <div className="text-center text-sm text-gray-600">
            <p>Need help? Contact support at <a href="mailto:support@snappy.com" className="text-blue-600 hover:underline">support@snappy.com</a></p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UPIPaymentModal;
