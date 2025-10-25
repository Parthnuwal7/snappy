import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
// import Razorpay from 'razorpay'; // COMMENTED: Using manual UPI verification instead
// import crypto from 'crypto'; // COMMENTED: No longer needed for signature verification
import supabase from './database.js';
import { generateLicenseKey, calculateExpiryDate, calculateDaysRemaining } from './utils.js';
import { sendLicenseEmail, sendWelcomeEmail } from './email.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true
}));
app.use(express.json());

// COMMENTED: Razorpay initialization - Using manual UPI verification
// const razorpay = new Razorpay({
//   key_id: process.env.RAZORPAY_KEY_ID,
//   key_secret: process.env.RAZORPAY_KEY_SECRET,
// });

// ==================== HEALTH CHECK ROUTE ====================
// This endpoint is pinged by the frontend to wake up Render if sleeping
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    message: 'Server is awake and running' 
  });
});

// Auth Middleware
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({ error: 'Invalid or expired token' });
    }
    req.user = user;
    next();
  });
}

// ==================== AUTH ROUTES ====================

// Register
app.post('/api/auth/register', async (req, res) => {
  try {
    const { name, email, phone, password, profession, gender, dob, city } = req.body;

    // Validation
    if (!name || !email || !phone || !password || !profession || !gender || !dob || !city) {
      return res.status(400).json({ error: 'All fields are required' });
    }

    // Check if user exists
    const { data: existingUser } = await supabase
      .from('users')
      .select('*')
      .eq('email', email)
      .single();
    
    if (existingUser) {
      return res.status(400).json({ error: 'Email already registered' });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Insert user
    const { data: newUser, error } = await supabase
      .from('users')
      .insert({
        name,
        email,
        phone,
        password: hashedPassword,
        profession,
        gender,
        dob,
        city
      })
      .select()
      .single();

    if (error) throw error;

    // Send welcome email
    await sendWelcomeEmail(email, name);

    res.status(201).json({ 
      message: 'Account created successfully',
      userId: newUser.id
    });
  } catch (error) {
    console.error('Register error:', error);
    res.status(500).json({ error: 'Registration failed' });
  }
});

// Login
app.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password required' });
    }

    // Find user
    const { data: user, error } = await supabase
      .from('users')
      .select('*')
      .eq('email', email)
      .single();
    
    if (error || !user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Verify password
    const validPassword = await bcrypt.compare(password, user.password);
    if (!validPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Update last login
    await supabase
      .from('users')
      .update({ last_login: new Date().toISOString() })
      .eq('id', user.id);

    // Generate JWT
    const token = jwt.sign(
      { userId: user.id, email: user.email, name: user.name },
      process.env.JWT_SECRET,
      { expiresIn: '7d' }
    );

    res.json({
      token,
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        phone: user.phone,
        profession: user.profession,
        gender: user.gender,
        dob: user.dob,
        city: user.city,
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

// Get current user
app.get('/api/auth/me', authenticateToken, async (req, res) => {
  try {
    const { data: user, error } = await supabase
      .from('users')
      .select('id, name, email, phone, profession, gender, dob, city, created_at, last_login')
      .eq('id', req.user.userId)
      .single();
    
    if (error || !user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ user });
  } catch (error) {
    console.error('Get user error:', error);
    res.status(500).json({ error: 'Failed to fetch user data' });
  }
});

// ==================== PAYMENT ROUTES (UPI Manual Verification) ====================

// Get UPI payment details for a plan
app.get('/api/payment/upi-details/:plan', authenticateToken, (req, res) => {
  try {
    const { plan } = req.params;

    // Determine amount based on plan
    let amount;
    switch (plan.toLowerCase()) {
      case 'starter':
        amount = parseInt(process.env.PRICE_STARTER) / 100; // Convert paise to rupees
        break;
      case 'pro':
        amount = parseInt(process.env.PRICE_PRO) / 100;
        break;
      case 'enterprise':
        amount = parseInt(process.env.PRICE_ENTERPRISE) / 100;
        break;
      default:
        return res.status(400).json({ error: 'Invalid plan' });
    }

    // Return UPI QR code paths and payment details
    res.json({
      plan: plan,
      amount: amount,
      upiId: process.env.UPI_ID || 'your-upi@paytm',
      qrCodeUrl: `/qr-codes/${plan.toLowerCase()}.png`, // Path to QR code images
      instructions: [
        `Scan the QR code or pay ₹${amount} to UPI ID: ${process.env.UPI_ID || 'your-upi@paytm'}`,
        'After payment, enter your UPI Transaction ID below',
        'Admin will verify your payment within 24 hours',
        'License key will be sent to your email after verification'
      ]
    });
  } catch (error) {
    console.error('Get UPI details error:', error);
    res.status(500).json({ error: 'Failed to fetch UPI details' });
  }
});

// Submit UPI payment for verification
app.post('/api/payment/submit-upi', authenticateToken, async (req, res) => {
  try {
    const { plan, upiTransactionId } = req.body;

    if (!plan || !upiTransactionId) {
      return res.status(400).json({ error: 'Plan and UPI Transaction ID are required' });
    }

    // Determine amount
    let amount;
    switch (plan.toLowerCase()) {
      case 'starter':
        amount = parseInt(process.env.PRICE_STARTER);
        break;
      case 'pro':
        amount = parseInt(process.env.PRICE_PRO);
        break;
      case 'enterprise':
        amount = parseInt(process.env.PRICE_ENTERPRISE);
        break;
      default:
        return res.status(400).json({ error: 'Invalid plan' });
    }

    // Check if transaction ID already used
    const { data: existingLicense } = await supabase
      .from('licenses')
      .select('*')
      .eq('upi_transaction_id', upiTransactionId)
      .single();
    
    if (existingLicense) {
      return res.status(400).json({ error: 'This transaction ID has already been used' });
    }

    // Generate license key
    const licenseKey = generateLicenseKey();

    // Create pending license record
    const { data: licenseResult, error: licenseError } = await supabase
      .from('licenses')
      .insert({
        user_id: req.user.userId,
        license_key: licenseKey,
        plan,
        payment_method: 'upi',
        upi_transaction_id: upiTransactionId,
        amount,
        status: 'pending_verification',
        admin_verified: false,
        email_sent: false
      })
      .select()
      .single();

    if (licenseError) throw licenseError;

    // Log payment submission
    await supabase
      .from('payment_logs')
      .insert({
        user_id: req.user.userId,
        license_id: licenseResult.id,
        payment_method: 'upi',
        upi_transaction_id: upiTransactionId,
        amount,
        status: 'pending_verification',
        admin_verified: false
      });

    res.json({
      success: true,
      message: 'Payment submitted for verification. You will receive an email once admin approves.',
      licenseId: licenseResult.id,
      status: 'pending_verification'
    });
  } catch (error) {
    console.error('Submit UPI payment error:', error);
    res.status(500).json({ error: 'Failed to submit payment' });
  }
});

// COMMENTED OUT: Old Razorpay payment routes
// These are kept for reference but not used with UPI manual verification

/*
// Create Razorpay order
app.post('/api/payment/create-order', authenticateToken, async (req, res) => {
  try {
    const { plan } = req.body;
    let amount;
    switch (plan.toLowerCase()) {
      case 'starter':
        amount = parseInt(process.env.PRICE_STARTER);
        break;
      case 'pro':
        amount = parseInt(process.env.PRICE_PRO);
        break;
      case 'enterprise':
        amount = parseInt(process.env.PRICE_ENTERPRISE);
        break;
      default:
        return res.status(400).json({ error: 'Invalid plan' });
    }

    const options = {
      amount: amount,
      currency: 'INR',
      receipt: `receipt_${Date.now()}`,
      notes: {
        userId: req.user.userId,
        plan: plan
      }
    };

    const order = await razorpay.orders.create(options);
    const licenseKey = generateLicenseKey();
    const licenseResult = db.prepare(`
      INSERT INTO licenses (user_id, license_key, plan, razorpay_order_id, amount, status)
      VALUES (?, ?, ?, ?, ?, 'pending')
    `).run(req.user.userId, licenseKey, plan, order.id, amount);

    res.json({
      orderId: order.id,
      amount: order.amount,
      currency: order.currency,
      licenseId: licenseResult.lastInsertRowid,
      key: process.env.RAZORPAY_KEY_ID
    });
  } catch (error) {
    console.error('Create order error:', error);
    res.status(500).json({ error: 'Failed to create payment order' });
  }
});

// Verify payment and activate license
app.post('/api/payment/verify', authenticateToken, async (req, res) => {
  try {
    const { razorpay_order_id, razorpay_payment_id, razorpay_signature } = req.body;

    const body = razorpay_order_id + '|' + razorpay_payment_id;
    const expectedSignature = crypto
      .createHmac('sha256', process.env.RAZORPAY_KEY_SECRET)
      .update(body)
      .digest('hex');

    const isAuthentic = expectedSignature === razorpay_signature;

    if (!isAuthentic) {
      return res.status(400).json({ error: 'Invalid payment signature' });
    }

    const license = db.prepare('SELECT * FROM licenses WHERE razorpay_order_id = ?').get(razorpay_order_id);
    
    if (!license) {
      return res.status(404).json({ error: 'License not found' });
    }

    const now = new Date().toISOString();
    const expiresAt = calculateExpiryDate(new Date()).toISOString();

    db.prepare(`
      UPDATE licenses 
      SET status = 'active', 
          razorpay_payment_id = ?,
          invoked_at = ?,
          expires_at = ?
      WHERE id = ?
    `).run(razorpay_payment_id, now, expiresAt, license.id);

    db.prepare(`
      INSERT INTO payment_logs (user_id, license_id, razorpay_order_id, razorpay_payment_id, razorpay_signature, amount, status)
      VALUES (?, ?, ?, ?, ?, ?, 'success')
    `).run(req.user.userId, license.id, razorpay_order_id, razorpay_payment_id, razorpay_signature, license.amount);

    const user = db.prepare('SELECT name, email FROM users WHERE id = ?').get(req.user.userId);
    await sendLicenseEmail(user.email, user.name, license.license_key, license.plan);

    res.json({
      success: true,
      message: 'Payment verified and license activated',
      license: {
        key: license.license_key,
        plan: license.plan,
        invokedAt: now,
        expiresAt: expiresAt
      }
    });
  } catch (error) {
    console.error('Verify payment error:', error);
    res.status(500).json({ error: 'Payment verification failed' });
  }
});
*/

// ==================== LICENSE ROUTES ====================

// Get user licenses
app.get('/api/licenses', authenticateToken, (req, res) => {
  try {
    const licenses = db.prepare(`
      SELECT id, license_key, plan, payment_method, upi_transaction_id, status, admin_verified, email_sent, invoked_at, expires_at, created_at, amount
      FROM licenses
      WHERE user_id = ?
      ORDER BY created_at DESC
    `).all(req.user.userId);

    // Add days remaining to each license
    const licensesWithDays = licenses.map(license => ({
      ...license,
      daysRemaining: license.expires_at ? calculateDaysRemaining(license.expires_at) : null,
      isActive: license.status === 'active' && license.expires_at && new Date(license.expires_at) > new Date()
    }));

    res.json({ licenses: licensesWithDays });
  } catch (error) {
    console.error('Get licenses error:', error);
    res.status(500).json({ error: 'Failed to fetch licenses' });
  }
});

// Get single license details
app.get('/api/licenses/:id', authenticateToken, (req, res) => {
  try {
    const license = db.prepare(`
      SELECT id, license_key, plan, payment_method, upi_transaction_id, status, admin_verified, email_sent, invoked_at, expires_at, created_at, amount
      FROM licenses
      WHERE id = ? AND user_id = ?
    `).get(req.params.id, req.user.userId);

    if (!license) {
      return res.status(404).json({ error: 'License not found' });
    }

    const licenseWithDays = {
      ...license,
      daysRemaining: license.expires_at ? calculateDaysRemaining(license.expires_at) : null,
      isActive: license.status === 'active' && license.expires_at && new Date(license.expires_at) > new Date()
    };

    res.json({ license: licenseWithDays });
  } catch (error) {
    console.error('Get license error:', error);
    res.status(500).json({ error: 'Failed to fetch license' });
  }
});

// ==================== ADMIN ROUTES ====================

// Admin login endpoint
app.post('/api/admin/login', async (req, res) => {
  try {
    const { password } = req.body;

    if (!password) {
      return res.status(400).json({ error: 'Password is required' });
    }

    // Check if password matches
    if (password !== process.env.ADMIN_PASSWORD) {
      return res.status(401).json({ error: 'Invalid admin password' });
    }

    // Generate admin token (with isAdmin flag)
    const adminToken = jwt.sign(
      { isAdmin: true, role: 'admin' },
      process.env.JWT_SECRET,
      { expiresIn: '7d' }
    );

    res.json({
      success: true,
      token: adminToken,
      message: 'Admin login successful'
    });
  } catch (error) {
    console.error('Admin login error:', error);
    res.status(500).json({ error: 'Admin login failed' });
  }
});

// Admin middleware - simplified password-based check
async function authenticateAdmin(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  jwt.verify(token, process.env.JWT_SECRET, (err, decoded) => {
    if (err) {
      return res.status(403).json({ error: 'Invalid or expired token' });
    }
    
    // Check if token has admin flag
    if (!decoded.isAdmin || decoded.role !== 'admin') {
      return res.status(403).json({ error: 'Admin access required' });
    }
    
    req.admin = decoded;
    next();
  });
}

// Get all pending license verifications (Admin only)
app.get('/api/admin/pending-licenses', authenticateAdmin, async (req, res) => {
  try {
    const { data: pendingLicenses, error } = await supabase
      .from('licenses')
      .select(`
        id,
        license_key,
        plan,
        payment_method,
        upi_transaction_id,
        amount,
        status,
        admin_verified,
        email_sent,
        created_at,
        users!inner (
          id,
          name,
          email,
          phone
        )
      `)
      .eq('status', 'pending_verification')
      .eq('admin_verified', false)
      .order('created_at', { ascending: false });

    if (error) throw error;

    // Transform to match expected format
    const formattedLicenses = pendingLicenses?.map(l => ({
      id: l.id,
      license_key: l.license_key,
      plan: l.plan,
      payment_method: l.payment_method,
      upi_transaction_id: l.upi_transaction_id,
      amount: l.amount,
      status: l.status,
      admin_verified: l.admin_verified,
      email_sent: l.email_sent,
      created_at: l.created_at,
      user_id: l.users.id,
      user_name: l.users.name,
      user_email: l.users.email,
      user_phone: l.users.phone
    })) || [];

    res.json({ pendingLicenses: formattedLicenses });
  } catch (error) {
    console.error('Get pending licenses error:', error);
    res.status(500).json({ error: 'Failed to fetch pending licenses' });
  }
});

// Get all licenses (Admin only)
app.get('/api/admin/all-licenses', authenticateAdmin, async (req, res) => {
  try {
    const { data: allLicenses, error } = await supabase
      .from('licenses')
      .select(`
        *,
        users!inner (
          name,
          email,
          phone
        )
      `)
      .order('created_at', { ascending: false });

    if (error) throw error;

    // Transform to match expected format
    const formattedLicenses = allLicenses?.map(l => ({
      ...l,
      user_name: l.users.name,
      user_email: l.users.email,
      user_phone: l.users.phone
    })) || [];

    res.json({ licenses: formattedLicenses });
  } catch (error) {
    console.error('Get all licenses error:', error);
    res.status(500).json({ error: 'Failed to fetch licenses' });
  }
});

// Admin: Verify payment (Step 1 - doesn't send email yet)
app.post('/api/admin/verify-payment/:licenseId', authenticateAdmin, async (req, res) => {
  try {
    const { licenseId } = req.params;
    const { notes } = req.body;

    const { data: license, error: fetchError } = await supabase
      .from('licenses')
      .select('*')
      .eq('id', licenseId)
      .single();
    
    if (fetchError || !license) {
      return res.status(404).json({ error: 'License not found' });
    }

    if (license.admin_verified) {
      return res.status(400).json({ error: 'License already verified' });
    }

    const now = new Date().toISOString();
    const expiresAt = calculateExpiryDate(new Date()).toISOString();

    // Update license - mark as verified but don't activate yet
    const { error: updateError } = await supabase
      .from('licenses')
      .update({
        admin_verified: true,
        verified_at: now,
        admin_notes: notes || 'Payment verified by admin',
        invoked_at: now,
        expires_at: expiresAt
      })
      .eq('id', licenseId);

    if (updateError) throw updateError;

    // Update payment log
    await supabase
      .from('payment_logs')
      .update({ admin_verified: true })
      .eq('license_id', licenseId);

    res.json({
      success: true,
      message: 'Payment verified. You can now send the license email.',
      license: {
        id: licenseId,
        verified: true,
        emailSent: false
      }
    });
  } catch (error) {
    console.error('Verify payment error:', error);
    res.status(500).json({ error: 'Failed to verify payment' });
  }
});

// Admin: Send license email (Step 2 - after manual verification)
app.post('/api/admin/send-license-email/:licenseId', authenticateAdmin, async (req, res) => {
  try {
    const { licenseId } = req.params;

    const { data: license, error: fetchError } = await supabase
      .from('licenses')
      .select(`
        *,
        users!inner (
          name,
          email
        )
      `)
      .eq('id', licenseId)
      .single();
    
    if (fetchError || !license) {
      return res.status(404).json({ error: 'License not found' });
    }

    if (!license.admin_verified) {
      return res.status(400).json({ error: 'Payment must be verified first' });
    }

    if (license.email_sent) {
      return res.status(400).json({ error: 'License email already sent' });
    }

    // Send license email
    await sendLicenseEmail(license.users.email, license.users.name, license.license_key, license.plan);

    // Update license status to active and mark email as sent
    await supabase
      .from('licenses')
      .update({
        status: 'active',
        email_sent: true
      })
      .eq('id', licenseId);

    // Update payment log
    await supabase
      .from('payment_logs')
      .update({ status: 'completed' })
      .eq('license_id', licenseId);

    res.json({
      success: true,
      message: 'License email sent successfully and license activated',
      license: {
        id: licenseId,
        key: license.license_key,
        status: 'active',
        emailSent: true
      }
    });
  } catch (error) {
    console.error('Send license email error:', error);
    res.status(500).json({ error: 'Failed to send license email' });
  }
});

// Admin: Reject payment
app.post('/api/admin/reject-payment/:licenseId', authenticateAdmin, async (req, res) => {
  try {
    const { licenseId } = req.params;
    const { reason } = req.body;

    const { data: license, error: fetchError } = await supabase
      .from('licenses')
      .select('*')
      .eq('id', licenseId)
      .single();
    
    if (fetchError || !license) {
      return res.status(404).json({ error: 'License not found' });
    }

    // Update license status
    await supabase
      .from('licenses')
      .update({
        status: 'rejected',
        admin_notes: reason || 'Payment rejected by admin'
      })
      .eq('id', licenseId);

    // Update payment log
    await supabase
      .from('payment_logs')
      .update({ status: 'rejected' })
      .eq('license_id', licenseId);

    res.json({
      success: true,
      message: 'Payment rejected',
      license: {
        id: licenseId,
        status: 'rejected'
      }
    });
  } catch (error) {
    console.error('Reject payment error:', error);
    res.status(500).json({ error: 'Failed to reject payment' });
  }
});

// Delete license (Admin only) - For removing fraudulent licenses
app.delete('/api/admin/delete-license/:licenseId', authenticateAdmin, async (req, res) => {
  try {
    const { licenseId } = req.params;

    // Delete license (payment_logs will be deleted via CASCADE)
    const { error } = await supabase
      .from('licenses')
      .delete()
      .eq('id', licenseId);
    
    if (error) throw error;

    res.json({
      success: true,
      message: 'License deleted permanently'
    });
  } catch (error) {
    console.error('Delete license error:', error);
    res.status(500).json({ error: 'Failed to delete license' });
  }
});

// ==================== DASHBOARD ROUTES ====================

// Get dashboard data
app.get('/api/dashboard', authenticateToken, async (req, res) => {
  try {
    const { data: user, error: userError } = await supabase
      .from('users')
      .select('id, name, email, phone, profession, gender, dob, city, created_at, last_login')
      .eq('id', req.user.userId)
      .single();

    if (userError) throw userError;

    const { data: licenses, error: licensesError } = await supabase
      .from('licenses')
      .select('id, license_key, plan, payment_method, upi_transaction_id, status, admin_verified, email_sent, invoked_at, expires_at, created_at, amount, admin_notes')
      .eq('user_id', req.user.userId)
      .order('created_at', { ascending: false });

    if (licensesError) throw licensesError;

    const activeLicense = licenses?.find(l => l.status === 'active' && l.expires_at && new Date(l.expires_at) > new Date());

    res.json({
      user,
      licenses: (licenses || []).map(license => ({
        ...license,
        // Hide license key if not verified by admin
        license_key: license.admin_verified ? license.license_key : '••••••••••••••••',
        daysRemaining: license.expires_at ? calculateDaysRemaining(license.expires_at) : null,
        isActive: license.status === 'active' && license.expires_at && new Date(license.expires_at) > new Date()
      })),
      activeLicense: activeLicense ? {
        ...activeLicense,
        daysRemaining: calculateDaysRemaining(activeLicense.expires_at),
        isActive: true
      } : null
    });
  } catch (error) {
    console.error('Get dashboard error:', error);
    res.status(500).json({ error: 'Failed to fetch dashboard data' });
  }
});

// ==================== HEALTH CHECK ====================

app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'SNAPPY API is running' });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 SNAPPY API server running on port ${PORT}`);
  console.log(`📍 Frontend URL: ${process.env.FRONTEND_URL}`);
});
