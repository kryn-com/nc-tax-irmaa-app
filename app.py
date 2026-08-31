import streamlit as st
import pandas as pd
import altair as alt

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

def calculate_tax_scenario(wages, ltcg, ss, pretax, muni, fed_ded_base, nc_ded_base, nc_adj, status, tp_65, sp_65):
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
    
    # 3. OBA Senior Bonus Deduction
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
    
    # 6. Federal LTCG Brackets
    fed_ltcg_tax = 0.0
    
    # 7. Net Investment Income Tax
    niit_tax = 0.0
    niit_subject = 0.0
    if magi > p["niit_threshold"] and ltcg > 0:
        niit_subject = min(float(ltcg), magi - p["niit_threshold"])
        niit_tax = niit_subject * 0.038
        
    # Calculate Ordinary Tax
    prev_limit = 0.0
    for limit, rate in p["ord_brackets"]:
        if fed_ord_taxable > prev_limit:
            chunk = min(fed_ord_taxable, limit) - prev_limit
            fed_ord_tax += chunk * rate
            prev_limit = limit
        else:
            break
            
    # Calculate LTCG Tax
    start_stack = fed_ord_taxable
    end_stack = fed_ord_taxable + fed_ltcg_taxable
    ltcg_b = p["ltcg_brackets"]
    t_0 = max(0.0, min(end_stack, ltcg_b[0][0]) - max(start_stack, 0.0))
    t_15 = max(0.0, min(end_stack, ltcg_b[1][0]) - max(start_stack, ltcg_b[0][0]))
    t_20 = max(0.0, end_stack - max(start_stack, ltcg_b[1][0]))
    fed_ltcg_tax = (t_0 * ltcg_b[0][1]) + (t_15 * ltcg_b[1][1]) + (t_20 * ltcg_b[2][1])
    
    total_fed_tax = fed_ord_tax + fed_ltcg_tax + niit_tax
    
    # 8. NC State Tax
    nc_taxable = max(0.0, wages + ltcg - pretax - nc_ded_base + nc_adj)
    nc_tax = nc_taxable * NC_TAX_RATE
    
    # 9. Projected IRMAA
    tier_name = ""
    monthly_irmaa = 0.0
    headroom_irmaa = None
    depth_irmaa = 0.0
    previous_limit = 0.0
    
    for limit, surcharge, name in p["irmaa_tiers"]:
        if magi <= limit:
            tier_name = name
            monthly_irmaa = surcharge
            headroom_irmaa = limit - magi if limit != float('inf') else None
            depth_irmaa = magi - previous_limit
            break
        previous_limit = limit
            
    annual_irmaa = monthly_irmaa * 12.0
    total_outflows = total_fed_tax + nc_tax + annual_irmaa
    
    return {
        "fed_agi": fed_agi, "magi": magi, "taxable_ss": taxable_ss,
        "total_fed_deduction": total_fed_deduction,
        "fed_ord_taxable": fed_ord_taxable, "fed_ltcg_taxable": fed_ltcg_taxable,
        "fed_ord_tax": fed_ord_tax, "fed_ltcg_tax": fed_ltcg_tax,
        "niit_tax": niit_tax, "niit_subject": niit_subject,
        "nc_tax": nc_tax,
        "annual_irmaa": annual_irmaa, "tier_name": tier_name, 
        "headroom_irmaa": headroom_irmaa, "depth_irmaa": depth_irmaa,
        "total_outflows": total_outflows
    }

def format_breakdown(base, new, is_up=True):
    """Helper to generate the specific tax cost/savings breakdown string."""
    sign = 1 if is_up else -1
    dfed = sign * (new["fed_ord_tax"] + new["fed_ltcg_tax"] - base["fed_ord_tax"] - base["fed_ltcg_tax"])
    dnc = sign * (new["nc_tax"] - base["nc_tax"])
    dniit = sign * (new["niit_tax"] - base["niit_tax"])
    dirmaa = sign * (new["annual_irmaa"] - base["annual_irmaa"])
    dss = sign * (new["taxable_ss"] - base["taxable_ss"])
    
    parts = []
    if dfed != 0: parts.append(f"Fed: ${dfed:,.0f}")
    if dnc != 0: parts.append(f"NC: ${dnc:,.0f}")
    if dniit != 0: parts.append(f"NIIT: ${dniit:,.0f}")
    if dirmaa != 0: parts.append(f"Medicare: ${dirmaa:,.0f}")
    if dss != 0: parts.append(f"SS Bump: +${dss:,.0f}")
    
    return " | ".join(parts) if parts else "No tax impact"


# ---------------------------------------------------------
# UI: SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.title("2026 Year-End Planner")

filing_status = st.sidebar.radio("Filing Status", ["Single", "MFJ"], horizontal=True)

st.sidebar.subheader("Taxpayer Profile")
col_tp, col_sp = st.sidebar.columns(2)
with col_tp: tp_65 = st.checkbox("TP 65+", value=False)
with col_sp: sp_65 = st.checkbox("SP 65+", value=False) if filing_status == "MFJ" else False

st.sidebar.subheader("Income Sources")
wages_in = st.sidebar.number_input("Ordinary Income / tIRA ($)", min_value=0, max_value=1000000, value=120000, step=1000)
ltcg_in = st.sidebar.number_input("Long-Term Capital Gains ($)", min_value=0, max_value=1000000, value=20000, step=1000)
ss_in = st.sidebar.number_input("Social Security Benefits ($)", min_value=0, max_value=150000, value=15000, step=500)
pretax_in = st.sidebar.number_input("Pre-Tax Deductions (401k) ($)", min_value=0, max_value=150000, value=0, step=500)
muni_in = st.sidebar.number_input("Tax-Exempt Muni Interest ($)", min_value=0, max_value=150000, value=0, step=1000)

st.sidebar.subheader("Deductions & State Adjustments")
fed_std_val = PARAMS[filing_status]["fed_std_deduction"] + (PARAMS[filing_status]["age_65_bump"] if tp_65 else 0) + (PARAMS[filing_status]["age_65_bump"] if sp_65 else 0)
nc_std_val = PARAMS[filing_status]["nc_std_deduction"]

fed_ded_mode = st.sidebar.radio("Federal Deduction", ["Standard", "Itemized"], horizontal=True)
fed_ded_val = fed_std_val if fed_ded_mode == "Standard" else st.sidebar.number_input("Federal Itemized ($)", 0, 300000, int(fed_std_val), 1000)

nc_ded_mode = st.sidebar.radio("NC State Deduction", ["Standard", "Itemized"], horizontal=True)
nc_ded_val = nc_std_val if nc_ded_mode == "Standard" else st.sidebar.number_input("NC Itemized ($)", 0, 300000, int(nc_std_val), 1000)

nc_adj_in = st.sidebar.number_input("NC Income Adjustments (+/-) ($)", value=0, step=500, help="Enter net adjustments for state taxation differences (e.g., subtract U.S. Treasury interest, add out-of-state munis).")

# ---------------------------------------------------------
# CALCULATIONS
# ---------------------------------------------------------
base = calculate_tax_scenario(wages_in, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)

up_ord = calculate_tax_scenario(wages_in + 1000, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
dn_ord = calculate_tax_scenario(max(0, wages_in - 1000), ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
up_ord_cost = up_ord["total_outflows"] - base["total_outflows"]
dn_ord_save = base["total_outflows"] - dn_ord["total_outflows"]

up_ltcg = calculate_tax_scenario(wages_in, ltcg_in + 1000, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
dn_ltcg = calculate_tax_scenario(wages_in, max(0, ltcg_in - 1000), ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
up_ltcg_cost = up_ltcg["total_outflows"] - base["total_outflows"]
dn_ltcg_save = base["total_outflows"] - dn_ltcg["total_outflows"]

# ---------------------------------------------------------
# UI: DASHBOARD
# ---------------------------------------------------------
st.title(f"Year-End Tax & Medicare Cliff Planner ({filing_status})")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Federal Income Tax", f"${base['fed_ord_tax'] + base['fed_ltcg_tax']:,.0f}")
kpi2.metric("NC State Tax", f"${base['nc_tax']:,.0f}")
kpi3.metric("Net Investment Income Tax", f"${base['niit_tax']:,.0f}")
kpi4.metric("Projected 2028 Medicare Surcharge", f"${base['annual_irmaa']:,.0f}/yr")

st.divider()

# ---------------------------------------------------------
# DYNAMIC 3-ROW MAGI STACKING CHART
# ---------------------------------------------------------
st.subheader("Income Stacking & Vulnerability Cliffs")
st.caption("Maps exact dollar placement across absolute MAGI boundaries. Empty outlines indicate remaining room in your current marginal bracket.")

blocks = []
p = PARAMS[filing_status]

# 1. Deductions Row (0 to used_ded)
used_ded = min(base['fed_agi'], base['total_fed_deduction'])
if used_ded > 0:
    blocks.append({"Category": "Deductions", "Start": 0, "End": used_ded, "Row": "1. Deductions", "Type": "Actual", "RateLabel": "0%"})

# 2. Ordinary Taxable Row (Starts at used_ded)
curr_magi = used_ded
prev_limit = 0.0
for limit, rate in p["ord_brackets"]:
    bracket_min = prev_limit
    bracket_max = limit
    
    if base['fed_ord_taxable'] > bracket_min:
        filled = min(base['fed_ord_taxable'], bracket_max) - bracket_min
        blocks.append({"Category": f"Ord {int(rate*100)}%", "Start": curr_magi, "End": curr_magi + filled, "Row": "2. Ordinary Taxable", "Type": "Actual", "RateLabel": f"{int(rate*100)}%"})
        curr_magi += filled
        
        # Draw phantom capacity only for the active marginal bucket
        if base['fed_ord_taxable'] < bracket_max and bracket_max != float('inf'):
            phantom = bracket_max - base['fed_ord_taxable']
            blocks.append({"Category": f"Ord {int(rate*100)}%", "Start": curr_magi, "End": curr_magi + phantom, "Row": "2. Ordinary Taxable", "Type": "Phantom", "RateLabel": "Capacity"})
            break
    else:
        break
    prev_limit = limit

# 3. LTCG Taxable Row (Starts where Ordinary ends)
curr_magi = used_ded + base['fed_ord_taxable']
total_taxable = base['fed_ord_taxable'] + base['fed_ltcg_taxable']
prev_limit = 0.0

for limit, rate in p["ltcg_brackets"]:
    if base['fed_ord_taxable'] >= limit:
        prev_limit = limit
        continue
        
    start_in_bracket = max(base['fed_ord_taxable'], prev_limit)
    
    if total_taxable > start_in_bracket:
        filled = min(total_taxable, limit) - start_in_bracket
        blocks.append({"Category": f"LTCG {int(rate*100)}%", "Start": curr_magi, "End": curr_magi + filled, "Row": "3. LTCG Taxable", "Type": "Actual", "RateLabel": f"{int(rate*100)}%"})
        curr_magi += filled
        
        # Draw phantom capacity only for the active marginal LTCG bucket
        if total_taxable < limit and limit != float('inf'):
            phantom = limit - total_taxable
            blocks.append({"Category": f"LTCG {int(rate*100)}%", "Start": curr_magi, "End": curr_magi + phantom, "Row": "3. LTCG Taxable", "Type": "Phantom", "RateLabel": "Capacity"})
            break
    else:
        # Show first available bucket as phantom if no LTCG exists
        if limit != float('inf'):
            phantom = limit - start_in_bracket
            blocks.append({"Category": f"LTCG {int(rate*100)}%", "Start": curr_magi, "End": curr_magi + phantom, "Row": "3. LTCG Taxable", "Type": "Phantom", "RateLabel": f"{int(rate*100)}% Cap."})
        break
    prev_limit = limit

for b in blocks:
    b['Middle'] = (b['Start'] + b['End']) / 2

df_blocks = pd.DataFrame(blocks)

# Calculate dynamic X-axis maximum limit
# Show up to Tier 3 threshold + a little padding, unless MAGI forces it wider
tier_3_limit = p["irmaa_tiers"][2][0]
x_max_val = max(base['magi'] * 1.05, tier_3_limit + 15000)

base_chart = alt.Chart(df_blocks).encode(
    y=alt.Y("Row:N", title="", sort=["1. Deductions", "2. Ordinary Taxable", "3. LTCG Taxable"], axis=alt.Axis(labels=True, ticks=False, labelPadding=10, labelFontSize=12)),
    x=alt.X("Start:Q", title="Modified Adjusted Gross Income (MAGI)", scale=alt.Scale(domain=[0, x_max_val]), axis=alt.Axis(format="$,.0f")),
    x2=alt.X2("End:Q")
)

bar_actual = base_chart.transform_filter(alt.datum.Type == 'Actual').mark_bar(size=30, cornerRadius=2).encode(
    color=alt.Color("Category:N", scale=alt.Scale(scheme="tableau20"), legend=None),
    tooltip=["Category", alt.Tooltip("Start:Q", format="$,.0f"), alt.Tooltip("End:Q", format="$,.0f")]
)

# Phantom bars use light opacity and an identical color stroke to represent "empty space" in the bucket
bar_phantom = base_chart.transform_filter(alt.datum.Type == 'Phantom').mark_bar(size=30, fillOpacity=0.1, strokeWidth=1.5, strokeDash=[4,4]).encode(
    color=alt.Color("Category:N", scale=alt.Scale(scheme="tableau20"), legend=None),
    stroke=alt.Color("Category:N", scale=alt.Scale(scheme="tableau20"), legend=None),
    tooltip=["Category", alt.Tooltip("Start:Q", format="$,.0f"), alt.Tooltip("End:Q", format="$,.0f")]
)

text_labels = base_chart.mark_text(align='center', baseline='middle', color='white', fontSize=11, fontWeight='bold').encode(
    x=alt.X('Middle:Q'),
    text='RateLabel:N'
)

# Vertical rules for IRMAA/NIIT cliffs
rules_data = [{"Name": "NIIT (3.8%)", "Value": p["niit_threshold"]}]
for limit, _, name in p["irmaa_tiers"]:
    if limit != float('inf'):
        rules_data.append({"Name": f"Medicare {name.split()[1]}", "Value": limit})

rule_chart = alt.Chart(pd.DataFrame(rules_data)).mark_rule(strokeDash=[4,4], color='red', size=1.5).encode(
    x="Value:Q",
    tooltip=["Name", alt.Tooltip("Value:Q", format="$,.0f")]
)

st.altair_chart((bar_actual + bar_phantom + text_labels + rule_chart).properties(height=220), use_container_width=True)

st.divider()

# ---------------------------------------------------------
# SLIVER ANALYSIS
# ---------------------------------------------------------
st.subheader("Sliver Analysis")
col_add, col_sub = st.columns(2)

with col_add:
    st.markdown("#### 📈 Realize +$1,000")
    st.metric(label="Add $1,000 Ordinary", value=f"Costs ${up_ord_cost:,.0f}", delta=f"{up_ord_cost/10.0:.1f}% effective rate", delta_color="inverse")
    st.caption(f"_{format_breakdown(base, up_ord, True)}_")
    
    st.metric(label="Add $1,000 LTCG", value=f"Costs ${up_ltcg_cost:,.0f}", delta=f"{up_ltcg_cost/10.0:.1f}% effective rate", delta_color="inverse")
    st.caption(f"_{format_breakdown(base, up_ltcg, True)}_")

with col_sub:
    st.markdown("#### 📉 Defer -$1,000")
    st.metric(label="Reduce $1,000 Ordinary", value=f"Saves ${dn_ord_save:,.0f}", delta=f"{dn_ord_save/10.0:.1f}% effective rate", delta_color="normal")
    st.caption(f"_{format_breakdown(base, dn_ord, False)}_")
    
    st.metric(label="Reduce $1,000 LTCG", value=f"Saves ${dn_ltcg_save:,.0f}", delta=f"{dn_ltcg_save/10.0:.1f}% effective rate", delta_color="normal")
    st.caption(f"_{format_breakdown(base, dn_ltcg, False)}_")

st.divider()

# ---------------------------------------------------------
# STATUS BOXES (Markdown-Safe)
# ---------------------------------------------------------
alert1, alert2 = st.columns(2)
with alert1:
    st.markdown("### Projected 2028 Medicare Surcharge")
    if base["annual_irmaa"] == 0:
        st.success(f"**{base['tier_name']}**\n\nCurrent MAGI is ${base['magi']:,.0f}. You are ${base['depth_irmaa']:,.0f} deep into this tier, leaving ${base['headroom_irmaa']:,.0f} in headroom before hitting Tier 1.")
    elif base["headroom_irmaa"] is not None:
        st.warning(f"**{base['tier_name']}**\n\nAnnual Surcharge is ${base['annual_irmaa']:,.0f}. You are ${base['depth_irmaa']:,.0f} past the previous cliff, leaving ${base['headroom_irmaa']:,.0f} in headroom before the next penalty jump.")
    else:
        st.error(f"**{base['tier_name']}**\n\nMaximum bracket. Annual Surcharge is ${base['annual_irmaa']:,.0f}. You are ${base['depth_irmaa']:,.0f} over the final cliff threshold.")

with alert2:
    st.markdown("### Net Investment Income Tax")
    nl = p["niit_threshold"]
    if base["magi"] > nl and ltcg_in > 0:
        st.warning(f"**NIIT Active (3.8%)**\n\nMAGI of ${base['magi']:,.0f} exceeds the limit. ${base['niit_subject']:,.0f} of investment income is penalized.")
    elif base["magi"] > nl:
        st.info(f"**NIIT Clear**\n\nMAGI exceeds the limit, but there is $0 of investment income to penalize.")
    else:
        st.success(f"**NIIT Exempt**\n\nMAGI is ${base['magi']:,.0f}. You have ${(nl - base['magi']):,.0f} in headroom before the penalty applies.")

st.divider()

# ---------------------------------------------------------
# MARGINAL TAX CURVE
# ---------------------------------------------------------
st.subheader("Interactive Marginal Tax Curve")
st.caption("Visualizes the exact cost to realize the *next* $1,000 of income across the entire spectrum.")

curve_axis = st.radio("Select sweep variable:", ["Ordinary Income (tIRA, Wages)", "Long-Term Capital Gains"], horizontal=True)

curve_data = []
test_range = range(0, 305000, 2500)

if "Ordinary" in curve_axis:
    for w in test_range:
        b_res = calculate_tax_scenario(w, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
        u_res = calculate_tax_scenario(w + 1000, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
        m_rate = ((u_res['total_outflows'] - b_res['total_outflows']) / 1000.0) * 100.0
        curve_data.append({"Income": w, "Marginal Rate (%)": m_rate})
    current_val = wages_in
else:
    for c in test_range:
        b_res = calculate_tax_scenario(wages_in, c, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
        u_res = calculate_tax_scenario(wages_in, c + 1000, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
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
