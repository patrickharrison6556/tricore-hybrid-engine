# TriCore Hybrid Income Engine (v2.6)

A 3-in-1 **Programmatic SEO + High-Ticket Affiliate + Micro-SaaS** platform built with FastAPI, SQLite, and SSR Jinja2 templates.

## Included Verticals

1. **WattWise™ (Off-Grid Solar & Power Station Sizing Engine)**
   - Interactive appliance load calculator (continuous watts, compressor surge watts, duty cycle, LiFePO4 DoD math, solar array sizing).
   - Live `$/Wh` ranking with pre-tagged affiliate links (`$50–$300` commission per sale).
   - 96 auto-generated `/seo/can-{station}-run-{appliance}` compatibility pages + 28 `/seo/vs/wattwise/...` comparison pages.
2. **SellerPulse™ (E-Commerce Profit Calculator + AI Store Spy SaaS)**
   - Cross-platform take-home profit & break-even ROAS calculator across Shopify, TikTok Shop, Etsy, and Amazon FBA.
   - **Live AI Store Spy & Listing Generator**: Paste any Shopify store URL (extracts `/products.json`) or product brief to generate SEO titles, 5 conversion bullets, 3 viral TikTok/Meta ad scripts, and a 1-click **Shopify Import CSV**.
3. **TokenIndex™ (AI API & Cloud GPU Cost Calculator)**
   - Simulates monthly token volume and dedicated GPU hours across Gemini 2.5 Flash, DeepSeek V3, Claude 3.7 Sonnet, GPT-4o, RunPod H100, Vast.ai RTX 4090, and Lambda Labs A100.
   - Syncs live token pricing from OpenRouter's public API (`POST /api/automation/sync`).
4. **Unified Command Center (Owner Admin Dashboard)**
   - Configure all affiliate partner tags, Stripe Pro checkout URL, and optional Gemini API key in one place.
   - Tracks every outbound affiliate click (`/go/{vertical}/{slug}`), estimated EPC, Pro Watchdog leads, and automated scraper runs.

## Quick Start

```powershell
cd C:\Users\USER\.gemini\antigravity\scratch\hybrid-income-engine
python -m uvicorn app:app --host 127.0.0.1 --port 8080
```

Then open `http://127.0.0.1:8080` in your browser.
