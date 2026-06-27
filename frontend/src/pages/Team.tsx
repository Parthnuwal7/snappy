import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, FirmMember, FirmRole } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';
import { UserPlus, Trash2, Mail, Clock } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

export default function Team() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { has } = usePermissions();
  const { user } = useAuth();

  const canManageRoles = has('members.manage_roles');
  const canRemove = has('members.remove');
  const canInvite = has('members.invite');
  const canSeeRoles = has('roles.read');

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRoleId, setInviteRoleId] = useState<number | ''>('');

  const { data: members = [], isLoading } = useQuery({
    queryKey: ['firm', 'members'],
    queryFn: api.getMembers,
  });

  const { data: roles = [] } = useQuery({
    queryKey: ['firm', 'roles'],
    queryFn: api.getRoles,
    enabled: canSeeRoles,
  });

  const { data: invites = [] } = useQuery({
    queryKey: ['firm', 'invites'],
    queryFn: api.getInvites,
    enabled: canInvite,
  });

  const pendingInvites = invites.filter((i) => i.status === 'pending');

  const roleName = (id: number) => roles.find((r) => r.id === id)?.name ?? `Role #${id}`;

  const changeRole = useMutation({
    mutationFn: ({ userId, roleId }: { userId: number; roleId: number }) =>
      api.changeMemberRole(userId, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['firm', 'members'] });
      showToast('Role updated');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const removeMember = useMutation({
    mutationFn: (userId: number) => api.removeMember(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['firm', 'members'] });
      showToast('Member removed');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const sendInvite = useMutation({
    mutationFn: (data: { email: string; role_id: number }) => api.createInvite(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['firm', 'invites'] });
      setInviteEmail('');
      setInviteRoleId('');
      showToast('Invitation sent');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const revokeInvite = useMutation({
    mutationFn: (id: number) => api.revokeInvite(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['firm', 'invites'] });
      showToast('Invitation revoked');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail || inviteRoleId === '') return;
    sendInvite.mutate({ email: inviteEmail, role_id: Number(inviteRoleId) });
  };

  const isSelf = (m: FirmMember) =>
    !!user?.email && m.email.toLowerCase() === user.email.toLowerCase();

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="mb-10">
        <div className="page-eyebrow">Folio VI · Chambers</div>
        <h1 className="page-title">Team</h1>
        <p className="page-subtitle">
          The people in your firm and the role each one holds. Roles decide what
          a member can see and do.
        </p>
      </header>

      {/* Invite form */}
      {canInvite && (
        <section className="card p-6 mb-8">
          <div className="eyebrow mb-3">Invite a colleague</div>
          <form onSubmit={handleInvite} className="flex flex-col md:flex-row gap-3 md:items-end">
            <div className="flex-1">
              <label className="field-label">Email</label>
              <input
                type="email"
                required
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="field-input"
                placeholder="colleague@firm.com"
              />
            </div>
            <div className="md:w-56">
              <label className="field-label">Role</label>
              <select
                required
                value={inviteRoleId}
                onChange={(e) => setInviteRoleId(e.target.value === '' ? '' : Number(e.target.value))}
                className="field-select"
              >
                <option value="" disabled>Select a role…</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn-primary" disabled={sendInvite.isPending}>
              <UserPlus size={14} strokeWidth={2} />
              <span>Send invite</span>
            </button>
          </form>
          {!canSeeRoles && (
            <p className="text-2xs text-ink-faint mt-2">
              You need the Roles permission to choose a role for invitees.
            </p>
          )}
        </section>
      )}

      {/* Pending invites */}
      {canInvite && pendingInvites.length > 0 && (
        <section className="mb-8">
          <div className="eyebrow mb-3">Pending invitations</div>
          <div className="border border-rule divide-y divide-rule">
            {pendingInvites.map((inv) => (
              <div key={inv.id} className="bg-surface flex items-center gap-3 px-5 py-3">
                <Mail size={15} strokeWidth={1.5} className="text-ink-faint shrink-0" />
                <span className="text-sm text-ink flex-1 truncate">{inv.email}</span>
                <span className="text-2xs uppercase tracking-eyebrow text-ink-muted px-2 py-0.5
                                 bg-paper-deep rounded-sm">
                  {roleName(inv.role_id)}
                </span>
                <span className="hidden sm:flex items-center gap-1 text-2xs text-ink-faint">
                  <Clock size={11} strokeWidth={1.5} />
                  {inv.expires_at ? `expires ${new Date(inv.expires_at).toLocaleDateString()}` : ''}
                </span>
                <button
                  onClick={() => revokeInvite.mutate(inv.id)}
                  className="text-xs text-ink-muted hover:text-oxblood transition-colors"
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Members */}
      <section>
        <div className="eyebrow mb-3">Members</div>
        {isLoading ? (
          <div className="card p-16 flex justify-center"><div className="spinner" /></div>
        ) : (
          <div className="border border-rule divide-y divide-rule">
            {members.map((m) => (
              <div key={m.id} className="bg-surface flex items-center gap-4 px-5 py-4">
                <div className="shrink-0 h-9 w-9 rounded-full bg-paper-deep border border-rule
                                flex items-center justify-center font-display text-sm text-ink-soft"
                     style={{ fontVariationSettings: '"opsz" 48, "wght" 600' }}>
                  {m.email[0]?.toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-ink truncate font-medium">
                    {m.email}
                    {isSelf(m) && <span className="text-2xs text-ink-faint ml-2">(you)</span>}
                  </div>
                  <div className="text-2xs uppercase tracking-eyebrow text-ink-muted mt-0.5">
                    {m.role_name ?? '—'}
                  </div>
                </div>

                {canManageRoles && canSeeRoles ? (
                  <select
                    value={m.role_id ?? ''}
                    onChange={(e) => changeRole.mutate({ userId: m.id, roleId: Number(e.target.value) })}
                    className="field-select !py-1.5 !text-sm w-40"
                  >
                    {roles.map((r: FirmRole) => (
                      <option key={r.id} value={r.id}>{r.name}</option>
                    ))}
                  </select>
                ) : (
                  <span className="text-sm text-ink-muted w-40 text-right pr-1">{m.role_name}</span>
                )}

                {canRemove && !isSelf(m) ? (
                  <button
                    onClick={() => {
                      if (confirm(`Remove ${m.email} from the firm?`)) removeMember.mutate(m.id);
                    }}
                    className="p-1.5 text-ink-muted hover:text-oxblood hover:bg-oxblood-wash rounded-sm transition-colors"
                    title="Remove member"
                  >
                    <Trash2 size={14} strokeWidth={1.75} />
                  </button>
                ) : (
                  <span className="w-7" />
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
