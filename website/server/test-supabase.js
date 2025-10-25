#!/usr/bin/env node

/**
 * SUPABASE MIGRATION SCRIPT
 * 
 * This script will help you complete the migration to Supabase.
 * 
 * Run this after:
 * 1. Creating tables in Supabase (using supabase-schema.sql)
 * 2. Installing dependencies: npm install
 * 3. Setting SUPABASE_URL and SUPABASE_KEY in .env
 * 
 * This script will test your Supabase connection and provide migration instructions.
 */

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;

console.log('\n🚀 SUPABASE MIGRATION CHECKER\n');

// Check environment variables
if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing Supabase credentials!');
  console.error('Please add these to your .env file:');
  console.error('   SUPABASE_URL=your-project-url');
  console.error('   SUPABASE_KEY=your-anon-key\n');
  process.exit(1);
}

console.log('✅ Environment variables found');
console.log(`   URL: ${supabaseUrl}`);
console.log(`   Key: ${supabaseKey.substring(0, 20)}...\n`);

// Test connection
const supabase = createClient(supabaseUrl, supabaseKey);

console.log('🔗 Testing Supabase connection...\n');

async function testConnection() {
  try {
    // Test users table
    const { data: users, error: usersError } = await supabase
      .from('users')
      .select('count');
    
    if (usersError) {
      console.error('❌ Users table error:', usersError.message);
      console.error('\n📋 Have you created the tables? Run this SQL in Supabase SQL Editor:');
      console.error('   See: website/server/supabase-schema.sql\n');
      return false;
    }
    
    console.log('✅ Users table accessible');
    
    // Test licenses table
    const { data: licenses, error: licensesError } = await supabase
      .from('licenses')
      .select('count');
    
    if (licensesError) {
      console.error('❌ Licenses table error:', licensesError.message);
      return false;
    }
    
    console.log('✅ Licenses table accessible');
    
    // Test payment_logs table
    const { data: logs, error: logsError } = await supabase
      .from('payment_logs')
      .select('count');
    
    if (logsError) {
      console.error('❌ Payment logs table error:', logsError.message);
      return false;
    }
    
    console.log('✅ Payment logs table accessible\n');
    
    console.log('🎉 All tables are accessible!\n');
    console.log('📝 Next Steps:');
    console.log('   1. Review the updated index.js file');
    console.log('   2. Install dependencies: npm install');
    console.log('   3. Start the server: node index.js');
    console.log('   4. Test the registration and login endpoints\n');
    
    return true;
  } catch (error) {
    console.error('❌ Connection test failed:', error.message);
    return false;
  }
}

testConnection();
