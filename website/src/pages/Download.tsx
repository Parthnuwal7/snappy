import { Download as DownloadIcon, CheckCircle, AlertCircle, Laptop } from 'lucide-react';

const Download = () => {
  const systemRequirements = [
    'Windows 10 or later (64-bit)',
    '4GB RAM minimum (8GB recommended)',
    '500MB free disk space',
    '.NET Framework 4.7.2 or later',
    'Internet connection for cloud sync (optional)',
  ];

  const installationSteps = [
    {
      title: 'Download the Installer',
      description: 'Click the download button above to get the latest version of SNAPPY for Windows.',
    },
    {
      title: 'Run the Installer',
      description: 'Double-click the downloaded .msi file. Windows may show a security warning - click "Run anyway".',
    },
    {
      title: 'Follow the Setup Wizard',
      description: 'Accept the license agreement and choose your installation folder. The default location is recommended.',
    },
    {
      title: 'Complete Installation',
      description: 'Wait for the installation to finish. This usually takes 1-2 minutes.',
    },
    {
      title: 'Launch SNAPPY',
      description: 'Find SNAPPY in your Start menu or desktop shortcut. Create your account and start billing!',
    },
  ];

  return (
    <div className="bg-white min-h-screen py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-100 rounded-full mb-6">
            <DownloadIcon className="w-10 h-10 text-blue-600" />
          </div>
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Download SNAPPY
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Get the desktop app for Windows. Works offline with cloud sync when connected.
          </p>
        </div>

        {/* Download Button */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-8 mb-16 text-white text-center">
          <h2 className="text-3xl font-bold mb-4">SNAPPY for Windows</h2>
          <p className="text-blue-100 mb-6">Version 1.0.0 • Released: January 2026 • Size: 45MB</p>
          <button className="bg-white text-blue-600 px-10 py-4 rounded-lg hover:bg-gray-100 transition-colors duration-200 inline-flex items-center space-x-3 text-lg font-semibold">
            <DownloadIcon size={24} />
            <span>Download SNAPPY-Setup.msi</span>
          </button>
          <p className="text-sm text-blue-100 mt-4">
            Free 7-day trial included • No credit card required
          </p>
        </div>

        {/* System Requirements */}
        <div className="grid md:grid-cols-2 gap-12 mb-16">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-6">
              System Requirements
            </h2>
            <div className="bg-gray-50 rounded-xl p-6">
              <div className="flex items-center mb-4">
                <Laptop className="w-6 h-6 text-blue-600 mr-2" />
                <span className="font-semibold text-gray-900">Minimum Requirements</span>
              </div>
              <ul className="space-y-3">
                {systemRequirements.map((req, index) => (
                  <li key={index} className="flex items-start">
                    <CheckCircle className="w-5 h-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">{req}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Important Notes */}
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-6">
              Important Notes
            </h2>
            <div className="space-y-4">
              <div className="bg-blue-50 border-l-4 border-blue-600 p-4 rounded">
                <div className="flex items-start">
                  <AlertCircle className="w-5 h-5 text-blue-600 mr-2 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">Offline Capability</h3>
                    <p className="text-sm text-gray-700">
                      SNAPPY works completely offline. Internet is only needed for cloud backups and license validation (checked every 7 days).
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-green-50 border-l-4 border-green-600 p-4 rounded">
                <div className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">Automatic Updates</h3>
                    <p className="text-sm text-gray-700">
                      SNAPPY checks for updates automatically. You'll be notified when a new version is available.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-yellow-50 border-l-4 border-yellow-600 p-4 rounded">
                <div className="flex items-start">
                  <AlertCircle className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">Windows Defender</h3>
                    <p className="text-sm text-gray-700">
                      Windows may show a security warning on first run. Click "More info" and "Run anyway". SNAPPY is safe and virus-free.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Installation Guide */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            Installation Guide
          </h2>
          <div className="grid md:grid-cols-5 gap-6">
            {installationSteps.map((step, index) => (
              <div key={index} className="relative">
                <div className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow duration-200">
                  <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg mb-4">
                    {index + 1}
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2">{step.title}</h3>
                  <p className="text-sm text-gray-600">{step.description}</p>
                </div>
                {index < installationSteps.length - 1 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 w-6 h-0.5 bg-gray-300"></div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Screenshot Placeholder */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            What You'll See
          </h2>
          <div className="bg-gray-100 rounded-xl p-8">
            <div className="bg-white rounded-lg shadow-xl">
              <div className="bg-gray-800 px-4 py-2 rounded-t-lg flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-white text-sm ml-4">SNAPPY - Professional Billing</span>
              </div>
              <div className="aspect-video bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Laptop className="w-12 h-12 text-blue-600" />
                  </div>
                  <p className="text-gray-600 font-semibold">[Screenshot of SNAPPY Dashboard]</p>
                  <p className="text-sm text-gray-500 mt-2">Clean, intuitive interface</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Need Help? */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-8 text-white text-center">
          <h2 className="text-3xl font-bold mb-4">Need Help?</h2>
          <p className="text-blue-100 mb-6">
            Having trouble installing or using SNAPPY? We're here to help!
          </p>
          <a
            href="/support"
            className="bg-white text-blue-600 px-8 py-3 rounded-lg hover:bg-gray-100 transition-colors duration-200 inline-block font-semibold"
          >
            Contact Support
          </a>
        </div>
      </div>
    </div>
  );
};

export default Download;
