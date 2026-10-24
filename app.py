import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database import init_db, get_conn, get_settings_dict, build_affiliate_url
from automation import run_price_sync_job, spy_and_generate_listing
from seo_engine import (
    list_all_programmatic_pages,
    build_compatibility_seo_data,
    build_versus_seo_data,
)

app = FastAPI(title="TriCore Hybrid Income Engine — Affiliate + Programmatic SEO + Micro-SaaS")
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def on_startup():
    init_db()


class SpyRequest(BaseModel):
    url_or_product: str
    supplier_cost: float = 18.50


class SettingsUpdateRequest(BaseModel):
    updates: dict[str, str]


class LeadRequest(BaseModel):
    email: str
    vertical: str
    alert_rule: str
    tier: str = "Pro Watchdog ($19/mo)"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    init_db()
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/api/bootstrap")
async def api_bootstrap():
    conn = get_conn()
    stations = [dict(r) for r in conn.execute("SELECT * FROM power_stations ORDER BY (live_price_usd / capacity_wh) ASC").fetchall()]
    for s in stations:
        s["dollar_per_wh"] = round(s["live_price_usd"] / s["capacity_wh"], 2)
        s["est_commission_usd"] = round(s["live_price_usd"] * (s["commission_rate_pct"] / 100.0), 2)
        s["savings_usd"] = round(s["msrp_usd"] - s["live_price_usd"], 0)

    appliances = [dict(r) for r in conn.execute("SELECT * FROM appliances ORDER BY category, name").fetchall()]
    platforms = [dict(r) for r in conn.execute("SELECT * FROM ecom_platforms").fetchall()]
    for p in platforms:
        p["pros"] = json.loads(p["pros_json"])

    ai_providers = [dict(r) for r in conn.execute("SELECT * FROM ai_providers").fetchall()]
    settings_rows = [dict(r) for r in conn.execute("SELECT * FROM settings").fetchall()]
    clicks = [dict(r) for r in conn.execute("SELECT * FROM click_logs ORDER BY id DESC LIMIT 25").fetchall()]
    click_totals = conn.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(est_epc_usd), 0) as total_epc FROM click_logs").fetchone()
    leads = [dict(r) for r in conn.execute("SELECT * FROM pro_leads ORDER BY id DESC LIMIT 20").fetchall()]
    auto_logs = [dict(r) for r in conn.execute("SELECT * FROM automation_logs ORDER BY id DESC LIMIT 10").fetchall()]
    conn.close()

    seo_index = list_all_programmatic_pages()

    return {
        "stations": stations,
        "appliances": appliances,
        "platforms": platforms,
        "ai_providers": ai_providers,
        "settings": settings_rows,
        "clicks": clicks,
        "stats": {
            "total_clicks": click_totals["cnt"],
            "est_pipeline_epc_usd": round(click_totals["total_epc"], 2),
            "total_pro_leads": len(leads),
            "total_seo_pages": seo_index["total_pages"],
        },
        "leads": leads,
        "automation_logs": auto_logs,
        "seo_index": seo_index,
    }


@app.post("/api/sellerpulse/spy")
async def api_sellerpulse_spy(payload: SpyRequest):
    result = await spy_and_generate_listing(payload.url_or_product, payload.supplier_cost)
    return result


@app.post("/api/automation/sync")
async def api_automation_sync():
    res = await run_price_sync_job()
    return res


@app.post("/api/settings")
async def api_update_settings(payload: SettingsUpdateRequest):
    conn = get_conn()
    cur = conn.cursor()
    for k, v in payload.updates.items():
        cur.execute("UPDATE settings SET value = ? WHERE key = ?", (str(v).strip(), k))
    conn.commit()
    conn.close()
    return {"status": "ok", "updated": len(payload.updates)}


@app.post("/api/leads")
async def api_create_lead(payload: LeadRequest):
    conn = get_conn()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    conn.execute(
        "INSERT INTO pro_leads (created_at, email, vertical, alert_rule, tier) VALUES (?, ?, ?, ?, ?)",
        (now, payload.email.strip(), payload.vertical, payload.alert_rule, payload.tier),
    )
    conn.commit()
    conn.close()
    cfg = get_settings_dict()
    return {
        "status": "ok",
        "stripe_checkout_url": cfg.get("stripe_pro_checkout_url", "https://buy.stripe.com/test_pro_tier"),
        "pro_price": cfg.get("pro_monthly_price_usd", "19"),
    }


@app.get("/go/{vertical}/{slug}")
async def affiliate_redirect(vertical: str, slug: str, request: Request, source: str = "calculator"):
    conn = get_conn()
    item_name = slug
    base_url = "https://example.com"
    est_epc = 1.85
    est_commission_full = 45.0

    if vertical == "wattwise":
        row = conn.execute("SELECT * FROM power_stations WHERE slug = ?", (slug,)).fetchone()
        if row:
            item_name = row["name"]
            base_url = row["base_url"]
            est_commission_full = round(row["live_price_usd"] * (row["commission_rate_pct"] / 100.0), 2)
            # Assume 3.5% affiliate click-to-sale conversion for high-intent calculator clicks
            est_epc = round(est_commission_full * 0.035, 2)
    elif vertical == "sellerpulse":
        row = conn.execute("SELECT * FROM ecom_platforms WHERE slug = ?", (slug,)).fetchone()
        if row:
            item_name = row["name"]
            base_url = row["base_url"]
            est_commission_full = row["avg_affiliate_bounty_usd"] or 95.0
            est_epc = round(est_commission_full * 0.04, 2)
    elif vertical == "tokenindex":
        row = conn.execute("SELECT * FROM ai_providers WHERE slug = ?", (slug,)).fetchone()
        if row:
            item_name = row["name"]
            base_url = row["base_url"]
            est_commission_full = row["avg_bounty_usd"] or 60.0
            est_epc = round(est_commission_full * 0.04, 2)

    dest_url = build_affiliate_url(vertical, slug, base_url)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    conn.execute(
        "INSERT INTO click_logs (created_at, vertical, item_slug, item_name, destination_url, est_epc_usd, source_page) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (now, vertical, slug, item_name, dest_url, est_epc, source),
    )
    conn.commit()
    conn.close()

    cfg = get_settings_dict()
    if cfg.get("redirect_preview_mode", "true").lower() == "true":
        html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="utf-8">
  <title>Affiliate Attribution Logged — {item_name}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex items-center justify-center p-6">
  <div class="max-w-xl w-full bg-slate-900 border border-emerald-500/40 rounded-2xl p-8 shadow-2xl">
    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold mb-4">
      ✅ AFFILIATE CLICK LOGGED IN COMMAND CENTER
    </div>
    <h1 class="text-2xl font-bold text-white mb-2">{item_name}</h1>
    <p class="text-slate-400 text-sm mb-6">
      Affiliate Preview Mode is active so you can verify your tracking tags before sending live traffic.
      (You can toggle this off anytime in the <strong>Unified Command Center</strong> for instant 302 redirects.)
    </p>
    <div class="space-y-3 bg-slate-950/90 border border-slate-800 rounded-xl p-4 text-xs font-mono mb-6">
      <div><span class="text-slate-500">Vertical:</span> <span class="text-indigo-400 uppercase">{vertical}</span></div>
      <div><span class="text-slate-500">Source Page:</span> <span class="text-slate-300">{source}</span></div>
      <div><span class="text-slate-500">Est. Full Conversion Payout:</span> <span class="text-emerald-400 font-bold">${est_commission_full:.2f}</span></div>
      <div><span class="text-slate-500">Logged Click EPC Value:</span> <span class="text-emerald-300">${est_epc:.2f}</span></div>
      <div class="break-all"><span class="text-slate-500">Tagged Destination URL:</span><br><span class="text-amber-300">{dest_url}</span></div>
    </div>
    <div class="flex flex-wrap gap-3">
      <a href="{dest_url}" target="_blank" rel="noopener" class="flex-1 text-center bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold py-3 px-5 rounded-xl transition">
        Continue to Merchant Website ↗
      </a>
      <a href="/" class="py-3 px-5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition">
        ← Back to Engine
      </a>
    </div>
  </div>
</body>
</html>"""
        return HTMLResponse(content=html)

    return RedirectResponse(url=dest_url, status_code=302)


@app.get("/seo/can-{station_slug}-run-{appliance_slug}", response_class=HTMLResponse)
async def seo_compatibility_page(station_slug: str, appliance_slug: str, request: Request):
    data = build_compatibility_seo_data(station_slug, appliance_slug)
    if not data:
        raise HTTPException(status_code=404, detail="Programmatic SEO Page Not Found")
    return templates.TemplateResponse(request=request, name="seo_page.html", context={"seo": data})


@app.get("/seo/vs/{vertical}/{slug_pair}", response_class=HTMLResponse)
async def seo_versus_page(vertical: str, slug_pair: str, request: Request):
    data = build_versus_seo_data(vertical, slug_pair)
    if not data:
        raise HTTPException(status_code=404, detail="Programmatic Versus Page Not Found")
    return templates.TemplateResponse(request=request, name="seo_page.html", context={"seo": data})


@app.get("/google2883eb2e672d8d5d.html")
async def google_site_verification():
    # Google Search Console ownership verification file
    return Response(
        content="google-site-verification: google2883eb2e672d8d5d.html",
        media_type="text/html",
    )


@app.get("/sitemap.xml")
async def sitemap_xml(request: Request):
    base = str(request.base_url).rstrip("/")
    idx = list_all_programmatic_pages()
    urls = [f"{base}/"]
    for group in ["compatibility_pages", "wattwise_vs", "sellerpulse_vs", "tokenindex_vs"]:
        for item in idx[group]:
            urls.append(f"{base}{item['url']}")

    xml_items = "\n".join(
        f"  <url><loc>{u}</loc><changefreq>daily</changefreq><priority>0.8</priority></url>"
        for u in urls
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_items}
</urlset>"""
    return Response(content=xml, media_type="application/xml")
