import { Play, FileText, Users, BarChart, Cloud, CheckCircle } from 'lucide-react';

const Demo = () => {
  const features = [
    {
      icon: <FileText className="w-6 h-6" />,
      title: 'Invoice Generation',
      description: 'Create professional invoices in seconds with customizable templates',
    },
    {
      icon: <Users className="w-6 h-6" />,
      title: 'Client Management',
      description: 'Keep all client information organized in one place',
    },
    {
      icon: <BarChart className="w-6 h-6" />,
      title: 'Analytics Dashboard',
      description: 'Track revenue, aging reports, and business insights',
    },
    {
      icon: <Cloud className="w-6 h-6" />,
      title: 'Cloud Backup',
      description: 'Automatic encrypted backups ensure your data is safe',
    },
  ];

  const demoSteps = [
    {
      title: 'Create Your First Invoice',
      description: 'Start by adding a client and creating your first invoice. Choose from professional templates like LAW_001, perfect for legal professionals.',
      image: '[Invoice creation screenshot]',
    },
    {
      title: 'Manage Your Clients',
      description: 'Add unlimited clients with all their details. Track payment history, outstanding invoices, and more from one central location.',
      image: '[Client management screenshot]',
    },
    {
      title: 'View Analytics',
      description: 'Get insights into your business with powerful analytics. See revenue trends, top clients, and aging reports at a glance.',
      image: '[Analytics dashboard screenshot]',
    },
    {
      title: 'Export & Share',
      description: 'Export invoices to PDF, CSV, or Excel. Print or email directly to clients. Everything you need in one place.',
      image: '[Export options screenshot]',
    },
  ];

  return (
    <div className="bg-white min-h-screen py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            See SNAPPY in Action
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Explore the features that make SNAPPY the perfect billing solution for legal professionals
          </p>
        </div>

        {/* Video Demo Placeholder */}
        <div className="mb-20">
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-8">
            <div className="aspect-video bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
              <div className="text-center text-white">
                <div className="w-24 h-24 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center mx-auto mb-6">
                  <Play className="w-12 h-12" />
                </div>
                <h3 className="text-2xl font-bold mb-2">Watch Product Demo</h3>
                <p className="text-blue-100">[Video coming soon]</p>
                <button className="mt-6 bg-white text-blue-600 px-8 py-3 rounded-lg hover:bg-gray-100 transition-colors duration-200 font-semibold">
                  Play Demo Video
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Key Features */}
        <div className="mb-20">
          <h2 className="text-3xl font-bold text-gray-900 mb-12 text-center">
            Key Features
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow duration-200"
              >
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600 text-sm">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Step-by-Step Walkthrough */}
        <div className="mb-20">
          <h2 className="text-3xl font-bold text-gray-900 mb-12 text-center">
            Step-by-Step Walkthrough
          </h2>
          <div className="space-y-12">
            {demoSteps.map((step, index) => (
              <div
                key={index}
                className={`grid md:grid-cols-2 gap-8 items-center ${
                  index % 2 === 1 ? 'md:flex-row-reverse' : ''
                }`}
              >
                <div className={index % 2 === 1 ? 'md:order-2' : ''}>
                  <div className="inline-block bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-semibold mb-4">
                    Step {index + 1}
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 mb-4">
                    {step.title}
                  </h3>
                  <p className="text-gray-600 mb-6">{step.description}</p>
                  <div className="flex items-center text-blue-600 font-semibold">
                    <CheckCircle className="w-5 h-5 mr-2" />
                    <span>Easy to use</span>
                  </div>
                </div>

                <div className={index % 2 === 1 ? 'md:order-1' : ''}>
                  <div className="bg-gray-100 rounded-xl p-8 shadow-lg">
                    <div className="aspect-video bg-white rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300">
                      <div className="text-center text-gray-500">
                        <FileText className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                        <p className="font-medium">{step.image}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Interactive Demo CTA */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-12 text-white text-center mb-20">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Try It Yourself?
          </h2>
          <p className="text-blue-100 text-lg mb-8 max-w-2xl mx-auto">
            The best way to experience SNAPPY is to use it. Download now and start your free 7-day trial.
            No credit card required.
          </p>
          <a
            href="/download"
            className="inline-block bg-white text-blue-600 px-10 py-4 rounded-lg hover:bg-gray-100 transition-colors duration-200 font-semibold text-lg"
          >
            Download Free Trial
          </a>
        </div>

        {/* Screenshots Gallery */}
        <div className="mb-20">
          <h2 className="text-3xl font-bold text-gray-900 mb-12 text-center">
            Screenshots
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              'Dashboard Overview',
              'Invoice Creation',
              'Client Management',
              'Analytics Report',
              'Settings Panel',
              'Export Options',
            ].map((title, index) => (
              <div key={index} className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow duration-200">
                <div className="aspect-video bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center">
                  <div className="text-center text-gray-600">
                    <BarChart className="w-16 h-16 mx-auto mb-3 text-blue-600" />
                    <p className="font-semibold">[{title}]</p>
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-gray-900">{title}</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Clean and intuitive interface
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Testimonial */}
        <div className="bg-gray-50 rounded-2xl p-12 text-center">
          <div className="max-w-3xl mx-auto">
            <div className="flex justify-center mb-6">
              {[...Array(5)].map((_, i) => (
                <svg
                  key={i}
                  className="w-8 h-8 text-yellow-400 fill-current"
                  viewBox="0 0 20 20"
                >
                  <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z" />
                </svg>
              ))}
            </div>
            <p className="text-xl text-gray-700 italic mb-6">
              "SNAPPY has completely transformed how I manage my practice's billing. 
              The interface is incredibly intuitive, and the offline capability is a game-changer. 
              I can't imagine going back to my old system."
            </p>
            <div className="font-semibold text-gray-900">Advocate Sharma</div>
            <div className="text-gray-600">Senior Partner, Law Firm</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Demo;
