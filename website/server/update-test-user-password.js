import bcrypt from 'bcryptjs';
import supabase from './database.js';

/**
 * Updates the test user password to "123456"
 * Email: test@example.com
 */
async function updateTestUserPassword() {
  try {
    console.log('🔐 Updating test user password...');
    
    const testEmail = 'test@example.com';
    const newPassword = '123456';
    
    // Hash the new password
    const hashedPassword = await bcrypt.hash(newPassword, 10);
    
    // Update user in Supabase
    const { data, error } = await supabase
      .from('users')
      .update({ password: hashedPassword })
      .eq('email', testEmail)
      .select();
    
    if (error) {
      console.error('❌ Error updating password:', error);
      return;
    }
    
    if (!data || data.length === 0) {
      console.log('⚠️  Test user not found. Creating new test user...');
      
      // Create test user if doesn't exist
      const { data: newUser, error: createError } = await supabase
        .from('users')
        .insert([{
          name: 'Test User',
          email: testEmail,
          phone: '1234567890',
          password: hashedPassword,
          profession: 'Developer',
          gender: 'Other',
          dob: '1990-01-01',
          city: 'Test City',
          created_at: new Date().toISOString()
        }])
        .select();
      
      if (createError) {
        console.error('❌ Error creating test user:', createError);
        return;
      }
      
      console.log('✅ Test user created successfully!');
      console.log('📧 Email:', testEmail);
      console.log('🔑 Password:', newPassword);
      return;
    }
    
    console.log('✅ Test user password updated successfully!');
    console.log('📧 Email:', testEmail);
    console.log('🔑 New Password:', newPassword);
    console.log('\n🎯 You can now login to the website with these credentials');
    
  } catch (error) {
    console.error('❌ Unexpected error:', error);
  }
}

// Run the update
updateTestUserPassword();
