"""Live Portfolio Dashboard — ₹1 Crore, 3-Year Plan (Investment Management assignment)

Run:  streamlit run app.py
Every slider, number box and table edit re-runs the model instantly.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from engine import FACTORS, SEGMENTS, Policy, load_model, preset_policy, run

st.set_page_config(page_title="₹1 Cr Portfolio Dashboard", page_icon="📈", layout="wide")

TEAL, NAVY, GOLD, GREY, RED, GREEN = "#0B5345", "#0B3C49", "#D4AC0D", "#95A5A6", "#C0392B", "#1E8449"
SEG_COLORS = {"Large Cap": NAVY, "Mid Cap": "#1ABC9C", "Small Cap": GOLD, "Debt": GREY, "Cash": "#D5DBDB"}

st.markdown(
    f"""
    <style>
      .block-container {{padding-top: 1.4rem;}}
      .kpi {{background:#F7FBFA;border:1px solid #D5E3E0;border-radius:10px;padding:10px 14px;height:100%;}}
      .kpi .lab {{font-size:0.72rem;letter-spacing:.04em;color:#5D6D7E;text-transform:uppercase;font-weight:600;}}
      .kpi .val {{font-size:1.55rem;font-weight:700;color:{NAVY};line-height:1.25;}}
      .kpi .sub {{font-size:0.75rem;color:#7F8C8D;}}
      .verdict {{border-radius:10px;padding:12px 16px;font-weight:600;margin:6px 0 4px 0;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def get_model(file_bytes: bytes | None):
    return load_model(io.BytesIO(file_bytes) if file_bytes else None)


def inr(x: float) -> str:
    """Indian-style ₹ formatting (lakh / crore grouping)."""
    neg = x < 0
    x = abs(round(x))
    s = str(int(x))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("−₹" if neg else "₹") + s


def cr(x: float) -> str:
    return f"₹{x / 1e7:,.2f} Cr"


with st.sidebar:
    st.markdown("### ⚙️ Controls")
    up = st.file_uploader("Load an updated workbook (optional)", type=["xlsx"],
                          help="Upload Investment_Management_Portfolio.xlsx after changing prices or fundamentals in Excel.")
md = get_model(up.getvalue() if up else None)
INVESTORS = list(md.personas.index)


# ----------------------------------------------------------------------------- session state helpers
def load_preset():
    inv = st.session_state["investor"]
    p = preset_policy(md, inv)
    ss = st.session_state
    ss["target_cr"] = round(p.target / 1e7, 2)
    ss["corpus_cr"] = round(p.corpus / 1e7, 2)
    ss["horizon"] = int(p.horizon)
    ss["equity"] = int(round(p.equity * 100))
    ss["large"], ss["mid"], ss["small"] = (int(round(v * 100)) for v in (p.large, p.mid, p.small))
    ss["max_beta"] = float(p.max_beta)
    ss["min_score"] = int(p.min_score)
    ss["d_gsec"], ss["d_aaa"], ss["d_a"] = (int(round(v * 100)) for v in (p.debt_gsec, p.debt_aaa, p.debt_a))
    ss["rf"], ss["erp"], ss["tilt"], ss["blend"] = (round(v * 100, 2) for v in (p.rf, p.erp, p.tilt, p.blend))
    for name, _, _ in FACTORS:
        ss[f"w_{name}"] = int(round(p.weights[name] * 100))


if st.session_state.get("investor") not in INVESTORS:
    st.session_state["investor"] = INVESTORS[0]
if "corpus_cr" not in st.session_state:
    load_preset()

with st.sidebar:
    st.selectbox("Investor", INVESTORS, key="investor", on_change=load_preset,
                 format_func=lambda n: f"{n} — {md.personas.loc[n, 'archetype']}")
    p_row = md.personas.loc[st.session_state["investor"]]
    st.caption(f"**{p_row['risk']} risk** · {p_row['profile']}")
    st.button("↺ Reset to this investor's preset", on_click=load_preset, use_container_width=True)

    with st.expander("🎯 Goal", expanded=True):
        st.number_input("Starting corpus (₹ crore)", 0.10, 100.0, step=0.10, key="corpus_cr")
        st.number_input("Target corpus (₹ crore)", 0.10, 200.0, step=0.05, key="target_cr")
        st.slider("Horizon (years)", 1, 10, key="horizon")

    with st.expander("📊 Asset allocation", expanded=True):
        st.slider("Equity allocation (%)", 0, 100, key="equity")
        st.caption("Split of the equity sleeve (auto-normalised)")
        c1, c2, c3 = st.columns(3)
        c1.number_input("Large %", 0, 100, key="large")
        c2.number_input("Mid %", 0, 100, key="mid")
        c3.number_input("Small %", 0, 100, key="small")
        st.caption("Debt sleeve mix (auto-normalised)")
        d1, d2, d3 = st.columns(3)
        d1.number_input("G-Sec %", 0, 100, key="d_gsec")
        d2.number_input("AAA %", 0, 100, key="d_aaa")
        d3.number_input("A %", 0, 100, key="d_a")

    with st.expander("🛡️ Stock filters", expanded=True):
        st.slider("Max beta allowed per stock", 0.3, 3.0, step=0.05, key="max_beta")
        st.slider("Min investor score to qualify", 0, 100, key="min_score")

    with st.expander("🏦 Market assumptions"):
        st.slider("Risk-free rate – 10Y G-Sec (%)", 4.0, 10.0, step=0.05, key="rf")
        st.slider("Equity risk premium (%)", 3.0, 12.0, step=0.25, key="erp")
        st.slider("Weight on CAPM in expected return (%)", 0.0, 100.0, step=5.0, key="blend")
        st.slider("Max score tilt ± (%)", 0.0, 6.0, step=0.25, key="tilt")

    with st.expander("⚖️ Factor weights (scoring)"):
        st.caption("Auto-normalised — they don't need to add to 100.")
        for name, _, higher in FACTORS:
            st.slider(f"{name} ({'↑' if higher else '↓'} better)", 0, 40, key=f"w_{name}")


# ----------------------------------------------------------------------------- build policy & run
ss = st.session_state
seg_tot = max(ss["large"] + ss["mid"] + ss["small"], 1)
pol = Policy(
    corpus=ss["corpus_cr"] * 1e7, target=ss["target_cr"] * 1e7, horizon=ss["horizon"], equity=ss["equity"] / 100,
    large=ss["large"] / seg_tot, mid=ss["mid"] / seg_tot, small=ss["small"] / seg_tot,
    max_beta=ss["max_beta"], min_score=ss["min_score"],
    debt_gsec=ss["d_gsec"], debt_aaa=ss["d_aaa"], debt_a=ss["d_a"],
    rf=ss["rf"] / 100, erp=ss["erp"] / 100, blend=ss["blend"] / 100, tilt=ss["tilt"] / 100, gcap=md.market["gcap"],
    weights=pd.Series({n: ss[f"w_{n}"] / 100 for n, _, _ in FACTORS}),
)

if "universe_edit" not in ss or up is not None and ss.get("_src") != up.name:
    ss["universe_edit"] = md.universe.copy()
    ss["_src"] = up.name if up else "bundled"
res = run(md, pol, ss["universe_edit"])
k, stocks, debt = res["kpi"], res["stocks"], res["debt"]


# ----------------------------------------------------------------------------- header + KPIs
st.markdown(f"## 📈 Live Portfolio Dashboard  ·  {ss['investor']} — *{p_row['archetype']}*")
st.caption("Prices: NSE close 14-Oct-2026 (Yahoo Finance) · Fundamentals: Screener.in / Stockanalysis.com · "
           "Yields: RBI, Trading Economics. Move any control on the left and everything below recalculates.")

if k["gap"] >= 0:
    bg, txt = "#D5F5E3", f"✔ ON TRACK — expected {cr(k['projected'])} vs target {cr(pol.target)} (surplus {inr(k['gap'])})."
elif k["prob"] >= 0.30:
    bg, txt = "#FCF3CF", f"◐ STRETCH — expected {cr(k['projected'])} vs target {cr(pol.target)}; {k['prob']:.0%} chance of getting there."
else:
    bg, txt = "#FADBD8", (f"✖ SHORTFALL — expected {cr(k['projected'])} vs target {cr(pol.target)} "
                         f"(gap {inr(-k['gap'])}). Needs {k['req_cagr']:.1%} a year vs {k['exp_cagr']:.1%} expected.")
st.markdown(f'<div class="verdict" style="background:{bg}">{txt}</div>', unsafe_allow_html=True)


def kpi(col, label, value, sub=""):
    col.markdown(f'<div class="kpi"><div class="lab">{label}</div><div class="val">{value}</div><div class="sub">{sub}</div></div>',
                 unsafe_allow_html=True)


r1 = st.columns(6)
kpi(r1[0], "Projected value", cr(k["projected"]), f"after {pol.horizon:g} years")
kpi(r1[1], "Expected CAGR", f"{k['exp_cagr']:.1%}", "model central estimate")
kpi(r1[2], "Required CAGR", f"{k['req_cagr']:.1%}", f"to reach {cr(pol.target)}")
kpi(r1[3], "Probability of target", f"{k['prob']:.0%}", "lognormal, 5Y volatility")
kpi(r1[4], "Portfolio beta", f"{k['beta']:.2f}", "1.00 = moves with NIFTY")
kpi(r1[5], "Volatility", f"{k['vol']:.1%}", "annualised, 5Y monthly")
st.write("")
r2 = st.columns(6)
kpi(r2[0], "Surplus / (shortfall)", inr(k["gap"]), "vs target")
kpi(r2[1], "Expected Sharpe", f"{k['sharpe']:.2f}", "(E[r] − Rƒ) ÷ σ")
kpi(r2[2], "Stocks held", f"{k['n_stocks']} / {len(stocks)}", "pass score & beta filters")
top = stocks["weight"].idxmax() if stocks["weight"].max() > 0 else "—"
kpi(r2[3], "Largest position", f"{stocks['weight'].max():.1%}", top)
kpi(r2[4], "Backtest CAGR (5Y)", f"{k['bt_cagr']:.1%}", f"NIFTY {k['nifty_cagr']:.1%} · hypothetical")
kpi(r2[5], "Backtest max drawdown", f"{k['bt_mdd']:.1%}", "today's weights on past data")
st.write("")

tabs = st.tabs(["📊 Overview", "📋 Holdings", "🏅 Scorecard", "⚠️ Risk", "👥 Compare investors", "✏️ Edit stock data", "📘 Method"])

# ----------------------------------------------------------------------------- Overview
with tabs[0]:
    a, b = st.columns([1.35, 1])
    h = pd.concat([
        stocks.assign(asset=stocks.index, kind=stocks["segment"])[["asset", "weight", "kind"]],
        debt.assign(asset=debt.index, kind="Debt")[["asset", "weight", "kind"]],
    ])
    h = h[h["weight"] > 0].sort_values("weight")
    fig = px.bar(h, x="weight", y="asset", color="kind", orientation="h", color_discrete_map=SEG_COLORS,
                 labels={"weight": "Weight", "asset": "", "kind": ""}, title="Weight by holding")
    fig.update_layout(xaxis_tickformat=".0%", height=430, margin=dict(l=10, r=10, t=50, b=10), legend_orientation="h", legend_y=-0.12)
    a.plotly_chart(fig, use_container_width=True)
    mix = pd.DataFrame({"part": list(res["seg_mix"].keys()), "share": list(res["seg_mix"].values())})
    fig = px.pie(mix[mix["share"] > 0.0005], names="part", values="share", hole=0.55, color="part",
                 color_discrete_map=SEG_COLORS, title="Asset mix")
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
    b.plotly_chart(fig, use_container_width=True)

    a, b = st.columns(2)
    pth = res["path"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pth["Year"], y=pth["Upside (+1σ)"] / 1e7, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=pth["Year"], y=pth["Downside (−1σ)"] / 1e7, fill="tonexty", fillcolor="rgba(11,83,69,0.12)",
                             line=dict(width=0), name="±1σ range"))
    fig.add_trace(go.Scatter(x=pth["Year"], y=pth["Expected"] / 1e7, name="Expected", line=dict(color=TEAL, width=3)))
    fig.add_trace(go.Scatter(x=pth["Year"], y=pth["Target path"] / 1e7, name="Required path", line=dict(color=RED, dash="dash")))
    fig.update_layout(title="Corpus path vs target (₹ crore)", yaxis_title="₹ crore", xaxis_title="Year", height=380,
                      margin=dict(l=10, r=10, t=50, b=10), legend_orientation="h", legend_y=-0.2)
    a.plotly_chart(fig, use_container_width=True)
    bt = res["backtest"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bt.index, y=bt["Portfolio"], name="This portfolio", line=dict(color=TEAL, width=2.5)))
    fig.add_trace(go.Scatter(x=bt.index, y=bt["NIFTY 50"], name="NIFTY 50", line=dict(color=GREY, width=2)))
    fig.update_layout(title="Growth of ₹100 — 5-year hypothetical backtest", height=380, margin=dict(l=10, r=10, t=50, b=10),
                      legend_orientation="h", legend_y=-0.2)
    b.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------------- Holdings
with tabs[1]:
    eq = stocks.assign(Asset=stocks.index, Class="Equity")
    eq = eq[["Asset", "company", "segment", "sector", "score", "eligible", "weight", "price", "units", "invested", "beta",
             "exp_return", "target_price", "value_h"]]
    eq.columns = ["Asset", "Company", "Segment", "Sector", "Score", "Eligible", "Weight", "Price ₹", "Units", "Invested ₹",
                  "Beta", "Exp. return", f"Target price (Y{pol.horizon:g}) ₹", f"Value (Y{pol.horizon:g}) ₹"]
    eq = eq.sort_values(["Weight", "Score"], ascending=False)
    db = debt.assign(Asset=debt.index)[["Asset", "name", "rating", "weight", "unit_price", "units", "invested", "credit_adj", "value_h"]]
    db.columns = ["Asset", "Instrument", "Rating", "Weight", "Unit price ₹", "Units", "Invested ₹", "Credit-adj. yield", f"Value (Y{pol.horizon:g}) ₹"]
    st.markdown("**Equity** — stocks with zero weight did not pass the score / beta filters for this investor.")
    st.dataframe(
        eq.style.format({"Score": "{:.1f}", "Weight": "{:.1%}", "Price ₹": "{:,.2f}", "Units": "{:,.0f}", "Invested ₹": "{:,.0f}",
                         "Beta": "{:.2f}", "Exp. return": "{:.1%}", f"Target price (Y{pol.horizon:g}) ₹": "{:,.2f}",
                         f"Value (Y{pol.horizon:g}) ₹": "{:,.0f}"})
          .background_gradient(subset=["Score"], cmap="RdYlGn", vmin=0, vmax=100)
          .bar(subset=["Weight"], color="#A3E4D7", vmin=0),
        use_container_width=True, hide_index=True, height=530)
    st.markdown("**Debt**")
    st.dataframe(db.style.format({"Weight": "{:.1%}", "Unit price ₹": "{:,.2f}", "Units": "{:,.0f}", "Invested ₹": "{:,.0f}",
                                  "Credit-adj. yield": "{:.2%}", f"Value (Y{pol.horizon:g}) ₹": "{:,.0f}"}),
                 use_container_width=True, hide_index=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Invested", inr(k["invested"])); c2.metric("Uninvested cash (earns G-Sec yield)", inr(k["cash"]))
    c3.metric("Weights total", f"{stocks['weight'].sum() + debt['weight'].sum():.1%}")
    out = pd.concat([eq.assign(Type="Equity"), db.rename(columns={"Instrument": "Company", "Rating": "Sector"}).assign(Type="Debt")])
    st.download_button("⬇️ Download holdings (CSV)", out.to_csv(index=False).encode(), f"holdings_{ss['investor']}.csv", "text/csv")

# ----------------------------------------------------------------------------- Scorecard
with tabs[2]:
    sc = res["scores"].copy()
    sc["Live score"] = stocks["score"]
    sc = sc.sort_values("Live score", ascending=False)
    a, b = st.columns([1.6, 1])
    fig = px.imshow(sc.drop(columns="Live score"), color_continuous_scale="RdYlGn", zmin=0, zmax=100, aspect="auto",
                    text_auto=".0f", title="Factor scores (0 = worst in universe, 100 = best)")
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10), coloraxis_showscale=False)
    fig.update_xaxes(side="top", tickangle=-35)
    a.plotly_chart(fig, use_container_width=True)
    rk = sc[["Live score"]].assign(Segment=stocks["segment"], Eligible=stocks["eligible"]).reset_index(names="Ticker").sort_values("Live score")
    fig = px.bar(rk, x="Live score", y="Ticker", color="Segment", orientation="h", color_discrete_map=SEG_COLORS,
                 title=f"Investor score (cut-off {pol.min_score:.0f})")
    fig.add_vline(x=pol.min_score, line_dash="dash", line_color=RED)
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10), xaxis_range=[0, 100], legend_orientation="h", legend_y=-0.12)
    b.plotly_chart(fig, use_container_width=True)
    wt = pol.weights / pol.weights.sum() if pol.weights.sum() > 0 else pol.weights
    wdf = pd.DataFrame({"Factor": wt.index, "Weight": wt.values})
    fig = px.bar(wdf, x="Factor", y="Weight", title="Factor weights in use (normalised)", color_discrete_sequence=[GOLD])
    fig.update_layout(yaxis_tickformat=".0%", height=320, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------------- Risk
with tabs[3]:
    a, b = st.columns(2)
    rk = stocks.reset_index(names="Ticker")
    rk["Held weight"] = rk["weight"].clip(lower=0.004)
    fig = px.scatter(rk, x="sd", y="exp_return", size="Held weight", color="segment", text="Ticker", color_discrete_map=SEG_COLORS,
                     labels={"sd": "Annualised volatility", "exp_return": "Expected return", "segment": ""},
                     title="Risk vs expected return (bubble = weight)")
    fig.update_traces(textposition="top center")
    fig.update_layout(xaxis_tickformat=".0%", yaxis_tickformat=".0%", height=440, margin=dict(l=10, r=10, t=50, b=10))
    a.plotly_chart(fig, use_container_width=True)
    fig = px.bar(rk.sort_values("beta"), x="beta", y="Ticker", orientation="h", color="segment", color_discrete_map=SEG_COLORS,
                 title=f"Beta vs NIFTY 50 (cap {pol.max_beta:.2f})", labels={"beta": "Beta", "Ticker": "", "segment": ""})
    fig.add_vline(x=pol.max_beta, line_dash="dash", line_color=RED)
    fig.add_vline(x=1, line_dash="dot", line_color=GREY)
    fig.update_layout(height=440, margin=dict(l=10, r=10, t=50, b=10))
    b.plotly_chart(fig, use_container_width=True)
    dd = res["drawdown"]
    fig = go.Figure(go.Scatter(x=dd.index, y=dd.values, fill="tozeroy", line=dict(color=RED), name="Drawdown"))
    fig.update_layout(title="Drawdown from peak — hypothetical backtest", yaxis_tickformat=".0%", height=300, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------------- Compare investors
with tabs[4]:
    st.caption("Each investor's preset policy, using the market assumptions and stock data currently in the sidebar / editor.")
    rows = []
    for inv in INVESTORS:
        p2 = preset_policy(md, inv)
        p2.rf, p2.erp, p2.blend, p2.tilt = pol.rf, pol.erp, pol.blend, pol.tilt
        r2_ = run(md, p2, ss["universe_edit"])["kpi"]
        rows.append(dict(Investor=inv, Archetype=md.personas.loc[inv, "archetype"], Target=p2.target, Projected=r2_["projected"],
                         **{"Required CAGR": r2_["req_cagr"], "Expected CAGR": r2_["exp_cagr"], "Probability": r2_["prob"],
                            "Beta": r2_["beta"], "Volatility": r2_["vol"], "Stocks": r2_["n_stocks"], "Equity %": p2.equity}))
    cmp_ = pd.DataFrame(rows)
    st.dataframe(cmp_.style.format({"Target": "₹{:,.0f}", "Projected": "₹{:,.0f}", "Required CAGR": "{:.1%}", "Expected CAGR": "{:.1%}",
                                    "Probability": "{:.0%}", "Beta": "{:.2f}", "Volatility": "{:.1%}", "Equity %": "{:.0%}"}),
                 use_container_width=True, hide_index=True)
    a, b = st.columns(2)
    m = cmp_.melt(id_vars="Investor", value_vars=["Target", "Projected"])
    m["value"] = m["value"] / 1e7
    fig = px.bar(m, x="Investor", y="value", color="variable", barmode="group", color_discrete_sequence=["#B2BABB", TEAL],
                 title="Target vs projected (₹ crore)", labels={"value": "₹ crore", "variable": ""})
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
    a.plotly_chart(fig, use_container_width=True)
    fig = px.scatter(cmp_, x="Volatility", y="Expected CAGR", size="Probability", text="Investor", color="Investor",
                     title="Risk–return of the four investors (bubble = probability of target)", size_max=40)
    fig.update_traces(textposition="top center")
    fig.update_layout(xaxis_tickformat=".0%", yaxis_tickformat=".0%", height=380, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
    b.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------------- Edit stock data
with tabs[5]:
    st.markdown("Change any **price or fundamental** below — scores, eligibility, weights and every chart update immediately. "
                "Ratios such as P/E, P/BV, PEG and EPS growth are re-derived from these inputs.")
    view = ss["universe_edit"][["company", "price", "mcap", "eps_ttm", "eps_fy25", "eps_fy26", "bv", "roe", "roce", "dy",
                                "sales_yoy", "profit_3y", "de"]].copy()
    edited = st.data_editor(
        view, use_container_width=True, height=540, key="editor",
        disabled=["company"],
        column_config={
            "company": "Company", "price": st.column_config.NumberColumn("Price ₹", format="%.2f"),
            "mcap": st.column_config.NumberColumn("Mkt cap ₹ Cr", format="%d"),
            "eps_ttm": st.column_config.NumberColumn("EPS TTM", format="%.2f"),
            "eps_fy25": st.column_config.NumberColumn("EPS FY25", format="%.2f"),
            "eps_fy26": st.column_config.NumberColumn("EPS FY26", format="%.2f"),
            "bv": st.column_config.NumberColumn("Book value/sh", format="%.2f"),
            "roe": st.column_config.NumberColumn("ROE", format="%.4f"), "roce": st.column_config.NumberColumn("ROCE", format="%.4f"),
            "dy": st.column_config.NumberColumn("Div. yield", format="%.4f"),
            "sales_yoy": st.column_config.NumberColumn("Sales YoY", format="%.4f"),
            "profit_3y": st.column_config.NumberColumn("Profit CAGR 3Y", format="%.4f"),
            "de": st.column_config.NumberColumn("Debt/Equity", format="%.3f", help="Blank = not meaningful (bank) → neutral score"),
        },
    )
    def _norm(df):
        return df.drop(columns="company").astype(float).round(8).fillna(-9e9)
    if not _norm(edited).equals(_norm(view)):
        new = ss["universe_edit"].copy()
        new.update(edited)
        ss["universe_edit"] = new
        st.rerun()
    c1, c2 = st.columns([1, 3])
    if c1.button("↺ Restore original data"):
        ss["universe_edit"] = md.universe.copy()
        ss.pop("editor", None)
        st.rerun()
    c2.caption("Percentages are decimals (0.15 = 15%). Market cap drives the Large/Mid/Small classification (≥ ₹1,00,000 Cr / ≥ ₹30,000 Cr).")

# ----------------------------------------------------------------------------- Method
with tabs[6]:
    st.markdown(f"""
**1. Universe** – 14 NSE stocks from 14 sectors (7 large, 3 mid, 4 small cap) + 3 debt instruments (3Y G-Sec, Reliance AAA NCD, SMC Global A NCD).

**2. Factor scores** – 13 metrics (market cap, sales growth, EPS growth, ROE, ROCE, P/E, PEG, P/BV, beta, volatility, price vs 10-month SMA,
6-month momentum, debt/equity) are each turned into a 0–100 percentile: *(rank − 1) ÷ (n − 1) × 100* in the "better" direction.

**3. Investor score** – Σ (factor score × weight) ÷ Σ weights. The brief's priority factors (market cap, sales YoY, EPS) carry the largest share.

**4. Selection & weights** – a stock qualifies if score ≥ **{pol.min_score:.0f}** and beta ≤ **{pol.max_beta:.2f}**. Equity
(**{pol.equity:.0%}**) is split Large/Mid/Small **{pol.large:.0%} / {pol.mid:.0%} / {pol.small:.0%}** (re-spread if a segment has no
qualifier); inside a segment, weight ∝ score. Debt (**{1 - pol.equity:.0%}**) follows the debt mix. Units are rounded down; leftover cash earns the G-Sec yield.

**5. Expected return** – {pol.blend:.0%} × CAPM (Rƒ {pol.rf:.2%} + β × ERP {pol.erp:.2%}) + {1 - pol.blend:.0%} × (dividend yield + ROE × retention, capped at
{pol.gcap:.0%}) ± up to {pol.tilt:.2%} for the score. Debt: yield − default probability × loss-given-default.

**6. Risk & feasibility** – beta and volatility from 60 monthly returns vs NIFTY 50; probability of target assumes lognormal returns
with the portfolio's historical volatility. The backtest applies today's weights to the past (look-ahead bias) — use it for risk, not as a return claim.

*Model estimates for coursework, not investment advice.*
""")
