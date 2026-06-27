# App Shell & IA Reorg + Quick Wins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapsible grouped sidebar + Home greeting landing + Dashboard→Reports rehome + Case Vault server-side search + view-an-enquiry detail.

**Architecture:** Frontend-only. New `Home`/`Writing` pages, a rewritten `Layout` sidebar (grouped + collapsible, `localStorage`-persisted), route changes in `App.tsx`, a debounced server-side search in `CaseVault`, and a lead-detail modal in `CaseVault`. No backend/API/schema change (the `/case-files?search=` filter already exists).

**Tech Stack:** React + TypeScript + Vite, React Router v6, TanStack Query, Tailwind tokens, lucide-react.

## Global Constraints

- Never run git commits/pushes — Parth does git. Stage only; run the gate and report.
- No backend changes, no migrations. Backend suite stays green (289) untouched.
- Gate per task: `npm run build` clean (no FE unit-test runner).
- Preserve permission gating: Cases→`case_files.read`, Team→`members.read`, Roles→`roles.read`.
- Greeting bands (IST): morning 05–12, afternoon 12–17, evening 17–21, night 21–05.

---

### Task 1: Home greeting page + Writing placeholder + routing

**Files:**
- Create: `frontend/src/pages/Home.tsx`, `frontend/src/pages/Writing.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create `Home.tsx`**

```tsx
import { useAuth } from '../contexts/AuthContext';

function istHour(): number {
  const utcMs = Date.now() + new Date().getTimezoneOffset() * 60000;
  return new Date(utcMs + 5.5 * 3600000).getHours();
}

function greetingFor(h: number): string {
  if (h >= 5 && h < 12) return 'Good morning';
  if (h >= 12 && h < 17) return 'Good afternoon';
  if (h >= 17 && h < 21) return 'Good evening';
  return 'Good night';
}

export default function Home() {
  const { user, firm } = useAuth();
  const raw = firm?.firm_name || (user?.email ? user.email.split('@')[0] : 'there');
  const name = raw.charAt(0).toUpperCase() + raw.slice(1);

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-24">
      <div className="page-eyebrow">{new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}</div>
      <h1 className="font-display text-4xl md:text-5xl text-ink mt-2">
        {greetingFor(istHour())}, {name}.
      </h1>
    </div>
  );
}
```

- [ ] **Step 2: Create `Writing.tsx` (placeholder)**

```tsx
import { PenLine } from 'lucide-react';

export default function Writing() {
  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="mb-12">
        <div className="page-eyebrow">Folio VI · Writing</div>
        <h1 className="page-title">Drafting</h1>
        <p className="page-subtitle">Templates, notices, and case drafts.</p>
      </header>
      <div className="card p-16 text-center">
        <PenLine size={32} strokeWidth={1.25} className="mx-auto text-ink-faint mb-6" />
        <div className="eyebrow text-oxblood">In preparation</div>
        <h2 className="section-title mt-2">The drafting workspace is being built</h2>
        <p className="text-base text-ink-muted mt-3 max-w-prose mx-auto">
          A rich-text editor with reusable templates, merge fields, and case-linked drafts is coming next.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Rewire routes in `App.tsx`**

- Replace the Dashboard import usage: keep `import Dashboard from './pages/Dashboard';`, and add `import Home from './pages/Home';` and `import Writing from './pages/Writing';`.
- Replace the index route `<Route index element={<Navigate to="/dashboard" replace />} />` with `<Route index element={<Home />} />`.
- Replace `<Route path="dashboard" element={<Dashboard />} />` with `<Route path="dashboard" element={<Navigate to="/reports" replace />} />`.
- Change `<Route path="reports" element={<Reports />} />` to `<Route path="reports" element={<Dashboard />} />` (the analytics Dashboard now IS Reports). Remove the now-unused `import Reports from './pages/Reports';`.
- Add `<Route path="writing" element={<Writing />} />`.

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: succeeds, no unused-import TS errors (ensure `Reports` import removed).

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add frontend/src/pages/Home.tsx frontend/src/pages/Writing.tsx frontend/src/App.tsx
```

---

### Task 2: Collapsible grouped sidebar (`Layout.tsx`)

**Files:**
- Modify (rewrite): `frontend/src/components/Layout.tsx`

**Interfaces:**
- Consumes: `useAuth`, `usePermissions().has`. Nav model = ordered list of standalone links and groups (label + children); gated leaves filtered out; a group with no visible children is hidden.

- [ ] **Step 1: Rewrite `Layout.tsx`**

Replace the whole file with:

```tsx
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
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: succeeds; sidebar renders grouped; collapse toggle persists.

- [ ] **Step 3: Stage (do NOT commit)**

```bash
git add frontend/src/components/Layout.tsx
```

---

### Task 3: Case Vault server-side search

**Files:**
- Modify: `frontend/src/pages/CaseVault.tsx`

- [ ] **Step 1: Add a debounced search bound to the API**

In `CaseVault.tsx`:
- Add `import { Search } from 'lucide-react';` to the lucide import.
- Add state + debounce near the other hooks:
  ```tsx
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  useEffect(() => { const t = setTimeout(() => setDebounced(search), 250); return () => clearTimeout(t); }, [search]);
  ```
  (Add `useEffect` to the `react` import.)
- Change the cases query to pass the term and key on it:
  ```tsx
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['case-files', debounced], queryFn: () => api.getCaseFiles(debounced ? { search: debounced } : undefined),
  });
  ```
- In the "All cases" section header, add a search input beside the heading:
  ```tsx
  <div className="flex items-center gap-3">
    <div className="relative">
      <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint" />
      <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search cases…"
        className="field-input !py-1.5 !pl-8 text-sm w-56" data-search />
    </div>
    {canCreate && (
      <button onClick={() => setModalOpen(true)} className="btn-primary"><Plus size={14} strokeWidth={2} /><span>New case</span></button>
    )}
  </div>
  ```
  (Replace the existing `{canCreate && (<button…New case…/>)}` block in the All-cases header with this wrapper that holds both search + button.)

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: succeeds; typing in the box refetches server-side (query key changes).

- [ ] **Step 3: Stage (do NOT commit)**

```bash
git add frontend/src/pages/CaseVault.tsx
```

---

### Task 4: View-an-enquiry detail modal

**Files:**
- Modify: `frontend/src/pages/CaseVault.tsx`

**Interfaces:**
- Consumes existing `api.getLeads`, `api.updateLead`, `api.convertLead`. Reuses the `Lead` type.

- [ ] **Step 1: Add a view/edit modal + open it from each enquiry row**

In `CaseVault.tsx`:
- Add state:
  ```tsx
  const [viewLead, setViewLead] = useState<Lead | null>(null);
  const [leadEdit, setLeadEdit] = useState(false);
  const [leadDraft, setLeadDraft] = useState<Partial<Lead>>({});
  const openLead = (l: Lead) => { setViewLead(l); setLeadEdit(false); setLeadDraft(l); };
  const saveLead = useMutation({
    mutationFn: () => api.updateLead(viewLead!.id, {
      contact_name: leadDraft.contact_name, phone: leadDraft.phone, email: leadDraft.email,
      matter_summary: leadDraft.matter_summary, intake_notes: leadDraft.intake_notes,
    }),
    onSuccess: (updated) => { queryClient.invalidateQueries({ queryKey: ['leads'] }); setViewLead(updated); setLeadEdit(false); showToast('Enquiry updated'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  ```
- Make each enquiry row open the modal: change the row's flex container to include a **View** button, and make the name clickable. In the enquiry `.map`, replace the row markup's action area so it reads:
  ```tsx
  <div key={l.id} className="bg-surface flex items-center gap-4 px-5 py-3">
    <button onClick={() => openLead(l)} className="flex-1 min-w-0 text-left">
      <div className="text-sm text-ink font-medium truncate hover:text-oxblood">{l.contact_name}</div>
      <div className="text-2xs text-ink-muted truncate">{l.matter_summary}</div>
    </button>
    <button onClick={() => openLead(l)} className="btn-ghost text-2xs">View</button>
    <button onClick={() => declineLead.mutate(l.id)} className="btn-ghost text-2xs">Decline</button>
    <button onClick={() => acceptLead.mutate(l)} className="btn-primary text-2xs">Accept → open file</button>
  </div>
  ```
- Add the modal near the other modals (before the closing `</div>` of the component fragment):
  ```tsx
  {viewLead && (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={() => setViewLead(null)} />
      <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
        <div className="h-[3px] bg-oxblood" />
        <div className="p-8">
          <button onClick={() => setViewLead(null)} className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted"><X size={20} strokeWidth={1.5} /></button>
          <div className="mb-6"><div className="page-eyebrow">Enquiry</div><h2 className="page-title !text-2xl">{viewLead.contact_name}</h2></div>
          {leadEdit ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><label className="field-label">Contact name</label><input value={leadDraft.contact_name ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, contact_name: e.target.value })} className="field-input" /></div>
                <div><label className="field-label">Phone</label><input value={leadDraft.phone ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, phone: e.target.value })} className="field-input" /></div>
              </div>
              <div><label className="field-label">Email</label><input value={leadDraft.email ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, email: e.target.value })} className="field-input" /></div>
              <div><label className="field-label">Matter summary</label><input value={leadDraft.matter_summary ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, matter_summary: e.target.value })} className="field-input" /></div>
              <div><label className="field-label">Intake notes</label><textarea rows={4} value={leadDraft.intake_notes ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, intake_notes: e.target.value })} className="field-textarea" /></div>
              <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                <button onClick={() => setLeadEdit(false)} className="btn-ghost">Cancel</button>
                <button onClick={() => saveLead.mutate()} className="btn-primary" disabled={saveLead.isPending}>Save</button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
                <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Phone</dt><dd className="text-sm text-ink mt-0.5">{viewLead.phone || '—'}</dd></div>
                <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Email</dt><dd className="text-sm text-ink mt-0.5">{viewLead.email || '—'}</dd></div>
                <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Status</dt><dd className="text-sm text-ink mt-0.5 capitalize">{viewLead.status}</dd></div>
                <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Matter</dt><dd className="text-sm text-ink mt-0.5">{viewLead.matter_summary || '—'}</dd></div>
              </dl>
              {viewLead.intake_notes && (
                <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint mb-1">Intake notes</dt>
                  <p className="text-sm text-ink-muted whitespace-pre-wrap">{viewLead.intake_notes}</p></div>
              )}
              <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                <button onClick={() => setLeadEdit(true)} className="btn-ghost">Edit</button>
                <button onClick={() => { declineLead.mutate(viewLead.id); setViewLead(null); }} className="btn-ghost">Decline</button>
                <button onClick={() => { acceptLead.mutate(viewLead); setViewLead(null); }} className="btn-primary">Accept → open file</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )}
  ```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: succeeds; clicking an enquiry opens the detail modal with View/Edit/Accept/Decline.

- [ ] **Step 3: Stage (do NOT commit)**

```bash
git add frontend/src/pages/CaseVault.tsx
```

---

## Self-Review

**Spec coverage:** collapsible grouped sidebar (Task 2) ✓ · Home greeting landing + IST bands (Task 1) ✓ · Dashboard→Reports rehome + `/dashboard` redirect (Task 1) ✓ · Writing placeholder (Task 1) ✓ · Vault server-side search (Task 3) ✓ · view-an-enquiry with Edit (Task 4) ✓. Permission gating preserved via `show` flags (Task 2). No backend change.

**Placeholder scan:** none (Writing "Coming soon" is intentional product copy).

**Type consistency:** nav `Entry`/`Leaf` shapes internal to Layout; `Lead`/`api.updateLead`/`getCaseFiles({search})` already exist in `api.ts`. `getCaseFiles` accepts `{ search }` (verified in api.ts).
