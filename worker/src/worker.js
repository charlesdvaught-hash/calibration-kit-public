/**
 * Calibration Probe Collector — Cloudflare Worker
 *
 * Accepts opt-in submissions from probe.py, stores them in D1,
 * and exposes aggregate stats. No IP addresses are logged or stored.
 *
 * Endpoints:
 *   POST /submit    — store a probe result (JSON body)
 *   GET  /stats     — aggregate stats across all submissions
 *   GET  /models    — per-model breakdown
 *   GET  /health    — simple health check
 *   GET  /          — landing page with instructions
 *
 * Privacy:
 *   - IP addresses are used only for in-memory rate limiting and are
 *     never written to D1 or any log.
 *   - The payload contains only entropy trajectories, pass/fail flags,
 *     and signal scan results. No code, no prompts, no user identity.
 */

const MAX_PAYLOAD_BYTES = 512 * 1024; // 512 KB
const RATE_LIMIT_PER_HOUR = 10;

// In-memory rate limiting (per-isolate, approximate — good enough for free tier)
const rateLimitMap = new Map(); // key: hashed-ip-hour -> count

// ─── Helpers ────────────────────────────────────────────────────────────────

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(),
    },
  });
}

function checkRateLimit(ip) {
  if (!ip) return true; // can't rate-limit without IP, allow it
  const hour = Math.floor(Date.now() / 3600000);
  const key = `${ip}:${hour}`;
  const count = rateLimitMap.get(key) || 0;
  if (count >= RATE_LIMIT_PER_HOUR) return false;
  rateLimitMap.set(key, count + 1);
  // Cleanup old entries (keep memory bounded)
  if (rateLimitMap.size > 10000) {
    for (const [k] of rateLimitMap) {
      const kHour = parseInt(k.split(':').pop(), 10);
      if (kHour < hour - 1) rateLimitMap.delete(k);
    }
  }
  return true;
}

function validatePayload(p) {
  const errors = [];
  if (!p || typeof p !== 'object') {
    return ['payload must be a JSON object'];
  }
  if (typeof p.model_label !== 'string' || p.model_label.length > 200) {
    errors.push('model_label must be a string (max 200 chars)');
  }
  if (typeof p.timestamp !== 'number') {
    errors.push('timestamp must be a number');
  }
  if (typeof p.n_tasks !== 'number' || p.n_tasks < 0 || p.n_tasks > 1000) {
    errors.push('n_tasks must be a number 0-1000');
  }
  if (typeof p.n_ok !== 'number' || p.n_ok < 0) {
    errors.push('n_ok must be a non-negative number');
  }
  if (typeof p.n_fail !== 'number' || p.n_fail < 0) {
    errors.push('n_fail must be a non-negative number');
  }
  if (!Array.isArray(p.per_task)) {
    errors.push('per_task must be an array');
  }
  if (!Array.isArray(p.scan_top10)) {
    errors.push('scan_top10 must be an array');
  }
  // best_signal can be null or an object
  if (p.best_signal !== null && typeof p.best_signal !== 'object') {
    errors.push('best_signal must be null or an object');
  }
  return errors;
}

function deriveFlags(p) {
  const hasSignal = p.best_signal !== null && typeof p.best_signal === 'object';
  const underpowered = p.n_fail < 3 && p.n_fail > 0;
  const noFailures = p.n_fail === 0;
  return { has_signal: hasSignal ? 1 : 0, underpowered: underpowered ? 1 : 0, no_failures: noFailures ? 1 : 0 };
}

// ─── Route handlers ─────────────────────────────────────────────────────────

async function handleSubmit(request, env) {
  // Get IP for rate limiting only — never stored
  const ip = request.headers.get('CF-Connecting-IP') ||
             request.headers.get('X-Forwarded-For') || '';
  if (!checkRateLimit(ip)) {
    return json({ error: 'Rate limit exceeded. Max 10 submissions per hour.' }, 429);
  }

  // Check payload size
  const contentLength = parseInt(request.headers.get('Content-Length') || '0', 10);
  if (contentLength > MAX_PAYLOAD_BYTES) {
    return json({ error: `Payload too large (max ${MAX_PAYLOAD_BYTES} bytes)` }, 413);
  }

  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ error: 'Invalid JSON' }, 400);
  }

  const errors = validatePayload(payload);
  if (errors.length > 0) {
    return json({ error: 'Validation failed', details: errors }, 400);
  }

  const flags = deriveFlags(payload);
  const now = Math.floor(Date.now() / 1000);

  try {
    await env.DB.prepare(
      `INSERT INTO submissions
       (model_label, client_timestamp, server_timestamp, n_tasks, n_ok, n_fail,
        per_task_json, scan_top10_json, best_signal_json,
        has_signal, underpowered, no_failures)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).bind(
      payload.model_label,
      payload.timestamp,
      now,
      payload.n_tasks,
      payload.n_ok,
      payload.n_fail,
      JSON.stringify(payload.per_task),
      JSON.stringify(payload.scan_top10),
      payload.best_signal ? JSON.stringify(payload.best_signal) : null,
      flags.has_signal,
      flags.underpowered,
      flags.no_failures,
    ).run();

    return json({
      ok: true,
      message: 'Submission stored. Thank you for contributing to the public evidence corpus.',
      flags,
    });
  } catch (e) {
    return json({ error: 'Database error', details: e.message }, 500);
  }
}

async function handleStats(env) {
  try {
    const total = await env.DB.prepare(
      'SELECT COUNT(*) as n FROM submissions'
    ).first();

    const signalStats = await env.DB.prepare(
      `SELECT
         SUM(has_signal) as n_with_signal,
         SUM(underpowered) as n_underpowered,
         SUM(no_failures) as n_no_failures,
         SUM(CASE WHEN has_signal = 0 AND underpowered = 0 AND no_failures = 0 THEN 1 ELSE 0 END) as n_no_signal
       FROM submissions`
    ).first();

    const distinctModels = await env.DB.prepare(
      'SELECT COUNT(DISTINCT model_label) as n FROM submissions'
    ).first();

    const recent = await env.DB.prepare(
      `SELECT model_label, n_tasks, n_ok, n_fail, has_signal, underpowered, no_failures, server_timestamp
       FROM submissions
       ORDER BY server_timestamp DESC
       LIMIT 20`
    ).all();

    return json({
      total_submissions: total?.n || 0,
      distinct_models: distinctModels?.n || 0,
      verdicts: {
        signal_found: signalStats?.n_with_signal || 0,
        no_signal: signalStats?.n_no_signal || 0,
        underpowered: signalStats?.n_underpowered || 0,
        no_failures: signalStats?.n_no_failures || 0,
      },
      recent_submissions: recent?.results || [],
    });
  } catch (e) {
    return json({ error: 'Database error', details: e.message }, 500);
  }
}

async function handleModels(env) {
  try {
    const results = await env.DB.prepare(
      `SELECT * FROM v_model_stats`
    ).all();
    return json({
      models: results?.results || [],
      count: results?.results?.length || 0,
    });
  } catch (e) {
    return json({ error: 'Database error', details: e.message }, 500);
  }
}

function handleHealth() {
  return json({ ok: true, timestamp: Math.floor(Date.now() / 1000) });
}

function handleLanding() {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Calibration Probe Collector</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #1a1a1a; }
  h1 { font-size: 1.5rem; }
  code { background: #f0f0f0; padding: 0.15em 0.3em; border-radius: 3px; font-size: 0.9em; }
  pre { background: #f0f0f0; padding: 1rem; border-radius: 6px; overflow-x: auto; }
  .endpoint { display: inline-block; padding: 0.1em 0.4em; border-radius: 3px; font-weight: bold; color: white; }
  .get { background: #2563eb; }
  .post { background: #059669; }
</style>
</head>
<body>
<h1>Calibration Probe Collector</h1>
<p>This is the public evidence corpus endpoint for the
<a href="https://github.com/charlesdvaught-hash/calibration-kit-public">calibration probe</a>.</p>

<h2>Endpoints</h2>
<p><span class="endpoint post">POST</span> <code>/submit</code> — Store a probe result (called by probe.py)</p>
<p><span class="endpoint get">GET</span> <code>/stats</code> — Aggregate stats across all submissions</p>
<p><span class="endpoint get">GET</span> <code>/models</code> — Per-model breakdown</p>
<p><span class="endpoint get">GET</span> <code>/health</code> — Health check</p>

<h2>Privacy</h2>
<ul>
<li><strong>No IP addresses</strong> are stored. IP is used only for in-memory rate limiting.</li>
<li><strong>No generated code</strong> is sent by the probe — only entropy trajectories and pass/fail flags.</li>
<li><strong>No user identity</strong> — the probe sends only model filename, trajectories, and signal scan results.</li>
</ul>

<h2>Contributing</h2>
<p>Run the probe with <code>--upload-url &lt;this-url&gt;/submit</code> to contribute:</p>
<pre>python probe.py --model your-model.gguf --upload-url https://this-worker.workers.dev/submit</pre>
<p>Or set the <code>PROBE_UPLOAD_URL</code> environment variable.</p>
</body>
</html>`;
  return new Response(html, {
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
  });
}

// ─── Main entry ─────────────────────────────────────────────────────────────

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Handle CORS preflight
    if (method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders() });
    }

    try {
      if (path === '/' && method === 'GET') {
        return handleLanding();
      }
      if (path === '/health' && method === 'GET') {
        return handleHealth();
      }
      if (path === '/submit' && method === 'POST') {
        return await handleSubmit(request, env);
      }
      if (path === '/stats' && method === 'GET') {
        return await handleStats(env);
      }
      if (path === '/models' && method === 'GET') {
        return await handleModels(env);
      }
      return json({ error: 'Not found', path }, 404);
    } catch (e) {
      return json({ error: 'Internal error', details: e.message }, 500);
    }
  },
};
