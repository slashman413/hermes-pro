#!/usr/bin/env python3
"""
hermes-pro — Central command center for all income streams.
Aggregates data from ALL repos to show:
- Real-time income
- Customer acquisition
- $500/day progress
- Multi-product dashboard
"""
import os, sys, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
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


def scan_income_logs() -> dict:
    """Scan all repos for income_log.json files."""
    all_income = defaultdict(list)
    total = 0.0
    
    for repo, repo_dir in REPO_DIRS.items():
        log_file = repo_dir / "data" / "income_log.json"
        if log_file.exists():
            try:
                data = json.loads(log_file.read_text())
                if isinstance(data, list):
                    for entry in data:
                        amt = entry.get("amount", entry.get("est_commission", 0))
                        total += amt
                        all_income[repo].append(entry)
                elif isinstance(data, dict):
                    amt = data.get("amount", data.get("est_commission", 0))
                    total += amt
                    all_income[repo].append(data)
            except Exception:
                pass
    
    return {"by_repo": dict(all_income), "total": round(total, 2)}


def generate_dashboard() -> str:
    """Generate the master dashboard HTML."""
    income_data = scan_income_logs()
    now = datetime.now()
    
    # Calculate progress
    total_income = income_data["total"]
    monthly_progress = min(total_income / TARGET_MONTHLY * 100, 100)
    daily_progress = min(total_income / 30 / TARGET_DAILY * 100, 100)
    
    # Product cards
    product_cards = ""
    for key, product in PRODUCTS.items():
        price_range = f"${min(product['tiers'].values())} - ${max(product['tiers'].values())}/mo"
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
            <p class="desc">{product.get('description', price_range)}</p>
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
        
        <h2>📋 收入來源</h2>
        <table class="income-table">
            <tr><th>來源</th><th>收入</th><th>佔比</th></tr>
            {' '.join(f'<tr><td>{repo}</td><td>${sum(e.get("amount", e.get("est_commission", 0)) for e in entries):.2f}</td><td>{sum(e.get("amount", e.get("est_commission", 0)) for e in entries)/total_income*100:.1f}%</td></tr>' for repo, entries in income_data['by_repo'].items()) if total_income > 0 else '<tr><td colspan="3" style="text-align:center;color:#475569;">還沒有收入記錄 — 第一個產品已上線！</td></tr>'}
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
    
    income = scan_income_logs()
    print(f"💰 總收入: ${income['total']:.2f}")
    print(f"📊 活躍來源: {len(income['by_repo'])}")
    print(f"🎯 進度: ${income['total']/30:.2f}/天 → $500/天目標")
    
    # Save income snapshot
    snapshot = {
        "date": datetime.now().isoformat(),
        "total_income": income["total"],
        "daily_rate": round(income["total"] / 30, 2),
        "progress_pct": round(income["total"] / 30 / TARGET_DAILY * 100, 2),
        "active_products": len(PRODUCTS),
        "sources": list(income["by_repo"].keys()),
    }
    (DATA_DIR / "snapshot.json").write_text(json.dumps(snapshot, indent=2))
