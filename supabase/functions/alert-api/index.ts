// supabase/functions/alert-api/index.ts

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-api-key',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

interface AlertRequest {
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
  application?: string
  metadata?: Record<string, any>
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  // Only allow POST requests
  if (req.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { 
        status: 405, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }

  try {
    // Get API key from header (user's custom API key)
    const apiKey = req.headers.get('x-api-key') || req.headers.get('authorization')?.replace('Bearer ', '')
    
    if (!apiKey) {
      return new Response(
        JSON.stringify({ error: 'API key required' }),
        { 
          status: 401, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Initialize Supabase client with service role key (full access)
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    // Validate API key and get user
    const { data: user, error: userError } = await supabase
      .from('users')
      .select('*')
      .eq('api_key', apiKey)
      .eq('is_active', true)
      .single()

    if (userError || !user) {
      return new Response(
        JSON.stringify({ error: 'Invalid or inactive API key' }),
        { 
          status: 401, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Parse request body
    const alertData: AlertRequest = await req.json()

    // Validate required fields
    if (!alertData.message || !alertData.level) {
      return new Response(
        JSON.stringify({ error: 'Missing required fields: message and level' }),
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Validate level
    const validLevels = ['info', 'warn', 'error', 'debug']
    if (!validLevels.includes(alertData.level.toLowerCase())) {
      return new Response(
        JSON.stringify({ error: `Invalid level. Must be one of: ${validLevels.join(', ')}` }),
        { 
          status: 400, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Store alert in database for Discord bot to process
    const { error: alertError } = await supabase
      .from('pending_alerts')
      .insert({
        discord_user_id: user.discord_user_id,
        level: alertData.level.toLowerCase(),
        message: alertData.message,
        application: alertData.application || 'Unknown',
        metadata: alertData.metadata || {}
      })
    
    if (alertError) {
      console.error('Failed to queue alert:', alertError)
      return new Response(
        JSON.stringify({ error: 'Failed to queue alert' }),
        { 
          status: 500, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Success response
    return new Response(
      JSON.stringify({ 
        success: true, 
        message: 'Alert queued successfully'
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )

  } catch (error) {
    console.error('Error processing alert request:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { 
        status: 500, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})