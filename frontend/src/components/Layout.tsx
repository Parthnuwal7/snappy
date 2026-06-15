import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import OnboardingWarning from './OnboardingWarning';
import {
  LayoutDashboard,
  FileText,
  Users,
  Package,
  BarChart3,
  Settings as SettingsIcon,
  LogOut,
} from 'lucide-react';

type Item = { name: string; path: string; Icon: typeof LayoutDashboard };

const NAV_PRIMARY: Item[] = [
  { name: 'Dashboard', path: '/dashboard', Icon: LayoutDashboard },
  { name: 'Invoices',  path: '/invoices',  Icon: FileText },
  { name: 'Clients',   path: '/clients',   Icon: Users },
  { name: 'Items',     path: '/items',     Icon: Package },
];

const NAV_SECONDARY: Item[] = [
  { name: 'Reports',  path: '/reports',  Icon: BarChart3 },
  { name: 'Settings', path: '/settings', Icon: SettingsIcon },
];

const linkClasses = ({ isActive }: { isActive: boolean }) =>
  [
    'group relative flex items-center gap-3 pl-5 pr-3 py-2 text-sm font-medium transition-colors',
    isActive
      ? 'text-oxblood'
      : 'text-ink-soft hover:text-ink',
  ].join(' ');

function NavGroup({ label, items }: { label: string; items: Item[] }) {
  return (
    <div>
      <div className="eyebrow px-5 mb-2">{label}</div>
      <nav className="space-y-px">
        {items.map(({ name, path, Icon }) => (
          <NavLink key={path} to={path} className={linkClasses}>
            {({ isActive }) => (
              <>
                {/* Active marker: thin oxblood bar on the left */}
                <span
                  className={[
                    'absolute left-0 top-1.5 bottom-1.5 w-[2px] transition-opacity',
                    isActive ? 'bg-oxblood opacity-100' : 'opacity-0',
                  ].join(' ')}
                />
                <Icon
                  size={16}
                  strokeWidth={isActive ? 2 : 1.5}
                  className="shrink-0"
                />
                <span>{name}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export default function Layout() {
  const navigate = useNavigate();
  const { user, firm, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Pull initials for the user badge (firm name first, fall back to email)
  const badgeSource = firm?.firm_name || user?.email || 'S';
  const initials = badgeSource
    .split(/[\s@]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join('');

  return (
    <div className="flex h-screen bg-paper">
      {/* ---- Sidebar -------------------------------------------------- */}
      <aside className="w-[252px] shrink-0 border-r border-rule bg-paper flex flex-col">
        {/* Wordmark */}
        <div className="px-5 pt-6 pb-8">
          <div className="flex items-baseline gap-1.5">
            <span
              className="font-display text-3xl text-ink"
              style={{ fontVariationSettings: '"opsz" 144, "wght" 600, "SOFT" 20' }}
            >
              Snappy
            </span>
            <span className="h-1.5 w-1.5 rounded-full bg-oxblood translate-y-[-2px]" />
          </div>
          <div className="eyebrow text-ink-faint mt-1">Counsel's Ledger</div>
        </div>

        {/* Primary navigation */}
        <div className="flex-1 px-0 overflow-y-auto space-y-7">
          <NavGroup label="Practice" items={NAV_PRIMARY} />
          <NavGroup label="Administration" items={NAV_SECONDARY} />
        </div>

        {/* Footer: identity + logout */}
        <div className="border-t border-rule px-5 py-4 space-y-3">
          {/* User badge */}
          <div className="flex items-center gap-3">
            <div className="shrink-0 h-9 w-9 rounded-full bg-paper-deep border border-rule
                            flex items-center justify-center font-display text-sm text-ink-soft"
                 style={{ fontVariationSettings: '"opsz" 48, "wght" 600' }}>
              {initials || 'S'}
            </div>
            <div className="min-w-0">
              <div className="text-sm text-ink truncate font-medium">
                {firm?.firm_name || 'Untitled firm'}
              </div>
              <div className="text-xs text-ink-muted truncate">{user?.email}</div>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-between text-xs text-ink-muted
                       hover:text-oxblood transition-colors group py-1"
          >
            <span className="uppercase tracking-eyebrow">Sign out</span>
            <LogOut size={14} strokeWidth={1.5}
                    className="group-hover:translate-x-0.5 transition-transform" />
          </button>

          <div className="text-2xs text-ink-faint tracking-eyebrow uppercase pt-1">
            v 1.0 · est. 2026
          </div>
        </div>
      </aside>

      {/* ---- Main column ---------------------------------------------- */}
      <main className="flex-1 overflow-auto flex flex-col bg-paper">
        <OnboardingWarning />
        <div className="flex-1">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
