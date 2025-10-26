import sgMail from '@sendgrid/mail';
import dotenv from 'dotenv';

dotenv.config();

// Initialize SendGrid with API key
sgMail.setApiKey(process.env.SENDGRID_API_KEY);

export async function sendLicenseEmail(userEmail, userName, licenseKey, plan) {
  const msg = {
    to: userEmail,
    from: {
      email: process.env.SENDGRID_FROM_EMAIL,
      name: 'SNAPPY'
    },
    subject: '🎉 Your SNAPPY License Key',
    html: `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(to right, #2563eb, #4f46e5); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
          .content { background: #f9fafb; padding: 30px; }
          .license-box { background: white; border: 2px solid #2563eb; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }
          .license-key { font-size: 24px; font-weight: bold; color: #2563eb; letter-spacing: 2px; font-family: 'Courier New', monospace; }
          .button { display: inline-block; background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; }
          .footer { background: #1f2937; color: #9ca3af; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 14px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>🎉 Welcome to SNAPPY!</h1>
          </div>
          <div class="content">
            <h2>Hi ${userName},</h2>
            <p>Thank you for purchasing SNAPPY ${plan} plan! Your payment has been confirmed.</p>
            
            <div class="license-box">
              <p style="margin: 0 0 10px 0; color: #6b7280;">Your License Key:</p>
              <div class="license-key">${licenseKey}</div>
            </div>

            <h3>📥 Next Steps:</h3>
            <ol>
              <li>Download SNAPPY from <a href="${process.env.FRONTEND_URL}/download">our website</a></li>
              <li>Install the application on your Windows computer</li>
              <li>Launch SNAPPY and enter your license key when prompted</li>
              <li>Start creating professional invoices!</li>
            </ol>

            <p style="text-align: center;">
              <a href="${process.env.FRONTEND_URL}/download" class="button">Download SNAPPY</a>
            </p>

            <h3>📝 Important Information:</h3>
            <ul>
              <li><strong>Valid for:</strong> 1 year from activation</li>
              <li><strong>Plan:</strong> ${plan}</li>
              <li><strong>Support:</strong> Email us at support@snappy.app</li>
            </ul>

            <p><strong>Keep this email safe!</strong> You can also view your license key anytime by logging into your account at ${process.env.FRONTEND_URL}/dashboard</p>
          </div>
          <div class="footer">
            <p>© 2025 SNAPPY by Parth Nuwal. All rights reserved.</p>
            <p>Need help? Reply to this email or visit our <a href="${process.env.FRONTEND_URL}/support" style="color: #60a5fa;">support page</a></p>
          </div>
        </div>
      </body>
      </html>
    `,
  };

  try {
    await sgMail.send(msg);
    console.log('✅ License email sent to:', userEmail);
    return true;
  } catch (error) {
    console.error('❌ SendGrid error:', error.response?.body || error.message);
    return false;
  }
}

export async function sendWelcomeEmail(userEmail, userName) {
  const msg = {
    to: userEmail,
    from: {
      email: process.env.SENDGRID_FROM_EMAIL,
      name: 'SNAPPY'
    },
    subject: 'Welcome to SNAPPY! 👋',
    html: `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(to right, #2563eb, #4f46e5); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
          .content { background: #f9fafb; padding: 30px; }
          .button { display: inline-block; background: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; }
          .footer { background: #1f2937; color: #9ca3af; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 14px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>👋 Welcome to SNAPPY!</h1>
          </div>
          <div class="content">
            <h2>Hi ${userName},</h2>
            <p>Thank you for creating an account with SNAPPY! We're excited to have you on board.</p>
            
            <h3>🚀 What's Next?</h3>
            <p>You're just one step away from streamlining your billing process:</p>
            <ol>
              <li>Choose your plan from our <a href="${process.env.FRONTEND_URL}/pricing">pricing page</a></li>
              <li>Complete the payment</li>
              <li>Receive your license key instantly</li>
              <li>Download and start using SNAPPY!</li>
            </ol>

            <p style="text-align: center;">
              <a href="${process.env.FRONTEND_URL}/pricing" class="button">View Pricing Plans</a>
            </p>

            <p>If you have any questions, feel free to reach out to our support team.</p>
          </div>
          <div class="footer">
            <p>© 2025 SNAPPY by Parth Nuwal. All rights reserved.</p>
            <p>Need help? Email us at support@snappy.app</p>
          </div>
        </div>
      </body>
      </html>
    `,
  };

  try {
    await sgMail.send(msg);
    console.log('✅ Welcome email sent to:', userEmail);
  } catch (error) {
    console.error('❌ Failed to send welcome email:', error.response?.body || error.message);
  }
}
