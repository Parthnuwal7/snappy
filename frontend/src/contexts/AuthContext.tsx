import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Session, User as SupabaseUser } from '@supabase/supabase-js';
import { supabase, getDeviceId, getDeviceInfo } from '../lib/supabase';

// Types for user profile and firm (fetched from our backend)
interface UserProfile {
  id: string;
  device_id: string | null;
  device_info: Record<string, unknown> | null;
  is_onboarded: boolean;
  created_at: string;
  updated_at: string;
}

interface Firm {
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
  upi_qr_path?: string;
  terms_and_conditions?: string;
  billing_terms?: string;
  default_template: string;
  invoice_prefix: string;
  default_tax_rate: number;
  currency: string;
  show_due_date?: boolean;
  created_at?: string;
  updated_at?: string;
}

interface AuthContextType {
  user: SupabaseUser | null;
  session: Session | null;
  profile: UserProfile | null;
  firm: Firm | null;
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
  const [isLoading, setIsLoading] = useState(true);

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
        setFirm(data.firm || null);
      } else if (response.status === 404) {
        // Profile doesn't exist yet - user needs to complete onboarding
        setProfile(null);
        setFirm(null);
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

        if (newSession?.access_token) {
          await fetchProfile(newSession.access_token);

          // Update device info on sign in
          if (event === 'SIGNED_IN') {
            await updateDeviceInfo(newSession.access_token);
          }
        } else {
          setProfile(null);
          setFirm(null);
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
