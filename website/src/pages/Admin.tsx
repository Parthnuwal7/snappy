import { useState, useEffect } from 'react';
import { Eye, EyeOff, Users, FileText, TrendingUp, Activity } from 'lucide-react';

const Admin = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  // Check if already authenticated
  useEffect(() => {
    const auth = localStorage.getItem('snappy_admin_auth');
    if (auth === 'authenticated') {
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Simple password protection - In production, use proper authentication
    if (password === 'snappy2025') {
      localStorage.setItem('snappy_admin_auth', 'authenticated');
      setIsAuthenticated(true);
      setError('');
    } else {
      setError('Incorrect password');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('snappy_admin_auth');
    setIsAuthenticated(false);
    setPassword('');
  };

  // Login Screen
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Eye className="w-8 h-8 text-blue-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Admin Dashboard</h1>
            <p className="text-gray-600">Enter password to access analytics</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
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

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors duration-200 font-semibold"
            >
              Access Dashboard
            </button>
          </form>

          <p className="text-xs text-gray-500 text-center mt-6">
            For demo purposes, password is: snappy2025
          </p>
        </div>
      </div>
    );
  }

  // Admin Dashboard
  const stats = [
    {
      icon: <Users className="w-8 h-8" />,
      title: 'Total Visitors',
      value: '1,234',
      change: '+12%',
      positive: true,
    },
    {
      icon: <FileText className="w-8 h-8" />,
      title: 'Form Submissions',
      value: '89',
      change: '+8%',
      positive: true,
    },
    {
      icon: <TrendingUp className="w-8 h-8" />,
      title: 'Downloads',
      value: '456',
      change: '+23%',
      positive: true,
    },
    {
      icon: <Activity className="w-8 h-8" />,
      title: 'Active Users',
      value: '234',
      change: '-5%',
      positive: false,
    },
  ];

  const recentSubmissions = [
    { date: '2025-01-15', name: 'Advocate Kumar', email: 'kumar@email.com', subject: 'Technical Support' },
    { date: '2025-01-14', name: 'CA Priya', email: 'priya@email.com', subject: 'Billing Question' },
    { date: '2025-01-14', name: 'Advocate Sharma', email: 'sharma@email.com', subject: 'Feature Request' },
    { date: '2025-01-13', name: 'CA Mehta', email: 'mehta@email.com', subject: 'General Inquiry' },
    { date: '2025-01-13', name: 'Advocate Patel', email: 'patel@email.com', subject: 'Enterprise Plan' },
  ];

  const topPages = [
    { page: '/pricing', views: 456, percentage: 35 },
    { page: '/download', views: 389, percentage: 30 },
    { page: '/', views: 234, percentage: 18 },
    { page: '/demo', views: 123, percentage: 10 },
    { page: '/support', views: 89, percentage: 7 },
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-gray-600 mt-1">Website Analytics & Monitoring</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center space-x-2 bg-white border border-gray-300 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-50 transition-colors duration-200"
          >
            <EyeOff size={18} />
            <span>Logout</span>
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => (
            <div key={index} className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600">
                  {stat.icon}
                </div>
                <span className={`text-sm font-semibold ${
                  stat.positive ? 'text-green-600' : 'text-red-600'
                }`}>
                  {stat.change}
                </span>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-1">{stat.value}</h3>
              <p className="text-sm text-gray-600">{stat.title}</p>
            </div>
          ))}
        </div>

        <div className="grid lg:grid-cols-2 gap-8 mb-8">
          {/* Top Pages */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Top Pages</h2>
            <div className="space-y-4">
              {topPages.map((item, index) => (
                <div key={index}>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-700 font-medium">{item.page}</span>
                    <span className="text-gray-900 font-semibold">{item.views} views</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${item.percentage}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Traffic Chart Placeholder */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Traffic Overview</h2>
            <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
              <div className="text-center text-gray-500">
                <Activity className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                <p className="font-medium">[Chart placeholder]</p>
                <p className="text-sm mt-1">Integrate with Google Analytics or similar</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Form Submissions */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">Recent Form Submissions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Subject
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {recentSubmissions.map((submission, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {submission.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {submission.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {submission.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                        {submission.subject}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="p-4 bg-gray-50 text-center">
            <button className="text-blue-600 hover:text-blue-700 font-semibold text-sm">
              View All Submissions →
            </button>
          </div>
        </div>

        {/* Note */}
        <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-gray-700">
            <strong>Note:</strong> This is a demo dashboard with placeholder data. 
            Integrate with Google Analytics, Google Sheets API, or your preferred analytics platform 
            for real-time data.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Admin;
