import { Link } from 'react-router-dom';
import { 
  Zap, Shield, Cloud, BarChart, FileText, Users, 
  Check, ArrowRight, Download, Star 
} from 'lucide-react';

const Home = () => {
  const features = [
    {
      icon: <FileText className="w-8 h-8" />,
      title: 'Professional Invoices',
      description: 'Create beautiful, professional invoices with customizable templates including LAW_001 format perfect for legal professionals.',
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: 'Client Management',
      description: 'Manage all your clients in one place. Track contact information, billing history, and payment status effortlessly.',
    },
    {
      icon: <BarChart className="w-8 h-8" />,
      title: 'Advanced Analytics',
      description: 'Get insights into your business with powerful analytics. Track revenue, top clients, and aging reports.',
    },
    {
      icon: <Cloud className="w-8 h-8" />,
      title: 'Cloud Backup',
      description: 'Automatic encrypted backups to the cloud. Your data is safe and accessible from anywhere.',
    },
    {
      icon: <Zap className="w-8 h-8" />,
      title: 'Lightning Fast',
      description: 'Desktop app works offline. No internet required for core functionality. Blazing fast performance.',
    },
    {
      icon: <Shield className="w-8 h-8" />,
      title: 'Secure & Private',
      description: 'Your data stays on your device. Industry-standard encryption for cloud backups. GDPR compliant.',
    },
  ];

  const benefits = [
    'Save 10+ hours per month on billing',
    'Professional GST-compliant invoices',
    'Works offline - no internet required',
    'Automatic payment reminders',
    'Detailed business analytics',
    'Export to CSV, PDF, Excel',
  ];

  const testimonials = [
    {
      name: 'Advocate Sharma',
      role: 'Senior Partner, Law Firm',
      content: 'SNAPPY has transformed how we handle billing. The LAW_001 format is perfect for our needs, and the client management features are excellent.',
      rating: 5,
    },
    {
      name: 'CA Priya Mehta',
      role: 'Chartered Accountant',
      content: 'As a CA, I needed billing software that was fast, reliable, and worked offline. SNAPPY checks all the boxes. Highly recommended!',
      rating: 5,
    },
    {
      name: 'Advocate Kumar',
      role: 'Solo Practitioner',
      content: 'The best investment I made for my practice. Easy to use, professional invoices, and the price is very reasonable.',
      rating: 5,
    },
  ];

  return (
    <div className="bg-white">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-blue-50 via-white to-indigo-50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div>
              <div className="inline-block bg-blue-100 text-blue-800 px-4 py-1 rounded-full text-sm font-semibold mb-6">
                Professional Billing Made Simple
              </div>
              <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
                Billing Software for
                <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                  {' '}Legal Professionals
                </span>
              </h1>
              <p className="text-xl text-gray-600 mb-8">
                Create professional invoices, manage clients, and track payments effortlessly. 
                Perfect for lawyers, CAs, and consultants. Works offline with cloud sync.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link
                  to="/download"
                  className="bg-blue-600 text-white px-8 py-4 rounded-lg hover:bg-blue-700 transition-colors duration-200 flex items-center justify-center space-x-2 text-lg font-semibold"
                >
                  <Download size={20} />
                  <span>Download for Windows</span>
                </Link>
                <Link
                  to="/demo"
                  className="border-2 border-blue-600 text-blue-600 px-8 py-4 rounded-lg hover:bg-blue-50 transition-colors duration-200 flex items-center justify-center space-x-2 text-lg font-semibold"
                >
                  <span>Try Demo</span>
                  <ArrowRight size={20} />
                </Link>
              </div>
              <p className="text-sm text-gray-500 mt-4">
                🎉 Free 7-day trial • No credit card required • ₹400/month after trial
              </p>
            </div>

            {/* Right Content - Placeholder Image */}
            <div className="relative">
              <div className="bg-gradient-to-br from-blue-100 to-indigo-100 rounded-2xl p-8 shadow-2xl">
                <div className="bg-white rounded-lg shadow-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-32 h-6 bg-gray-200 rounded"></div>
                    <div className="w-24 h-6 bg-blue-600 rounded"></div>
                  </div>
                  <div className="space-y-3">
                    <div className="w-full h-4 bg-gray-100 rounded"></div>
                    <div className="w-3/4 h-4 bg-gray-100 rounded"></div>
                    <div className="w-5/6 h-4 bg-gray-100 rounded"></div>
                  </div>
                  <div className="mt-6 pt-4 border-t border-gray-200">
                    <div className="flex justify-between mb-2">
                      <div className="w-24 h-3 bg-gray-100 rounded"></div>
                      <div className="w-20 h-3 bg-gray-200 rounded"></div>
                    </div>
                    <div className="flex justify-between mb-2">
                      <div className="w-24 h-3 bg-gray-100 rounded"></div>
                      <div className="w-20 h-3 bg-gray-200 rounded"></div>
                    </div>
                    <div className="flex justify-between pt-2 border-t border-gray-200">
                      <div className="w-24 h-4 bg-gray-200 rounded"></div>
                      <div className="w-24 h-4 bg-blue-600 rounded"></div>
                    </div>
                  </div>
                </div>
              </div>
              {/* Floating badges */}
              <div className="absolute -top-4 -right-4 bg-white rounded-lg shadow-lg px-4 py-2">
                <div className="flex items-center space-x-1">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} size={16} className="text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className="text-xs text-gray-600 mt-1">Rated 5/5</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Everything You Need to Run Your Practice
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Powerful features designed specifically for legal professionals and consultants
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow duration-200"
              >
                <div className="w-14 h-14 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left - Benefits List */}
            <div>
              <h2 className="text-4xl font-bold text-gray-900 mb-6">
                Why Choose SNAPPY?
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                Built specifically for Indian legal professionals and consultants. 
                We understand your billing needs.
              </p>
              <ul className="space-y-4">
                {benefits.map((benefit, index) => (
                  <li key={index} className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
                      <Check size={14} className="text-green-600" />
                    </div>
                    <span className="text-gray-700">{benefit}</span>
                  </li>
                ))}
              </ul>
              <Link
                to="/pricing"
                className="inline-block mt-8 bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition-colors duration-200"
              >
                View Pricing Plans
              </Link>
            </div>

            {/* Right - Stats */}
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-white rounded-xl p-6 shadow-lg">
                <div className="text-4xl font-bold text-blue-600 mb-2">10+</div>
                <div className="text-gray-600">Hours Saved Per Month</div>
              </div>
              <div className="bg-white rounded-xl p-6 shadow-lg">
                <div className="text-4xl font-bold text-blue-600 mb-2">100%</div>
                <div className="text-gray-600">GST Compliant</div>
              </div>
              <div className="bg-white rounded-xl p-6 shadow-lg">
                <div className="text-4xl font-bold text-blue-600 mb-2">0</div>
                <div className="text-gray-600">Internet Required</div>
              </div>
              <div className="bg-white rounded-xl p-6 shadow-lg">
                <div className="text-4xl font-bold text-blue-600 mb-2">₹400</div>
                <div className="text-gray-600">Starting Price/Month</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Trusted by Professionals
            </h2>
            <p className="text-xl text-gray-600">
              See what our users have to say
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <div
                key={index}
                className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow duration-200"
              >
                <div className="flex items-center mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} size={18} className="text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className="text-gray-700 mb-4 italic">"{testimonial.content}"</p>
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-semibold mr-3">
                    {testimonial.name.charAt(0)}
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900">{testimonial.name}</div>
                    <div className="text-sm text-gray-500">{testimonial.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl font-bold mb-6">
            Ready to Streamline Your Billing?
          </h2>
          <p className="text-xl mb-8 text-blue-100">
            Join hundreds of legal professionals who trust SNAPPY for their billing needs.
            Start your free 7-day trial today.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/download"
              className="bg-white text-blue-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors duration-200 flex items-center justify-center space-x-2 text-lg font-semibold"
            >
              <Download size={20} />
              <span>Download Now</span>
            </Link>
            <Link
              to="/pricing"
              className="border-2 border-white text-white px-8 py-4 rounded-lg hover:bg-white hover:text-blue-600 transition-colors duration-200 flex items-center justify-center text-lg font-semibold"
            >
              View Pricing
            </Link>
          </div>
          <p className="text-sm text-blue-100 mt-6">
            No credit card required • 7-day free trial • Cancel anytime
          </p>
        </div>
      </section>
    </div>
  );
};

export default Home;
