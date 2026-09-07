# Probe Collector Worker

Cloudflare Worker that collects opt-in probe results from the public.
Stores submissions in D1 (SQLite). No IP addresses, no user identity,
no generated code — only entropy trajectories and signal scan results.

## Deploy (5 minutes, free tier)

### 1. Install Wrangler

```bash
npm install -g wrangler
wrangler login
```

### 2. Create the D1 database

```bash
cd worker
wrangler d1 create probe-results
```

This prints a `database_id`. Copy it into `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "probe-results"
database_id = "PASTE_THE_ID_HERE"
```

### 3. Create the schema

```bash
wrangler d1 execute probe-results --file=schema.sql
```

### 4. Deploy

```bash
wrangler deploy
```

This prints your worker URL, e.g.:
```
https://calibration-probe-collector.<your-subdomain>.workers.dev
```

### 5. Test it

```bash
# Health check
curl https://calibration-probe-collector.your-subdomain.workers.dev/health

# View aggregate stats
curl https://calibration-probe-collector.your-subdomain.workers.dev/stats

# View per-model breakdown
curl https://calibration-probe-collector.your-subdomain.workers.dev/models
```

### 6. Tell users to upload

Set the default upload URL in the probe by editing `probe.py`:

```python
DEFAULT_UPLOAD_URL = "https://calibration-probe-collector.your-subdomain.workers.dev/submit"
```

Or users can pass it directly:

```bash
python probe.py --model your-model.gguf \
  --upload-url https://calibration-probe-collector.your-subdomain.workers.dev/submit
```

Or set the environment variable:

```bash
export PROBE_UPLOAD_URL=https://calibration-probe-collector.your-subdomain.workers.dev/submit
python probe.py --model your-model.gguf
```

## What gets stored

```sql
CREATE TABLE submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model_label TEXT,          -- e.g. "qwen3-4b-Q5_K_M.gguf"
  client_timestamp INTEGER,  -- from the probe
  server_timestamp INTEGER,  -- when the worker received it
  n_tasks INTEGER,           -- usually 42
  n_ok INTEGER,              -- how many passed
  n_fail INTEGER,            -- how many failed
  per_task_json TEXT,        -- per-task trajectories + pass/fail
  scan_top10_json TEXT,      -- top 10 signal candidates
  best_signal_json TEXT,     -- the winning signal or null
  has_signal INTEGER,        -- 1 if a signal survived correction
  underpowered INTEGER,      -- 1 if too few failures
  no_failures INTEGER        -- 1 if model passed everything
);
```

## What does NOT get stored

- **No IP addresses** — used only for in-memory rate limiting, never written to D1
- **No generated code** — the probe only sends entropy trajectories and pass/fail
- **No prompts** — tasks are standard public tasks, no need to send descriptions
- **No user identity** — no accounts, no tokens, no names

## Querying the data

```bash
# Total submissions and verdict distribution
wrangler d1 execute probe-results --command="
  SELECT COUNT(*) as total,
    SUM(has_signal) as with_signal,
    SUM(underpowered) as underpowered,
    SUM(no_failures) as no_failures
  FROM submissions"

# Per-model stats
wrangler d1 execute probe-results --command="
  SELECT * FROM v_model_stats"

# All submissions for a specific model
wrangler d1 execute probe-results --command="
  SELECT model_label, n_ok, n_fail, has_signal, best_signal_json
  FROM submissions
  WHERE model_label LIKE '%qwen3-4b%'
  ORDER BY server_timestamp DESC"
```

## Costs

Cloudflare Workers free tier includes:
- 100,000 requests/day
- 5M D1 reads/day
- 100K D1 writes/day
- 5GB D1 storage

This is more than enough for a public probe corpus. Each submission is
one write (~1KB). You'd need 100K submissions/day to hit the write limit.

## Rate limiting

The worker limits each IP to 10 submissions per hour (in-memory, per-isolate).
This is approximate — Workers isolates may rotate, so the real limit may be
slightly higher. The goal is to prevent abuse, not to enforce exact quotas.
