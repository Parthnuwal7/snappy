import { Mail, Linkedin, Github, Heart, Award, Target, Users } from 'lucide-react';

const About = () => {
  const values = [
    {
      icon: <Target className="w-8 h-8" />,
      title: 'Our Mission',
      description: 'To empower legal professionals with simple, powerful billing software that saves time and improves efficiency.',
    },
    {
      icon: <Heart className="w-8 h-8" />,
      title: 'User-Centric',
      description: 'Every feature is designed with the end user in mind. We listen to feedback and continuously improve.',
    },
    {
      icon: <Award className="w-8 h-8" />,
      title: 'Quality First',
      description: 'We never compromise on quality. SNAPPY is built with the highest standards of code quality and security.',
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: 'Community Driven',
      description: 'We believe in building together. Our roadmap is influenced by what our users need most.',
    },
  ];

  const journey = [
    {
      year: '2024',
      title: 'The Beginning',
      description: 'SNAPPY was born from the frustration of complicated billing software. We knew there had to be a better way.',
    },
    {
      year: '2024',
      title: 'First Version',
      description: 'After months of development and testing with legal professionals, SNAPPY v1.0 was launched.',
    },
    {
      year: '2025',
      title: 'Growing Community',
      description: 'Hundreds of professionals now trust SNAPPY for their billing needs. We continue to add features based on feedback.',
    },
    {
      year: 'Future',
      title: 'What\'s Next',
      description: 'Mobile apps, advanced integrations, AI-powered insights, and more. The best is yet to come!',
    },
  ];

  return (
    <div className="bg-white min-h-screen py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            About SNAPPY
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Professional billing software built by developers who understand the needs of legal professionals
          </p>
        </div>

        {/* Founder Section */}
        <div className="grid md:grid-cols-2 gap-12 items-center mb-20">
          <div>
            <div className="bg-gradient-to-br from-blue-100 to-indigo-100 rounded-2xl p-8">
              <div className="w-48 h-48 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full mx-auto flex items-center justify-center text-white text-6xl font-bold">
                PN
              </div>
            </div>
          </div>

          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Meet Parth Nuwal
            </h2>
            <p className="text-lg text-gray-600 mb-4">
              Founder & Developer of SNAPPY
            </p>
            <p className="text-gray-700 mb-4">
              As a developer passionate about creating tools that solve real problems, I built SNAPPY 
              after witnessing firsthand how complicated and expensive billing software had become. 
              Legal professionals needed something simple, offline-capable, and affordable.
            </p>
            <p className="text-gray-700 mb-6">
              SNAPPY is designed for Indian professionals—lawyers, CAs, consultants—who need professional 
              invoicing without the complexity. Every line of code is written with the goal of making 
              your billing process as smooth as possible.
            </p>
            
            <div className="flex space-x-4">
              <a
                href="mailto:parth@snappy.app"
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200"
              >
                <Mail size={18} className="mr-2" />
                Email Me
              </a>
              <a
                href="#"
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors duration-200"
              >
                <Linkedin size={18} className="mr-2" />
                LinkedIn
              </a>
              <a
                href="#"
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors duration-200"
              >
                <Github size={18} className="mr-2" />
                GitHub
              </a>
            </div>
          </div>
        </div>

        {/* Values Section */}
        <div className="mb-20">
          <h2 className="text-3xl font-bold text-gray-900 mb-12 text-center">
            Our Values
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {values.map((value, index) => (
              <div
                key={index}
                className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow duration-200"
              >
                <div className="w-14 h-14 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 mb-4">
                  {value.icon}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {value.title}
                </h3>
                <p className="text-gray-600">{value.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Journey Timeline */}
        <div className="mb-20">
          <h2 className="text-3xl font-bold text-gray-900 mb-12 text-center">
            Our Journey
          </h2>
          <div className="relative">
            <div className="absolute left-1/2 transform -translate-x-1/2 h-full w-1 bg-blue-200"></div>
            <div className="space-y-12">
              {journey.map((milestone, index) => (
                <div
                  key={index}
                  className={`flex items-center ${
                    index % 2 === 0 ? 'flex-row' : 'flex-row-reverse'
                  }`}
                >
                  <div className={`w-1/2 ${index % 2 === 0 ? 'pr-8 text-right' : 'pl-8 text-left'}`}>
                    <div className="bg-white border border-gray-200 rounded-xl p-6">
                      <div className="text-blue-600 font-bold text-lg mb-2">{milestone.year}</div>
                      <h3 className="text-xl font-semibold text-gray-900 mb-2">
                        {milestone.title}
                      </h3>
                      <p className="text-gray-600">{milestone.description}</p>
                    </div>
                  </div>
                  <div className="w-8 h-8 bg-blue-600 rounded-full border-4 border-white shadow-lg z-10 flex items-center justify-center">
                    <div className="w-3 h-3 bg-white rounded-full"></div>
                  </div>
                  <div className="w-1/2"></div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Stats Section */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-12 mb-20 text-white text-center">
          <h2 className="text-3xl font-bold mb-12">SNAPPY by the Numbers</h2>
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="text-5xl font-bold mb-2">100+</div>
              <div className="text-blue-100">Active Users</div>
            </div>
            <div>
              <div className="text-5xl font-bold mb-2">5000+</div>
              <div className="text-blue-100">Invoices Generated</div>
            </div>
            <div>
              <div className="text-5xl font-bold mb-2">99.9%</div>
              <div className="text-blue-100">Uptime</div>
            </div>
            <div>
              <div className="text-5xl font-bold mb-2">4.9/5</div>
              <div className="text-blue-100">User Rating</div>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Join the SNAPPY Community
          </h2>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Be part of a growing community of professionals who have simplified their billing process
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="/download"
              className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition-colors duration-200 font-semibold"
            >
              Download SNAPPY
            </a>
            <a
              href="/support"
              className="border-2 border-blue-600 text-blue-600 px-8 py-3 rounded-lg hover:bg-blue-50 transition-colors duration-200 font-semibold"
            >
              Get in Touch
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default About;
