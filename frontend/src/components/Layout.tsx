import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import OnboardingWarning from './OnboardingWarning';

const navigation = [
  { name: 'Dashboard', path: '/dashboard', icon: '📊' },
  { name: 'Invoices', path: '/invoices', icon: '📄' },
  { name: 'Clients', path: '/clients', icon: '👥' },
  { name: 'Items', path: '/items', icon: '📦' },
  { name: 'Reports', path: '/reports', icon: '📈' },
  { name: 'Settings', path: '/settings', icon: '⚙️' },
];

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, firm, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`${sidebarOpen ? 'w-64' : 'w-20'
          } bg-primary-800 text-white transition-all duration-300 flex flex-col`}
      >
        <div className="p-6 flex items-center justify-between">
          <h1 className={`text-2xl font-bold ${!sidebarOpen && 'hidden'}`}>SNAPPY</h1>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-primary-700 rounded"
            aria-label="Toggle sidebar"
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        <nav className="flex-1 px-4 space-y-2">
          {navigation.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-primary-100 hover:bg-primary-700 hover:text-white'
                  }`}
              >
                <span className="text-xl">{item.icon}</span>
                {sidebarOpen && <span className="font-medium">{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-primary-700 space-y-2">
          {sidebarOpen && (
            <div className="px-4 py-2 bg-primary-700 rounded-lg">
              <div className="text-sm font-medium truncate">{user?.email}</div>
              {firm && (
                <div className="text-xs text-primary-300 truncate">{firm.firm_name}</div>
              )}
            </div>
          )}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-2 text-primary-100 hover:bg-primary-700 hover:text-white rounded-lg transition-colors"
          >
            <span className="text-xl">🚪</span>
            {sidebarOpen && <span className="font-medium">Logout</span>}
          </button>
          <div className={`text-xs text-primary-300 text-center ${!sidebarOpen && 'hidden'}`}>
            v1.0.0
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto flex flex-col">
        <OnboardingWarning />
        <div className="flex-1">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
