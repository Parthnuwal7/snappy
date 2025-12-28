import { createClient } from '@supabase/supabase-js';

// Supabase configuration from environment variables
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Debug logging - check what env vars are available
console.log('🔍 Supabase Config Debug:');
console.log('  VITE_SUPABASE_URL:', supabaseUrl ? `${supabaseUrl.substring(0, 30)}...` : 'NOT SET');
console.log('  VITE_SUPABASE_ANON_KEY:', supabaseAnonKey ? 'SET (hidden)' : 'NOT SET');
console.log('  All VITE_ env vars:', Object.keys(import.meta.env).filter(k => k.startsWith('VITE_')));

if (!supabaseUrl || !supabaseAnonKey) {
    console.error(
        '❌ Supabase credentials not found! Please ensure your .env file in the frontend folder contains:\n' +
        '  VITE_SUPABASE_URL=https://your-project.supabase.co\n' +
        '  VITE_SUPABASE_ANON_KEY=your-anon-key\n' +
        '\n⚠️ After updating .env, you MUST restart the dev server (Ctrl+C and npm run dev)'
    );
}

// Create Supabase client - throw if not configured
if (!supabaseUrl || supabaseUrl === 'https://placeholder.supabase.co') {
    throw new Error(
        'Supabase URL not configured. Set VITE_SUPABASE_URL in frontend/.env and restart the dev server.'
    );
}

export const supabase = createClient(
    supabaseUrl,
    supabaseAnonKey || '',
    {
        auth: {
            autoRefreshToken: true,
            persistSession: true,
            detectSessionInUrl: true,
        },
    }
);

// Helper to get current session
export const getSession = async () => {
    const { data: { session }, error } = await supabase.auth.getSession();
    if (error) {
        console.error('Error getting session:', error);
        return null;
    }
    return session;
};

// Helper to get current user
export const getCurrentUser = async () => {
    const { data: { user }, error } = await supabase.auth.getUser();
    if (error) {
        console.error('Error getting user:', error);
        return null;
    }
    return user;
};

// Helper to get device info for tracking
export const getDeviceInfo = () => {
    const ua = navigator.userAgent;
    let browser = 'Unknown';
    let os = 'Unknown';
    let deviceType = 'web';

    // Detect browser
    if (ua.includes('Chrome')) browser = 'Chrome';
    else if (ua.includes('Firefox')) browser = 'Firefox';
    else if (ua.includes('Safari')) browser = 'Safari';
    else if (ua.includes('Edge')) browser = 'Edge';

    // Detect OS
    if (ua.includes('Windows')) os = 'Windows';
    else if (ua.includes('Mac')) os = 'macOS';
    else if (ua.includes('Linux')) os = 'Linux';
    else if (ua.includes('Android')) os = 'Android';
    else if (ua.includes('iOS')) os = 'iOS';

    // Detect device type
    if (ua.includes('Mobile')) deviceType = 'mobile';
    else if (ua.includes('Tablet')) deviceType = 'tablet';

    return {
        browser,
        os,
        device_type: deviceType,
        user_agent: ua,
        last_active: new Date().toISOString(),
    };
};

// Generate a unique device ID (stored in localStorage)
export const getDeviceId = () => {
    let deviceId = localStorage.getItem('snappy_device_id');
    if (!deviceId) {
        deviceId = `device_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
        localStorage.setItem('snappy_device_id', deviceId);
    }
    return deviceId;
};

export default supabase;
