import { NavLink, Outlet } from 'react-router-dom';

const tabClass = ({ isActive }: { isActive: boolean }) =>
  [
    'px-1 pb-2 -mb-px text-sm font-medium border-b-2 transition-colors',
    isActive
      ? 'border-oxblood text-ink'
      : 'border-transparent text-ink-muted hover:text-ink',
  ].join(' ');

export default function CasesLayout() {
  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="mb-6">
        <div className="page-eyebrow">Folio V · Docket</div>
        <h1 className="page-title">Case files</h1>
      </header>
      <nav className="flex gap-6 border-b border-rule mb-8">
        <NavLink end to="/cases" className={tabClass}>Kanban</NavLink>
        <NavLink to="/cases/vault" className={tabClass}>Case Vault</NavLink>
        <NavLink to="/cases/calendar" className={tabClass}>Calendar</NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
