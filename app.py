```python
import streamlit as st
import pandas as pd
import altair as alt

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="2026 Tax & 2028 IRMAA Dashboard",
    page_icon="📊",
    layout="wide"
)

# ---------------------------------------------------------
# 1. INPUT CONTROLS (Sidebar)
# ---------------------------------------------------------
st.sidebar.title("Input Parameters")
st.sidebar.caption("Single Filer Assumptions (2026 Tax / 2028 IRMAA)")

# Primary Income Sources
wages = st.sidebar.slider(
    "Wages / Ordinary Income ($)",
    min_value=0,
    max_value=300000,
    value=120000,
    step=1000
)

ltcg = st.sidebar.slider(
    "Long-Term Capital Gains (LTCG) ($)",
    min_value=0,
    max_value=100000,
    value=20000,
    step=1000
)

ss_benefits = st.sidebar.slider(
    "Social Security Benefits ($)",
    min_value=0,
    max_value=50000,
    value=15000,
    step=500
)

pre_tax_deductions = st.sidebar.slider(
    "Pre-Tax Deductions (401k/HSA) ($)",
    min_value=0,
    max_value=35000,
    value=0,
    step=500
)

# Expandable Section: Deductions
with st.sidebar.expander("Deductions", expanded=False):
    fed_deduction_type = st.radio(
        "Federal Deduction Type",
        options=["Standard", "Itemized"],
        index=0
    )
    if fed_deduction_type == "Itemized":
        fed_itemized_total = st.number_input(
            "Federal Itemized Total ($)",
            min_value=0,
            max_value=100000,
            value=18000,
            step=500
        )
    else:
        fed_itemized_total = 0.0

    nc_deduction_type = st.radio(
        "NC State Deduction Type",
        options=["Standard", "Itemized"],
        index=0
    )
    if nc_deduction_type == "Itemized":
        nc_itemized_total = st.number_input(
            "NC Itemized Total ($)",
            min_value=0,
            max_value=100000,
            value=14000,
            step=500
        )
    else:
        nc_itemized_total = 0.0

# Expandable Section: Other Income & Adjustments
with st.sidebar.expander("Other Income & Adjustments", expanded=False):
    muni_interest = st.number_input(
        "Tax-Exempt Muni Bond Interest ($)",
        min_value=0,
        max_value=50000,
        value=0,
        step=500
    )
    nontaxable_cash = st.number_input(
        "Completely Nontaxable Income ($)",
        min_value=0,
        max_value=100000,
        value=0,
        step=1000,
        help="Roth distributions, gifts, inheritances, etc."
    )

# ---------------------------------------------------------
# 2. TAX LOGIC ENGINE (Backend)
# ---------------------------------------------------------
# Deductions Selection
fed_deduction = 16100.0 if fed_deduction_type == "Standard" else float(fed_itemized_total)
nc_deduction = 12750.0 if nc_deduction_type == "Standard" else float(nc_itemized_total)
NC_TAX_RATE = 0.0399

# Social Security Taxability Calculation
# Provisional Income = Wages + LTCG + Tax-Exempt Interest - PreTax + 50% of SS
provisional_income = wages + ltcg + muni_interest - pre_tax_deductions + (0.50 * ss_benefits)
if provisional_income > 34000.0:
    taxable_ss = 0.85 * ss_benefits
else:
    taxable_ss = 0.0

# Federal AGI & MAGI
fed_agi = max(0.0, wages + ltcg + taxable_ss - pre_tax_deductions)
magi = max(0.0, wages + ltcg + taxable_ss + muni_interest - pre_tax_deductions)

# Federal Ordinary Taxable Income
fed_ordinary_taxable = max(0.0, fed_agi - fed_deduction - ltcg)

# Federal Ordinary Income Tax Calculation (2026 Brackets)
ordinary_brackets = [
    (12400.0, 0.10),
    (50400.0, 0.12),
    (105700.0, 0.22),
    (201775.0, 0.24),
    (256125.0, 0.32),
    (566350.0, 0.35),
    (float('inf'), 0.37)
]

fed_ordinary_tax = 0.0
prev_bracket_limit = 0.0

for bracket_limit, rate in ordinary_brackets:
    if fed_ordinary_taxable > prev_bracket_limit:
        taxable_in_bracket = min(fed_ordinary_taxable, bracket_limit) - prev_bracket_limit
        fed_ordinary_tax += taxable_in_bracket * rate
        prev_bracket_limit = bracket_limit
    else:
        break

# Federal LTCG Tax Calculation (Stacked on top of ordinary income)
ltcg_0_limit = 49450.0
ltcg_15_limit = 545500.0

taxable_start = fed_ordinary_taxable
taxable_end = fed_ordinary_taxable + ltcg

taxable_ltcg_0 = max(0.0, min(taxable_end, ltcg_0_limit) - max(taxable_start, 0.0))
taxable_ltcg_15 = max(0.0, min(taxable_end, ltcg_15_limit) - max(taxable_start, ltcg_0_limit))
taxable_ltcg_20 = max(0.0, taxable_end - max(taxable_start, ltcg_15_limit))

fed_ltcg_tax = (taxable_ltcg_0 * 0.00) + (taxable_ltcg_15 * 0.15) + (taxable_ltcg_20 * 0.20)

# Net Investment Income Tax (NIIT) Logic
NIIT_THRESHOLD = 200000.0
if magi > NIIT_THRESHOLD and ltcg > 0:
    investment_income_subject_to_niit = min(float(ltcg), magi - NIIT_THRESHOLD)
    niit_tax = investment_income_subject_to_niit * 0.038
else:
    investment_income_subject_to_niit = 0.0
    niit_tax = 0.0

total_fed_tax = fed_ordinary_tax + fed_ltcg_tax + niit_tax

# NC State Tax Calculation (SS & Muni interest exempt)
nc_taxable_income = max(0.0, wages + ltcg - pre_tax_deductions - nc_deduction)
nc_state_tax = nc_taxable_income * NC_TAX_RATE

# ---------------------------------------------------------
# 3. IRMAA TIER LOGIC (2028 Projected using MAGI)
# ---------------------------------------------------------
irmaa_tier_name = ""
monthly_surcharge = 0.0
headroom_to_next = None
status_level = "success"

if magi <= 114000.0:
    irmaa_tier_name = "Tier 0 (Standard - No Surcharge)"
    monthly_surcharge = 0.0
    headroom_to_next = 114000.0 - magi
    status_level = "success"
elif magi <= 143000.0:
    irmaa_tier_name = "Tier 1 Surcharge"
    monthly_surcharge = 97.50
    headroom_to_next = 143000.0 - magi
    status_level = "warning"
elif magi <= 179000.0:
    irmaa_tier_name = "Tier 2 Surcharge"
    monthly_surcharge = 240.40
    headroom_to_next = 179000.0 - magi
    status_level = "warning"
else:
    irmaa_tier_name = "Tier 3 Surcharge (Maximum)"
    monthly_surcharge = 385.00
    headroom_to_next = None
    status_level = "error"

annual_irmaa = monthly_surcharge * 12.0
total_gross_income = wages + ltcg + ss_benefits + muni_interest + nontaxable_cash
take_home_pay = (
    total_gross_income
    - (total_fed_tax + nc_state_tax + annual_irmaa + pre_tax_deductions)
)

# ---------------------------------------------------------
# 4. UI & VISUALIZATION DASHBOARD
# ---------------------------------------------------------
st.title("2026 Federal & NC Tax + 2028 IRMAA Dashboard")
st.write("Real-time tax liability, NIIT surcharge, Medicare cliff thresholds, and true take-home liquidity for Single Filers.")

# Top Metrics Row
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(
    label="Federal Tax Liability",
    value=f"${total_fed_tax:,.0f}",
    help=f"Ordinary: ${fed_ordinary_tax:,.0f} | LTCG: ${fed_ltcg_tax:,.0f} | NIIT: ${niit_tax:,.0f}"
)
kpi2.metric(
    label="NC State Tax",
    value=f"${nc_state_tax:,.0f}",
    help=f"Flat {NC_TAX_RATE*100:.2f}% on NC Taxable Income"
)
kpi3.metric(
    label="2028 IRMAA Surcharge",
    value=f"${annual_irmaa:,.0f}/yr",
    help=f"${monthly_surcharge:,.2f}/month (Part B + Part D based on MAGI)"
)
kpi4.metric(
    label="True Net Cash Flow",
    value=f"${take_home_pay:,.0f}",
    help="Total Gross & Nontaxable Receipts minus all taxes, pre-tax savings, and IRMAA surcharges"
)

st.divider()

# IRMAA & NIIT Warning/Status Alerts
alert_col1, alert_col2 = st.columns(2)

with alert_col1:
    if status_level == "success":
        st.success(
            f"**IRMAA Status:** Current MAGI is **${magi:,.0f}** ({irmaa_tier_name}). "
            f"You have **${headroom_to_next:,.0f}** in headroom before triggering Tier 1."
        )
    elif status_level == "warning":
        st.warning(
            f"**IRMAA Warning:** Current MAGI is **${magi:,.0f}** ({irmaa_tier_name} - ${annual_irmaa:,.0f}/year). "
            f"You are **${headroom_to_next:,.0f}** away from the next IRMAA surcharge cliff."
        )
    else:
        st.error(
            f"**IRMAA Alert:** Current MAGI is **${magi:,.0f}** ({irmaa_tier_name} - ${annual_irmaa:,.0f}/year). "
            f"You are in the highest IRMAA bracket."
        )

with alert_col2:
    if magi > NIIT_THRESHOLD and ltcg > 0:
        st.warning(
            f"**NIIT Active:** MAGI exceeds $200,000 threshold by **${(magi - NIIT_THRESHOLD):,.0f}**. "
            f"A **3.8% surcharge** (${niit_tax:,.0f}) is applied to **${investment_income_subject_to_niit:,.0f}** of net investment gains."
        )
    elif magi > NIIT_THRESHOLD:
        st.info(f"**NIIT Inactive:** MAGI (**${magi:,.0f}**) exceeds $200,000, but there is $0 of net investment income subject to tax.")
    else:
        st.success(f"**NIIT Clear:** MAGI is **${magi:,.0f}**, leaving **${(NIIT_THRESHOLD - magi):,.0f}** in headroom before the 3.8% NIIT applies.")

st.divider()

# Visual Breakdown Layout
col_chart, col_details = st.columns([3, 2])

with col_chart:
    st.subheader("Cash Flow & Tax Distribution")
    
    chart_data = pd.DataFrame([
        {"Category": "Net Take-Home Cash", "Amount": max(0.0, take_home_pay), "Group": "Distribution"},
        {"Category": "Pre-tax Savings", "Amount": pre_tax_deductions, "Group": "Distribution"},
        {"Category": "Federal Ordinary Tax", "Amount": fed_ordinary_tax, "Group": "Distribution"},
        {"Category": "Federal LTCG Tax", "Amount": fed_ltcg_tax, "Group": "Distribution"},
        {"Category": "NIIT Surcharge (3.8%)", "Amount": niit_tax, "Group": "Distribution"},
        {"Category": "NC State Tax", "Amount": nc_state_tax, "Group": "Distribution"},
        {"Category": "IRMAA Surcharge", "Amount": annual_irmaa, "Group": "Distribution"}
    ])
    
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Amount:Q", title="Total Inflow Allocation ($)", axis=alt.Axis(format="$,.0f")),
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
                        "IRMAA Surcharge"
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
            "Federal Deduction Applied",
            "NC Deduction Applied",
            "Provisional Income (SS)",
            "Federal AGI",
            "Federal MAGI (IRMAA/NIIT)",
            "Fed Ordinary Taxable Income",
            "NC Taxable Income",
            "NIIT Subject Amount (3.8%)"
        ],
        "Value": [
            f"${total_gross_income:,.0f}",
            f"${fed_deduction:,.0f} ({fed_deduction_type})",
            f"${nc_deduction:,.0f} ({nc_deduction_type})",
            f"${provisional_income:,.0f}",
            f"${fed_agi:,.0f}",
            f"${magi:,.0f}",
            f"${fed_ordinary_taxable:,.0f}",
            f"${nc_taxable_income:,.0f}",
            f"${investment_income_subject_to_niit:,.0f}"
        ]
    })
    st.dataframe(summary_df, hide_index=True, use_container_width=True)

```
