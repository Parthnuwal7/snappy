import { useState, useEffect } from 'react';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Mail, 
  User, 
  Phone, 
  CreditCard,
  Calendar,
  AlertCircle,
  Send
} from 'lucide-react';
import { adminAPI } from '../api/client';

interface PendingLicense {
  id: number;
  license_key: string;
  plan: string;
  payment_method: string;
  upi_transaction_id: string;
  amount: number;
  status: string;
  admin_verified: boolean;
  email_sent: boolean;
  created_at: string;
  user_id: number;
  user_name: string;
  user_email: string;
  user_phone: string;
}

const AdminPaymentVerification = () => {
  const [pendingLicenses, setPendingLicenses] = useState<PendingLicense[]>([]);
  const [verifiedLicenses, setVerifiedLicenses] = useState<PendingLicense[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState<'pending' | 'verified'>('pending');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // Check if admin is authenticated
  useEffect(() => {
    const token = localStorage.getItem('snappy_admin_token');
    if (token) {
      setIsAuthenticated(true);
      fetchLicenses();
    }
  }, []);

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');
    
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';
      const response = await fetch(`${API_URL}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Login failed');
      }
      
      localStorage.setItem('snappy_admin_token', data.token);
      setIsAuthenticated(true);
      setPassword('');
      fetchLicenses();
    } catch (err: any) {
      setLoginError(err.message || 'Login failed. Please try again.');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('snappy_admin_token');
    setIsAuthenticated(false);
    setPassword('');
  };

  const fetchLicenses = async () => {
    try {
      setLoading(true);
      setError('');
      
      const [pendingRes, allRes] = await Promise.all([
        adminAPI.getPendingLicenses(),
        adminAPI.getAllLicenses()
      ]);
      
      setPendingLicenses(pendingRes.data.pendingLicenses || []);
      
      // Filter verified licenses that haven't sent emails yet
      const verified = allRes.data.licenses.filter(
        (l: any) => l.admin_verified && !l.email_sent
      );
      setVerifiedLicenses(verified);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load licenses');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyPayment = async (licenseId: number) => {
    if (!confirm('Are you sure you want to verify this payment?')) return;

    try {
      setProcessingId(licenseId);
      setError('');
      setSuccess('');

      await adminAPI.verifyPayment(licenseId, 'Payment verified by admin');
      setSuccess('Payment verified successfully! You can now send the license email.');
      
      // Refresh lists
      await fetchLicenses();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to verify payment');
    } finally {
      setProcessingId(null);
    }
  };

  const handleSendEmail = async (licenseId: number) => {
    if (!confirm('Send license key email to user? This will activate the license.')) return;

    try {
      setProcessingId(licenseId);
      setError('');
      setSuccess('');

      await adminAPI.sendLicenseEmail(licenseId);
      setSuccess('License email sent successfully and license activated!');
      
      // Refresh lists
      await fetchLicenses();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to send email');
    } finally {
      setProcessingId(null);
    }
  };

  const handleRejectPayment = async (licenseId: number) => {
    const reason = prompt('Enter reason for rejection (optional):');
    if (reason === null) return; // User cancelled

    try {
      setProcessingId(licenseId);
      setError('');
      setSuccess('');

      await adminAPI.rejectPayment(licenseId, reason || 'Invalid payment');
      setSuccess('Payment rejected successfully.');
      
      // Refresh lists
      await fetchLicenses();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to reject payment');
    } finally {
      setProcessingId(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatAmount = (paise: number) => {
    return `₹${(paise / 100).toFixed(2)}`;
  };

  // Admin Login Screen
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-blue-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Admin Panel</h1>
            <p className="text-gray-600">Payment Verification Dashboard</p>
          </div>

          <form onSubmit={handleAdminLogin} className="space-y-6">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Admin Password
              </label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter admin password"
                required
              />
            </div>

            {loginError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {loginError}
              </div>
            )}

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors duration-200 font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loginLoading ? 'Logging in...' : 'Access Admin Panel'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading payment verifications...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Payment Verification Admin Panel</h1>
            <p className="text-gray-600 mt-2">Verify UPI payments and send license keys</p>
          </div>
          <button
            onClick={handleLogout}
            className="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition-colors"
          >
            Logout
          </button>
        </div>

        {/* Success/Error Messages */}
        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start space-x-3">
            <CheckCircle className="text-green-600 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <p className="text-green-900 font-semibold">Success</p>
              <p className="text-green-700 text-sm">{success}</p>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-3">
            <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <p className="text-red-900 font-semibold">Error</p>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 border-b border-gray-200">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('pending')}
              className={`pb-4 px-1 border-b-2 font-medium transition-colors ${
                activeTab === 'pending'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Pending Verification ({pendingLicenses.length})
            </button>
            <button
              onClick={() => setActiveTab('verified')}
              className={`pb-4 px-1 border-b-2 font-medium transition-colors ${
                activeTab === 'verified'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Verified - Pending Email ({verifiedLicenses.length})
            </button>
          </div>
        </div>

        {/* Pending Payments Tab */}
        {activeTab === 'pending' && (
          <div className="space-y-4">
            {pendingLicenses.length === 0 ? (
              <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                <Clock className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Pending Payments</h3>
                <p className="text-gray-600">All payments have been verified!</p>
              </div>
            ) : (
              pendingLicenses.map((license) => (
                <div key={license.id} className="bg-white rounded-lg border border-gray-200 p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {license.plan.toUpperCase()} Plan - {formatAmount(license.amount)}
                      </h3>
                      <p className="text-sm text-gray-500">
                        Submitted: {formatDate(license.created_at)}
                      </p>
                    </div>
                    <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-medium">
                      Pending Verification
                    </span>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4 mb-6">
                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <User className="text-gray-400" size={18} />
                        <span className="text-sm text-gray-700">{license.user_name}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Mail className="text-gray-400" size={18} />
                        <span className="text-sm text-gray-700">{license.user_email}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Phone className="text-gray-400" size={18} />
                        <span className="text-sm text-gray-700">{license.user_phone}</span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <CreditCard className="text-gray-400" size={18} />
                        <span className="text-sm font-mono text-gray-700">{license.upi_transaction_id}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Calendar className="text-gray-400" size={18} />
                        <span className="text-sm text-gray-700">License Key: {license.license_key}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex space-x-3">
                    <button
                      onClick={() => handleVerifyPayment(license.id)}
                      disabled={processingId === license.id}
                      className="flex-1 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
                    >
                      <CheckCircle size={18} />
                      <span>{processingId === license.id ? 'Verifying...' : 'Verify Payment'}</span>
                    </button>
                    <button
                      onClick={() => handleRejectPayment(license.id)}
                      disabled={processingId === license.id}
                      className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
                    >
                      <XCircle size={18} />
                      <span>{processingId === license.id ? 'Rejecting...' : 'Reject Payment'}</span>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Verified - Pending Email Tab */}
        {activeTab === 'verified' && (
          <div className="space-y-4">
            {verifiedLicenses.length === 0 ? (
              <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                <Mail className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Verified Payments Pending Email</h3>
                <p className="text-gray-600">All verified payments have been emailed!</p>
              </div>
            ) : (
              verifiedLicenses.map((license) => (
                <div key={license.id} className="bg-white rounded-lg border border-green-200 p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {license.plan.toUpperCase()} Plan - {formatAmount(license.amount)}
                      </h3>
                      <p className="text-sm text-gray-500">
                        Verified, ready to send license email
                      </p>
                    </div>
                    <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium flex items-center space-x-1">
                      <CheckCircle size={16} />
                      <span>Verified</span>
                    </span>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4 mb-6">
                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <User className="text-gray-400" size={18} />
                        <span className="text-sm text-gray-700">{license.user_name}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Mail className="text-gray-400" size={18} />
                        <span className="text-sm text-gray-700">{license.user_email}</span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <Calendar className="text-gray-400" size={18} />
                        <span className="text-sm text-gray-700">License: {license.license_key}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <CreditCard className="text-gray-400" size={18} />
                        <span className="text-sm font-mono text-gray-700">{license.upi_transaction_id}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleSendEmail(license.id)}
                    disabled={processingId === license.id}
                    className="w-full bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2 font-semibold"
                  >
                    <Send size={18} />
                    <span>{processingId === license.id ? 'Sending Email...' : 'Send License Email & Activate'}</span>
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPaymentVerification;
