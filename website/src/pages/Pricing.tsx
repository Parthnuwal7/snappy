import { Check, X, Zap, Crown, Building2 } from 'lucide-react';
import { Link } from 'react-router-dom';

const Pricing = () => {
  const plans = [
    {
      name: 'Trial',
      icon: <Zap className="w-8 h-8" />,
      price: 0,
      period: '7 days',
      description: 'Try all features for free',
      features: [
        { text: 'Up to 10 invoices', included: true },
        { text: '5 clients', included: true },
        { text: 'Basic templates', included: true },
        { text: 'PDF export', included: true },
        { text: 'Cloud backup', included: false },
        { text: 'Advanced analytics', included: false },
        { text: 'Priority support', included: false },
        { text: 'Custom branding', included: false },
      ],
      cta: 'Start Free Trial',
      highlight: false,
    },
    {
      name: 'Starter',
      icon: <Zap className="w-8 h-8" />,
      price: 400,
      period: 'month',
      description: 'Perfect for solo practitioners',
      features: [
        { text: 'Unlimited invoices', included: true },
        { text: 'Unlimited clients', included: true },
        { text: 'All templates (LAW_001, etc.)', included: true },
        { text: 'PDF, CSV, Excel export', included: true },
        { text: 'Cloud backup (5GB)', included: true },
        { text: 'Basic analytics', included: true },
        { text: 'Email support', included: true },
        { text: 'Custom branding', included: false },
      ],
      cta: 'Get Started',
      highlight: false,
    },
    {
      name: 'Pro',
      icon: <Crown className="w-8 h-8" />,
      price: 1000,
      period: 'month',
      description: 'For growing practices',
      features: [
        { text: 'Everything in Starter', included: true },
        { text: 'Cloud backup (50GB)', included: true },
        { text: 'Advanced analytics & reports', included: true },
        { text: 'Automated payment reminders', included: true },
        { text: 'Recurring invoices', included: true },
        { text: 'Custom branding', included: true },
        { text: 'Priority email support', included: true },
        { text: 'Phone support', included: false },
      ],
      cta: 'Upgrade to Pro',
      highlight: true,
    },
    {
      name: 'Enterprise',
      icon: <Building2 className="w-8 h-8" />,
      price: 1500,
      period: 'month',
      description: 'For established firms',
      features: [
        { text: 'Everything in Pro', included: true },
        { text: 'Cloud backup (Unlimited)', included: true },
        { text: 'Multi-user access (5 users)', included: true },
        { text: 'Advanced permissions', included: true },
        { text: 'Dedicated account manager', included: true },
        { text: 'Priority phone support', included: true },
        { text: 'Custom integrations', included: true },
        { text: 'On-site training', included: true },
      ],
      cta: 'Contact Sales',
      highlight: false,
    },
  ];

  const faqs = [
    {
      question: 'Can I switch plans later?',
      answer: 'Yes! You can upgrade or downgrade your plan at any time. Changes take effect at the start of your next billing cycle.',
    },
    {
      question: 'What payment methods do you accept?',
      answer: 'We accept all major credit/debit cards, UPI, net banking, and wallets through Razorpay. All payments are secure and encrypted.',
    },
    {
      question: 'Is there a contract or can I cancel anytime?',
      answer: 'No contracts! You can cancel anytime. If you cancel, you can continue using SNAPPY until the end of your current billing period.',
    },
    {
      question: 'Do you offer annual billing?',
      answer: 'Yes! Pay annually and save 20%. Contact us for annual pricing and custom enterprise plans.',
    },
    {
      question: 'What happens after the trial ends?',
      answer: 'After your 7-day trial, you can choose a paid plan. Your data is preserved. If you don\'t subscribe, you\'ll have read-only access to your data.',
    },
    {
      question: 'Is there a setup fee?',
      answer: 'No setup fees or hidden charges. You only pay the monthly subscription price.',
    },
  ];

  return (
    <div className="bg-white min-h-screen py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Choose the plan that fits your practice. All plans include a 7-day free trial.
          </p>
          <div className="mt-6 inline-flex items-center bg-green-100 text-green-800 px-4 py-2 rounded-full">
            <Check className="w-5 h-5 mr-2" />
            <span className="font-semibold">Save 20% with annual billing</span>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
          {plans.map((plan, index) => (
            <div
              key={index}
              className={`rounded-2xl p-6 ${
                plan.highlight
                  ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-2xl ring-4 ring-blue-200 transform scale-105'
                  : 'bg-white border-2 border-gray-200'
              }`}
            >
              {plan.highlight && (
                <div className="bg-yellow-400 text-gray-900 text-xs font-bold px-3 py-1 rounded-full inline-block mb-4">
                  MOST POPULAR
                </div>
              )}
              
              <div className={`w-14 h-14 rounded-lg flex items-center justify-center mb-4 ${
                plan.highlight ? 'bg-white/20 text-white' : 'bg-blue-100 text-blue-600'
              }`}>
                {plan.icon}
              </div>

              <h3 className={`text-2xl font-bold mb-2 ${plan.highlight ? 'text-white' : 'text-gray-900'}`}>
                {plan.name}
              </h3>
              
              <p className={`text-sm mb-4 ${plan.highlight ? 'text-blue-100' : 'text-gray-600'}`}>
                {plan.description}
              </p>

              <div className="mb-6">
                <span className={`text-5xl font-bold ${plan.highlight ? 'text-white' : 'text-gray-900'}`}>
                  ₹{plan.price}
                </span>
                <span className={`text-lg ml-2 ${plan.highlight ? 'text-blue-100' : 'text-gray-600'}`}>
                  /{plan.period}
                </span>
              </div>

              <Link
                to="/download"
                className={`block w-full py-3 rounded-lg font-semibold text-center mb-6 transition-colors duration-200 ${
                  plan.highlight
                    ? 'bg-white text-blue-600 hover:bg-gray-100'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {plan.cta}
              </Link>

              <ul className="space-y-3">
                {plan.features.map((feature, fIndex) => (
                  <li key={fIndex} className="flex items-start">
                    {feature.included ? (
                      <Check className={`w-5 h-5 mr-2 flex-shrink-0 mt-0.5 ${
                        plan.highlight ? 'text-green-300' : 'text-green-600'
                      }`} />
                    ) : (
                      <X className={`w-5 h-5 mr-2 flex-shrink-0 mt-0.5 ${
                        plan.highlight ? 'text-white/40' : 'text-gray-400'
                      }`} />
                    )}
                    <span className={`text-sm ${
                      feature.included 
                        ? (plan.highlight ? 'text-white' : 'text-gray-700')
                        : (plan.highlight ? 'text-white/60' : 'text-gray-400')
                    }`}>
                      {feature.text}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Comparison Table */}
        <div className="mb-20">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            Compare All Features
          </h2>
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden overflow-x-auto">
            <p className="p-8 text-center text-gray-600">
              [Detailed feature comparison table placeholder - to be added]
            </p>
          </div>
        </div>

        {/* FAQs */}
        <div className="mb-20">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            Frequently Asked Questions
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {faqs.map((faq, index) => (
              <div key={index} className="bg-white border border-gray-200 rounded-xl p-6">
                <h3 className="font-semibold text-gray-900 mb-2">{faq.question}</h3>
                <p className="text-gray-600 text-sm">{faq.answer}</p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-8 text-white text-center">
          <h2 className="text-3xl font-bold mb-4">Still Have Questions?</h2>
          <p className="text-blue-100 mb-6">
            Our team is here to help you choose the right plan for your practice.
          </p>
          <Link
            to="/support"
            className="bg-white text-blue-600 px-8 py-3 rounded-lg hover:bg-gray-100 transition-colors duration-200 inline-block font-semibold"
          >
            Contact Us
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Pricing;
