#!/usr/bin/env python3
"""
hermes-pro — Central command center for all income streams.
Aggregates data from ALL repos to show:
- Real-time income
- Customer acquisition
- $500/day progress
- Multi-product dashboard

Revenue source of truth
-----------------------
REAL booked revenue is read exclusively from data/revenue.json, which is
populated by hermes-pay/scripts/webhook.py (Ko-fi + Gumroad live webhook
events). This file is synced here from hermes-pay — see PAYMENTS.md in
hermes-pay for the sync procedure.

NEVER use est_commission, modeled figures, or test entries from individual
repo income_log.json files as revenue. Those files may still be scanned for
informational context but are NOT counted in the dashboard totals.
"""
import os, sys, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# Canonical real-revenue log.  Populated by hermes-pay webhook handler.
# If absent the dashboard correctly shows $0 booked.
REVENUE_FILE = DATA_DIR / "revenue.json"

# Experiment 0 funnel metrics (pageview -> checkout/signup -> trial -> paid),
# filled weekly from GA4.  If absent the funnel section is hidden.
FUNNEL_FILE = DATA_DIR / "funnel.json"

ALL_REPOS = [
    "hermes-make-money",
    "hermes-deal-finder",
    "hermes-seo-farm",
    "hermes-lead-magnet",
    "hermes-content-recycle",
    "hermes-shortsgen",
    "pixabay-shorts-bot",
]

REPO_DIRS = {
    repo: Path(__file__).parent.parent.parent / repo
    for repo in ALL_REPOS
}

# $500/day target
TARGET_DAILY = 500.0
TARGET_MONTHLY = TARGET_DAILY * 30

# Product definitions with pricing
PRODUCTS = {
    "shortsgen": {
        "name": "ShortsGen Pro",
        "url": "https://github.com/slashman413/hermes-shortsgen",
        "tiers": {"free": 0, "pro": 29, "business": 99, "enterprise": 499},
        "target_customers": {"pro": 165, "business": 50, "enterprise": 15},
    },
    "deal_finder": {
        "name": "Deal Finder Pro",
        "url": "https://github.com/slashman413/hermes-deal-finder",
        "tiers": {"free": 0, "pro": 9, "business": 29},
        "target_customers": {"pro": 300, "business": 50},
    },
    "seo_farm": {
        "name": "SEO Content Engine",
        "url": "https://github.com/slashman413/hermes-seo-farm",
        "tiers": {"free": 0, "pro": 19},
        "target_customers": {"pro": 200},
    },
    "lead_magnet": {
        "name": "Lead Magnet Pro",
        "url": "https://github.com/slashman413/hermes-lead-magnet",
        "tiers": {"free": 0, "pro": 9},
        "target_customers": {"pro": 500},
    },
    "affiliate": {
        "name": "聯盟行銷",
        "url": "https://github.com/slashman413/hermes-deal-finder",
        "description": "Amazon/博客來聯盟佣金",
        "commission_rate": 0.04,  # 4% avg
        "target_monthly_sales": 25000,  # $25k in sales to get $1000
    },
    "adsense": {
        "name": "AdSense 廣告",
        "url": "https://github.com/slashman413/hermes-seo-farm",
        "description": "工具站 + SEO 站廣告收入",
        "target_rpm": 3.0,  # $3 per 1000 views
        "target_daily_views": 50000,  # 50k views/day
    },
    "sponsors": {
        "name": "GitHub Sponsors",
        "url": "https://github.com/slashman413/hermes-make-money",
        "target_monthly": 500,
    },
}


def load_real_revenue() -> dict:
    """
    Load REAL booked revenue from data/revenue.json (webhook-sourced records).

    Returns:
        {
            "records": list of raw records,
            "by_product": {product_key: [records]},
            "total": float total in USD,
        }

    This is the ONLY function whose output counts toward the dashboard's
    booked-revenue numbers.  It deliberately does NOT read est_commission or
    any modeled figure.
    """
    by_product: dict = defaultdict(list)
    total = 0.0

    if REVENUE_FILE.exists():
        try:
            records = json.loads(REVENUE_FILE.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                records = []
        except Exception:
            records = []
    else:
        records = []

    for rec in records:
        # Only count records with a real positive amount.
        # est_commission / modeled fields are NOT present in this file;
        # if someone accidentally merged an old income_log entry, guard here.
        amt = rec.get("amount", 0)
        try:
            amt = float(amt)
        except (TypeError, ValueError):
            amt = 0.0
        if amt <= 0:
            continue
        total += amt
        product_key = rec.get("product", "unknown")
        by_product[product_key].append(rec)

    return {
        "records": records,
        "by_product": dict(by_product),
        "total": round(total, 2),
    }


def load_funnel() -> dict:
    """
    Load the latest week's funnel metrics from data/funnel.json.

    Returns {"week_of": str, "products": {...}} for the most recent week,
    or {} if the file is missing/empty.  This is the top-of-funnel companion
    to booked revenue: it answers "is traffic reaching checkout?", which
    revenue alone cannot.
    """
    if not FUNNEL_FILE.exists():
        return {}
    try:
        data = json.loads(FUNNEL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    weeks = data.get("weeks", [])
    if not weeks:
        return {}
    # Latest by week_of (ISO date sorts lexically)
    latest = sorted(weeks, key=lambda w: w.get("week_of", ""))[-1]
    return latest


def render_funnel_rows(funnel: dict) -> str:
    """Build the funnel table rows (pageview -> checkout/signup -> trial -> paid)."""
    products = funnel.get("products", {})
    if not products:
        return ('<tr><td colspan="6" style="text-align:center;color:#475569;">'
                'No funnel data yet — fill data/funnel.json weekly from GA4.</td></tr>')
    rows = ""
    for name, m in products.items():
        views = m.get("pageviews", 0) or 0
        mid = m.get("checkout_opens", m.get("email_signups", 0)) or 0
        trials = m.get("trials", 0) or 0
        paid = m.get("paid", 0) or 0
        conv = f"{paid / views * 100:.1f}%" if views else "—"
        rows += (
            f'<tr><td>{name}</td>'
            f'<td>{views:,}</td>'
            f'<td>{mid:,}</td>'
            f'<td>{trials:,}</td>'
            f'<td>{paid:,}</td>'
            f'<td>{conv}</td></tr>'
        )
    return rows


def scan_income_logs() -> dict:
    """
    DEPRECATED — do not use for revenue totals.

    Scans per-repo income_log.json files.  These may contain modeled
    est_commission values and test entries (e.g. success-test@example.com).
    Kept for informational/diagnostic purposes ONLY.  The dashboard no longer
    sums these into the displayed revenue figures.
    """
    all_income: dict = defaultdict(list)

    for repo, repo_dir in REPO_DIRS.items():
        log_file = repo_dir / "data" / "income_log.json"
        if log_file.exists():
            try:
                data = json.loads(log_file.read_text())
                if isinstance(data, list):
                    for entry in data:
                        all_income[repo].append(entry)
                elif isinstance(data, dict):
                    all_income[repo].append(data)
            except Exception:
                pass

    return {"by_repo": dict(all_income)}


def generate_dashboard() -> str:
    """Generate the master dashboard HTML."""
    # ---- REAL booked revenue (webhook-sourced, deduplicated) ----
    revenue = load_real_revenue()
    total_income = revenue["total"]   # <-- this is the ONLY number shown as revenue

    funnel = load_funnel()            # top-of-funnel metrics (Experiment 0)

    now = datetime.now()

    # Calculate progress against targets
    monthly_progress = min(total_income / TARGET_MONTHLY * 100, 100)
    daily_progress = min(total_income / 30 / TARGET_DAILY * 100, 100)
    
    # Product cards
    product_cards = ""
    for key, product in PRODUCTS.items():
        if "tiers" in product:
            price_range = f"${min(product['tiers'].values())} - ${max(product['tiers'].values())}/mo"
        else:
            price_range = product.get("description", "")
        target = product.get("target_monthly", 0) if "target_monthly" in product else 0
        if "target_customers" in product:
            target_revenue = sum(
                product["tiers"][t] * c for t, c in product["target_customers"].items()
            )
        elif "target_monthly_sales" in product:
            target_revenue = product["target_monthly_sales"] * product.get("commission_rate", 0.04)
        elif "target_daily_views" in product:
            target_revenue = product["target_daily_views"] * product.get("target_rpm", 3) / 1000 * 30
        else:
            target_revenue = target
        
        product_cards += f"""
        <div class="product-card">
            <h3>{product['name']}</h3>
            <p class="desc">{price_range}</p>
            <div class="target">目標: <strong>${target_revenue:,.0f}/月</strong></div>
            <a href="{product['url']}" class="repo-link" target="_blank">🔗 GitHub</a>
        </div>"""
    
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>hermes-pro — $500/day 收入儀表板</title>
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:-apple-system,sans-serif; background:#0a0a1a; color:#e2e8f0; }}
    .container {{ max-width:1000px; margin:auto; padding:20px; }}
    h1 {{ text-align:center; font-size:2.5rem; padding:40px 0 10px; }}
    .target-box {{ text-align:center; padding:30px; margin:20px 0; background:#1e293b; border-radius:20px; }}
    .target-box .big {{ font-size:4rem; font-weight:bold; }}
    .target-box .big.green {{ color:#22c55e; }}
    .target-box .big.red {{ color:#ef4444; }}
    .target-box .big.amber {{ color:#f59e0b; }}
    .progress-bar {{ background:#0f172a; border-radius:20px; height:30px; margin:20px 0; overflow:hidden; }}
    .progress-fill {{ height:100%; border-radius:20px; transition:width 1s; background:linear-gradient(90deg,#3b82f6,#a855f7); }}
    .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:15px; margin:20px 0; }}
    .stat-card {{ background:#1e293b; border-radius:16px; padding:20px; text-align:center; }}
    .stat-card .num {{ font-size:2rem; font-weight:bold; color:#3b82f6; }}
    .products {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:15px; margin:20px 0; }}
    .product-card {{ background:#1e293b; border-radius:16px; padding:20px; }}
    .product-card h3 {{ margin-bottom:5px; }}
    .product-card .desc {{ color:#94a3b8; font-size:0.9rem; }}
    .product-card .target {{ margin:10px 0; color:#f59e0b; }}
    .repo-link {{ color:#3b82f6; text-decoration:none; font-size:0.9rem; }}
    .income-table {{ width:100%; border-collapse:collapse; margin:20px 0; }}
    .income-table th,.income-table td {{ padding:10px; text-align:left; border-bottom:1px solid #1e293b; }}
    .income-table th {{ color:#94a3b8; }}
    .milestones {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; margin:20px 0; }}
    .milestone {{ background:#1e293b; border-radius:12px; padding:15px; text-align:center; }}
    .milestone.reached {{ border:2px solid #22c55e; }}
    .milestone .amt {{ font-weight:bold; color:#94a3b8; }}
    footer {{ text-align:center; padding:40px; color:#475569; }}
</style>
</head>
<body>
    <div class="container">
        <h1>💰 $500 / day</h1>
        <p style="text-align:center;color:#64748b;">hermes-pro — 多產品收入儀表板</p>
        
        <div class="target-box">
            <div class="big {'green' if daily_progress >= 100 else 'amber' if daily_progress >= 50 else 'red'}">
                ${total_income/30:.2f}
            </div>
            <p>每日收入 / $500 目標</p>
            <div class="progress-bar">
                <div class="progress-fill" style="width:{min(daily_progress,100)}%"></div>
            </div>
            <p style="color:#94a3b8;">{daily_progress:.1f}% 完成 — 還差 ${max(0, TARGET_DAILY - total_income/30):.2f}/天</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="num">${total_income:,.2f}</div>
                <p style="color:#94a3b8;font-size:0.9rem;">總收入</p>
            </div>
            <div class="stat-card">
                <div class="num">${total_income/30:.2f}</div>
                <p style="color:#94a3b8;font-size:0.9rem;">日均收入</p>
            </div>
            <div class="stat-card">
                <div class="num">${TARGET_MONTHLY - total_income:,.0f}</div>
                <p style="color:#94a3b8;font-size:0.9rem;">距月目標</p>
            </div>
            <div class="stat-card">
                <div class="num">{len(PRODUCTS)}</div>
                <p style="color:#94a3b8;font-size:0.9rem;">產品數</p>
            </div>
        </div>
        
        <h2>🚀 產品組合</h2>
        <div class="products">{product_cards}</div>
        
        <h2>🎯 里程碑</h2>
        <div class="milestones">
            {' '.join(f'<div class="milestone {"reached" if total_income/30 >= m else ""}"><div class="amt">${m}/天</div><div style="font-size:0.8rem;color:#475569;">' + ['起步','零用錢','基本收入','半職','全職','超標'][i] + '</div></div>' for i, m in enumerate([1, 10, 50, 100, 300, 500]))}
        </div>
        
        <h2>📋 Booked Revenue — Real Payments Only</h2>
        <p style="color:#64748b;font-size:0.85rem;margin:-10px 0 10px;">
          Source: data/revenue.json (Ko-fi + Gumroad webhooks). Est. commissions and modelled figures are excluded.
        </p>
        <table class="income-table">
            <tr><th>產品</th><th>筆數</th><th>實收金額</th><th>佔比</th></tr>
            {
                ' '.join(
                    f'<tr><td>{prod}</td>'
                    f'<td>{len(recs)}</td>'
                    f'<td>${sum(float(r.get("amount",0)) for r in recs):.2f}</td>'
                    f'<td>{sum(float(r.get("amount",0)) for r in recs)/total_income*100:.1f}%</td></tr>'
                    for prod, recs in revenue["by_product"].items()
                )
                if total_income > 0 else
                '<tr><td colspan="4" style="text-align:center;color:#475569;">$0.00 booked — no real payments yet. Configure webhooks per hermes-pay/PAYMENTS.md.</td></tr>'
            }
        </table>
        
        <h2>📈 Funnel — Pageview → Paid (Experiment 0)</h2>
        <p style="color:#64748b;font-size:0.85rem;margin:-10px 0 10px;">
          Week of {funnel.get('week_of', '—')} · source: GA4 (fill data/funnel.json weekly). Revenue tells you <em>if</em> money came in; this tells you <em>where</em> the funnel leaks.
        </p>
        <table class="income-table">
            <tr><th>產品</th><th>Pageviews</th><th>Checkout/Signup</th><th>Trials</th><th>Paid</th><th>View→Paid</th></tr>
            {render_funnel_rows(funnel)}
        </table>

        <footer>
            <p>hermes-pro · 最後更新: {now.strftime('%Y-%m-%d %H:%M')}</p>
            <p style="margin-top:10px;">
                <a href="https://github.com/slashman413/hermes-pro" style="color:#3b82f6;">GitHub</a>
            </p>
        </footer>
    </div>
</body>
</html>"""


if __name__ == "__main__":
    dashboard = generate_dashboard()
    docs_dir = BASE_DIR / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "index.html").write_text(dashboard, encoding="utf-8")

    # Use real revenue only — no modelled numbers
    revenue = load_real_revenue()
    booked = revenue["total"]
    txn_count = len(revenue["records"])

    print(f"Real booked revenue: ${booked:.2f}  ({txn_count} transactions)")
    print(f"Daily rate: ${booked/30:.2f}/day  target $500/day")
    print(f"Progress: {booked/30/TARGET_DAILY*100:.1f}%")
    if txn_count == 0:
        print("NOTE: No real payments yet. Set up webhooks per hermes-pay/PAYMENTS.md.")

    # Save snapshot — clearly labelled as booked (real) vs projected
    snapshot = {
        "date": datetime.now().isoformat(),
        # --- REAL booked revenue (webhook-sourced) ---
        "booked_total_usd": booked,
        "booked_daily_rate_usd": round(booked / 30, 2),
        "booked_txn_count": txn_count,
        "booked_progress_pct": round(booked / 30 / TARGET_DAILY * 100, 2),
        # --- Targets (projections only — NOT revenue) ---
        "target_daily_usd": TARGET_DAILY,
        "target_monthly_usd": TARGET_MONTHLY,
        # --- Meta ---
        "active_products": len(PRODUCTS),
        "revenue_source": str(REVENUE_FILE),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "snapshot.json").write_text(json.dumps(snapshot, indent=2))
