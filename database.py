import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "engine.db"


def get_conn() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    # 1. Affiliate & System Settings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        label TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL
    )
    """)

    # 2. Vertical 1: Power Stations & Solar Gear (WattWise)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS power_stations (
        slug TEXT PRIMARY KEY,
        brand TEXT NOT NULL,
        name TEXT NOT NULL,
        capacity_wh INTEGER NOT NULL,
        continuous_w INTEGER NOT NULL,
        surge_w INTEGER NOT NULL,
        solar_input_w INTEGER NOT NULL,
        chemistry TEXT NOT NULL,
        cycle_life INTEGER NOT NULL,
        weight_lbs REAL NOT NULL,
        ups_ms INTEGER NOT NULL,
        msrp_usd REAL NOT NULL,
        live_price_usd REAL NOT NULL,
        affiliate_network TEXT NOT NULL,
        base_url TEXT NOT NULL,
        commission_rate_pct REAL NOT NULL,
        last_updated TEXT NOT NULL
    )
    """)

    # 3. Vertical 1: Appliances for Compatibility & Sizing Calculator
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appliances (
        slug TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        running_watts INTEGER NOT NULL,
        surge_watts INTEGER NOT NULL,
        duty_cycle_pct REAL NOT NULL,
        default_hours REAL NOT NULL,
        icon TEXT NOT NULL
    )
    """)

    # 4. Vertical 2: E-Commerce Platforms & Tools (SellerPulse)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ecom_platforms (
        slug TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        monthly_fee_usd REAL NOT NULL,
        transaction_fee_pct REAL NOT NULL,
        processing_fee_pct REAL NOT NULL,
        processing_fixed_usd REAL NOT NULL,
        avg_affiliate_bounty_usd REAL NOT NULL,
        recurring_commission_pct REAL NOT NULL,
        affiliate_network TEXT NOT NULL,
        base_url TEXT NOT NULL,
        best_for TEXT NOT NULL,
        pros_json TEXT NOT NULL
    )
    """)

    # 5. Vertical 3: AI APIs & Cloud GPUs (TokenIndex)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_providers (
        slug TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        name TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        input_cost_per_m REAL NOT NULL,
        output_cost_per_m REAL NOT NULL,
        hourly_gpu_cost REAL NOT NULL,
        vram_gb INTEGER NOT NULL,
        context_window INTEGER NOT NULL,
        speed_tok_sec INTEGER NOT NULL,
        affiliate_commission_pct REAL NOT NULL,
        avg_bounty_usd REAL NOT NULL,
        base_url TEXT NOT NULL,
        last_updated TEXT NOT NULL
    )
    """)

    # 6. Click & Revenue Attribution Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS click_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        vertical TEXT NOT NULL,
        item_slug TEXT NOT NULL,
        item_name TEXT NOT NULL,
        destination_url TEXT NOT NULL,
        est_epc_usd REAL NOT NULL,
        source_page TEXT NOT NULL
    )
    """)

    # 7. Pro Price Alerts & SaaS Leads
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pro_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        email TEXT NOT NULL,
        vertical TEXT NOT NULL,
        alert_rule TEXT NOT NULL,
        tier TEXT NOT NULL
    )
    """)

    # 8. Automation Job Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS automation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ran_at TEXT NOT NULL,
        job_name TEXT NOT NULL,
        items_updated INTEGER NOT NULL,
        status TEXT NOT NULL,
        details TEXT NOT NULL
    )
    """)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Seed default settings if empty
    cur.execute("SELECT COUNT(*) FROM settings")
    if cur.fetchone()[0] == 0:
        default_settings = [
            ("amazon_associate_tag", "tricore0a-20", "Amazon Associates Tag", "Affiliate IDs", "Appended as ?tag= to Amazon hardware links (4-8% commission)"),
            ("impact_partner_id", "wattwise-impact", "Impact / CJ Partner ID", "Affiliate IDs", "Used for direct EcoFlow, Anker, and Jackery links (6-10% commission)"),
            ("shopify_affiliate_id", "sellerpulse-partner", "Shopify Partner Ref ID", "Affiliate IDs", "Used for Shopify trial referrals ($50-$150 bounty per store)"),
            ("spocket_affiliate_id", "sellerpulse-spocket", "Spocket / Printful Ref ID", "Affiliate IDs", "20-30% recurring affiliate commission on e-commerce supplier tools"),
            ("cloud_gpu_affiliate_id", "sk1me166", "RunPod / Vast.ai / ElevenLabs Ref", "Affiliate IDs", "10-25% recurring commission on GPU compute and AI API credits"),
            ("stripe_pro_checkout_url", "https://buy.stripe.com/test_3cIcN59OKdQa1WbfxSbV600", "Stripe Pro Checkout URL ($15/mo)", "SaaS Monetization", "Payment link for Pro Watchdog Alerts, BOM PDF Exports & Unlimited AI Store Spy"),
            ("pro_monthly_price_usd", "15", "Pro SaaS Monthly Price ($)", "SaaS Monetization", "Displayed price for the Pro subscription upgrade across all 3 verticals"),
            ("redirect_preview_mode", "false", "Affiliate Link Preview Mode", "System", "When 'true', clicking affiliate links opens an attribution verifier with a 1-click jump to the live merchant URL"),
            ("gemini_api_key", "", "Gemini API Key (Optional)", "System", "Used by SellerPulse AI Store Spy & Listing Generator (falls back to built-in deterministic copy engine if blank)")
        ]
        cur.executemany("INSERT INTO settings VALUES (?, ?, ?, ?, ?)", default_settings)

    # Seed Power Stations if empty
    cur.execute("SELECT COUNT(*) FROM power_stations")
    if cur.fetchone()[0] == 0:
        stations = [
            ("ecoflow-delta-2-max", "EcoFlow", "EcoFlow DELTA 2 Max", 2048, 2400, 4800, 1000, "LiFePO4", 3000, 50.7, 20, 1899.0, 1399.0, "Impact / Direct", "https://us.ecoflow.com/products/delta-2-max-portable-power-station", 8.0, now),
            ("bluetti-ac200l", "Bluetti", "Bluetti AC200L", 2048, 2400, 3600, 1200, "LiFePO4", 3000, 62.4, 20, 1999.0, 1299.0, "ShareASale / Amazon", "https://www.bluettipower.com/products/ac200l", 8.0, now),
            ("anker-solix-c1000", "Anker", "Anker SOLIX C1000", 1056, 1800, 2400, 600, "LiFePO4", 3000, 28.4, 20, 999.0, 649.0, "Impact / Amazon", "https://www.anker.com/anker-solix/c1000", 7.0, now),
            ("ecoflow-delta-pro-3", "EcoFlow", "EcoFlow DELTA Pro 3", 4096, 4000, 8000, 2600, "LiFePO4", 4000, 113.5, 10, 3699.0, 3199.0, "Impact / Direct", "https://us.ecoflow.com/products/delta-pro-3-portable-power-station", 8.0, now),
            ("anker-solix-f3800", "Anker", "Anker SOLIX F3800", 3840, 6000, 9000, 2400, "LiFePO4", 3000, 132.3, 20, 3999.0, 2999.0, "Impact / Direct", "https://www.anker.com/anker-solix/f3800", 7.5, now),
            ("jackery-explorer-2000-plus", "Jackery", "Jackery Explorer 2000 Plus", 2042, 3000, 6000, 1400, "LiFePO4", 4000, 61.5, 20, 2199.0, 1599.0, "CJ / Amazon", "https://www.jackery.com/products/explorer-2000-plus-portable-power-station", 7.0, now),
            ("bluetti-elite-200-v2", "Bluetti", "Bluetti Elite 200 V2", 2073, 2600, 3900, 1000, "LiFePO4", 6000, 53.4, 15, 1999.0, 1199.0, "ShareASale / Direct", "https://www.bluettipower.com/products/elite-200-v2", 8.5, now),
            ("jackery-explorer-1000-v2", "Jackery", "Jackery Explorer 1000 v2", 1070, 1500, 3000, 400, "LiFePO4", 4000, 23.8, 20, 799.0, 549.0, "CJ / Amazon", "https://www.jackery.com/products/explorer-1000-v2", 7.0, now),
        ]
        cur.executemany("INSERT INTO power_stations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", stations)

    # Seed Appliances if empty
    cur.execute("SELECT COUNT(*) FROM appliances")
    if cur.fetchone()[0] == 0:
        appliances = [
            ("full-size-refrigerator", "Full-Size Refrigerator", "Kitchen & Food", 150, 1200, 0.35, 24.0, "🧊"),
            ("cpap-machine", "CPAP Machine (Heated Humidifier)", "Medical & Sleep", 65, 90, 1.0, 8.0, "🫁"),
            ("starlink-dish", "Starlink Standard Dish + Router", "Internet & Work", 60, 110, 1.0, 12.0, "🛰️"),
            ("chest-freezer", "Deep Chest Freezer", "Kitchen & Food", 100, 800, 0.30, 24.0, "❄️"),
            ("sump-pump-half-hp", "Basement Sump Pump (1/2 HP)", "Home Emergency", 800, 2100, 0.15, 6.0, "🌊"),
            ("window-ac-5000-btu", "Window Air Conditioner (5,000 BTU)", "Climate Control", 500, 1400, 0.65, 8.0, "🌬️"),
            ("rv-air-conditioner", "RV Rooftop Air Conditioner (13,500 BTU)", "RV & Vanlife", 1350, 3200, 0.70, 6.0, "🚐"),
            ("espresso-machine", "Dual-Boiler Espresso Machine", "Kitchen & Food", 1400, 1600, 1.0, 0.5, "☕"),
            ("microwave-oven", "Countertop Microwave (1000W)", "Kitchen & Food", 1200, 1800, 1.0, 0.5, "🍲"),
            ("portable-space-heater", "Electric Space Heater (Low/High)", "Climate Control", 1500, 1500, 0.80, 4.0, "🔥"),
            ("laptop-workstation", "MacBook Pro + External Monitor", "Internet & Work", 85, 120, 1.0, 8.0, "💻"),
            ("oxygen-concentrator", "Home Medical Oxygen Concentrator", "Medical & Sleep", 350, 500, 1.0, 12.0, "🏥"),
        ]
        cur.executemany("INSERT INTO appliances VALUES (?, ?, ?, ?, ?, ?, ?, ?)", appliances)

    # Seed E-Commerce Platforms if empty
    cur.execute("SELECT COUNT(*) FROM ecom_platforms")
    if cur.fetchone()[0] == 0:
        platforms = [
            ("shopify-basic", "Shopify (Basic Plan)", "Storefront Platform", 39.0, 0.0, 2.9, 0.30, 150.0, 0.0, "Shopify Partners", "https://www.shopify.com/free-trial", "Best for branded niche stores & automated dropshipping", json.dumps(["Zero platform referral fee when using Shopify Payments", "1-click integration with CJ, Spocket & Printful", "$150 partner referral bounty"])),
            ("tiktok-shop", "TikTok Shop Seller", "Social Marketplace", 0.0, 6.0, 0.0, 0.0, 75.0, 0.0, "TikTok Partner", "https://seller-us.tiktok.com/", "Best for viral short-form video products & impulse buys", json.dumps(["Built-in organic traffic from Reels/TikTok creator affiliates", "6% flat referral fee (includes payment processing)", "Strict 2-day dispatch SLA required"])),
            ("etsy-marketplace", "Etsy Marketplace", "Handmade & POD Marketplace", 0.0, 6.5, 3.0, 0.45, 45.0, 0.0, "Awin / Printful", "https://www.etsy.com/sell", "Best for Print-on-Demand (Printful/Printify) & custom digital products", json.dumps(["Built-in buyer search traffic", "$0.20 listing fee + 6.5% transaction fee", "Pairs seamlessly with automated Printful fulfillment"])),
            ("amazon-fba", "Amazon FBA (Professional)", "Global Marketplace", 39.99, 15.0, 0.0, 0.0, 85.0, 0.0, "JungleScout / Helium10", "https://sell.amazon.com/", "Best for private-label hardware & high-velocity Prime search demand", json.dumps(["Highest buyer conversion rate on the internet", "15% referral fee + FBA pick & pack fees", "Hands-off Prime shipping fulfillment"])),
            ("spocket-pro", "Spocket US/EU Suppliers", "Supplier Automation", 39.99, 0.0, 0.0, 0.0, 0.0, 30.0, "PartnerStack", "https://www.spocket.co/", "Fast 2-5 day US/EU dropshipping suppliers with automated Shopify sync", json.dumps(["Eliminates 3-week overseas shipping delays", "Branded invoicing included", "Pays 30% recurring affiliate commission up to $1,080/yr per user"])),
            ("printful-pod", "Printful Automated POD", "On-Demand Fulfillment", 0.0, 0.0, 0.0, 0.0, 0.0, 10.0, "Printful Affiliates", "https://www.printful.com/", "Zero-inventory automated apparel & merch fulfillment", json.dumps(["$0 monthly base fee", "Automatic order routing for Shopify, Etsy & TikTok Shop", "10% revenue share on every referred seller order"])),
        ]
        cur.executemany("INSERT INTO ecom_platforms VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", platforms)

    # Seed AI APIs & Cloud GPUs if empty
    cur.execute("SELECT COUNT(*) FROM ai_providers")
    if cur.fetchone()[0] == 0:
        ai_rows = [
            ("gemini-2-5-flash", "Google Cloud / Vertex", "Gemini 2.5 Flash", "LLM API", 0.15, 0.60, 0.0, 0, 1000000, 195, 15.0, 45.0, "https://ai.google.dev/pricing", now),
            ("deepseek-v3-together", "Together AI / Fireworks", "DeepSeek V3 (Hosted)", "LLM API", 0.27, 1.10, 0.0, 0, 128000, 110, 20.0, 60.0, "https://www.together.ai/pricing", now),
            ("claude-3-7-sonnet", "Anthropic / AWS Bedrock", "Claude 3.7 Sonnet", "LLM API", 3.00, 15.00, 0.0, 0, 200000, 82, 10.0, 50.0, "https://www.anthropic.com/pricing", now),
            ("gpt-4o-standard", "OpenAI / Azure", "GPT-4o Standard", "LLM API", 2.50, 10.00, 0.0, 0, 128000, 95, 10.0, 40.0, "https://openai.com/api/pricing/", now),
            ("llama-3-3-70b-groq", "Groq Cloud LPU", "Llama 3.3 70B SpecDec", "LLM API", 0.59, 0.79, 0.0, 0, 128000, 310, 15.0, 35.0, "https://groq.com/pricing/", now),
            ("runpod-h100-sxm", "RunPod Cloud GPUs", "NVIDIA H100 80GB SXM", "Cloud GPU", 0.0, 0.0, 2.69, 80, 0, 0, 15.0, 120.0, "https://www.runpod.io/gpu-instance/pricing", now),
            ("vastai-rtx-4090", "Vast.ai GPU Market", "NVIDIA RTX 4090 24GB", "Cloud GPU", 0.0, 0.0, 0.39, 24, 0, 0, 20.0, 85.0, "https://vast.ai/pricing", now),
            ("lambda-a100-80gb", "Lambda Labs Cloud", "NVIDIA A100 80GB PCIe", "Cloud GPU", 0.0, 0.0, 1.29, 80, 0, 0, 10.0, 95.0, "https://lambdalabs.com/service/gpu-cloud#pricing", now),
        ]
        cur.executemany("INSERT INTO ai_providers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ai_rows)

    conn.commit()
    conn.close()


def get_settings_dict() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def build_affiliate_url(vertical: str, item_slug: str, base_url: str) -> str:
    cfg = get_settings_dict()
    sep = "&" if "?" in base_url else "?"
    if vertical == "wattwise":
        impact_id = cfg.get("impact_partner_id", "").strip()
        amz = cfg.get("amazon_associate_tag", "yourtag-20").strip()
        # If Impact isn't active yet, automatically route all Power Station links to Amazon Associates!
        if not impact_id or impact_id == "wattwise-impact":
            query = item_slug.replace("-", "+")
            return f"https://www.amazon.com/s?k={query}+portable+power+station&tag={amz}&linkCode=ll2"
        return f"{base_url}{sep}ref={impact_id}&tag={amz}&utm_source=wattwise_calc&utm_medium=affiliate"
    elif vertical == "sellerpulse":
        ref = cfg.get("shopify_affiliate_id", "sellerpulse-partner").strip()
        if "spocket" in item_slug or "printful" in item_slug:
            ref = cfg.get("spocket_affiliate_id", "sellerpulse-spocket").strip()
        if ref.startswith("http://") or ref.startswith("https://"):
            return ref
        return f"{base_url}{sep}ref={ref}&utm_source=sellerpulse_calc&utm_medium=affiliate"
    else:
        ref = cfg.get("cloud_gpu_affiliate_id", "tokenindex-gpu").strip()
        if ref.startswith("http://") or ref.startswith("https://"):
            return ref
        return f"{base_url}{sep}ref={ref}&utm_source=tokenindex_calc&utm_medium=affiliate"
