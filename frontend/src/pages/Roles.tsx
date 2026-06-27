import { useEffect, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, FirmRole, PermissionModule } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { useToast } from '../contexts/ToastContext';
import { Plus, Trash2, Lock, Check } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

// A draft is the editable shape of a role: name + the set of ticked keys.
interface Draft {
  name: string;
  description: string;
  permissions: Set<string>;
}

const draftFromRole = (r: FirmRole): Draft => ({
  name: r.name,
  description: r.description ?? '',
  permissions: new Set(r.permissions),
});

const NEW_DRAFT: Draft = { name: '', description: '', permissions: new Set() };

export default function Roles() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { has } = usePermissions();
  const canManage = has('roles.manage');

  const { data: roles = [], isLoading } = useQuery({
    queryKey: ['firm', 'roles'],
    queryFn: api.getRoles,
  });

  const { data: catalog } = useQuery({
    queryKey: ['firm', 'permissions', 'catalog'],
    queryFn: api.getPermissionsCatalog,
  });
  const modules: PermissionModule[] = catalog?.modules ?? [];

  // selectedId === 'new' is the create form; a number selects an existing role.
  const [selectedId, setSelectedId] = useState<number | 'new' | null>(null);
  const [draft, setDraft] = useState<Draft>(NEW_DRAFT);

  const selectedRole = useMemo(
    () => (typeof selectedId === 'number' ? roles.find((r) => r.id === selectedId) ?? null : null),
    [roles, selectedId],
  );
  const isSystem = !!selectedRole?.is_system;
  const readOnly = !canManage || isSystem;

  // Default the selection to the first role once data arrives.
  useEffect(() => {
    if (selectedId === null && roles.length > 0) setSelectedId(roles[0].id);
  }, [roles, selectedId]);

  // Sync the draft whenever the selected role changes.
  useEffect(() => {
    if (selectedId === 'new') setDraft(NEW_DRAFT);
    else if (selectedRole) setDraft(draftFromRole(selectedRole));
  }, [selectedId, selectedRole]);

  const togglePerm = (key: string) => {
    if (readOnly) return;
    setDraft((d) => {
      const next = new Set(d.permissions);
      if (next.has(key)) next.delete(key); else next.add(key);
      return { ...d, permissions: next };
    });
  };

  const toggleModule = (m: PermissionModule, on: boolean) => {
    if (readOnly) return;
    setDraft((d) => {
      const next = new Set(d.permissions);
      m.actions.forEach((a) => {
        const key = `${m.key}.${a}`;
        if (on) next.add(key); else next.delete(key);
      });
      return { ...d, permissions: next };
    });
  };

  const createRole = useMutation({
    mutationFn: (d: Draft) =>
      api.createRole({ name: d.name, description: d.description, permissions: [...d.permissions] }),
    onSuccess: (role) => {
      queryClient.invalidateQueries({ queryKey: ['firm', 'roles'] });
      setSelectedId(role.id);
      showToast('Role created');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const updateRole = useMutation({
    mutationFn: ({ id, d }: { id: number; d: Draft }) =>
      api.updateRole(id, { name: d.name, description: d.description, permissions: [...d.permissions] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['firm', 'roles'] });
      showToast('Role saved');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const deleteRole = useMutation({
    mutationFn: (id: number) => api.deleteRole(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['firm', 'roles'] });
      setSelectedId(null);
      showToast('Role deleted');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const handleSave = () => {
    if (!draft.name.trim()) { showToast('Role needs a name', 'error'); return; }
    if (selectedId === 'new') createRole.mutate(draft);
    else if (typeof selectedId === 'number') updateRole.mutate({ id: selectedId, d: draft });
  };

  // For the Owner system role we show the full catalog ticked, read-only.
  const effectivePerms = isSystem
    ? new Set(modules.flatMap((m) => m.actions.map((a) => `${m.key}.${a}`)))
    : draft.permissions;

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="flex items-end justify-between flex-wrap gap-6 mb-10">
        <div>
          <div className="page-eyebrow">Folio VII · Authority</div>
          <h1 className="page-title">Roles &amp; permissions</h1>
          <p className="page-subtitle">
            Each role is a set of permissions across modules. Assign roles to members on the Team page.
          </p>
        </div>
        {canManage && (
          <button onClick={() => setSelectedId('new')} className="btn-primary">
            <Plus size={14} strokeWidth={2} />
            <span>New role</span>
          </button>
        )}
      </header>

      {isLoading ? (
        <div className="card p-16 flex justify-center"><div className="spinner" /></div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-px bg-rule border border-rule">
          {/* Role list */}
          <aside className="bg-surface">
            {selectedId === 'new' && (
              <div className="px-4 py-3 text-sm text-oxblood bg-oxblood-wash border-l-2 border-oxblood">
                New role…
              </div>
            )}
            {roles.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelectedId(r.id)}
                className={[
                  'w-full text-left px-4 py-3 flex items-center gap-2 transition-colors',
                  selectedId === r.id ? 'bg-paper-deep text-ink' : 'text-ink-soft hover:bg-paper-deep/50',
                ].join(' ')}
              >
                {r.is_system && <Lock size={12} strokeWidth={1.75} className="text-ink-faint shrink-0" />}
                <span className="text-sm truncate">{r.name}</span>
              </button>
            ))}
          </aside>

          {/* Editor */}
          <div className="bg-surface p-7">
            {selectedId === null ? (
              <p className="text-sm text-ink-muted">Select a role to view its permissions.</p>
            ) : (
              <>
                <div className="flex flex-col sm:flex-row sm:items-end gap-4 mb-6">
                  <div className="flex-1">
                    <label className="field-label">Role name</label>
                    <input
                      value={draft.name}
                      onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                      disabled={readOnly}
                      className="field-input disabled:opacity-60"
                      placeholder="e.g., Paralegal"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="field-label">Description</label>
                    <input
                      value={draft.description}
                      onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                      disabled={readOnly}
                      className="field-input disabled:opacity-60"
                      placeholder="What this role is for"
                    />
                  </div>
                </div>

                {isSystem && (
                  <div className="flex items-center gap-2 text-xs text-ink-muted mb-5">
                    <Lock size={12} strokeWidth={1.75} />
                    The Owner role always holds every permission and can't be edited.
                  </div>
                )}

                {/* Module × action grid */}
                <div className="border border-rule divide-y divide-rule">
                  {modules.map((m) => {
                    const allOn = m.actions.every((a) => effectivePerms.has(`${m.key}.${a}`));
                    return (
                      <div key={m.key} className="px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-3">
                        <div className="sm:w-40 shrink-0 flex items-center gap-2">
                          <button
                            type="button"
                            disabled={readOnly}
                            onClick={() => toggleModule(m, !allOn)}
                            className="text-sm text-ink font-medium hover:text-oxblood transition-colors
                                       disabled:hover:text-ink text-left"
                            title={readOnly ? undefined : (allOn ? 'Clear all' : 'Select all')}
                          >
                            {m.label}
                          </button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {m.actions.map((a) => {
                            const key = `${m.key}.${a}`;
                            const on = effectivePerms.has(key);
                            return (
                              <button
                                key={a}
                                type="button"
                                disabled={readOnly}
                                onClick={() => togglePerm(key)}
                                className={[
                                  'inline-flex items-center gap-1 px-2.5 py-1 rounded-sm text-xs border transition-colors',
                                  on
                                    ? 'bg-oxblood-wash border-oxblood/40 text-oxblood'
                                    : 'bg-paper border-rule text-ink-muted hover:border-ink-faint',
                                  readOnly ? 'cursor-default' : 'cursor-pointer',
                                ].join(' ')}
                              >
                                {on && <Check size={11} strokeWidth={2.25} />}
                                {a}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {!readOnly && (
                  <div className="flex items-center justify-between gap-3 pt-6">
                    <div>
                      {typeof selectedId === 'number' && !isSystem && (
                        <button
                          onClick={() => {
                            if (confirm(`Delete the "${draft.name}" role?`)) deleteRole.mutate(selectedId);
                          }}
                          className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-oxblood transition-colors"
                        >
                          <Trash2 size={13} strokeWidth={1.75} />
                          Delete role
                        </button>
                      )}
                    </div>
                    <button
                      onClick={handleSave}
                      disabled={createRole.isPending || updateRole.isPending}
                      className="btn-primary"
                    >
                      {selectedId === 'new' ? 'Create role' : 'Save changes'}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
