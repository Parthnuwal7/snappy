import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Home from './pages/Home';
import Writing from './pages/Writing';
import NewInvoice from './pages/NewInvoice';
import InvoiceList from './pages/InvoiceList';
import Clients from './pages/Clients';
import Settings from './pages/Settings';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Onboarding from './pages/Onboarding';
import Items from './pages/Items';
import Recurring from './pages/Recurring';
import LegalFeed from './pages/LegalFeed';
import PublicInvoice from './pages/PublicInvoice';
import Team from './pages/Team';
import Roles from './pages/Roles';
import AcceptInvite from './pages/AcceptInvite';
import InviteeProfile from './pages/InviteeProfile';
import CasesLayout from './pages/CasesLayout';
import CasesKanban from './pages/CasesKanban';
import CaseVault from './pages/CaseVault';
import CaseCalendar from './pages/CaseCalendar';
import CaseDetail from './pages/CaseDetail';
import CauseListPrint from './pages/CauseListPrint';
import DraftEditor from './pages/DraftEditor';
import TemplateEditor from './pages/TemplateEditor';
import DraftPrint from './pages/DraftPrint';

function App() {
  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const modKey = isMac ? e.metaKey : e.ctrlKey;

      if (modKey && e.key === 'k') {
        e.preventDefault();
        // Focus search input (implement in InvoiceList)
        const searchInput = document.querySelector<HTMLInputElement>('[data-search]');
        searchInput?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <Routes>
          {/* Public Routes */}
          <Route path="/i/:userId/:invoiceId/:sig" element={<PublicInvoice />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          {/* Invite acceptance: authenticated but not gated on onboarding —
              the invitee has a login but no firm until they accept. */}
          <Route
            path="/accept-invite/:token"
            element={
              <ProtectedRoute>
                <AcceptInvite />
              </ProtectedRoute>
            }
          />
          <Route
            path="/onboarding"
            element={
              <ProtectedRoute>
                <Onboarding />
              </ProtectedRoute>
            }
          />
          {/* Invitee profile capture after a token-based accept. */}
          <Route
            path="/invitee-profile"
            element={
              <ProtectedRoute>
                <InviteeProfile />
              </ProtectedRoute>
            }
          />
          {/* Printable cause-list: auth-gated but chrome-free (outside Layout) */}
          <Route
            path="/print/cause-list"
            element={
              <ProtectedRoute requireOnboarding>
                <CauseListPrint />
              </ProtectedRoute>
            }
          />
          <Route
            path="/print/draft/:id"
            element={
              <ProtectedRoute requireOnboarding>
                <DraftPrint />
              </ProtectedRoute>
            }
          />

          {/* Protected Routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute requireOnboarding>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Home />} />
            <Route path="dashboard" element={<Navigate to="/reports" replace />} />
            <Route path="writing" element={<Writing />} />
            <Route path="writing/draft/:id" element={<DraftEditor />} />
            <Route path="writing/template/:id" element={<TemplateEditor />} />
            <Route path="invoices" element={<InvoiceList />} />
            <Route path="invoices/new" element={<NewInvoice />} />
            <Route path="recurring" element={<Recurring />} />
            <Route path="invoices/:id/edit" element={<NewInvoice />} />
            <Route path="cases" element={<CasesLayout />}>
              <Route index element={<CasesKanban />} />
              <Route path="vault" element={<CaseVault />} />
              <Route path="calendar" element={<CaseCalendar />} />
            </Route>
            <Route path="cases/:id" element={<CaseDetail />} />
            <Route path="clients" element={<Clients />} />
            <Route path="items" element={<Items />} />
            <Route path="legal-feed" element={<LegalFeed />} />
            <Route path="reports" element={<Dashboard />} />
            <Route path="team" element={<Team />} />
            <Route path="roles" element={<Roles />} />
            <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
