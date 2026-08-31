import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

st.set_page_config(
    page_title="2026 Federal & NC Tax Planner",
    page_icon="📊",
    layout="wide"
)

# ---------------------------------------------------------
# TAX CONSTANTS & ENGINE
# ---------------------------------------------------------
PARAMS = {
    "Single": {
        "fed_std_deduction": 16100.0,
        "nc_std_deduction": 12750.0,
        "age_65_bump": 2050.0,
        "ss_thresh_1": 25000.0,
        "ss_thresh_2": 34000.0,
        "ord_brackets": [(12400.0, 0.10), (50400.0, 0.12), (105700.0, 0.22), (201775.0, 0.24), (256125.0, 0.32), (566350.0, 0.35), (float('inf'), 0.37)],
        "ltcg_brackets": [(49450.0, 0.00), (545500.0, 0.15), (float('inf'), 0.20)],
        "niit_threshold": 200000.0,
        "oba_phaseout_start": 75000.0,
        "irmaa_tiers": [
            (114000.0, 0.0, "Tier 0 (Standard)"),
            (143000.0, 97.50, "Tier 1 Surcharge"),
            (179000.0, 240.40, "Tier 2 Surcharge"),
            (float('inf'), 385.00, "Tier 3 Surcharge")
        ]
    },
    "MFJ": {
        "fed_std_deduction": 32200.0,
        "nc_std_deduction": 25500.0,
        "age_65_bump": 1650.0,
        "ss_thresh_1": 32000.0,
        "ss_thresh_2": 44000.0,
        "ord_brackets": [(24800.0, 0.10), (100800.0, 0.12), (211400.0, 0.22), (403550.0, 0.24), (512250.0, 0.32), (732600.0, 0.35), (float('inf'), 0.37)],
        "ltcg_brackets": [(98900.0, 0.00), (613600.0, 0.15), (float('inf'), 0.20)],
        "niit_threshold": 250000.0,
        "oba_phaseout_start": 150000.0,
        "irmaa_tiers": [
            (228000.0, 0.0, "Tier 0 (Standard)"),
            (286000.0, 97.50 * 2, "Tier 1 Surcharge (2x)"),
            (358000.0, 240.40 * 2, "Tier 2 Surcharge (2x)"),
            (float('inf'), 385.00 * 2, "Tier 3 Surcharge (2x)")
        ]
    }
}
NC_TAX_RATE = 0.0399

def calculate_tax_scenario(wages, ltcg, ss, pretax, muni, fed_ded_base, nc_ded_base, status, tp_65, sp_65):
    p = PARAMS[status]
    
    # 1. Social Security Taxability
    prov_income = wages + ltcg + muni - pretax + (0.50 * ss)
    t1, t2 = p["ss_thresh_1"], p["ss_thresh_2"]
    
    if prov_income <= t1:
        taxable_ss = 0.0
    elif prov_income <= t2:
        taxable_ss = min(0.50 * ss, 0.50 * (prov_income - t1))
    else:
        taxable_ss = min(0.85 * ss, (0.50 * min(ss, t2 - t1)) + 0.85 * (prov_income - t2))
    
    # 2. AGI & MAGI
    fed_agi = max(0.0, wages + ltcg + taxable_ss - pretax)
    magi = max(0.0, fed_agi + muni)
    
    # 3. OBA Senior Bonus Deduction (Below-the-line)
    senior_bonus = 0.0
    if tp_65 or sp_65:
        count = sum([tp_65, sp_65]) if status == "MFJ" else (1 if tp_65 else 0)
        max_ded = 6000.0 * count
        phase_out = max(0.0, (magi - p["oba_phaseout_start"]) * 0.06)
        senior_bonus = max(0.0, max_ded - phase_out)
        
    total_fed_deduction = fed_ded_base + senior_bonus
    
    # 4. Deduction Absorption Stacking
    total_taxable_income = max(0.0, fed_agi - total_fed_deduction)
    ordinary_gross = max(0.0, fed_agi - ltcg)
    
    fed_ord_taxable = min(total_taxable_income, max(0.0, ordinary_gross - total_fed_deduction))
    fed_ltcg_taxable = total_taxable_income - fed_ord_taxable
    
    # 5. Federal Ordinary Brackets
    fed_ord_tax = 0.0
    prev_limit = 0.0
    ord_bracket_amts = []
    
    for limit, rate in p["ord_brackets"]:
        if fed_ord_taxable > prev_limit:
            chunk = min(fed_ord_taxable, limit) - prev_limit
            fed_ord_tax += chunk * rate
            ord_bracket_amts.append({"rate": rate, "amount": chunk})
            prev_limit = limit
        else:
            break
            
    # 6. Federal LTCG Brackets
    start_stack = fed_ord_taxable
    end_stack = fed_ord_taxable + fed_ltcg_taxable
    fed_ltcg_tax = 0.0
    ltcg_bracket_amts = []
    
    ltcg_b = p["ltcg_brackets"]
    t_0 = max(0.0, min(end_stack, ltcg_b[0][0]) - max(start_stack, 0.0))
    t_15 = max(0.0, min(end_stack, ltcg_b[1][0]) - max(start_stack, ltcg_b[0][0]))
    t_20 = max(0.0, end_stack - max(start_stack, ltcg_b[1][0]))
    
    if t_0 > 0: ltcg_bracket_amts.append({"rate": ltcg_b[0][1], "amount": t_0})
    if t_15 > 0: ltcg_bracket_amts.append({"rate": ltcg_b[1][1], "amount": t_15})
    if t_20 > 0: ltcg_bracket_amts.append({"rate": ltcg_b[2][1], "amount": t_20})
    
    fed_ltcg_tax = (t_0 * ltcg_b[0][1]) + (t_15 * ltcg_b[1][1]) + (t_20 * ltcg_b[2][1])
    
    # 7. Net Investment Income Tax
    niit_tax = 0.0
    niit_subject = 0.0
    if magi > p["niit_threshold"] and ltcg > 0:
        niit_subject = min(float(ltcg), magi - p["niit_threshold"])
        niit_tax = niit_subject * 0.038
        
    total_fed_tax = fed_ord_tax + fed_ltcg_tax + niit_tax
    
    # 8. NC State Tax
    nc_taxable = max(0.0, wages + ltcg - pretax - nc_ded_base)
    nc_tax = nc_taxable * NC_TAX_RATE
    
    # 9. Projected IRMAA
    tier_name = ""
    monthly_irmaa = 0.0
    headroom_irmaa = None
    
    for limit, surcharge, name in p["irmaa_tiers"]:
        if magi <= limit:
            tier_name = name
            monthly_irmaa = surcharge
            headroom_irmaa = limit - magi if limit != float('inf') else None
            break
            
    annual_irmaa = monthly_irmaa * 12.0
    total_outflows = total_fed_tax + nc_tax + annual_irmaa
    
    return {
        "fed_agi": fed_agi, "magi": magi, "taxable_ss": taxable_ss,
        "total_fed_deduction": total_fed_deduction,
        "fed_ord_taxable": fed_ord_taxable, "fed_ltcg_taxable": fed_ltcg_taxable,
        "fed_ord_tax": fed_ord_tax, "fed_ltcg_tax": fed_ltcg_tax,
        "niit_tax": niit_tax, "niit_subject": niit_subject,
        "nc_tax": nc_tax,
        "annual_irmaa": annual_irmaa, "tier_name": tier_name, "headroom_irmaa": headroom_irmaa,
        "total_outflows": total_outflows,
        "ord_bracket_amts": ord_bracket_amts, "ltcg_bracket_amts": ltcg_bracket_amts
    }

# ---------------------------------------------------------
# UI: SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.title("2026 Year-End Planner")

filing_status = st.sidebar.radio("Filing Status", ["Single", "MFJ"], horizontal=True)

st.sidebar.subheader("Taxpayer Profile")
tp_65 = st.sidebar.checkbox("Taxpayer 65 or older", value=False)
sp_65 = st.sidebar.checkbox("Spouse 65 or older", value=False) if filing_status == "MFJ" else False

st.sidebar.subheader("Income Sources")
wages_in = st.sidebar.slider("Ordinary Income / tIRA ($)", 0, 400000, 120000, 1000)
ltcg_in = st.sidebar.slider("Long-Term Capital Gains ($)", 0, 200000, 20000, 1000)
ss_in = st.sidebar.slider("Social Security Benefits ($)", 0, 100000, 15000, 500)
pretax_in = st.sidebar.slider("Pre-Tax Deductions (401k) ($)", 0, 60000, 0, 500)
muni_in = st.sidebar.slider("Tax-Exempt Muni Interest ($)", 0, 100000, 0, 1000)

st.sidebar.subheader("Deduction Selection")
fed_std_val = PARAMS[filing_status]["fed_std_deduction"]
if tp_65: fed_std_val += PARAMS[filing_status]["age_65_bump"]
if sp_65: fed_std_val += PARAMS[filing_status]["age_65_bump"]

nc_std_val = PARAMS[filing_status]["nc_std_deduction"]

fed_ded_mode = st.sidebar.radio("Federal Deduction", ["Standard", "Itemized"], horizontal=True)
fed_ded_val = fed_std_val if fed_ded_mode == "Standard" else st.sidebar.number_input("Federal Itemized ($)", 0, 200000, int(fed_std_val), 500)

nc_ded_mode = st.sidebar.radio("NC State Deduction", ["Standard", "Itemized"], horizontal=True)
nc_ded_val = nc_std_val if nc_ded_mode == "Standard" else st.sidebar.number_input("NC Itemized ($)", 0, 200000, int(nc_std_val), 500)

# ---------------------------------------------------------
# CALCULATIONS
# ---------------------------------------------------------
base = calculate_tax_scenario(wages_in, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, filing_status, tp_65, sp_65)

# +/- $1k Sliver Analysis
up_ord = calculate_tax_scenario(wages_in + 1000, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, filing_status, tp_65, sp_65)
dn_ord = calculate_tax_scenario(max(0, wages_in - 1000), ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, filing_status, tp_65, sp_65)
up_ord_cost = up_ord["total_outflows"] - base["total_outflows"]
dn_ord_save = base["total_outflows"] - dn_ord["total_outflows"]

up_ltcg = calculate_tax_scenario(wages_in, ltcg_in + 1000, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, filing_status, tp_65, sp_65)
dn_ltcg = calculate_tax_scenario(wages_in, max(0, ltcg_in - 1000), ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, filing_status, tp_65, sp_65)
up_ltcg_cost = up_ltcg["total_outflows"] - base["total_outflows"]
dn_ltcg_save = base["total_outflows"] - dn_ltcg["total_outflows"]

# ---------------------------------------------------------
# UI: DASHBOARD
# ---------------------------------------------------------
st.title(f"Year-End Tax & Medicare Cliff Planner ({filing_status})")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Federal Income Tax", f"${base['fed_ord_tax'] + base['fed_ltcg_tax']:,.0f}")
kpi2.metric("NC State Tax", f"${base['nc_tax']:,.0f}")
kpi3.metric("NIIT Surcharge (3.8%)", f"${base['niit_tax']:,.0f}")
kpi4.metric("Proj. 2028 IRMAA", f"${base['annual_irmaa']:,.0f}/yr")

st.divider()

# Stacking Chart
st.subheader("Income Stacking & Vulnerability Cliffs")
st.caption("Shows exactly where your taxable dollars sit relative to MAGI-based IRMAA and NIIT thresholds.")

blocks = []
current_x = 0.0

used_ded = min(base['fed_agi'], base['total_fed_deduction'])
if used_ded > 0:
    blocks.append({"Category": "Deductions", "Start": current_x, "End": current_x + used_ded, "Row": "1. Ordinary Income Base"})
    current_x += used_ded

for b in base['ord_bracket_amts']:
    blocks.append({"Category": f"Ordinary {int(b['rate']*100)}%", "Start": current_x, "End": current_x + b['amount'], "Row": "1. Ordinary Income Base"})
    current_x += b['amount']

for b in base['ltcg_bracket_amts']:
    blocks.append({"Category": f"LTCG {int(b['rate']*100)}%", "Start": current_x, "End": current_x + b['amount'], "Row": "2. Long-Term Capital Gains"})
    current_x += b['amount']

if muni_in > 0:
    blocks.append({"Category": "Tax-Exempt Muni", "Start": current_x, "End": current_x + muni_in, "Row": "3. Tax-Exempt Yield"})

df_blocks = pd.DataFrame(blocks)
bar_chart = alt.Chart(df_blocks).mark_bar(size=25, cornerRadius=2).encode(
    x=alt.X("Start:Q", title="Modified Adjusted Gross Income (MAGI)", axis=alt.Axis(format="$,.0f")),
    x2=alt.X2("End:Q"),
    y=alt.Y("Row:N", title="", axis=alt.Axis(labels=True, ticks=False)),
    color=alt.Color("Category:N", scale=alt.Scale(scheme="tableau20")),
    tooltip=["Category", alt.Tooltip("Start:Q", format="$,.0f"), alt.Tooltip("End:Q", format="$,.0f")]
)

rules_data = [{"Name": "NIIT (3.8%)", "Value": PARAMS[filing_status]["niit_threshold"]}]
for limit, _, name in PARAMS[filing_status]["irmaa_tiers"]:
    if limit != float('inf'):
        rules_data.append({"Name": f"IRMAA {name.split()[1]}", "Value": limit})

rule_chart = alt.Chart(pd.DataFrame(rules_data)).mark_rule(strokeDash=[4,4], color='red', size=2).encode(
    x="Value:Q",
    tooltip=["Name", alt.Tooltip("Value:Q", format="$,.0f")]
)

st.altair_chart((bar_chart + rule_chart).properties(height=160), use_container_width=True)

# Sliver Analysis
st.subheader("+$1,000 / -$1,000 Sliver Analysis")
c1, c2 = st.columns(2)
with c1:
    st.markdown("#### 📈 Realize +$1,000")
    st.markdown(f"- **Add $1k Ordinary:** Costs **${up_ord_cost:,.0f}** (`{(up_ord_cost/10.0):.1f}%` effective rate)")
    st.markdown(f"- **Add $1k LTCG:** Costs **${up_ltcg_cost:,.0f}** (`{(up_ltcg_cost/10.0):.1f}%` effective rate)")
with c2:
    st.markdown("#### 📉 Defer -$1,000")
    st.markdown(f"- **Reduce $1k Ordinary:** Saves **${dn_ord_save:,.0f}** (`{(dn_ord_save/10.0):.1f}%` effective rate)")
    st.markdown(f"- **Reduce $1k LTCG:** Saves **${dn_ltcg_save:,.0f}** (`{(dn_ltcg_save/10.0):.1f}%` effective rate)")

st.divider()

# Status Boxes
alert1, alert2 = st.columns(2)
with alert1:
    st.markdown("### Projected 2028 IRMAA")
    if base["annual_irmaa"] == 0:
        st.success(f"**{base['tier_name']}**\n\nCurrent MAGI: ${base['magi']:,.0f}. Headroom before Tier 1: ${base['headroom_irmaa']:,.0f}.")
    elif base["headroom_irmaa"] is not None:
        st.warning(f"**{base['tier_name']}**\n\nAnnual Surcharge: ${base['annual_irmaa']:,.0f}. Headroom before next cliff: ${base['headroom_irmaa']:,.0f}.")
    else:
        st.error(f"**{base['tier_name']}**\n\nMaximum bracket. Annual Surcharge: ${base['annual_irmaa']:,.0f}.")

with alert2:
    st.markdown("### Net Investment Income Tax")
    nl = PARAMS[filing_status]["niit_threshold"]
    if base["magi"] > nl and ltcg_in > 0:
        st.warning(f"**NIIT Active (3.8%)**\n\nMAGI of ${base['magi']:,.0f} exceeds limit. ${base['niit_subject']:,.0f} of investment income is penalized.")
    elif base["magi"] > nl:
        st.info(f"**NIIT Clear**\n\nMAGI exceeds limit, but there is $0 of investment income to penalize.")
    else:
        st.success(f"**NIIT Exempt**\n\nMAGI is ${base['magi']:,.0f}. Headroom before penalty: ${(nl - base['magi']):,.0f}.")

st.divider()

# Marginal Tax Curve
st.subheader("Interactive Marginal Tax Curve")
st.caption("Visualizes the exact cost to realize the *next* $1,000 of income across the entire spectrum. Spikes represent IRMAA cliffs or Social Security phase-ins.")

curve_axis = st.radio("Select sweep variable:", ["Ordinary Income (tIRA, Wages)", "Long-Term Capital Gains"], horizontal=True)

curve_data = []
test_range = range(0, 305000, 2000)

if "Ordinary" in curve_axis:
    for w in test_range:
        b_res = calculate_tax_scenario(w, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, filing_status, tp_65, sp_65)
        u_res = calculate_tax_scenario(w + 1000, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, filing_status, tp_65, sp_65)
        m_rate = ((u_res['total_outflows'] - b_res['total_outflows']) / 1000.0) * 100.0
        curve_data.append({"Income": w, "Marginal Rate (%)": m_rate})
    current_val = wages_in
else:
    for c in test_range:
        b_res = calculate_tax_scenario(wages_in, c, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, filing_status, tp_65, sp_65)
        u_res = calculate_tax_scenario(wages_in, c + 1000, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, filing_status, tp_65, sp_65)
        m_rate = ((u_res['total_outflows'] - b_res['total_outflows']) / 1000.0) * 100.0
        curve_data.append({"Income": c, "Marginal Rate (%)": m_rate})
    current_val = ltcg_in

df_curve = pd.DataFrame(curve_data)
line_chart = alt.Chart(df_curve).mark_line(interpolate='step-after', strokeWidth=3).encode(
    x=alt.X("Income:Q", title="Income Axis ($)", axis=alt.Axis(format="$,.0f")),
    y=alt.Y("Marginal Rate (%):Q", scale=alt.Scale(domain=[0, max(60, df_curve['Marginal Rate (%)'].max())], clamp=True)),
    tooltip=[alt.Tooltip("Income:Q", format="$,.0f"), alt.Tooltip("Marginal Rate (%):Q", format=".1f")]
)

current_marker = alt.Chart(pd.DataFrame({'x': [current_val]})).mark_rule(color='red', strokeDash=[4,4]).encode(x='x:Q')
st.altair_chart((line_chart + current_marker).properties(height=350), use_container_width=True)
