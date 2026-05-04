/**
 * Supabase client for the browser. Uses the public anon key, which is safe to
 * expose since Row Level Security on the database controls actual access.
 */

import { createClient } from "@supabase/supabase-js";

import type { Database } from "./types";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing Supabase environment variables. Check web/.env.local has NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY."
  );
}

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: false,
  },
});

export const DEFAULT_SCHOOL =
  process.env.NEXT_PUBLIC_DEFAULT_SCHOOL ?? "vanderbilt";
