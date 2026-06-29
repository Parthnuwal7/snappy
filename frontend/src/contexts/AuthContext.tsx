import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { Session, User as SupabaseUser } from '@supabase/supabase-js';
import { supabase, getDeviceId, getDeviceInfo } from '../lib/supabase';

// Types for user profile and firm (fetched from our backend)
interface UserProfile {
  id: string;
  device_id: string | null;
  device_info: Record<string, unknown> | null;
  is_onboarded: boolean;
  full_name: string | null;
  designation: string | null;
  bar_council_number: string | null;
  personal_phone: string | null;
  is_solo: boolean | null;
  checklist_dismissed: boolean;
  created_at: string;
  updated_at: string;
}

export interface SetupState {
  bank: boolean;
  branding: boolean;
  billing: boolean;
  team: boolean;
  dismissed: boolean;
  complete: boolean;
}

export interface PendingInvite {
  firm_name: string;
  role_name: string;
}

export interface Firm {
  id: string;
  user_id: string;
  firm_name: string;
  firm_address: string;
  firm_email?: string;
  firm_phone?: string;
  firm_phone_2?: string;
  firm_website?: string;
  logo_path?: string;
  signature_path?: string;
  bank_name?: string;
  account_number?: string;
  account_holder_name?: string;
  ifsc_code?: string;
  upi_id?: string;
  upi_payee_name?: string;
  upi_note?: string;
  terms_and_conditions?: string;
  billing_terms?: string;
  email_subject_template?: string;
  email_body_template?: string;
  whatsapp_template?: string;
  default_template: string;
  invoice_prefix: string;
  use_invoice_prefix?: boolean;
  default_tax_rate: number;
  currency: string;
  show_due_date?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Membership {
  firm_id: number;
  role: { id: number; name: string; is_system: boolean };
  permissions: string[];
}

interface AuthContextType {
  user: SupabaseUser | null;
  session: Session | null;
  profile: UserProfile | null;
  firm: Firm | null;
  membership: Membership | null;
  setup: SetupState | null;
  pendingInvite: PendingInvite | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isOnboarded: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  updatePassword: (newPassword: string) => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// API base URL for backend calls
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1';

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<SupabaseUser | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [firm, setFirm] = useState<Firm | null>(null);
  const [membership, setMembership] = useState<Membership | null>(null);
  const [setup, setSetup] = useState<SetupState | null>(null);
  const [pendingInvite, setPendingInvite] = useState<PendingInvite | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // supabase-js re-emits SIGNED_IN on every tab focus and TOKEN_REFRESHED on the
  // auto-refresh timer. Track identity so we only re-fetch the profile when the
  // user actually changes, and only push device info once per real sign-in —
  // otherwise every focus fires /auth/me + /auth/device needlessly.
  const lastUserId = useRef<string | null>(null);
  const deviceSynced = useRef(false);

  // Fetch user profile and firm from backend
  const fetchProfile = useCallback(async (accessToken: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setProfile(data.profile || null);
        setMembership(data.membership || null);
        setSetup(data.setup || null);
        setPendingInvite(data.pending_invite || null);

        // Merge bank data into firm object for Settings page compatibility
        if (data.firm) {
          const firmWithBank = {
            ...data.firm,
            ...(data.bank && {
              bank_name: data.bank.bank_name,
              account_number: data.bank.account_number,
              account_holder_name: data.bank.account_holder_name,
              ifsc_code: data.bank.ifsc_code,
              upi_id: data.bank.upi_id,
              upi_payee_name: data.bank.upi_payee_name,
              upi_note: data.bank.upi_note,
            }),
          };
          setFirm(firmWithBank);
        } else {
          setFirm(null);
        }
      } else if (response.status === 404) {
        // Profile doesn't exist yet - user needs to complete onboarding
        setProfile(null);
        setFirm(null);
        setMembership(null);
        setSetup(null);
        setPendingInvite(null);
      } else {
        // Transient error (most commonly 401 from JWT clock-skew on first
        // call after login). Don't blank out the profile — leave whatever
        // state we had so the user isn't bounced to /onboarding just because
        // one request failed. Log so we can see it in dev tools.
        const body = await response.text().catch(() => '');
        console.warn(
          `[auth/me] ${response.status} ${response.statusText} — keeping prior profile state`,
          body,
        );
      }
    } catch (error) {
      console.error('Error fetching profile:', error);
    }
  }, []);

  // Update device info on login
  const updateDeviceInfo = useCallback(async (accessToken: string) => {
    try {
      const deviceId = getDeviceId();
      const deviceInfo = getDeviceInfo();

      await fetch(`${API_BASE_URL}/auth/device`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          device_id: deviceId,
          device_info: deviceInfo,
        }),
      });
    } catch (error) {
      console.error('Error updating device info:', error);
    }
  }, []);

  // Initialize auth state
  useEffect(() => {
    const initializeAuth = async () => {
      setIsLoading(true);

      // Get initial session
      const { data: { session: initialSession } } = await supabase.auth.getSession();

      if (initialSession) {
        setSession(initialSession);
        setUser(initialSession.user);
        lastUserId.current = initialSession.user.id;
        await fetchProfile(initialSession.access_token);
      }

      setIsLoading(false);
    };

    initializeAuth();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event: string, newSession: Session | null) => {
        setSession(newSession);
        setUser(newSession?.user ?? null);

        const uid = newSession?.user?.id ?? null;

        if (!uid || !newSession?.access_token) {
          lastUserId.current = null;
          deviceSynced.current = false;
          setProfile(null);
          setFirm(null);
          setMembership(null);
          setSetup(null);
          setPendingInvite(null);
          return;
        }

        // Only re-fetch the profile when the user genuinely changed — skip the
        // redundant SIGNED_IN re-emits supabase fires on tab focus / refresh.
        if (uid !== lastUserId.current) {
          lastUserId.current = uid;
          await fetchProfile(newSession.access_token);
        }

        // Push device info once per real sign-in, not on every focus event.
        if (event === 'SIGNED_IN' && !deviceSynced.current) {
          deviceSynced.current = true;
          await updateDeviceInfo(newSession.access_token);
        }
      }
    );

    return () => {
      subscription.unsubscribe();
    };
  }, [fetchProfile, updateDeviceInfo]);

  const login = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      throw new Error(error.message);
    }
  };

  const register = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          device_id: getDeviceId(),
        },
      },
    });

    if (error) {
      throw new Error(error.message);
    }
  };

  const logout = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      throw new Error(error.message);
    }
    setUser(null);
    setSession(null);
    setProfile(null);
    setFirm(null);
    setMembership(null);
    setSetup(null);
    setPendingInvite(null);
  };

  const resetPassword = async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });

    if (error) {
      throw new Error(error.message);
    }
  };

  const updatePassword = async (newPassword: string) => {
    const { error } = await supabase.auth.updateUser({
      password: newPassword,
    });

    if (error) {
      throw new Error(error.message);
    }
  };

  const refreshProfile = async () => {
    if (session?.access_token) {
      await fetchProfile(session.access_token);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        firm,
        membership,
        setup,
        pendingInvite,
        isAuthenticated: !!user,
        isLoading,
        isOnboarded: profile?.is_onboarded ?? false,
        login,
        register,
        logout,
        resetPassword,
        updatePassword,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
