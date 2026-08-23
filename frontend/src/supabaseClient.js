import { createClient } from '@supabase/supabase-js'

// Using service role key for this admin-only dashboard.
// This bypasses RLS so all tables are readable.
// ⚠️  Never expose this key in a public-facing app.
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_SERVICE_ROLE_KEY

export const supabase = createClient(supabaseUrl, supabaseKey)

