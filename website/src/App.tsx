import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { useEffect } from 'react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Download from './pages/Download';
import Pricing from './pages/Pricing';
import Support from './pages/Support';
import About from './pages/About';
import Demo from './pages/Demo';
import Admin from './pages/Admin';
import Register from './pages/Register';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AdminPaymentVerification from './pages/AdminPaymentVerification';
import AdminLicenseManager from './pages/AdminLicenseManager';

// Wake up backend on app load
const wakeUpBackend = async () => {
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/health`, {
      method: 'GET',
    });
    if (response.ok) {
      console.log('✅ Backend is awake');
    }
  } catch (error) {
    console.log('⏳ Waking up backend...');
  }
};

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

function App() {
  // Wake up backend when app loads
  useEffect(() => {
    wakeUpBackend();
  }, []);

  return (
    <Router>
      <AuthProvider>
        <div className="min-h-screen flex flex-col">
          <Navbar />
          <main className="flex-grow">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/download" element={<Download />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/support" element={<Support />} />
              <Route path="/about" element={<About />} />
              <Route path="/demo" element={<Demo />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/admin/payments" element={<AdminPaymentVerification />} />
              <Route path="/admin/licenses" element={<AdminLicenseManager />} />
              <Route path="/register" element={<Register />} />
              <Route path="/login" element={<Login />} />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </main>
          <Footer />
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;
