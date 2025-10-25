import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function OnboardingWarning() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  // Don't show if user is onboarded or warning is dismissed
  if (!user || user.is_onboarded || dismissed) {
    return null;
  }

  return (
    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-yellow-400"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              <strong>Onboarding not complete!</strong> Complete your firm profile to unlock all features
              and create professional invoices.
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => navigate('/onboarding')}
            className="px-4 py-2 bg-yellow-400 text-yellow-900 rounded-md hover:bg-yellow-500 font-medium text-sm"
          >
            Complete Now
          </button>
          <button
            onClick={() => setDismissed(true)}
            className="px-4 py-2 bg-white text-yellow-700 border border-yellow-400 rounded-md hover:bg-yellow-50 font-medium text-sm"
          >
            Later
          </button>
        </div>
      </div>
    </div>
  );
}
