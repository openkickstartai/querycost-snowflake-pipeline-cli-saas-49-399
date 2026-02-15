# QueryCost — Query-Level Cloud Warehouse Cost Attribution

Stop getting surprised by your Snowflake/BigQuery bill. QueryCost fingerprints every query, calculates per-query costs, detects anomalies, and identifies the users and pipelines burning your budget.

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Scan a query history export (CSV)
python main.py scan sample.csv --platform bigquery

# Top 10 most expensive query patterns
python main.py top sample.csv -n 10

# Detect cost anomalies (z-score based)
python main.py anomalies sample.csv

# Top spenders by user
python main.py users sample.csv

# JSON output for CI/CD integration
python main.py scan sample.csv --json-out
```

### CSV Format

| Column | Required | Description |
|---|---|---|
| `query_text` | ✅ | SQL query string |
| `user_email` | ✅ | Who ran it |
| `bytes_scanned` | ✅ (BQ) | Bytes processed |
| `credits_used` | ✅ (SF) | Snowflake credits |
| `execution_time_ms` | optional | Runtime in ms |

## 📊 Why Pay for QueryCost?

Teams spending **$10k+/month** on cloud warehouses typically waste **20-40%** on unoptimized queries. QueryCost pays for itself by finding:

- 🔴 Full-table scans costing $50+ each run
- 📈 Queries that suddenly 10x in cost (anomaly detection)
- 👤 Users running expensive ad-hoc queries without filters
- 🔁 Identical query patterns running thousands of times

**ROI example**: $20k/month warehouse → find $4k waste → QueryCost costs $99/month → **40x ROI**

## 💰 Pricing

| Feature | Free | Pro $49/mo | Team $199/mo | Enterprise $399/mo |
|---|---|---|---|---|
| Query fingerprinting | ✅ | ✅ | ✅ | ✅ |
| Cost estimation (BQ/SF) | ✅ | ✅ | ✅ | ✅ |
| Top queries & users | 10 | Unlimited | Unlimited | Unlimited |
| Anomaly detection | ❌ | ✅ | ✅ | ✅ |
| JSON/CI output | ❌ | ✅ | ✅ | ✅ |
| Slack/webhook alerts | ❌ | ❌ | ✅ | ✅ |
| Team attribution | ❌ | ❌ | ✅ | ✅ |
| dbt/Airflow integration | ❌ | ❌ | ❌ | ✅ |
| Redshift + Databricks | ❌ | ❌ | ❌ | ✅ |
| SaaS dashboard | ❌ | ❌ | ✅ | ✅ |
| SSO & audit log | ❌ | ❌ | ❌ | ✅ |

## Architecture

```
query_history.csv → fingerprint → cost calc → anomaly detect → report
                         │              │              │
                    group by SQL    $/TB or $/credit   z-score
```

## License

BSL 1.1 — Free for teams < 5 users. Commercial license required above.
