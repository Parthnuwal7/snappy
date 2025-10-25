import 'dotenv/config';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_KEY
);

async function checkAdmin() {
  console.log('\n🔍 Checking Admin Setup...\n');
  console.log('Expected Admin Email:', process.env.ADMIN_EMAIL);
  
  // Check if admin user exists
  const { data: adminUser, error: adminError } = await supabase
    .from('users')
    .select('*')
    .eq('email', process.env.ADMIN_EMAIL)
    .single();
  
  if (adminError) {
    if (adminError.code === 'PGRST116') {
      console.log('❌ No user found with admin email:', process.env.ADMIN_EMAIL);
      console.log('\n📝 Steps to fix:');
      console.log('1. Register a user on your website with email:', process.env.ADMIN_EMAIL);
      console.log('2. Or update ADMIN_EMAIL in .env to match an existing user');
    } else {
      console.log('❌ Error checking admin:', adminError.message);
    }
    return;
  }
  
  console.log('✅ Admin user found:');
  console.log('   ID:', adminUser.id);
  console.log('   Name:', adminUser.name);
  console.log('   Email:', adminUser.email);
  
  // Check pending licenses
  console.log('\n🔍 Checking Pending Licenses...\n');
  const { data: pendingLicenses, error: licenseError } = await supabase
    .from('licenses')
    .select('*, users!inner(name, email)')
    .eq('admin_verified', false)
    .order('created_at', { ascending: false });
  
  if (licenseError) {
    console.log('❌ Error fetching licenses:', licenseError.message);
    return;
  }
  
  if (pendingLicenses.length === 0) {
    console.log('ℹ️  No pending licenses found');
    console.log('   This means no payments have been submitted yet, or all have been verified');
  } else {
    console.log(`✅ Found ${pendingLicenses.length} pending license(s):\n`);
    pendingLicenses.forEach((license, index) => {
      console.log(`${index + 1}. License ID: ${license.id}`);
      console.log(`   User: ${license.users.name} (${license.users.email})`);
      console.log(`   Plan: ${license.plan}`);
      console.log(`   UPI Transaction: ${license.upi_transaction_id}`);
      console.log(`   Status: ${license.status}`);
      console.log(`   Created: ${new Date(license.created_at).toLocaleString()}`);
      console.log('');
    });
  }
  
  // Check all licenses
  const { data: allLicenses, error: allError } = await supabase
    .from('licenses')
    .select('*');
  
  if (!allError) {
    console.log(`\n📊 Total licenses in database: ${allLicenses.length}`);
  }
}

checkAdmin().catch(console.error);
