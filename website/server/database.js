import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing Supabase credentials in .env file');
  console.error('Please add SUPABASE_URL and SUPABASE_KEY to your .env file');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

console.log('✅ Connected to Supabase');

// Helper functions for database operations
export const dbRun = async (table, operation, data) => {
  if (operation === 'insert') {
    const { data: result, error } = await supabase
      .from(table)
      .insert(data)
      .select()
      .single();
    
    if (error) throw error;
    return { lastID: result.id, changes: 1 };
  } else if (operation === 'update') {
    const { match, set } = data;
    const { error } = await supabase
      .from(table)
      .update(set)
      .match(match);
    
    if (error) throw error;
    return { changes: 1 };
  }
};

export const dbGet = async (table, query = {}) => {
  const { data, error } = await supabase
    .from(table)
    .select('*')
    .match(query)
    .single();
  
  if (error && error.code !== 'PGRST116') throw error; // PGRST116 = no rows
  return data;
};

export const dbAll = async (table, query = {}, options = {}) => {
  let queryBuilder = supabase.from(table).select(options.select || '*');
  
  // Apply filters
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      queryBuilder = queryBuilder.eq(key, value);
    });
  }
  
  // Apply ordering
  if (options.orderBy) {
    const { column, ascending = false } = options.orderBy;
    queryBuilder = queryBuilder.order(column, { ascending });
  }
  
  const { data, error } = await queryBuilder;
  
  if (error) throw error;
  return data || [];
};

export default supabase;
