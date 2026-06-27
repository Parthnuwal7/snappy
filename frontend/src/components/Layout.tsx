import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { usePermissions } from '../hooks/usePermissions';
import OnboardingWarning from './OnboardingWarning';
import {
  Home as HomeIcon, Briefcase, Receipt, Users, PenLine, Sparkles,
  ShieldCheck, UsersRound, Settings as SettingsIcon, BarChart3, Scale,
  LayoutGrid, CalendarDays, FileText, Package, LogOut, PanelLeftClose, PanelLeft,
} from 'lucide-react';

type Leaf = { name: string; path: string; Icon: typeof HomeIcon; show?: boolean };
type Entry =
  | { kind: 'link'; leaf: Leaf }
  | { kind: 'group'; label: string; Icon: typeof HomeIcon; children: Leaf[] };

const STORAGE_KEY = 'snappy.sidebar.collapsed';

export default function Layout() {
  const navigate = useNavigate();
  const { user, firm, logout } = useAuth();
  const { has } = usePermissions();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(STORAGE_KEY) === '1');

  const toggle = () => setCollapsed((c) => { localStorage.setItem(STORAGE_KEY, c ? '0' : '1'); return !c; });

  const nav: Entry[] = [
    { kind: 'link', leaf: { name: 'Home', path: '/', Icon: HomeIcon } },
    { kind: 'group', label: 'Cases', Icon: Briefcase, children: [
      { name: 'Kanban', path: '/cases', Icon: LayoutGrid, show: has('case_files.read') },
      { name: 'Case Vault', path: '/cases/vault', Icon: Briefcase, show: has('case_files.read') },
      { name: 'Calendar', path: '/cases/calendar', Icon: CalendarDays, show: has('case_files.read') },
    ] },
    { kind: 'group', label: 'Billing', Icon: Receipt, children: [
      { name: 'Invoices', path: '/invoices', Icon: FileText },
      { name: 'Items', path: '/items', Icon: Package },
    ] },
    { kind: 'link', leaf: { name: 'Clients', path: '/clients', Icon: Users } },
    { kind: 'link', leaf: { name: 'Writing', path: '/writing', Icon: PenLine } },
    { kind: 'group', label: 'Personalize', Icon: Sparkles, children: [
      { name: 'News feed', path: '/legal-feed', Icon: Scale },
      { name: 'Reports', path: '/reports', Icon: BarChart3 },
    ] },
    { kind: 'group', label: 'Administration', Icon: SettingsIcon, children: [
      { name: 'Team', path: '/team', Icon: UsersRound, show: has('members.read') },
      { name: 'Roles', path: '/roles', Icon: ShieldCheck, show: has('roles.read') },
      { name: 'Settings', path: '/settings', Icon: SettingsIcon },
    ] },
  ];

  const visible = (l: Leaf) => l.show !== false;

  const handleLogout = async () => { await logout(); navigate('/login'); };

  const badgeSource = firm?.firm_name || user?.email || 'S';
  const initials = badgeSource.split(/[\s@]+/).filter(Boolean).slice(0, 2)
    .map((w) => w[0]?.toUpperCase()).join('');

  const leafLink = (l: Leaf, indent: boolean) => (
    <NavLink key={l.path} to={l.path} end={l.path === '/'} title={l.name}
      className={({ isActive }) => [
        'group relative flex items-center gap-3 py-2 text-sm font-medium transition-colors',
        collapsed ? 'justify-center px-0' : (indent ? 'pl-8 pr-3' : 'pl-5 pr-3'),
        isActive ? 'text-oxblood' : 'text-ink-soft hover:text-ink',
      ].join(' ')}>
      {({ isActive }) => (
        <>
          <span className={['absolute left-0 top-1.5 bottom-1.5 w-[2px] transition-opacity',
            isActive ? 'bg-oxblood opacity-100' : 'opacity-0'].join(' ')} />
          <l.Icon size={16} strokeWidth={isActive ? 2 : 1.5} className="shrink-0" />
          {!collapsed && <span>{l.name}</span>}
        </>
      )}
    </NavLink>
  );

  return (
    <div className="flex h-screen bg-paper">
      <aside className={`${collapsed ? 'w-[64px]' : 'w-[252px]'} shrink-0 border-r border-rule bg-paper flex flex-col transition-[width] duration-150`}>
        {/* Header: wordmark + collapse toggle */}
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between'} px-5 pt-6 pb-6`}>
          {!collapsed && (
            <div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-display text-2xl text-ink" style={{ fontVariationSettings: '"opsz" 144, "wght" 600, "SOFT" 20' }}>Snappy</span>
                <span className="h-1.5 w-1.5 rounded-full bg-oxblood translate-y-[-2px]" />
              </div>
              <div className="eyebrow text-ink-faint mt-1">Counsel's Ledger</div>
            </div>
          )}
          <button onClick={toggle} className="text-ink-faint hover:text-ink" title={collapsed ? 'Expand' : 'Collapse'}>
            {collapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        {/* Nav */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden space-y-4 pb-4">
          {nav.map((entry) => {
            if (entry.kind === 'link') return <div key={entry.leaf.path}>{leafLink(entry.leaf, false)}</div>;
            const kids = entry.children.filter(visible);
            if (kids.length === 0) return null;
            if (collapsed) {
              // Collapsed: one icon for the group, linking to its first visible child.
              const first = kids[0];
              return (
                <NavLink key={entry.label} to={first.path} title={entry.label}
                  className={({ isActive }) => ['flex items-center justify-center py-2 transition-colors',
                    isActive ? 'text-oxblood' : 'text-ink-soft hover:text-ink'].join(' ')}>
                  <entry.Icon size={16} strokeWidth={1.5} />
                </NavLink>
              );
            }
            return (
              <div key={entry.label}>
                <div className="eyebrow px-5 mb-1.5">{entry.label}</div>
                <nav className="space-y-px">{kids.map((l) => leafLink(l, true))}</nav>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="border-t border-rule px-3 py-4 space-y-3">
          {!collapsed && (
            <div className="flex items-center gap-3 px-2">
              <div className="shrink-0 h-9 w-9 rounded-full bg-paper-deep border border-rule flex items-center justify-center font-display text-sm text-ink-soft"
                   style={{ fontVariationSettings: '"opsz" 48, "wght" 600' }}>{initials || 'S'}</div>
              <div className="min-w-0">
                <div className="text-sm text-ink truncate font-medium">{firm?.firm_name || 'Untitled firm'}</div>
                <div className="text-xs text-ink-muted truncate">{user?.email}</div>
              </div>
            </div>
          )}
          <button onClick={handleLogout} title="Sign out"
            className={`w-full flex items-center ${collapsed ? 'justify-center' : 'justify-between px-2'} text-xs text-ink-muted hover:text-oxblood transition-colors group py-1`}>
            {!collapsed && <span className="uppercase tracking-eyebrow">Sign out</span>}
            <LogOut size={14} strokeWidth={1.5} className="group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto flex flex-col bg-paper">
        <OnboardingWarning />
        <div className="flex-1"><Outlet /></div>
      </main>
    </div>
  );
}
