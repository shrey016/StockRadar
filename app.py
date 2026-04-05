# app.py
# Run: streamlit run app.py

import re
import json
import streamlit as st
from datetime import datetime, timezone
import anthropic

from analyzer import run_analysis
from config import MODEL


st.set_page_config(
    page_title="Stock Radar",
    page_icon="📈",
    layout="wide",
)

st.markdown("""
<style>
  .verdict-bullish { background:#d4edda; color:#155724; padding:4px 14px; border-radius:20px; font-weight:700; font-size:13px; }
  .verdict-bearish { background:#f8d7da; color:#721c24; padding:4px 14px; border-radius:20px; font-weight:700; font-size:13px; }
  .verdict-neutral { background:#e2e3e5; color:#383d41; padding:4px 14px; border-radius:20px; font-weight:700; font-size:13px; }
  .impact-high     { background:#f8d7da; color:#721c24; padding:3px 10px; border-radius:12px; font-size:12px; }
  .impact-medium   { background:#fff3cd; color:#856404; padding:3px 10px; border-radius:12px; font-size:12px; }
  .impact-low      { background:#e2e3e5; color:#383d41; padding:3px 10px; border-radius:12px; font-size:12px; }
  .mood-risk-on    { background:#d4edda; color:#155724; padding:5px 18px; border-radius:20px; font-weight:700; font-size:15px; }
  .mood-risk-off   { background:#f8d7da; color:#721c24; padding:5px 18px; border-radius:20px; font-weight:700; font-size:15px; }
  .mood-mixed      { background:#fff3cd; color:#856404; padding:5px 18px; border-radius:20px; font-weight:700; font-size:15px; }
  .news-card       { border-left:3px solid #4a9eff; padding:12px 16px; margin-bottom:12px;
                     background:#1e2530; border-radius:0 8px 8px 0; }
  .news-headline   { font-size:14px; font-weight:600; color:#ffffff; line-height:1.4; margin-bottom:4px; }
  .news-headline a { color:#4a9eff; text-decoration:none; }
  .news-headline a:hover { text-decoration:underline; }
  .news-meta       { font-size:12px; color:#9aa5b4; margin-bottom:6px; }
  .news-summary    { font-size:13px; color:#c9d1d9; line-height:1.5; margin-bottom:6px; }
  .news-readmore   { font-size:12px; color:#4a9eff; text-decoration:none; }
  .news-readmore:hover { text-decoration:underline; }
  .score-wrap      { background:#e9ecef; border-radius:6px; height:8px; margin:6px 0 2px 0; }
  .meta            { font-size:12px; color:#6c757d; }
  .rel-link        { font-size:12px; color:#0d6efd; text-decoration:none; display:block; margin-bottom:4px; }
  .rel-link:hover  { text-decoration:underline; }
  .disclaimer      { font-size:12px; color:#6c757d; border-top:1px solid #dee2e6; padding-top:10px; margin-top:16px; }
</style>
""", unsafe_allow_html=True)


with st.sidebar:
    st.title("📈 About")
    st.markdown("""
Automatically searches for the latest Indian stock market news
and identifies the most impacted stocks using AI — no manual input needed.

**What it does**
- Searches live financial news from the last 48 hours
- Identifies top impacted Indian stocks (NSE / BSE)
- Returns sentiment, impact score, and reasoning per stock

**What you get**
- Overall market mood
- Key news driving the market
- Top stocks with bullish / bearish / neutral verdict
- Impact scores and price direction
""")
    st.divider()
    st.caption(f"Powered by Claude AI · {MODEL}")


st.title("📈 Stock Radar - Indian Stock Sentiment Analyzer")
st.caption("Live AI-powered analysis of the latest Indian market news — updated on every run")
st.divider()

col_btn, col_info = st.columns([2, 5])
with col_btn:
    run_btn = st.button("🔍 Run Analysis", type="primary", use_container_width=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_cite_tags(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'<cite[^>]*>(.*?)</cite>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'</?cite[^>]*>', '', text)
    return text.strip()

def sentiment_badge(s: str) -> str:
    s   = s.lower()
    cls = {"bullish": "verdict-bullish", "bearish": "verdict-bearish"}.get(s, "verdict-neutral")
    return f'<span class="{cls}">{s.capitalize()}</span>'

def impact_badge(i: str) -> str:
    i   = i.lower()
    cls = {"high": "impact-high", "medium": "impact-medium"}.get(i, "impact-low")
    return f'<span class="{cls}">{i.capitalize()} impact</span>'

def mood_badge(m: str) -> str:
    m   = m.lower().replace(" ", "-")
    cls = {"risk-on": "mood-risk-on", "risk-off": "mood-risk-off"}.get(m, "mood-mixed")
    return f'<span class="{cls}">{m.replace("-", " ").title()}</span>'

def direction_icon(d: str) -> str:
    return {"up": "🟢 Up", "down": "🔴 Down"}.get(d.lower(), "🟡 Sideways")

def score_bar(score: int) -> str:
    color = "#28a745" if score >= 70 else "#ffc107" if score >= 40 else "#dc3545"
    return (
        f'<div class="score-wrap">'
        f'<div style="width:{score}%;background:{color};height:8px;border-radius:6px;"></div>'
        f'</div>'
        f'<span class="meta">Impact score: {score} / 100</span>'
    )


# ── Analysis ──────────────────────────────────────────────────────────────────
if run_btn:
    with st.status("Searching latest news and analyzing stocks...", expanded=True) as status:
        st.write("🔍 Searching Indian financial news from the last 48 hours...")
        st.write("🤖 Identifying top impacted stocks...")

        try:
            result = run_analysis()
            n = len(result.get("topStocks", []))
            status.update(label=f"✅ Done — {n} stocks identified.", state="complete")
        except anthropic.AuthenticationError:
            status.update(label="❌ Authentication failed.", state="error")
            st.error("Invalid API key. Please check config.py.")
            st.stop()
        except anthropic.RateLimitError:
            status.update(label="❌ Rate limit hit.", state="error")
            st.error("Too many requests. Please wait a moment and try again.")
            st.stop()
        except Exception as e:
            status.update(label="❌ Analysis failed.", state="error")
            st.error(f"Something went wrong: {e}")
            st.stop()

    # ── Market Overview ───────────────────────────────────────────────────────
    st.subheader("🌐 Market Overview")
    mood_col, summary_col = st.columns([1, 4])

    with mood_col:
        mood = result.get("marketMood", "mixed")
        st.markdown("**Market mood**")
        st.markdown(mood_badge(mood), unsafe_allow_html=True)
        st.caption(f"As of {datetime.now().strftime('%d %b %Y, %H:%M')}")

    with summary_col:
        st.markdown("**Summary**")
        st.write(strip_cite_tags(result.get("summary", "—")))

    st.divider()

    stocks_col, news_col = st.columns([3, 2])

    # ── Stocks ────────────────────────────────────────────────────────────────
    with stocks_col:
        top_stocks = result.get("topStocks", [])
        st.subheader(f"🏆 Top {len(top_stocks)} Stocks to Watch")

        if not top_stocks:
            st.warning("No stocks were identified in this run.")
        else:
            news_url_map = {
                strip_cite_tags(item.get("headline", "")).strip(): item.get("url", "")
                for item in result.get("news", [])
            }

            for stock in top_stocks:
                ticker    = stock.get("ticker", "?").upper()
                company   = stock.get("company", "")
                sector    = stock.get("sector", "")
                sentiment = stock.get("sentiment", "neutral")
                impact    = stock.get("impact", "medium")
                score     = int(stock.get("impactScore", 50))
                direction = stock.get("priceDirection", "sideways")
                reasoning = strip_cite_tags(stock.get("reasoning", "—"))
                rel_news  = stock.get("relatedNews", [])

                with st.expander(f"**{ticker}** — {company}", expanded=False):
                    st.markdown(
                        f"{sentiment_badge(sentiment)}&nbsp;&nbsp;"
                        f"{impact_badge(impact)}&nbsp;&nbsp;"
                        f"<span class='meta'>Direction: {direction_icon(direction)}</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown(score_bar(score), unsafe_allow_html=True)

                    if sector:
                        st.caption(f"Sector: {sector}")

                    st.markdown("**Why this stock?**")
                    st.write(reasoning)

                    if rel_news:
                        st.markdown("**Related headlines**")
                        links_html = ""
                        for h in rel_news:
                            clean_h = strip_cite_tags(h)
                            url     = news_url_map.get(clean_h.strip(), "")
                            if url:
                                links_html += f'<a href="{url}" target="_blank" class="rel-link">📰 {clean_h}</a>'
                            else:
                                links_html += f'<span class="meta">📰 {clean_h}</span><br>'
                        st.markdown(links_html, unsafe_allow_html=True)

    # ── News ──────────────────────────────────────────────────────────────────
    with news_col:
        st.subheader("📰 Key News")
        news_items = result.get("news", [])

        if not news_items:
            st.warning("No news items returned.")
        else:
            for item in news_items:
                headline = strip_cite_tags(item.get("headline", ""))
                summary  = strip_cite_tags(item.get("summary", ""))
                source   = item.get("source", "")
                pub_at   = item.get("publishedAt", "")
                url      = item.get("url", "")

                # Skip empty items
                if not headline and not summary:
                    continue

                headline_html = (
                    f'<a href="{url}" target="_blank" class="news-headline" '
                    f'style="color:#4a9eff;text-decoration:none;">{headline}</a>'
                    if url else
                    f'<span>{headline}</span>'
                )

                meta_parts = [p for p in [source, pub_at] if p]
                meta_html  = " · ".join(meta_parts)

                card  = f'<div class="news-card">'
                card += f'<div class="news-headline">{headline_html}</div>'
                if meta_html:
                    card += f'<div class="news-meta">{meta_html}</div>'
                if summary:
                    card += f'<div class="news-summary">{summary}</div>'
                if url:
                    card += f'<a href="{url}" target="_blank" class="news-readmore">Read more →</a>'
                card += '</div>'

                st.markdown(card, unsafe_allow_html=True)

    st.divider()

    # ── Summary Table ─────────────────────────────────────────────────────────
    st.subheader("📊 Summary")
    table_data = []
    for s in top_stocks:
        sent  = s.get("sentiment", "neutral")
        emoji = "🟢" if sent == "bullish" else "🔴" if sent == "bearish" else "🟡"
        table_data.append({
            "Ticker"         : s.get("ticker", "?").upper(),
            "Company"        : s.get("company", "?"),
            "Sector"         : s.get("sector", "?"),
            "Sentiment"      : f"{emoji} {sent.capitalize()}",
            "Impact"         : s.get("impact", "?").capitalize(),
            "Impact Score"   : s.get("impactScore", "?"),
            "Price Direction": direction_icon(s.get("priceDirection", "sideways")),
        })
    st.dataframe(table_data, use_container_width=True, hide_index=True)

    # ── Download ──────────────────────────────────────────────────────────────
    st.divider()
    dl_col, meta_col = st.columns([2, 5])
    with dl_col:
        st.download_button(
            label="⬇️ Download Full Report (JSON)",
            data=json.dumps(result, indent=2),
            file_name=f"sentiment_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
        )
    with meta_col:
        st.caption(
            f"Last run: {datetime.now().strftime('%d %b %Y, %H:%M')} · "
            f"Model: {result.get('_model', MODEL)}"
        )

    st.markdown(
        '<div class="disclaimer">⚠️ AI-generated analysis for informational purposes only. '
        'Not financial advice. Consult a SEBI-registered advisor before making investment decisions.</div>',
        unsafe_allow_html=True
    )

else:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px; color:#6c757d;">
        <div style="font-size:56px;">📡</div>
        <h3 style="color:#343a40;">Ready to scan</h3>
        <p>Click <strong>Run Analysis</strong> to search the latest Indian finance news<br>
        and get AI-powered verdicts on the most impacted stocks.</p>
    </div>
    """, unsafe_allow_html=True)