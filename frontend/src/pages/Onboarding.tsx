import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';

export default function Onboarding() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [step, setStep] = useState(1);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    firm_name: '',
    firm_address: '',
    firm_email: '',
    firm_phone: '',
    firm_phone_2: '',
    firm_website: '',
    bank_name: '',
    account_number: '',
    account_holder_name: '',
    ifsc_code: '',
    upi_id: '',
    billing_terms: 'Payment due within 30 days of invoice date.\nLate payments may incur additional charges.\nAll disputes subject to local jurisdiction.',
    // Set default preferences (user can change later in Settings)
    default_template: 'LAW_001',
    invoice_prefix: 'LAW',
    default_tax_rate: 18.0,
    currency: 'INR',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'default_tax_rate' ? parseFloat(value) || 0 : value,
    }));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLFormElement>) => {
    // Handle Enter key behavior
    if (e.key === 'Enter') {
      const target = e.target as HTMLElement;
      
      // On step 1: Enter acts as Next button
      if (step < 2) {
        e.preventDefault();
        console.log('Enter key pressed on step 1 - prevented submission');
        nextStep();
        return;
      }
      
      // On step 2 (Banking Details): Enter acts as Tab, except on last field
      if (step === 2) {
        const isTextarea = target.tagName === 'TEXTAREA';
        const isBillingTerms = (target as HTMLInputElement).name === 'billing_terms';
        
        // If we're on the billing_terms textarea (last field), allow submit
        if (isTextarea && isBillingTerms) {
          console.log('Enter pressed on last field (billing_terms) - allowing submit');
          return; // Allow form submission
        }
        
        // For all other fields on step 2, treat Enter as Tab
        e.preventDefault();
        console.log('Enter pressed on step 2 field - acting as Tab');
        
        // Find all focusable elements
        const form = e.currentTarget;
        const focusableElements = form.querySelectorAll(
          'input:not([disabled]), textarea:not([disabled]), button:not([disabled])'
        );
        const focusableArray = Array.from(focusableElements) as HTMLElement[];
        const currentIndex = focusableArray.indexOf(target);
        
        // Move to next focusable element
        if (currentIndex > -1 && currentIndex < focusableArray.length - 1) {
          focusableArray[currentIndex + 1].focus();
        }
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Form submitted, current step:', step);
    setError('');

    // Only submit if we're on step 2 (Banking Details)
    if (step < 2) {
      console.log('Preventing early submission - not on final step');
      return;
    }

    // Validation
    if (!formData.firm_name.trim()) {
      setError('Firm name is required');
      return;
    }

    if (!formData.firm_address.trim()) {
      setError('Firm address is required');
      return;
    }

    setIsLoading(true);

    try {
      await api.onboard(formData);
      // Refresh user data to update onboarding status
      try {
        await refreshUser();
      } catch (refreshError) {
        console.error('Failed to refresh user data:', refreshError);
      }
      // Navigate regardless of refresh success
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Onboarding failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const nextStep = () => {
    console.log('Next step clicked, current step:', step);
    if (step === 1) {
      if (!formData.firm_name.trim()) {
        setError('Firm name is required');
        return;
      }
      if (!formData.firm_address.trim()) {
        setError('Firm address is required');
        return;
      }
    }
    setError('');
    console.log('Moving to step:', step + 1);
    setStep(step + 1);
  };

  const prevStep = () => {
    setError('');
    setStep(step - 1);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-indigo-600 mb-2">Welcome to SNAPPY</h1>
          <p className="text-gray-600">Let's set up your firm profile</p>
        </div>

        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center">
            {/* Step 1 */}
            <div className="flex items-center flex-1">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-colors ${
                  step >= 1 ? 'bg-indigo-600 text-white' : 'bg-gray-300 text-gray-600'
                }`}
              >
                1
              </div>
              <div className="flex-1 mx-2">
                <div className={`h-1 ${step > 1 ? 'bg-indigo-600' : 'bg-gray-300'}`} />
              </div>
            </div>
            
            {/* Step 2 */}
            <div className="flex items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-colors ${
                  step >= 2 ? 'bg-indigo-600 text-white' : 'bg-gray-300 text-gray-600'
                }`}
              >
                2
              </div>
            </div>
          </div>
          
          <div className="flex justify-between mt-2 px-1">
            <span className="text-sm text-gray-600 text-left" style={{ width: '50%' }}>Basic Info</span>
            <span className="text-sm text-gray-600 text-right" style={{ width: '50%' }}>Banking Details</span>
          </div>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-lg shadow-xl p-8">
          {error && (
            <div className="mb-6 p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} onKeyDown={handleKeyDown}>
            {/* Debug info - remove later */}
            <div className="mb-4 p-2 bg-gray-100 rounded text-xs text-gray-600">
              Current Step: {step} / 2
            </div>

            {/* Step 1: Basic Information */}
            {step === 1 && (
              <div className="space-y-4">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Basic Information</h3>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Firm Name *
                  </label>
                  <input
                    type="text"
                    name="firm_name"
                    required
                    value={formData.firm_name}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Your Law Firm Name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Firm Address *
                  </label>
                  <textarea
                    name="firm_address"
                    required
                    value={formData.firm_address}
                    onChange={handleChange}
                    rows={3}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Street Address, City, State, PIN Code"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    name="firm_email"
                    value={formData.firm_email}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="contact@yourfirm.com"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      name="firm_phone"
                      value={formData.firm_phone}
                      onChange={handleChange}
                      className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="+91-XXXXXXXXXX"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Phone Number 2
                    </label>
                    <input
                      type="tel"
                      name="firm_phone_2"
                      value={formData.firm_phone_2}
                      onChange={handleChange}
                      className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="+91-XXXXXXXXXX"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Website
                  </label>
                  <input
                    type="url"
                    name="firm_website"
                    value={formData.firm_website}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="https://www.yourfirm.com"
                  />
                </div>
              </div>
            )}

            {/* Step 2: Banking Details */}
            {step === 2 && (
              <div className="space-y-4">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Banking Details</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Add your banking information to include payment details on invoices. You can skip this and update later in Settings.
                </p>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Bank Name</label>
                  <input
                    type="text"
                    name="bank_name"
                    value={formData.bank_name}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="State Bank of India"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Account Holder Name
                  </label>
                  <input
                    type="text"
                    name="account_holder_name"
                    value={formData.account_holder_name}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Account holder name"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Account Number
                    </label>
                    <input
                      type="text"
                      name="account_number"
                      value={formData.account_number}
                      onChange={handleChange}
                      className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="1234567890"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">IFSC Code</label>
                    <input
                      type="text"
                      name="ifsc_code"
                      value={formData.ifsc_code}
                      onChange={handleChange}
                      className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      placeholder="SBIN0001234"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">UPI ID</label>
                  <input
                    type="text"
                    name="upi_id"
                    value={formData.upi_id}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="yourfirm@oksbi"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Billing Terms & Conditions
                  </label>
                  <textarea
                    name="billing_terms"
                    value={formData.billing_terms}
                    onChange={handleChange}
                    rows={4}
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    placeholder="Payment terms..."
                  />
                </div>
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex justify-between mt-8 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={prevStep}
                disabled={step === 1}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>

              {step < 2 ? (
                <button
                  type="button"
                  onClick={nextStep}
                  className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? 'Completing...' : 'Complete Setup'}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
