import { useState, useEffect } from 'react';
import { 
  Key, 
  Trash2, 
  Search,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

interface License {
  id: number;
  license_key: string;
  plan: string;
  status: string;
  admin_verified: boolean;
  user_email: string;
  user_name: string;
  amount: number;
  created_at: string;
  invoked_at: string | null;
  expires_at: string | null;
  upi_transaction_id: string;
}

const AdminLicenseManager = () => {
  const [licenses, setLicenses] = useState<License[]>([]);
  const [filteredLicenses, setFilteredLicenses] = useState<License[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('snappy_admin_token');
    if (token) {
      setIsAuthenticated(true);
      fetchAllLicenses();
    }
  }, []);

  useEffect(() => {
    filterLicenses();
  }, [searchTerm, filterStatus, licenses]);

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');
    
    try {
      const response = await axios.post(`${API_URL}/admin/login`, { password });
      
      if (response.data.success) {
        localStorage.setItem('snappy_admin_token', response.data.token);
        setIsAuthenticated(true);
        setPassword('');
        fetchAllLicenses();
      }
    } catch (err: any) {
      setLoginError(err.response?.data?.error || 'Login failed. Please try again.');
    } finally {
      setLoginLoading(false);
    }
  };

  const fetchAllLicenses = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('snappy_admin_token');
      const response = await axios.get(`${API_URL}/admin/all-licenses`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setLicenses(response.data.licenses || []);
    } catch (error) {
      console.error('Failed to fetch licenses:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterLicenses = () => {
    let filtered = licenses;

    // Filter by status
    if (filterStatus !== 'all') {
      filtered = filtered.filter(l => {
        if (filterStatus === 'pending') return !l.admin_verified;
        if (filterStatus === 'verified') return l.admin_verified;
        if (filterStatus === 'active') return l.status === 'active';
        if (filterStatus === 'rejected') return l.status === 'rejected';
        return true;
      });
    }

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(l =>
        l.license_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
        l.user_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        l.user_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        l.upi_transaction_id?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    setFilteredLicenses(filtered);
  };

  const handleDeleteLicense = async (licenseId: number) => {
    const token = localStorage.getItem('snappy_admin_token');
    
    try {
      await axios.delete(`${API_URL}/admin/delete-license/${licenseId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Remove from state
      setLicenses(licenses.filter(l => l.id !== licenseId));
      setDeleteConfirm(null);
    } catch (error: any) {
      alert(error.response?.data?.error || 'Failed to delete license');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('snappy_admin_token');
    setIsAuthenticated(false);
    setPassword('');
  };

  const getStatusBadge = (license: License) => {
    if (license.status === 'active') {
      return (
        <span className="flex items-center px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
          <CheckCircle size={12} className="mr-1" />
          Active
        </span>
      );
    }
    if (license.status === 'rejected') {
      return (
        <span className="flex items-center px-2 py-1 bg-red-100 text-red-800 rounded text-xs">
          <XCircle size={12} className="mr-1" />
          Rejected
        </span>
      );
    }
    if (!license.admin_verified) {
      return (
        <span className="flex items-center px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
          <Clock size={12} className="mr-1" />
          Pending
        </span>
      );
    }
    return (
      <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
        Verified
      </span>
    );
  };

  // Admin Login Screen
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Key className="w-8 h-8 text-blue-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">License Manager</h1>
            <p className="text-gray-600">View and manage all license keys</p>
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
              {loginLoading ? 'Logging in...' : 'Access License Manager'}
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
          <p className="text-gray-600">Loading licenses...</p>
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
            <h1 className="text-3xl font-bold text-gray-900">License Manager</h1>
            <p className="text-gray-600 mt-2">View, monitor, and delete license keys</p>
          </div>
          <button
            onClick={handleLogout}
            className="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 transition-colors"
          >
            Logout
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Licenses</p>
                <p className="text-3xl font-bold text-gray-900">{licenses.length}</p>
              </div>
              <Key className="w-10 h-10 text-blue-500" />
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Pending</p>
                <p className="text-3xl font-bold text-yellow-600">
                  {licenses.filter(l => !l.admin_verified).length}
                </p>
              </div>
              <Clock className="w-10 h-10 text-yellow-500" />
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active</p>
                <p className="text-3xl font-bold text-green-600">
                  {licenses.filter(l => l.status === 'active').length}
                </p>
              </div>
              <CheckCircle className="w-10 h-10 text-green-500" />
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Rejected</p>
                <p className="text-3xl font-bold text-red-600">
                  {licenses.filter(l => l.status === 'rejected').length}
                </p>
              </div>
              <XCircle className="w-10 h-10 text-red-500" />
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-3 text-gray-400" size={20} />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search by key, email, name, or UPI ID..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by Status
              </label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Licenses</option>
                <option value="pending">Pending Verification</option>
                <option value="verified">Verified</option>
                <option value="active">Active</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>
        </div>

        {/* Licenses Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">License Key</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredLicenses.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                      <AlertCircle className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                      <p>No licenses found</p>
                    </td>
                  </tr>
                ) : (
                  filteredLicenses.map((license) => (
                    <tr key={license.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <code className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                          {license.license_key}
                        </code>
                      </td>
                      <td className="px-6 py-4">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{license.user_name}</p>
                          <p className="text-xs text-gray-500">{license.user_email}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm font-semibold text-gray-900 uppercase">
                          {license.plan}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {getStatusBadge(license)}
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm font-semibold text-gray-900">
                          ₹{(license.amount / 100).toFixed(2)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {new Date(license.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        {deleteConfirm === license.id ? (
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => handleDeleteLicense(license.id)}
                              className="px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="px-3 py-1 bg-gray-300 text-gray-700 rounded text-xs hover:bg-gray-400"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(license.id)}
                            className="flex items-center px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                            title="Delete license"
                          >
                            <Trash2 size={14} className="mr-1" />
                            <span className="text-xs">Delete</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start">
            <AlertCircle className="text-yellow-600 mr-3 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <p className="text-sm font-semibold text-gray-900 mb-1">Note:</p>
              <p className="text-sm text-gray-700">
                Deleting a license is <strong>permanent</strong> and cannot be undone. 
                Use this to remove fake/fraudulent license keys. The user will lose access immediately.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminLicenseManager;
