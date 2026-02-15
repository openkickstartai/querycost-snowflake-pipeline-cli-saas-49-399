"""QueryCost engine — SQL fingerprinting, cost estimation, anomaly detection."""
import re
import hashlib
import pandas as pd
import numpy as np

BQ_PRICE_PER_TB = 5.0
SF_CREDIT_PRICE = 3.0
FULL_SCAN_BYTES_THRESHOLD = 1_000_000_000  # 1 GB


def fingerprint_sql(sql: str) -> str:
    """Normalize SQL to a canonical fingerprint for grouping."""
    s = re.sub(r'--[^\n]*', '', sql.strip().lower())
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
    s = re.sub(r"'[^']*'", "'?'", s)
    s = re.sub(r'\b\d+\.?\d*\b', '?', s)
    return re.sub(r'\s+', ' ', s).strip()


def fingerprint_id(fp: str) -> str:
    """Short hash for a fingerprint string."""
    return hashlib.md5(fp.encode()).hexdigest()[:12]


def analyze_queries(df: pd.DataFrame, platform: str = "bigquery") -> pd.DataFrame:
    """Add fingerprint, cost, and full-scan columns to query history."""
    r = df.copy()
    r['fingerprint'] = r['query_text'].apply(fingerprint_sql)
    r['fp_id'] = r['fingerprint'].apply(fingerprint_id)
    if platform == "snowflake" and 'credits_used' in r.columns:
        r['cost_usd'] = r['credits_used'] * SF_CREDIT_PRICE
    else:
        r['cost_usd'] = r['bytes_scanned'] * BQ_PRICE_PER_TB / 1e12
    r['is_full_scan'] = r['bytes_scanned'] > FULL_SCAN_BYTES_THRESHOLD
    return r


def detect_anomalies(df: pd.DataFrame, z_thresh: float = 2.5) -> pd.DataFrame:
    """Find queries with cost z-score above threshold within their fingerprint group."""
    rows = []
    for fp_id, grp in df.groupby('fp_id'):
        if len(grp) < 3:
            continue
        mu, sigma = grp['cost_usd'].mean(), grp['cost_usd'].std()
        if sigma < 1e-12:
            continue
        for idx, row in grp.iterrows():
            z = (row['cost_usd'] - mu) / sigma
            if z > z_thresh:
                rows.append({
                    'fp_id': fp_id,
                    'query_preview': row['query_text'][:80],
                    'user': row['user_email'],
                    'cost_usd': round(row['cost_usd'], 4),
                    'mean_cost': round(mu, 4),
                    'z_score': round(z, 2),
                })
    return pd.DataFrame(rows)


def top_queries(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Rank query fingerprints by total cost."""
    return df.groupby('fp_id').agg(
        pattern=('fingerprint', 'first'),
        total_cost=('cost_usd', 'sum'),
        avg_cost=('cost_usd', 'mean'),
        runs=('cost_usd', 'count'),
        users=('user_email', lambda x: ','.join(sorted(set(x))[:3])),
    ).sort_values('total_cost', ascending=False).head(n).reset_index()


def top_users(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Rank users by total query cost."""
    return df.groupby('user_email').agg(
        total_cost=('cost_usd', 'sum'),
        queries=('cost_usd', 'count'),
        full_scans=('is_full_scan', 'sum'),
        avg_cost=('cost_usd', 'mean'),
    ).sort_values('total_cost', ascending=False).head(n).reset_index()


def summary(df: pd.DataFrame) -> dict:
    """Generate a full cost attribution summary."""
    total = df['cost_usd'].sum()
    fs_cost = df.loc[df['is_full_scan'], 'cost_usd'].sum()
    return {
        'total_cost_usd': round(total, 2),
        'total_queries': len(df),
        'unique_patterns': int(df['fp_id'].nunique()),
        'unique_users': int(df['user_email'].nunique()),
        'full_scan_count': int(df['is_full_scan'].sum()),
        'full_scan_cost_pct': round(fs_cost / max(total, 1e-9) * 100, 1),
        'anomaly_count': len(detect_anomalies(df)),
    }
