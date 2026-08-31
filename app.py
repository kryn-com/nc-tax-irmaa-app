import streamlit as st
import pandas as pd
import altair as alt

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="2026 Federal & NC Tax + 2028 IRMAA Dashboard",
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
        "ss_thresh_1": 25000.0,
        "ss_thresh_2": 34000.0,
        "ord_brackets": [
            (12400.0, 0.10),
            (50400.0, 0.12),
            (105700.0, 0.22),
            (201775.0, 0.24),
            (256125.0, 0.32),
            (566350.0, 0.35),
            (float('inf'), 0.37)
        ],
        "ltcg_brackets": [
            (49450.0, 0.00),
            (545500.0, 0.15),
            (float('inf'), 0.20)
        ],
        "niit_threshold": 200000.0,
        "irmaa_tiers": [
            (114000.0, 0.0, "Tier 0 (Standard - No Surcharge)"),
            (143000.0, 97.50, "Tier 1 Surcharge"),
            (179000.0, 240.40, "Tier 2 Surcharge"),
            (float('inf'), 385.00, "Tier 3 Surcharge (Maximum)")
        ]
    },
    "MFJ": {
        "fed_std_deduction": 32200.0,
        "nc_std_deduction": 25500.0,
        "ss_thresh_1": 32000.0,
        "ss_thresh_2": 44000.0,
        "ord_brackets": [
            (24800.0, 0.10),
            (100800.0, 0.12),
            (211400.0, 0.22),
            (403550.0, 0.24),
            (512250.0, 0.32),
            (732600.0, 0.35),
            (float('inf'), 0.37)
        ],
        "ltcg_brackets": [
            (98900.0, 0.00),
            (613600.0, 0.15),
            (float('inf'), 0.20)
        ],
        "niit_threshold": 250000.0,
        "irmaa_tiers": [
            (228000.0, 0.0 * 2, "Tier 0 (Standard - No Surcharge)"),
            (286000.0, 97.50 * 2, "Tier 1 Surcharge (Combined 2x)"),
            (358000.0, 240.40 * 2, "Tier 2 Surcharge (Combined 2x)"),
            (float('inf'), 385.00 * 2, "Tier 3 Surcharge (Maximum Combined 2x)")
        ]
    }
}
NC_TAX_RATE = 0.0399


def calculate_tax_scenario(wages, ltcg, ss, pretax, muni, nontaxable, fed_ded, nc_ded, status):
    """Accurately calculates federal, state, NIIT, and projected 2028 IRMAA liability."""
    p = PARAMS[status]
    
    # 1. Social Security Taxability (IRS 50% / 85% two-tier formula)
    prov_income = wages + ltcg + muni - pretax + (0.50 * ss)
    t1 = p["ss_thresh_1"]
    t2 = p["ss_thresh_2"]
    
    if prov_income <= t1:
        taxable_ss = 0.0
    elif prov_income <= t2:
        taxable_ss = min(0.50 * ss, 0.50 * (prov_income - t1))
    else:
        taxable_ss = min(0.85 * ss, (0.50 * min(ss, t2 - t1)) + 0.85 * (prov_income - t2))
    
    # 2. AGI & MAGI
    fed_agi = max(0.0, wages + ltcg + taxable_ss - pretax)
    magi = max(0.0, fed_agi + muni)
    
    # 3. Deduction Stacking (Deductions offset Ordinary income first, then excess offsets LTCG)
    total_taxable_income = max(0.0, fed_agi - fed_ded)
    ordinary_gross_in_agi = max(0.0, fed_agi - ltcg)
    
    # Ordinary taxable is min of total taxable and ordinary AGI
    fed_ord_taxable = min(total_taxable_income, max(0.0, ordinary_gross_in_agi - fed_ded))
    # Remaining taxable is LTCG
    fed_ltcg_taxable = total_taxable_income - fed_ord_taxable
    
    # 4. Federal Ordinary Tax
    fed_ord_tax = 0.0
    prev_limit = 0.0
    current_ord_bracket_rate = 0.10
    next_ord_bracket_limit = p["ord_brackets"][0][0]
    
    for limit, rate in p["ord_brackets"]:
        if fed_ord_taxable > prev_limit:
            taxable_chunk = min(fed_ord_taxable, limit) - prev_limit
            fed_ord_tax += taxable_chunk * rate
            current_ord_bracket_rate = rate
            prev_limit = limit
            next_ord_bracket_limit = limit
        else:
            next_ord_bracket_limit = limit
            break
            
    # 5. Federal LTCG Tax (Stacked above ordinary taxable income)
    fed_ltcg_tax = 0.0
    start_stack = fed_ord_taxable
    end_stack = fed_ord_taxable + fed_ltcg_taxable
    
    ltcg_b = p["ltcg_brackets"]
    # 0% Bracket
    t_0 = max(0.0, min(end_stack, ltcg_b[0][0]) - max(start_stack, 0.0))
    # 15% Bracket
    t_15 = max(0.0, min(end_stack, ltcg_b[1][0]) - max(start_stack, ltcg_b[0][0]))
    # 20% Bracket
    t_20 = max(0.0, end_stack - max(start_stack, ltcg_b[1][0]))
    
    fed_ltcg_tax = (t_0 * ltcg_b[0][1]) + (t_15 * ltcg_b[1][1]) + (t_20 * ltcg_b[2][1])
    
    # 6. Net Investment Income Tax (NIIT)
    niit_thresh = p["niit_threshold"]
    if magi > niit_thresh and ltcg > 0:
        niit_subject = min(float(ltcg), magi - niit_thresh)
        niit_tax = niit_subject * 0.038
    else:
        niit_subject = 0.0
        niit_tax = 0.0
        
    total_fed_tax = fed_ord_tax + fed_ltcg_tax + niit_tax
    
    # 7. NC State Tax (SS and muni interest 100% exempt)
    nc_taxable = max(0.0, wages + ltcg - pretax - nc_ded)
    nc_tax = nc_taxable * NC_TAX_RATE
    
    # 8. Projected 2028 IRMAA (Evaluated from 2026 MAGI)
    monthly_irmaa = 0.0
    tier_name = ""
    headroom_irmaa = None
    
    for limit, surcharge, name in p["irmaa_tiers"]:
        if magi <= limit:
            tier_name = name
            monthly_irmaa = surcharge
            headroom_irmaa = limit - magi if limit != float('inf') else None
            break
            
    annual_irmaa = monthly_irmaa * 12.0
    total_gross = wages + ltcg + ss + muni + nontaxable
    total_outflows = total_fed_tax + nc_tax + annual_irmaa + pretax
    take_home = total_gross - total_outflows
    
    return {
        "fed_agi": fed_agi,
        "magi": magi,
        "taxable_ss": taxable_ss,
        "prov_income": prov_income,
        "fed_ord_taxable": fed_ord_taxable,
        "fed_ltcg_taxable": fed_ltcg_taxable,
        "fed_ord_tax": fed_ord_tax,
        "fed_ltcg_tax": fed_ltcg_tax,
        "niit_tax": niit_tax,
        "niit_subject": niit_subject,
        "total_fed_tax": total_fed_tax,
        "nc_taxable": nc_taxable,
        "nc_tax": nc_tax,
        "monthly_irmaa": monthly_irmaa,
        "annual_irmaa": annual_irmaa,
        "tier_name": tier_name,
        "headroom_irmaa": headroom_irmaa,
        "total_gross": total_gross,
        "total_outflows": total_outflows,
        "take_home": take_home,
        "current_ord_rate": current_ord_bracket_rate,
        "headroom_ord_bracket": max(0.0, next_ord_bracket_limit - fed_ord_taxable) if next_ord_bracket_limit != float('inf') else 0.0
    }


# ---------------------------------------------------------
# 1. SIDEBAR: INPUT CONTROLS
# ---------------------------------------------------------
st.sidebar.title("Tax Engine Parameters")

filing_status = st.sidebar.radio(
    "Filing Status",
    options=["Single", "MFJ"],
    index=0,
    horizontal=True
)

st.sidebar.subheader("Income Sources")
wages_in = st.sidebar.slider("Wages / Ordinary Income ($)", 0, 400000, 120000, 1000)
ltcg_in = st.sidebar.slider("Long-Term Capital Gains ($)", 0, 200000, 20000, 1000)
ss_in = st.sidebar.slider("Social Security Benefits ($)", 0, 100000, 15000, 500)
pretax_in = st.sidebar.slider("Pre-Tax Deductions (401k/HSA) ($)", 0, 60000, 0, 500)
muni_in = st.sidebar.slider("Tax-Exempt Muni Bond Interest ($)", 0, 100000, 0, 1000)
nontaxable_in = st.sidebar.slider("Completely Nontaxable Receipts ($)", 0, 150000, 0, 1000)

st.sidebar.subheader("Deduction Selection")
fed_std_val = PARAMS[filing_status]["fed_std_deduction"]
nc_std_val = PARAMS[filing_status]["nc_std_deduction"]

fed_ded_mode = st.sidebar.radio("Federal Deduction", ["Standard", "Itemized"], index=0, horizontal=True)
fed_ded_val = fed_std_val if fed_ded_mode == "Standard" else st.sidebar.number_input(
    "Federal Itemized Total ($)", 0, 200000, int(fed_std_val), 500
)

nc_ded_mode = st.sidebar.radio("NC State Deduction", ["Standard", "Itemized"], index=0, horizontal=True)
nc_ded_val = nc_std_val if nc_ded_mode == "Standard" else st.sidebar.number_input(
    "NC Itemized Total ($)", 0, 200000, int(nc_std_val), 500
)

# ---------------------------------------------------------
# 2. RUN CALCULATIONS & MARGINAL SENSITIVITY
# ---------------------------------------------------------
base = calculate_tax_scenario(
    wages_in, ltcg_in, ss_in, pretax_in, muni_in, nontaxable_in,
    fed_ded_val, nc_ded_val, filing_status
)

# Marginal +$1,000 Ordinary Income
delta_ord = calculate_tax_scenario(
    wages_in + 1000, ltcg_in, ss_in, pretax_in, muni_in, nontaxable_in,
    fed_ded_val, nc_ded_val, filing_status
)
fed_ord_diff = delta_ord["total_fed_tax"] - base["total_fed_tax"]
nc_ord_diff = delta_ord["nc_tax"] - base["nc_tax"]
irmaa_ord_diff = delta_ord["annual_irmaa"] - base["annual_irmaa"]
ss_ord_diff = delta_ord["taxable_ss"] - base["taxable_ss"]
total_ord_diff = (delta_ord["total_outflows"] - base["total_outflows"])
marginal_ord_pct = (total_ord_diff / 1000.0) * 100.0

# Marginal +$1,000 LTCG Income
delta_ltcg = calculate_tax_scenario(
    wages_in, ltcg_in + 1000, ss_in, pretax_in, muni_in, nontaxable_in,
    fed_ded_val, nc_ded_val, filing_status
)
fed_ltcg_diff = delta_ltcg["total_fed_tax"] - base["total_fed_tax"]
nc_ltcg_diff = delta_ltcg["nc_tax"] - base["nc_tax"]
irmaa_ltcg_diff = delta_ltcg["annual_irmaa"] - base["annual_irmaa"]
ss_ltcg_diff = delta_ltcg["taxable_ss"] - base["taxable_ss"]
total_ltcg_diff = (delta_ltcg["total_outflows"] - base["total_outflows"])
marginal_ltcg_pct = (total_ltcg_diff / 1000.0) * 100.0

# Overall Effective Tax Rate
total_taxes_and_surcharges = base["total_fed_tax"] + base["nc_tax"] + base["annual_irmaa"]
effective_tax_rate = (total_taxes_and_surcharges / base["total_gross"] * 100.0) if base["total_gross"] > 0 else 0.0

# ---------------------------------------------------------
# 3. UI DASHBOARD DISPLAY
# ---------------------------------------------------------
st.title(f"2026 Federal & NC Tax + Projected 2028 IRMAA Dashboard ({filing_status})")
st.caption("Interactive cash-flow architecture, dynamic marginal sensitivity modeling, and multi-tier cliff tracker.")

# Top Metrics Row
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Federal Total Tax", f"${base['total_fed_tax']:,.0f}", help=f"Ordinary: ${base['fed_ord_tax']:,.0f} | LTCG: ${base['fed_ltcg_tax']:,.0f} | NIIT: ${base['niit_tax']:,.0f}")
kpi2.metric("NC State Tax", f"${base['nc_tax']:,.0f}", help=f"Flat {NC_TAX_RATE*100:.2f}% on NC Taxable Income")
kpi3.metric("Proj. 2028 IRMAA", f"${base['annual_irmaa']:,.0f}/yr", help=f"${base['monthly_irmaa']:,.2f}/mo surcharge based on 2026 MAGI")
kpi4.metric("Effective Outflow Rate", f"{effective_tax_rate:.1f}%", help="Taxes + IRMAA Surcharges divided by Total Inflows")
kpi5.metric("Net Take-Home Cash", f"${base['take_home']:,.0f}", help="Total receipts minus all taxes, pre-tax savings, and IRMAA")

st.divider()

# Marginal Tax & $1,000 Stress Test Row
st.subheader("Marginal Rate & +$1,000 Income Sensitivity Engine")
col_sens1, col_sens2 = st.columns(2)

with col_sens1:
    st.markdown("#### Impact of +$1,000 Ordinary Income")
    st.markdown(f"**Effective Marginal Drag: `{marginal_ord_pct:.1f}%`** (Cost: **${total_ord_diff:,.2f}** per $1k)")
    
    st.write(f"- **Federal Tax Delta:** `${fed_ord_diff:,.2f}` (Base Bracket: `{base['current_ord_rate']*100:.0f}%`)")
    st.write(f"- **NC State Tax Delta:** `${nc_ord_diff:,.2f}`")
    st.write(f"- **Projected 2028 IRMAA Surcharge Delta:** `${irmaa_ord_diff:,.2f}`")
    if ss_ord_diff > 0:
        st.write(f"- ⚠️ **SS Taxability Bump:** Triggers `${ss_ord_diff:,.2f}` additional taxable Social Security")
    st.caption(f"Headroom before crossing to next higher ordinary bracket: **${base['headroom_ord_bracket']:,.0f}**")

with col_sens2:
    st.markdown("#### Impact of +$1,000 Long-Term Capital Gains")
    st.markdown(f"**Effective Marginal Drag: `{marginal_ltcg_pct:.1f}%`** (Cost: **${total_ltcg_diff:,.2f}** per $1k)")
    
    st.write(f"- **Federal LTCG / NIIT Tax Delta:** `${fed_ltcg_diff:,.2f}`")
    st.write(f"- **NC State Tax Delta:** `${nc_ltcg_diff:,.2f}`")
    st.write(f"- **Projected 2028 IRMAA Surcharge Delta:** `${irmaa_ltcg_diff:,.2f}`")
    if ss_ltcg_diff > 0:
        st.write(f"- ⚠️ **SS Taxability Bump:** Triggers `${ss_ltcg_diff:,.2f}` additional taxable Social Security")
    
    niit_headroom = max(0.0, PARAMS[filing_status]["niit_threshold"] - base["magi"])
    st.caption(f"Headroom before triggering 3.8% NIIT threshold: **${niit_headroom:,.0f}**")

st.divider()

# IRMAA & NIIT Status Badges
b1, b2 = st.columns(2)
with b1:
    st.markdown("#### Projected 2028 IRMAA Cliff Status")
    if base["annual_irmaa"] == 0:
        st.success(f"**{base['tier_name']}**: Current MAGI is **${base['magi']:,.0f}**. You have **${base['headroom_irmaa']:,.0f}** in headroom before triggering Tier 1.")
    elif base["headroom_irmaa"] is not None:
        st.warning(f"**{base['tier_name']}**: Annual surcharge is **${base['annual_irmaa']:,.0f}**. You are **${base['headroom_irmaa']:,.0f}** away from the next higher IRMAA cliff.")
    else:
        st.error(f"**{base['tier_name']}**: In top IRMAA tier with annual surcharge of **${base['annual_irmaa']:,.0f}**.")

with b2:
    st.markdown("#### Net Investment Income Tax (NIIT)")
    if base["magi"] > PARAMS[filing_status]["niit_threshold"] and ltcg_in > 0:
        st.warning(f"**NIIT Active (3.8%)**: MAGI of **${base['magi']:,.0f}** exceeds the ${PARAMS[filing_status]['niit_threshold']:,.0f} threshold. **${base['niit_subject']:,.0f}** of LTCG is subject to 3.8% NIIT (${base['niit_tax']:,.0f}).")
    elif base["magi"] > PARAMS[filing_status]["niit_threshold"]:
        st.info(f"**NIIT Clear ($0 LTCG)**: MAGI exceeds threshold, but no investment gains are present.")
    else:
        st.success(f"**NIIT Exempt**: MAGI is **${base['magi']:,.0f}**, leaving **${(PARAMS[filing_status]['niit_threshold'] - base['magi']):,.0f}** in headroom before NIIT applies.")

st.divider()

# Visual Breakdown Layout
col_chart, col_details = st.columns([3, 2])

with col_chart:
    st.subheader("Inflow & Outflow Allocation")
    
    chart_data = pd.DataFrame([
        {"Category": "Net Take-Home Cash", "Amount": max(0.0, base["take_home"]), "Group": "Distribution"},
        {"Category": "Pre-tax Savings", "Amount": pretax_in, "Group": "Distribution"},
        {"Category": "Federal Ordinary Tax", "Amount": base["fed_ord_tax"], "Group": "Distribution"},
        {"Category": "Federal LTCG Tax", "Amount": base["fed_ltcg_tax"], "Group": "Distribution"},
        {"Category": "NIIT Surcharge (3.8%)", "Amount": base["niit_tax"], "Group": "Distribution"},
        {"Category": "NC State Tax", "Amount": base["nc_tax"], "Group": "Distribution"},
        {"Category": "Proj. 2028 IRMAA Surcharge", "Amount": base["annual_irmaa"], "Group": "Distribution"}
    ])
    
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Amount:Q", title="Total Allocation ($)", axis=alt.Axis(format="$,.0f")),
            y=alt.Y("Group:N", title="", axis=alt.Axis(labels=False, ticks=False)),
            color=alt.Color(
                "Category:N",
                scale=alt.Scale(
                    domain=[
                        "Net Take-Home Cash",
                        "Pre-tax Savings",
                        "Federal Ordinary Tax",
                        "Federal LTCG Tax",
                        "NIIT Surcharge (3.8%)",
                        "NC State Tax",
                        "Proj. 2028 IRMAA Surcharge"
                    ],
                    range=["#2ca02c", "#1f77b4", "#ff7f0e", "#ffbb78", "#e377c2", "#d62728", "#9467bd"]
                ),
                legend=alt.Legend(orient="bottom", title=None)
            ),
            tooltip=[
                alt.Tooltip("Category:N", title="Category"),
                alt.Tooltip("Amount:Q", title="Amount", format="$,.2f")
            ]
        )
        .properties(height=200)
    )
    st.altair_chart(chart, use_container_width=True)

with col_details:
    st.subheader("Tax Accounting Breakdown")
    summary_df = pd.DataFrame({
        "Metric": [
            "Total Inflows (Gross + Nontaxable)",
            "Provisional Income (SS)",
            "Taxable Social Security",
            "Federal AGI",
            "Federal MAGI (IRMAA/NIIT)",
            "Federal Deduction Applied",
            "Fed Ordinary Taxable Income",
            "Fed LTCG Taxable Income",
            "NC Taxable Income"
        ],
        "Value": [
            f"${base['total_gross']:,.0f}",
            f"${base['prov_income']:,.0f}",
            f"${base['taxable_ss']:,.0f}",
            f"${base['fed_agi']:,.0f}",
            f"${base['magi']:,.0f}",
            f"${fed_ded_val:,.0f} ({fed_ded_mode})",
            f"${base['fed_ord_taxable']:,.0f}",
            f"${base['fed_ltcg_taxable']:,.0f}",
            f"${base['nc_taxable']:,.0f}"
        ]
    })
    st.dataframe(summary_df, hide_index=True, use_container_width=True)
