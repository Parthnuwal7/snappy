import { useAuth } from '../contexts/AuthContext';

/**
 * Permission gate sourced from the `/me` membership block.
 *
 * `has('clients.create')` mirrors the backend `require_permission` check, so a
 * button hidden here lines up with a 403 the server would return anyway.
 * The Owner role resolves server-side to the full catalog, so `has` is true
 * for every key when the caller is an Owner.
 */
export function usePermissions() {
  const { membership } = useAuth();
  const permissions = membership?.permissions ?? [];

  const has = (perm: string) => permissions.includes(perm);
  const hasAny = (...perms: string[]) => perms.some((p) => permissions.includes(p));

  return {
    permissions,
    role: membership?.role ?? null,
    isOwner: membership?.role?.name === 'Owner' && !!membership?.role?.is_system,
    has,
    hasAny,
  };
}
