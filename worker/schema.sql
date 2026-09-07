-- D1 schema for the calibration probe collector.
-- Stores opt-in submissions from probe.py. No IP addresses, no user identity.
-- Run this with: wrangler d1 execute probe-results --file=schema.sql

CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model_label TEXT NOT NULL,
  client_timestamp INTEGER NOT NULL,
  server_timestamp INTEGER NOT NULL,
  n_tasks INTEGER NOT NULL,
  n_ok INTEGER NOT NULL,
  n_fail INTEGER NOT NULL,
  -- JSON blobs: per_task trajectories, scan results, best signal
  per_task_json TEXT NOT NULL,
  scan_top10_json TEXT NOT NULL,
  best_signal_json TEXT,
  -- derived flags for quick aggregation
  has_signal INTEGER NOT NULL DEFAULT 0,
  underpowered INTEGER NOT NULL DEFAULT 0,
  no_failures INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_submissions_model ON submissions(model_label);
CREATE INDEX IF NOT EXISTS idx_submissions_has_signal ON submissions(has_signal);
CREATE INDEX IF NOT EXISTS idx_submissions_server_ts ON submissions(server_timestamp);

-- Aggregate view: per-model signal rates
CREATE VIEW IF NOT EXISTS v_model_stats AS
SELECT
  model_label,
  COUNT(*) AS n_runs,
  SUM(has_signal) AS n_with_signal,
  SUM(underpowered) AS n_underpowered,
  SUM(no_failures) AS n_no_failures,
  SUM(n_ok) AS total_pass,
  SUM(n_fail) AS total_fail,
  -- average pass rate across runs
  ROUND(AVG(CAST(n_ok AS REAL) / NULLIF(n_tasks, 0)), 3) AS avg_pass_rate
FROM submissions
GROUP BY model_label
ORDER BY n_runs DESC;
