import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api';

interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_onboarded: boolean;
  created_at: string;
  last_login: string | null;
}

interface Firm {
  id: number;
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
  created_at?: string;
  updated_at?: string;
}

interface AuthContextType {
  user: User | null;
  firm: Firm | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, productKey?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [firm, setFirm] = useState<Firm | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const response = await api.getCurrentUser();
      setUser(response.user);
      setFirm(response.firm || null);
    } catch (error: any) {
      // Only logout if it's an authentication error (401)
      // Don't logout on network errors or other issues
      if (error.message?.includes('401') || error.message?.includes('Unauthorized')) {
        setUser(null);
        setFirm(null);
      }
      // Otherwise, keep the current user state and just log the error
      console.error('Failed to refresh user:', error);
      // Don't re-throw - let the caller continue
    }
  };

  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);
      await refreshUser();
      setIsLoading(false);
    };
    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await api.login(email, password);
    setUser(response.user);
    setFirm(response.firm || null);
  };

  const register = async (email: string, password: string, productKey?: string) => {
    const response = await api.register(email, password, productKey);
    setUser(response.user);
    setFirm(null);
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    setFirm(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        firm,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
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
