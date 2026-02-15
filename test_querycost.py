"""Tests for QueryCost engine — fingerprinting, costing, anomaly detection."""
import pandas as pd
import pytest
from querycost_engine import (
    fingerprint_sql, fingerprint_id, analyze_queries,
    detect_anomalies, top_queries, top_users, summary,
)


def _make_df(n=30, anomaly_idx=None, anomaly_bytes=5e12):
    """Deterministic test query history."""
    templates = [
        ("SELECT * FROM orders WHERE id = {}", "alice@co.com"),
        ("SELECT count(*) FROM events WHERE dt = '2024-0{}-01'", "bob@co.com"),
        ("SELECT a.name FROM users a WHERE a.region = '{}'", "carol@co.com"),
    ]
    rows = []
    for i in range(n):
        tpl, user = templates[i % 3]
        bs = 5e8 + i * 1e7
        if anomaly_idx is not None and i == anomaly_idx:
            bs = anomaly_bytes
        rows.append({
            'query_text': tpl.format(i),
            'user_email': user,
            'bytes_scanned': bs,
            'execution_time_ms': 1000 + i * 50,
        })
    return pd.DataFrame(rows)


def test_fingerprint_normalizes_numbers():
    assert fingerprint_sql("SELECT * FROM t WHERE id = 123") == \
           fingerprint_sql("SELECT * FROM t WHERE id = 999")


def test_fingerprint_normalizes_strings():
    assert fingerprint_sql("SELECT * FROM t WHERE name = 'alice'") == \
           fingerprint_sql("SELECT * FROM t WHERE name = 'bob'")


def test_fingerprint_different_structure():
    f1 = fingerprint_sql("SELECT * FROM orders WHERE id = 1")
    f2 = fingerprint_sql("SELECT count(*) FROM events WHERE dt = '2024'")
    assert f1 != f2
    assert fingerprint_id(f1) != fingerprint_id(f2)


def test_analyze_bigquery_costs():
    df = analyze_queries(_make_df(), 'bigquery')
    assert 'cost_usd' in df.columns
    assert 'fp_id' in df.columns
    assert 'is_full_scan' in df.columns
    assert all(df['cost_usd'] >= 0)
    assert df['cost_usd'].sum() > 0


def test_analyze_snowflake_costs():
    df = _make_df()
    df['credits_used'] = df['bytes_scanned'] / 1e11
    result = analyze_queries(df, 'snowflake')
    assert result['cost_usd'].sum() > 0
    assert all(result['cost_usd'] == df['credits_used'] * 3.0)


def test_full_scan_detection():
    df = analyze_queries(_make_df(), 'bigquery')
    above = df[df['bytes_scanned'] > 1e9]
    below = df[df['bytes_scanned'] <= 1e9]
    assert all(above['is_full_scan']) if len(above) else True
    assert not any(below['is_full_scan'])


def test_detect_anomalies_finds_spike():
    df = analyze_queries(_make_df(30, anomaly_idx=18, anomaly_bytes=5e12), 'bigquery')
    anoms = detect_anomalies(df, z_thresh=2.5)
    assert len(anoms) >= 1
    assert anoms.iloc[0]['cost_usd'] > anoms.iloc[0]['mean_cost'] * 5


def test_detect_anomalies_clean_data():
    df = analyze_queries(_make_df(30), 'bigquery')
    anoms = detect_anomalies(df, z_thresh=2.5)
    assert len(anoms) == 0


def test_top_queries_ordering():
    df = analyze_queries(_make_df(), 'bigquery')
    tq = top_queries(df, 3)
    assert len(tq) == 3
    costs = tq['total_cost'].tolist()
    assert costs == sorted(costs, reverse=True)


def test_top_users_counts():
    df = analyze_queries(_make_df(), 'bigquery')
    tu = top_users(df, 3)
    assert len(tu) == 3
    assert tu['queries'].sum() == 30


def test_summary_report():
    df = analyze_queries(_make_df(), 'bigquery')
    s = summary(df)
    assert s['total_queries'] == 30
    assert s['unique_patterns'] == 3
    assert s['unique_users'] == 3
    assert s['total_cost_usd'] > 0
    assert 'anomaly_count' in s
    assert 'full_scan_cost_pct' in s
