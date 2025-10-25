import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  User, Mail, Phone, Briefcase, Calendar, MapPin, 
  Key, LogOut, Shield, CheckCircle, AlertCircle
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { dashboardAPI } from '../api/client';

interface License {
  id: number;
  license_key: string;
  plan: string;
  status: string;
  invoked_at: string | null;
  expires_at: string | null;
  created_at: string;
  amount: number;
  daysRemaining: number | null;
  isActive: boolean;
  admin_notes?: string | null;
}

interface DashboardData {
  user: any;
  licenses: License[];
  activeLicense: License | null;
}

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await dashboardAPI.getDashboard();
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Not activated';
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-1">Welcome back, {user?.name}!</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center space-x-2 bg-white border border-gray-300 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-50 transition-colors duration-200"
          >
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>

        {/* Active License Status */}
        {data?.activeLicense ? (
          <div className="bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl p-6 mb-8 text-white">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center mb-2">
                  <CheckCircle className="w-6 h-6 mr-2" />
                  <h2 className="text-2xl font-bold">Active License</h2>
                </div>
                <p className="text-green-100 mb-4">Your SNAPPY {data.activeLicense.plan} plan is active</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-green-100 text-sm">License Key</p>
                    <p className="font-mono font-semibold text-lg">{data.activeLicense.license_key}</p>
                  </div>
                  <div>
                    <p className="text-green-100 text-sm">Activated On</p>
                    <p className="font-semibold">{formatDate(data.activeLicense.invoked_at)}</p>
                  </div>
                  <div>
                    <p className="text-green-100 text-sm">Expires On</p>
                    <p className="font-semibold">{formatDate(data.activeLicense.expires_at)}</p>
                  </div>
                  <div>
                    <p className="text-green-100 text-sm">Days Remaining</p>
                    <p className="font-semibold text-2xl">{data.activeLicense.daysRemaining}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-yellow-50 border-2 border-yellow-200 rounded-xl p-6 mb-8">
            <div className="flex items-start">
              <AlertCircle className="w-6 h-6 text-yellow-600 mr-3 flex-shrink-0 mt-1" />
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">No Active License</h2>
                <p className="text-gray-700 mb-4">
                  You don't have an active SNAPPY license. Purchase a plan to start using SNAPPY.
                </p>
                <Link
                  to="/pricing"
                  className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors duration-200 font-semibold"
                >
                  View Pricing Plans
                </Link>
              </div>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Personal Information */}
          <div className="lg:col-span-2 space-y-8">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center mb-6">
                <User className="w-6 h-6 text-blue-600 mr-2" />
                <h2 className="text-2xl font-bold text-gray-900">Personal Information</h2>
              </div>
              <div className="grid md:grid-cols-2 gap-6">
                <div className="flex items-start">
                  <User className="w-5 h-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm text-gray-500">Full Name</p>
                    <p className="font-semibold text-gray-900">{data?.user?.name}</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <Mail className="w-5 h-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm text-gray-500">Email</p>
                    <p className="font-semibold text-gray-900">{data?.user?.email}</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <Phone className="w-5 h-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm text-gray-500">Phone</p>
                    <p className="font-semibold text-gray-900">{data?.user?.phone}</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <Briefcase className="w-5 h-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm text-gray-500">Profession</p>
                    <p className="font-semibold text-gray-900">{data?.user?.profession}</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <Calendar className="w-5 h-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm text-gray-500">Date of Birth</p>
                    <p className="font-semibold text-gray-900">{formatDate(data?.user?.dob)}</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <MapPin className="w-5 h-5 text-gray-400 mr-3 mt-1" />
                  <div>
                    <p className="text-sm text-gray-500">City</p>
                    <p className="font-semibold text-gray-900">{data?.user?.city}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* All Licenses */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center">
                  <Key className="w-6 h-6 text-blue-600 mr-2" />
                  <h2 className="text-2xl font-bold text-gray-900">License History</h2>
                </div>
                {!data?.activeLicense && (
                  <Link
                    to="/pricing"
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors duration-200 font-semibold text-sm"
                  >
                    Buy License
                  </Link>
                )}
              </div>

              {data?.licenses && data.licenses.length > 0 ? (
                <div className="space-y-4">
                  {data.licenses.map((license) => (
                    <div
                      key={license.id}
                      className={`border rounded-lg p-4 ${
                        license.isActive
                          ? 'border-green-500 bg-green-50'
                          : license.status === 'pending'
                          ? 'border-yellow-500 bg-yellow-50'
                          : 'border-gray-200 bg-gray-50'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <div className="flex items-center mb-1">
                            <Shield className={`w-5 h-5 mr-2 ${license.isActive ? 'text-green-600' : 'text-gray-400'}`} />
                            <span className="font-bold text-gray-900">{license.plan.toUpperCase()} Plan</span>
                          </div>
                          <div className="font-mono text-sm text-gray-700 flex items-center">
                            {license.license_key === '••••••••••••••••' ? (
                              <div className="flex items-center">
                                <span className="text-gray-400">{license.license_key}</span>
                                <span className="ml-2 text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                                  Hidden until verified
                                </span>
                              </div>
                            ) : (
                              license.license_key
                            )}
                          </div>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          license.isActive
                            ? 'bg-green-200 text-green-800'
                            : license.status === 'pending'
                            ? 'bg-yellow-200 text-yellow-800'
                            : 'bg-gray-200 text-gray-800'
                        }`}>
                          {license.isActive ? 'Active' : license.status}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">Purchased</p>
                          <p className="font-semibold text-gray-900">{formatDate(license.created_at)}</p>
                        </div>
                        {license.invoked_at && (
                          <>
                            <div>
                              <p className="text-gray-500">Activated</p>
                              <p className="font-semibold text-gray-900">{formatDate(license.invoked_at)}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Days Remaining</p>
                              <p className="font-semibold text-gray-900">{license.daysRemaining || 0}</p>
                            </div>
                          </>
                        )}
                      </div>
                      {license.admin_notes && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <div className="flex items-start">
                            <AlertCircle className="w-4 h-4 text-blue-600 mr-2 flex-shrink-0 mt-0.5" />
                            <div>
                              <p className="text-xs font-semibold text-gray-700 mb-1">Admin Notes:</p>
                              <p className="text-sm text-gray-600">{license.admin_notes}</p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Key className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500 mb-4">No licenses yet</p>
                  <Link
                    to="/pricing"
                    className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors duration-200 font-semibold"
                  >
                    Purchase Your First License
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="font-bold text-gray-900 mb-4">Account Details</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-500">Member Since</p>
                  <p className="font-semibold text-gray-900">{formatDate(data?.user?.created_at)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Last Login</p>
                  <p className="font-semibold text-gray-900">{formatDate(data?.user?.last_login)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Gender</p>
                  <p className="font-semibold text-gray-900">{data?.user?.gender}</p>
                </div>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
              <h3 className="font-bold text-gray-900 mb-2">Need Help?</h3>
              <p className="text-sm text-gray-700 mb-4">
                Contact our support team for any assistance
              </p>
              <Link
                to="/support"
                className="block w-full bg-blue-600 text-white text-center py-2 rounded-lg hover:bg-blue-700 transition-colors duration-200 font-semibold"
              >
                Contact Support
              </Link>
            </div>

            <div className="bg-gradient-to-br from-indigo-500 to-purple-500 rounded-xl p-6 text-white">
              <h3 className="font-bold mb-2">Download SNAPPY</h3>
              <p className="text-sm text-indigo-100 mb-4">
                Download the desktop app to start billing
              </p>
              <Link
                to="/download"
                className="block w-full bg-white text-indigo-600 text-center py-2 rounded-lg hover:bg-gray-100 transition-colors duration-200 font-semibold"
              >
                Download Now
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
