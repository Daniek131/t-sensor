-- PostgreSQL: most recent readings from one organization and device.
-- Replace these public demo identifiers with your own registered values.
SELECT observed_at, moisture, temperature, ec, ph, nitrogen, phosphorus, potassium, source
FROM readings
WHERE org_id = 'synthetic-demo' AND device_id = 'probe-demo'
ORDER BY observed_at DESC
LIMIT 100;

-- Hourly averages remain grouped by both organization and device.
SELECT org_id, device_id, DATE_TRUNC('hour', observed_at) AS hour,
       AVG(moisture) AS moisture_mean, AVG(temperature) AS temperature_mean,
       AVG(ec) AS ec_mean, COUNT(*) AS samples
FROM readings
GROUP BY org_id, device_id, DATE_TRUNC('hour', observed_at)
ORDER BY hour DESC;
