#!/usr/bin/env python3
"""QueryCost CLI — Find wasteful cloud warehouse queries before bill shock."""
import json
import click
import pandas as pd
from querycost_engine import (
    analyze_queries, detect_anomalies, top_queries, top_users, summary,
)

BANNER = (
    "\n╔══════════════════════════════════════════════╗"
    "\n║  QueryCost — Query Cost Attribution Engine   ║"
    "\n╚══════════════════════════════════════════════╝\n"
)


@click.group()
@click.version_option('0.1.0')
def cli():
    """QueryCost: query-level cost attribution & anomaly detection."""


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--platform', '-p', default='bigquery',
              type=click.Choice(['bigquery', 'snowflake']))
@click.option('--json-out', '-j', is_flag=True, help='Output JSON')
def scan(csv_file, platform, json_out):
    """Scan query history and print cost summary."""
    df = analyze_queries(pd.read_csv(csv_file), platform)
    report = summary(df)
    if json_out:
        click.echo(json.dumps(report, indent=2))
        return
    click.echo(BANNER)
    for key, val in report.items():
        label = key.replace('_', ' ').title()
        click.echo(f"  {label:.<35} {val}")


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--platform', '-p', default='bigquery')
@click.option('-n', default=10, help='Number of results')
def top(csv_file, platform, n):
    """Show top N most expensive query patterns."""
    df = analyze_queries(pd.read_csv(csv_file), platform)
    for _, r in top_queries(df, n).iterrows():
        click.echo(f"  ${r['total_cost']:>8.4f} | {int(r['runs']):>4}x | {r['pattern'][:55]}")


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--platform', '-p', default='bigquery')
@click.option('--threshold', '-t', default=2.5, help='Z-score threshold')
def anomalies(csv_file, platform, threshold):
    """Detect cost anomalies in query history."""
    df = analyze_queries(pd.read_csv(csv_file), platform)
    anoms = detect_anomalies(df, threshold)
    if anoms.empty:
        click.echo("  ✅ No anomalies detected.")
        return
    click.echo(f"  ⚠️  {len(anoms)} anomalies found:\n")
    for _, r in anoms.iterrows():
        click.echo(
            f"  ${r['cost_usd']:>8.4f} (z={r['z_score']}) "
            f"| {r['user']} | {r['query_preview'][:45]}"
        )


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--platform', '-p', default='bigquery')
@click.option('-n', default=10)
def users(csv_file, platform, n):
    """Show top N most expensive users."""
    df = analyze_queries(pd.read_csv(csv_file), platform)
    for _, r in top_users(df, n).iterrows():
        flag = f" 🔴{int(r['full_scans'])}scans" if r['full_scans'] > 0 else ""
        click.echo(
            f"  ${r['total_cost']:>8.4f} | {int(r['queries']):>4} queries "
            f"| {r['user_email']}{flag}"
        )


if __name__ == '__main__':
    cli()
