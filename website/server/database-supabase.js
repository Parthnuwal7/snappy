import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing Supabase credentials in .env file');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

console.log('✅ Connected to Supabase');

// Helper functions to mimic SQLite API
export const dbRun = async (sql, params = []) => {
  // This will need custom implementation per query
  // Supabase uses different API than raw SQL
  console.warn('dbRun not directly supported with Supabase. Use supabase client methods.');
};

export const dbGet = async (tableName, query = {}) => {
  const { data, error } = await supabase
    .from(tableName)
    .select('*')
    .match(query)
    .single();
  
  if (error) throw error;
  return data;
};

export const dbAll = async (tableName, query = {}) => {
  const { data, error } = await supabase
    .from(tableName)
    .select('*')
    .match(query);
  
  if (error) throw error;
  return data;
};

export default supabase;
