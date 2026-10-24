import json
from itertools import combinations
from database import get_conn


def list_all_programmatic_pages() -> dict:
    """
    Generates the index of all programmatic SEO pages across all 3 verticals.
    """
    conn = get_conn()
    stations = [dict(r) for r in conn.execute("SELECT * FROM power_stations ORDER BY live_price_usd ASC").fetchall()]
    appliances = [dict(r) for r in conn.execute("SELECT * FROM appliances ORDER BY name ASC").fetchall()]
    platforms = [dict(r) for r in conn.execute("SELECT * FROM ecom_platforms").fetchall()]
    ai_providers = [dict(r) for r in conn.execute("SELECT * FROM ai_providers").fetchall()]
    conn.close()

    compatibility_pages = []
    for st in stations:
        for ap in appliances:
            usable_wh = st["capacity_wh"] * 0.85
            effective_watts = ap["running_watts"] * ap["duty_cycle_pct"]
            runtime_hrs = round(usable_wh / max(effective_watts, 1), 1)
            compatible = st["continuous_w"] >= ap["running_watts"] and st["surge_w"] >= ap["surge_watts"]
            compatibility_pages.append({
                "url": f"/seo/can-{st['slug']}-run-{ap['slug']}",
                "title": f"Can {st['name']} Run a {ap['name']}? ({runtime_hrs}h Runtime Math)",
                "vertical": "wattwise",
                "badge": "Compatible ✅" if compatible else "Overload ⚠️",
                "subtitle": f"{st['capacity_wh']}Wh LiFePO4 vs {ap['running_watts']}W continuous / {ap['surge_watts']}W surge",
            })

    wattwise_vs = []
    for a, b in combinations(stations, 2):
        d_wh_a = round(a["live_price_usd"] / a["capacity_wh"], 2)
        d_wh_b = round(b["live_price_usd"] / b["capacity_wh"], 2)
        wattwise_vs.append({
            "url": f"/seo/vs/wattwise/{a['slug']}-vs-{b['slug']}",
            "title": f"{a['name']} vs {b['name']}: $/Wh & Spec Comparison",
            "vertical": "wattwise",
            "badge": f"${d_wh_a}/Wh vs ${d_wh_b}/Wh",
            "subtitle": f"{a['capacity_wh']}Wh (${int(a['live_price_usd'])}) vs {b['capacity_wh']}Wh (${int(b['live_price_usd'])})",
        })

    sellerpulse_vs = []
    for a, b in combinations(platforms, 2):
        sellerpulse_vs.append({
            "url": f"/seo/vs/sellerpulse/{a['slug']}-vs-{b['slug']}",
            "title": f"{a['name']} vs {b['name']}: Fees, Margins & Affiliate Payouts",
            "vertical": "sellerpulse",
            "badge": f"{a['transaction_fee_pct']}% vs {b['transaction_fee_pct']}% Fee",
            "subtitle": f"Compare take-home profit margins on $10k/mo sales volume",
        })

    tokenindex_vs = []
    for a, b in combinations(ai_providers, 2):
        if a["resource_type"] == b["resource_type"]:
            tokenindex_vs.append({
                "url": f"/seo/vs/tokenindex/{a['slug']}-vs-{b['slug']}",
                "title": f"{a['name']} vs {b['name']}: Live Cost & Speed Benchmark",
                "vertical": "tokenindex",
                "badge": a["resource_type"],
                "subtitle": f"{a['provider']} vs {b['provider']} unit economics breakdown",
            })

    total_count = len(compatibility_pages) + len(wattwise_vs) + len(sellerpulse_vs) + len(tokenindex_vs)
    return {
        "total_pages": total_count,
        "compatibility_pages": compatibility_pages,
        "wattwise_vs": wattwise_vs,
        "sellerpulse_vs": sellerpulse_vs,
        "tokenindex_vs": tokenindex_vs,
    }


def build_compatibility_seo_data(station_slug: str, appliance_slug: str) -> dict | None:
    conn = get_conn()
    st = conn.execute("SELECT * FROM power_stations WHERE slug = ?", (station_slug,)).fetchone()
    ap = conn.execute("SELECT * FROM appliances WHERE slug = ?", (appliance_slug,)).fetchone()
    all_stations = [dict(r) for r in conn.execute("SELECT * FROM power_stations ORDER BY live_price_usd ASC").fetchall()]
    conn.close()

    if not st or not ap:
        return None

    st = dict(st)
    ap = dict(ap)

    usable_wh = round(st["capacity_wh"] * 0.85)
    effective_watts = round(ap["running_watts"] * ap["duty_cycle_pct"], 1)
    runtime_hours = round(usable_wh / max(effective_watts, 1), 1)
    daily_wh_needed = round(effective_watts * ap["default_hours"])
    solar_panels_needed_w = round((daily_wh_needed / 4.5) * 1.25)
    can_run = st["continuous_w"] >= ap["running_watts"] and st["surge_w"] >= ap["surge_watts"]
    dollar_per_wh = round(st["live_price_usd"] / st["capacity_wh"], 2)
    est_commission = round(st["live_price_usd"] * (st["commission_rate_pct"] / 100.0), 2)

    faqs = [
        {
            "q": f"Can the {st['name']} run a {ap['name']}?",
            "a": (
                f"{'Yes!' if can_run else 'No — the appliance exceeds the inverter rating.'} "
                f"The {st['name']} supplies {st['continuous_w']}W continuous ({st['surge_w']}W surge), while a typical {ap['name']} draws {ap['running_watts']}W running ({ap['surge_watts']}W starting surge)."
            )
        },
        {
            "q": f"How long will a {st['name']} power a {ap['name']}?",
            "a": f"With {st['capacity_wh']}Wh capacity ({usable_wh}Wh usable after 85% inverter efficiency) and a {int(ap['duty_cycle_pct']*100)}% compressor/duty cycle ({effective_watts}W average draw), the {st['name']} will run a {ap['name']} for approximately {runtime_hours} hours on a single charge."
        },
        {
            "q": f"How many solar panels do I need to run a {ap['name']} off-grid with the {st['name']}?",
            "a": f"To replenish {daily_wh_needed}Wh per day ({ap['default_hours']} hrs/day) assuming 4.5 peak sun hours, we recommend at least {max(solar_panels_needed_w, 200)}W of solar panels (the {st['name']} accepts up to {st['solar_input_w']}W solar input)."
        }
    ]

    schema_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["q"],
                "acceptedAnswer": {"@type": "Answer", "text": f["a"]}
            }
            for f in faqs
        ]
    }, indent=2)

    return {
        "page_type": "compatibility",
        "vertical": "wattwise",
        "title": f"Can {st['name']} Run a {ap['name']}? ({runtime_hours} Hours Tested Math)",
        "meta_description": f"Exact runtime calculator: See how long the {st['name']} ({st['capacity_wh']}Wh) runs a {ap['name']} ({ap['running_watts']}W), surge compatibility, and solar panel sizing.",
        "station": st,
        "appliance": ap,
        "usable_wh": usable_wh,
        "effective_watts": effective_watts,
        "runtime_hours": runtime_hours,
        "daily_wh_needed": daily_wh_needed,
        "solar_panels_needed_w": max(solar_panels_needed_w, 200),
        "can_run": can_run,
        "dollar_per_wh": dollar_per_wh,
        "est_commission": est_commission,
        "faqs": faqs,
        "schema_json": schema_json,
        "alternatives": [s for s in all_stations if s["slug"] != st["slug"]][:3],
    }


def build_versus_seo_data(vertical: str, slug_pair: str) -> dict | None:
    if "-vs-" not in slug_pair:
        return None
    slug_a, slug_b = slug_pair.split("-vs-", 1)
    conn = get_conn()

    if vertical == "wattwise":
        a = conn.execute("SELECT * FROM power_stations WHERE slug = ?", (slug_a,)).fetchone()
        b = conn.execute("SELECT * FROM power_stations WHERE slug = ?", (slug_b,)).fetchone()
        conn.close()
        if not a or not b:
            return None
        a, b = dict(a), dict(b)
        a["d_wh"] = round(a["live_price_usd"] / a["capacity_wh"], 2)
        b["d_wh"] = round(b["live_price_usd"] / b["capacity_wh"], 2)
        winner = a if a["d_wh"] <= b["d_wh"] else b
        return {
            "page_type": "versus",
            "vertical": "wattwise",
            "title": f"{a['name']} vs {b['name']}: $/Wh Value, Inverter & Solar Comparison",
            "meta_description": f"Side-by-side spec comparison of {a['name']} (${a['d_wh']}/Wh) vs {b['name']} (${b['d_wh']}/Wh). Compare LiFePO4 cycle life, solar charging speed, and surge watts.",
            "item_a": a,
            "item_b": b,
            "winner": winner,
            "metrics": [
                ("Live Deal Price", f"${int(a['live_price_usd']):,}", f"${int(b['live_price_usd']):,}"),
                ("Cost per Watt-Hour ($/Wh)", f"${a['d_wh']}/Wh", f"${b['d_wh']}/Wh"),
                ("Battery Capacity", f"{a['capacity_wh']:,} Wh", f"{b['capacity_wh']:,} Wh"),
                ("Continuous / Surge Output", f"{a['continuous_w']}W / {a['surge_w']}W", f"{b['continuous_w']}W / {b['surge_w']}W"),
                ("Max Solar Input", f"{a['solar_input_w']}W", f"{b['solar_input_w']}W"),
                ("Battery Chemistry & Cycles", f"{a['chemistry']} ({a['cycle_life']:,} cycles)", f"{b['chemistry']} ({b['cycle_life']:,} cycles)"),
                ("UPS Switchover Speed", f"{a['ups_ms']} ms", f"{b['ups_ms']} ms"),
                ("Weight", f"{a['weight_lbs']} lbs", f"{b['weight_lbs']} lbs"),
            ],
        }

    elif vertical == "sellerpulse":
        a = conn.execute("SELECT * FROM ecom_platforms WHERE slug = ?", (slug_a,)).fetchone()
        b = conn.execute("SELECT * FROM ecom_platforms WHERE slug = ?", (slug_b,)).fetchone()
        conn.close()
        if not a or not b:
            return None
        a, b = dict(a), dict(b)
        # Calculate fees on $10,000 monthly sales (200 orders @ $50 AOV)
        fee_a = round(a["monthly_fee_usd"] + 10000 * ((a["transaction_fee_pct"] + a["processing_fee_pct"]) / 100.0) + 200 * a["processing_fixed_usd"], 2)
        fee_b = round(b["monthly_fee_usd"] + 10000 * ((b["transaction_fee_pct"] + b["processing_fee_pct"]) / 100.0) + 200 * b["processing_fixed_usd"], 2)
        winner = a if fee_a <= fee_b else b
        return {
            "page_type": "versus",
            "vertical": "sellerpulse",
            "title": f"{a['name']} vs {b['name']}: E-Commerce Fee & Profit Margin Breakdown",
            "meta_description": f"Compare real platform fees, payment processing rates, and net take-home profit between {a['name']} and {b['name']} on $10,000/mo sales.",
            "item_a": a,
            "item_b": b,
            "winner": winner,
            "metrics": [
                ("Monthly Subscription Fee", f"${a['monthly_fee_usd']}/mo", f"${b['monthly_fee_usd']}/mo"),
                ("Marketplace / Referral Fee", f"{a['transaction_fee_pct']}%", f"{b['transaction_fee_pct']}%"),
                ("Card Processing Rate", f"{a['processing_fee_pct']}% + ${a['processing_fixed_usd']}", f"{b['processing_fee_pct']}% + ${b['processing_fixed_usd']}"),
                ("Total Fees on $10k/mo (200 orders)", f"${fee_a:,.2f}/mo", f"${fee_b:,.2f}/mo"),
                ("Best Use Case", a["best_for"], b["best_for"]),
            ],
        }

    elif vertical == "tokenindex":
        a = conn.execute("SELECT * FROM ai_providers WHERE slug = ?", (slug_a,)).fetchone()
        b = conn.execute("SELECT * FROM ai_providers WHERE slug = ?", (slug_b,)).fetchone()
        conn.close()
        if not a or not b:
            return None
        a, b = dict(a), dict(b)
        winner = a if (a["input_cost_per_m"] + a["hourly_gpu_cost"]) <= (b["input_cost_per_m"] + b["hourly_gpu_cost"]) else b
        return {
            "page_type": "versus",
            "vertical": "tokenindex",
            "title": f"{a['name']} vs {b['name']}: Live AI Cost, Throughput & Latency Benchmark",
            "meta_description": f"Compare {a['name']} ({a['provider']}) vs {b['name']} ({b['provider']}) token pricing, GPU hourly rates, context window, and throughput.",
            "item_a": a,
            "item_b": b,
            "winner": winner,
            "metrics": [
                ("Provider / Cloud", a["provider"], b["provider"]),
                ("Resource Category", a["resource_type"], b["resource_type"]),
                ("Input Token Cost (per 1M)", f"${a['input_cost_per_m']:.2f}", f"${b['input_cost_per_m']:.2f}"),
                ("Output Token Cost (per 1M)", f"${a['output_cost_per_m']:.2f}", f"${b['output_cost_per_m']:.2f}"),
                ("Dedicated GPU Hourly Rate", f"${a['hourly_gpu_cost']:.2f}/hr", f"${b['hourly_gpu_cost']:.2f}/hr"),
                ("Context Window / VRAM", f"{a['context_window']:,} tok / {a['vram_gb']}GB", f"{b['context_window']:,} tok / {b['vram_gb']}GB"),
                ("Throughput Speed", f"{a['speed_tok_sec']} tok/s", f"{b['speed_tok_sec']} tok/s"),
            ],
        }

    conn.close()
    return None
