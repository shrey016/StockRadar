# analyzer.py

import re
import json
import anthropic
from datetime import datetime, timezone
from typing import Optional
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, TOP_STOCKS


SYSTEM_PROMPT = f"""You are an elite financial analyst AI. Your job is to:
1. Search for the LATEST breaking financial and market news from today
2. Analyze which publicly traded indian stocks will be most significantly impacted
3. Return a structured JSON analysis

CRITICAL: You MUST respond with ONLY valid JSON — no markdown fences, no explanation text, nothing else.

Return this exact JSON structure:
{{
  "timestamp": "<ISO 8601 datetime>",
  "summary": "<2-3 sentence market overview>",
  "marketMood": "<'risk-on' | 'risk-off' | 'mixed'>",
  "news": [
    {{
      "headline": "<exact headline>",
      "summary": "<2-3 sentence summary>",
      "source": "<publication name>",
      "url": "<url if available>",
      "publishedAt": "<date string>"
    }}
  ],
  "topStocks": [
    {{
      "ticker": "<NSE/BSE ticker>",
      "company": "<full company name>",
      "sector": "<sector name>",
      "sentiment": "<'bullish' | 'bearish' | 'neutral'>",
      "impact": "<'high' | 'medium' | 'low'>",
      "impactScore": <integer 1-100>,
      "priceDirection": "<'up' | 'down' | 'sideways'>",
      "reasoning": "<specific reason this stock is affected>",
      "relatedNews": ["<headline1>", "<headline2>"]
    }}
  ]
}}

Rules:
- Include 5-8 top news items from today
- Include EXACTLY {TOP_STOCKS} stocks in topStocks — no more, no less
- Sort topStocks by impactScore descending
- Be specific about WHY each stock is impacted (earnings, regulation, macro, competitor news, etc.)
- Only include stocks listed on Indian exchanges (NSE, BSE)
- Prioritize stocks with clear, direct connections to today's news
- Do NOT hallucinate news. Only use real news found via search."""


def run_analysis(api_key: Optional[str] = None) -> dict:
    key    = api_key or ANTHROPIC_API_KEY
    client = anthropic.Anthropic(api_key=key)

    today  = datetime.now(timezone.utc).strftime("%A, %B %d %Y")

    user_message = (
        f"Search for the latest financial news for last 48 hours from today ({today}) "
        f"and analyze which stocks will be most impacted.\n\n"
        f"Search for:\n"
        f"- Major earnings reports or guidance changes\n"
        f"- Reserve Bank of India / interest rate news\n"
        f"- Geopolitical events affecting markets\n"
        f"- Sector-specific regulatory news\n"
        f"- Big M&A deals or corporate announcements\n"
        f"- Macro economic data releases (CPI, jobs, GDP, etc.)\n\n"
        f"Then identify EXACTLY {TOP_STOCKS} Indian stocks most directly impacted by this news "
        f"and return your complete analysis as JSON."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": user_message}],
    )

    # Extract text block (comes after tool use blocks)
    raw = ""
    for block in response.content:
        if block.type == "text":
            raw += block.text

    raw = raw.strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError(f"Could not parse JSON from response:\n{raw[:500]}")
        result = json.loads(match.group(0))

    result["_model"]      = MODEL
    result["_fetched_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Running analysis...")
    try:
        result = run_analysis()
        print(f"Mood    : {result.get('marketMood', '?').upper()}")
        print(f"Summary : {result.get('summary', '?')}")
        print(f"\nTop stocks ({len(result.get('topStocks', []))}):")
        for s in result.get("topStocks", []):
            sent  = s.get("sentiment", "?")
            color = "\033[92m" if sent == "bullish" else "\033[91m" if sent == "bearish" else "\033[93m"
            reset = "\033[0m"
            print(f"  {s.get('ticker','?'):<14} {color}{sent:<10}{reset} score={s.get('impactScore','?'):>3}  {s.get('company','?')}")

        out = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved -> {out}")

    except anthropic.AuthenticationError:
        print("Invalid API key. Update config.py")
    except Exception as e:
        print(f"Error: {e}")