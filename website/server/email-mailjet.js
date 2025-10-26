import Mailjet from 'node-mailjet';

// Initialize Mailjet client
const mailjet = new Mailjet({
  apiKey: process.env.MAILJET_API_KEY,
  apiSecret: process.env.MAILJET_API_SECRET
});

export async function sendLicenseEmail(userEmail, userName, licenseKey, plan) {
  try {
    const request = mailjet
      .post('send', { version: 'v3.1' })
      .request({
        Messages: [
          {
            From: {
              Email: process.env.MAILJET_FROM_EMAIL,
              Name: 'SNAPPY'
            },
            To: [
              {
                Email: userEmail,
                Name: userName
              }
            ],
            Subject: '🎉 Your SNAPPY License Key',
            HTMLPart: `
              <!DOCTYPE html>
              <html>
              <head>
                <style>
                  body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                  .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                  .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                  .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                  .license-box { background: white; border: 2px dashed #667eea; padding: 20px; margin: 20px 0; border-radius: 8px; text-align: center; }
                  .license-key { font-size: 24px; font-weight: bold; color: #667eea; letter-spacing: 2px; font-family: monospace; }
                  .plan-badge { display: inline-block; background: #667eea; color: white; padding: 8px 16px; border-radius: 20px; margin: 10px 0; }
                  .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                  .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
              </head>
              <body>
                <div class="container">
                  <div class="header">
                    <h1>🎉 Welcome to SNAPPY!</h1>
                    <p>Your license is ready</p>
                  </div>
                  <div class="content">
                    <p>Hi ${userName},</p>
                    <p>Thank you for purchasing SNAPPY! Your payment has been verified and your license is now active.</p>
                    
                    <div class="license-box">
                      <p style="margin: 0; color: #666; font-size: 14px;">Your License Key</p>
                      <div class="license-key">${licenseKey}</div>
                      <span class="plan-badge">${plan.toUpperCase()} PLAN</span>
                    </div>

                    <p><strong>Next Steps:</strong></p>
                    <ol>
                      <li>Save this license key in a safe place</li>
                      <li>Use it to activate your SNAPPY software</li>
                      <li>Enjoy all premium features!</li>
                    </ol>

                    <p style="text-align: center;">
                      <a href="${process.env.FRONTEND_URL}" class="button">Go to Dashboard</a>
                    </p>

                    <div class="footer">
                      <p>Need help? Contact us at ${process.env.MAILJET_FROM_EMAIL}</p>
                      <p>© 2025 SNAPPY. All rights reserved.</p>
                    </div>
                  </div>
                </div>
              </body>
              </html>
            `
          }
        ]
      });

    const result = await request;
    console.log('✅ License email sent successfully to:', userEmail);
    return result;
  } catch (error) {
    console.error('❌ Failed to send license email:', error);
    throw error;
  }
}

export async function sendWelcomeEmail(userEmail, userName) {
  try {
    const request = mailjet
      .post('send', { version: 'v3.1' })
      .request({
        Messages: [
          {
            From: {
              Email: process.env.MAILJET_FROM_EMAIL,
              Name: 'SNAPPY'
            },
            To: [
              {
                Email: userEmail,
                Name: userName
              }
            ],
            Subject: '👋 Welcome to SNAPPY!',
            HTMLPart: `
              <!DOCTYPE html>
              <html>
              <head>
                <style>
                  body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                  .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                  .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                  .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                  .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                  .feature { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #667eea; }
                  .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
                </style>
              </head>
              <body>
                <div class="container">
                  <div class="header">
                    <h1>👋 Welcome to SNAPPY!</h1>
                    <p>Let's get you started</p>
                  </div>
                  <div class="content">
                    <p>Hi ${userName},</p>
                    <p>Welcome aboard! We're excited to have you join the SNAPPY community.</p>
                    
                    <h3>🚀 What's Next?</h3>
                    <div class="feature">
                      <strong>1. Browse Plans</strong><br>
                      Check out our flexible licensing options
                    </div>
                    <div class="feature">
                      <strong>2. Make a Payment</strong><br>
                      Choose a plan and complete your purchase
                    </div>
                    <div class="feature">
                      <strong>3. Get Your License</strong><br>
                      Receive your activation key via email
                    </div>

                    <p style="text-align: center;">
                      <a href="${process.env.FRONTEND_URL}" class="button">Explore Plans</a>
                    </p>

                    <div class="footer">
                      <p>Need help? Contact us at ${process.env.MAILJET_FROM_EMAIL}</p>
                      <p>© 2025 SNAPPY. All rights reserved.</p>
                    </div>
                  </div>
                </div>
              </body>
              </html>
            `
          }
        ]
      });

    const result = await request;
    console.log('✅ Welcome email sent successfully to:', userEmail);
    return result;
  } catch (error) {
    console.error('❌ Failed to send welcome email:', error);
    throw error;
  }
}
