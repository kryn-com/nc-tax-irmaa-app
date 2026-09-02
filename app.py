import streamlit as st
import pandas as pd
import altair as alt
import math

st.set_page_config(
    page_title="Multi-Year Federal & NC Tax Planner",
    page_icon="📊",
    layout="wide"
)

# ---------------------------------------------------------
# MULTI-YEAR TAX CONSTANTS & ENGINE
# ---------------------------------------------------------
PARAMS = {
    2025: {
        "nc_tax_rate": 0.0425,
        "irmaa_year": 2027,
        "Single": {
            "fed_std_deduction": 15750.0,
            "nc_std_deduction": 12750.0,
            "age_65_bump": 2000.0,
            "ss_thresh_1": 25000.0,
            "ss_thresh_2": 34000.0,
            "oba_max": 6000.0,
            "oba_phaseout_start": 75000.0,
            "ord_brackets": [
                (11925.0, 0.10), 
                (48475.0, 0.12), 
                (103350.0, 0.22), 
                (197300.0, 0.24), 
                (250525.0, 0.32), 
                (626350.0, 0.35), 
                (float("inf"), 0.37)
            ],
            "ltcg_brackets": [(48350.0, 0.00), (533400.0, 0.15), (float("inf"), 0.20)],
            "niit_threshold": 200000.0,
            "irmaa_tiers": [
                (111000.0, 0.0, "Tier 0 (Standard)"),
                (139000.0, 94.80, "Tier 1 Surcharge"),
                (174000.0, 233.80, "Tier 2 Surcharge"),
                (float("inf"), 374.50, "Tier 3 Surcharge")
            ]
        },
        "MFJ": {
            "fed_std_deduction": 31500.0,
            "nc_std_deduction": 25500.0,
            "age_65_bump": 1600.0,
            "ss_thresh_1": 32000.0,
            "ss_thresh_2": 44000.0,
            "oba_max": 6000.0,
            "oba_phaseout_start": 150000.0,
            "ord_brackets": [
                (23850.0, 0.10), 
                (96950.0, 0.12), 
                (206700.0, 0.22), 
                (394600.0, 0.24), 
                (501050.0, 0.32), 
                (751600.0, 0.35), 
                (float("inf"), 0.37)
            ],
            "ltcg_brackets": [(96700.0, 0.00), (600050.0, 0.15), (float("inf"), 0.20)],
            "niit_threshold": 250000.0,
            "irmaa_tiers": [
                (222000.0, 0.0, "Tier 0 (Standard)"),
                (278000.0, 94.80 * 2, "Tier 1 Surcharge (2x)"),
                (348000.0, 233.80 * 2, "Tier 2 Surcharge (2x)"),
                (float("inf"), 374.50 * 2, "Tier 3 Surcharge (2x)")
            ]
        }
    },
    2026: {
        "nc_tax_rate": 0.0399,
        "irmaa_year": 2028,
        "Single": {
            "fed_std_deduction": 16100.0,
            "nc_std_deduction": 12750.0,
            "age_65_bump": 2050.0,
            "ss_thresh_1": 25000.0,
            "ss_thresh_2": 34000.0,
            "oba_max": 6000.0,
            "oba_phaseout_start": 75000.0,
            "ord_brackets": [(12400.0, 0.10), (50400.0, 0.12), (105700.0, 0.22), (201775.0, 0.24), (256125.0, 0.32), (566350.0, 0.35), (float("inf"), 0.37)],
            "ltcg_brackets": [(49450.0, 0.00), (545500.0, 0.15), (float("inf"), 0.20)],
            "niit_threshold": 200000.0,
            "irmaa_tiers": [
                (114000.0, 0.0, "Tier 0 (Standard)"),
                (143000.0, 97.50, "Tier 1 Surcharge"),
                (179000.0, 240.40, "Tier 2 Surcharge"),
                (float("inf"), 385.00, "Tier 3 Surcharge")
            ]
        },
        "MFJ": {
            "fed_std_deduction": 32200.0,
            "nc_std_deduction": 25500.0,
            "age_65_bump": 1650.0,
            "ss_thresh_1": 32000.0,
            "ss_thresh_2": 44000.0,
            "oba_max": 6000.0,
            "oba_phaseout_start": 150000.0,
            "ord_brackets": [(24800.0, 0.10), (100800.0, 0.12), (211400.0, 0.22), (403550.0, 0.24), (512250.0, 0.32), (732600.0, 0.35), (float("inf"), 0.37)],
            "ltcg_brackets": [(98900.0, 0.00), (613600.0, 0.15), (float("inf"), 0.20)],
            "niit_threshold": 250000.0,
            "irmaa_tiers": [
                (228000.0, 0.0, "Tier 0 (Standard)"),
                (286000.0, 97.50 * 2, "Tier 1 Surcharge (2x)"),
                (358000.0, 240.40 * 2, "Tier 2 Surcharge (2x)"),
                (float("inf"), 385.00 * 2, "Tier 3 Surcharge (2x)")
            ]
        }
    },
    2027: {
        "nc_tax_rate": 0.0399,
        "irmaa_year": 2029,
        "Single": {
            "fed_std_deduction": 16550.0,
            "nc_std_deduction": 12750.0,
            "age_65_bump": 2100.0,
            "ss_thresh_1": 25000.0,
            "ss_thresh_2": 34000.0,
            "oba_max": 6000.0,
            "oba_phaseout_start": 75000.0,
            "ord_brackets": [(12750.0, 0.10), (51800.0, 0.12), (108650.0, 0.22), (207400.0, 0.24), (263300.0, 0.32), (582200.0, 0.35), (float("inf"), 0.37)],
            "ltcg_brackets": [(50850.0, 0.00), (560750.0, 0.15), (float("inf"), 0.20)],
            "niit_threshold": 200000.0,
            "irmaa_tiers": [
                (117200.0, 0.0, "Tier 0 (Standard)"),
                (147000.0, 100.20, "Tier 1 Surcharge"),
                (184000.0, 247.10, "Tier 2 Surcharge"),
                (float("inf"), 395.70, "Tier 3 Surcharge")
            ]
        },
        "MFJ": {
            "fed_std_deduction": 33100.0,
            "nc_std_deduction": 25500.0,
            "age_65_bump": 1700.0,
            "ss_thresh_1": 32000.0,
            "ss_thresh_2": 44000.0,
            "oba_max": 6000.0,
            "oba_phaseout_start": 150000.0,
            "ord_brackets": [(25500.0, 0.10), (103600.0, 0.12), (217300.0, 0.22), (414800.0, 0.24), (526600.0, 0.32), (753100.0, 0.35), (float("inf"), 0.37)],
            "ltcg_brackets": [(101650.0, 0.00), (630750.0, 0.15), (float("inf"), 0.20)],
            "niit_threshold": 250000.0,
            "irmaa_tiers": [
                (234400.0, 0.0, "Tier 0 (Standard)"),
                (294000.0, 100.20 * 2, "Tier 1 Surcharge (2x)"),
                (368000.0, 247.10 * 2, "Tier 2 Surcharge (2x)"),
                (float("inf"), 395.70 * 2, "Tier 3 Surcharge (2x)")
            ]
        }
    }
}


def calculate_tax_scenario(year, wages, ltcg, ss, pretax, muni, fed_ded_base, nc_ded_base, nc_adj, status, tp_65, sp_65):
    yr_params = PARAMS[year]
    p = yr_params[status]
    nc_rate = yr_params["nc_tax_rate"]
    
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
        max_ded = p["oba_max"] * count
        phase_out = max(0.0, (magi - p["oba_phaseout_start"]) * 0.06)
        senior_bonus = max(0.0, max_ded - phase_out)
        
    total_fed_deduction = fed_ded_base + senior_bonus
    
    # 4. Deduction Absorption Stacking
    total_taxable_income = max(0.0, fed_agi - total_fed_deduction)
    ordinary_gross = max(0.0, fed_agi - ltcg)
    
    fed_ord_taxable = min(total_taxable_income, max(0.0, ordinary_gross - total_fed_deduction))
    fed_ltcg_taxable = total_taxable_income - fed_ord_taxable
    
    # 5. Federal Ordinary Brackets & Tax Table Logic (Midpoint for < $100k)
    if 0 < fed_ord_taxable < 100000:
        if fed_ord_taxable < 3000:
            lookup_income = math.floor(fed_ord_taxable / 25.0) * 25.0 + 12.5
        else:
            lookup_income = math.floor(fed_ord_taxable / 50.0) * 50.0 + 25.0
    else:
        lookup_income = fed_ord_taxable

    # Data for the visual chart (using exact actual placement)
    prev_limit = 0.0
    ord_bracket_amts = []
    for limit, rate in p["ord_brackets"]:
        if fed_ord_taxable > prev_limit:
            chunk = min(fed_ord_taxable, limit) - prev_limit
            ord_bracket_amts.append({"rate": rate, "amount": chunk, "bracket_limit": limit})
            prev_limit = limit
        else:
            break

    # Calculate actual tax dollar amount using the Tax Table lookup_income
    fed_ord_tax_raw = 0.0
    prev_limit = 0.0
    for limit, rate in p["ord_brackets"]:
        if lookup_income > prev_limit:
            chunk = min(lookup_income, limit) - prev_limit
            fed_ord_tax_raw += chunk * rate
            prev_limit = limit
        else:
            break
            
    # IRS specifies Tax Tables output whole dollar amounts
    fed_ord_tax = round(fed_ord_tax_raw) if fed_ord_taxable < 100000 else fed_ord_tax_raw
            
    # 6. Federal LTCG Brackets (LTCG stacks using exact taxable income boundary)
    start_stack = fed_ord_taxable
    end_stack = fed_ord_taxable + fed_ltcg_taxable
    fed_ltcg_tax = 0.0
    ltcg_bracket_amts = []
    
    ltcg_b = p["ltcg_brackets"]
    t_0 = max(0.0, min(end_stack, ltcg_b[0][0]) - max(start_stack, 0.0))
    t_15 = max(0.0, min(end_stack, ltcg_b[1][0]) - max(start_stack, ltcg_b[0][0]))
    t_20 = max(0.0, end_stack - max(start_stack, ltcg_b[1][0]))
    
    if t_0 > 0:
        ltcg_bracket_amts.append({"rate": ltcg_b[0][1], "amount": t_0, "bracket_limit": ltcg_b[0][0]})
    if t_15 > 0:
        ltcg_bracket_amts.append({"rate": ltcg_b[1][1], "amount": t_15, "bracket_limit": ltcg_b[1][0]})
    if t_20 > 0:
        ltcg_bracket_amts.append({"rate": ltcg_b[2][1], "amount": t_20, "bracket_limit": ltcg_b[2][0]})
    
    fed_ltcg_tax = (t_0 * ltcg_b[0][1]) + (t_15 * ltcg_b[1][1]) + (t_20 * ltcg_b[2][1])
    
    # 7. Net Investment Income Tax
    niit_tax = 0.0
    niit_subject = 0.0
    if magi > p["niit_threshold"] and ltcg > 0:
        niit_subject = min(float(ltcg), magi - p["niit_threshold"])
        niit_tax = niit_subject * 0.038
        
    total_fed_tax = fed_ord_tax + fed_ltcg_tax + niit_tax
    
    # 8. NC State Tax
    nc_taxable = max(0.0, wages + ltcg - pretax - nc_ded_base + nc_adj)
    nc_tax = nc_taxable * nc_rate
    
    # 9. Projected Medicare Surcharge
    tier_name = ""
    monthly_irmaa = 0.0
    headroom_irmaa = None
    depth_irmaa = 0.0
    previous_limit = 0.0
    
    for limit, surcharge, name in p["irmaa_tiers"]:
        if magi <= limit:
            tier_name = name
            monthly_irmaa = surcharge
            headroom_irmaa = limit - magi if limit != float("inf") else None
            depth_irmaa = magi - previous_limit
            break
        previous_limit = limit
            
    annual_irmaa = monthly_irmaa * 12.0
    total_outflows = total_fed_tax + nc_tax + annual_irmaa
    
    return {
        "fed_agi": fed_agi,
        "magi": magi,
        "taxable_ss": taxable_ss,
        "total_fed_deduction": total_fed_deduction,
        "fed_ord_taxable": fed_ord_taxable,
        "fed_ltcg_taxable": fed_ltcg_taxable,
        "fed_ord_tax": fed_ord_tax,
        "fed_ltcg_tax": fed_ltcg_tax,
        "total_fed_taxable_income": total_taxable_income,
        "niit_tax": niit_tax,
        "niit_subject": niit_subject,
        "nc_tax": nc_tax,
        "annual_irmaa": annual_irmaa,
        "tier_name": tier_name,
        "headroom_irmaa": headroom_irmaa,
        "depth_irmaa": depth_irmaa,
        "total_outflows": total_outflows,
        "ord_bracket_amts": ord_bracket_amts,
        "ltcg_bracket_amts": ltcg_bracket_amts
    }


def format_breakdown(base_res, new_res):
    """Generates a clean tax-delta breakdown with explicit +/- and $ signs."""
    dfed = new_res["fed_ord_tax"] + new_res["fed_ltcg_tax"] - base_res["fed_ord_tax"] - base_res["fed_ltcg_tax"]
    dnc = new_res["nc_tax"] - base_res["nc_tax"]
    dniit = new_res["niit_tax"] - base_res["niit_tax"]
    dirmaa = new_res["annual_irmaa"] - base_res["annual_irmaa"]
    dss = new_res["taxable_ss"] - base_res["taxable_ss"]
    
    def fmt(val):
        if val > 0: return f"+${val:,.0f}"
        elif val < 0: return f"-${abs(val):,.0f}"
        return f"${0}"

    parts = []
    if dfed != 0: parts.append(f"Fed: {fmt(dfed)}")
    if dnc != 0: parts.append(f"NC: {fmt(dnc)}")
    if dniit != 0: parts.append(f"NIIT: {fmt(dniit)}")
    if dirmaa != 0: parts.append(f"Medicare: {fmt(dirmaa)}")
    if dss != 0: parts.append(f"Taxable SS: {fmt(dss)}")
    
    return "  •  ".join(parts) if parts else "No tax impact"


# ---------------------------------------------------------
# UI: SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.title("Year-End Tax Planner")

tax_year = st.sidebar.selectbox("Tax Year", [2025, 2026, 2027], index=1, format_func=lambda x: f"{x} (Projected)" if x == 2027 else str(x))
filing_status = st.sidebar.radio("Filing Status", ["Single", "MFJ"], horizontal=True)

st.sidebar.subheader("Taxpayer Profile")
col_tp, col_sp = st.sidebar.columns(2)
with col_tp:
    tp_65 = st.checkbox("TP 65+", value=False)
with col_sp:
    sp_65 = st.checkbox("SP 65+", value=False) if filing_status == "MFJ" else False

st.sidebar.subheader("Income Sources")
wages_in = st.sidebar.number_input("Ordinary Income / tIRA ($)", min_value=0, max_value=1000000, value=120000, step=1000)
ltcg_in = st.sidebar.number_input("Long-Term Capital Gains ($)", min_value=0, max_value=1000000, value=20000, step=1000)
ss_in = st.sidebar.number_input("Social Security Benefits ($)", min_value=0, max_value=150000, value=15000, step=500)
pretax_in = st.sidebar.number_input("Pre-Tax Deductions (401k) ($)", min_value=0, max_value=150000, value=0, step=500)
muni_in = st.sidebar.number_input("Tax-Exempt Muni Interest ($)", min_value=0, max_value=150000, value=0, step=1000)

st.sidebar.subheader("Deductions & State Adjustments")
p_selected = PARAMS[tax_year][filing_status]

fed_std_val = (
    p_selected["fed_std_deduction"]
    + (p_selected["age_65_bump"] if tp_65 else 0)
    + (p_selected["age_65_bump"] if sp_65 else 0)
)
nc_std_val = p_selected["nc_std_deduction"]

fed_ded_mode = st.sidebar.radio("Federal Deduction", ["Standard", "Itemized"], horizontal=True)
fed_ded_val = (
    fed_std_val
    if fed_ded_mode == "Standard"
    else st.sidebar.number_input("Federal Itemized ($)", 0, 300000, int(fed_std_val), 1000)
)

nc_ded_mode = st.sidebar.radio("NC State Deduction", ["Standard", "Itemized"], horizontal=True)
nc_ded_val = (
    nc_std_val
    if nc_ded_mode == "Standard"
    else st.sidebar.number_input("NC Itemized ($)", 0, 300000, int(nc_std_val), 1000)
)

nc_adj_in = st.sidebar.number_input(
    "NC Income Adjustments (+/-) ($)",
    value=0,
    step=500,
    help="Net adjustments for state taxation differences (e.g., subtract U.S. Treasury interest, add out-of-state munis)."
)

# ---------------------------------------------------------
# CALCULATIONS
# ---------------------------------------------------------
base = calculate_tax_scenario(tax_year, wages_in, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)

up_ord = calculate_tax_scenario(tax_year, wages_in + 1000, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
dn_ord = calculate_tax_scenario(tax_year, max(0, wages_in - 1000), ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
up_ord_cost = up_ord["total_outflows"] - base["total_outflows"]
dn_ord_save = base["total_outflows"] - dn_ord["total_outflows"]

up_ltcg = calculate_tax_scenario(tax_year, wages_in, ltcg_in + 1000, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
dn_ltcg = calculate_tax_scenario(tax_year, wages_in, max(0, ltcg_in - 1000), ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
up_ltcg_cost = up_ltcg["total_outflows"] - base["total_outflows"]
dn_ltcg_save = base["total_outflows"] - dn_ltcg["total_outflows"]

# ---------------------------------------------------------
# UI: DASHBOARD
# ---------------------------------------------------------
header_year = f"{tax_year} (Projected)" if tax_year == 2027 else str(tax_year)
st.title(f"{header_year} Year-End Tax & Medicare Cliff Planner ({filing_status})")

# Primary Tax KPI Row
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Federal Income Tax", f"${base['fed_ord_tax'] + base['fed_ltcg_tax']:,.0f}")
kpi2.metric(f"NC State Tax ({PARAMS[tax_year]['nc_tax_rate']*100:.2f}%)", f"${base['nc_tax']:,.0f}")
kpi3.metric("Net Investment Income Tax", f"${base['niit_tax']:,.0f}")
kpi4.metric(f"Projected {PARAMS[tax_year]['irmaa_year']} Medicare Surcharge", f"${base['annual_irmaa']:,.0f}/yr")

st.markdown("<hr style='margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)

# Secondary Base Variables Row
sub1, sub2, sub3 = st.columns(3)
sub1.metric("Federal Adjusted Gross Income (AGI)", f"${base['fed_agi']:,.0f}")
sub2.metric("Federal Taxable Income", f"${base['total_fed_taxable_income']:,.0f}")
sub3.metric("Taxable Social Security", f"${base['taxable_ss']:,.0f}")

st.divider()

# ---------------------------------------------------------
# 3-ROW MAGI STACKING CHART
# ---------------------------------------------------------
st.subheader("Income Stacking & Vulnerability Cliffs")
st.caption("Visualizes dollar placement across absolute MAGI boundaries. Outlined segments represent remaining capacity in your current marginal bracket.")

blocks = []

# Row 1: Deductions (0% band)
used_ded = min(base["fed_agi"], base["total_fed_deduction"])
if used_ded > 0:
    blocks.append({
        "Row": "Deductions",
        "Start": 0.0,
        "End": used_ded,
        "Category": "Deductions (0%)",
        "Type": "Actual",
        "Label": "0%"
    })

# Row 2: Ordinary Income
curr_ord_x = used_ded
prev_limit = 0.0
for limit, rate in p_selected["ord_brackets"]:
    if base["fed_ord_taxable"] > prev_limit:
        chunk = min(base["fed_ord_taxable"], limit) - prev_limit
        cat_name = f"Ord {int(rate*100)}%"
        blocks.append({
            "Row": "Ordinary",
            "Start": curr_ord_x,
            "End": curr_ord_x + chunk,
            "Category": cat_name,
            "Type": "Actual",
            "Label": f"{int(rate*100)}%"
        })
        curr_ord_x += chunk
        
        if base["fed_ord_taxable"] < limit and limit != float("inf"):
            phantom_amt = limit - base["fed_ord_taxable"]
            blocks.append({
                "Row": "Ordinary",
                "Start": curr_ord_x,
                "End": curr_ord_x + phantom_amt,
                "Category": cat_name,
                "Type": "Phantom",
                "Label": "Capacity"
            })
            break
    else:
        break
    prev_limit = limit

# Row 3: LTCG
curr_ltcg_x = used_ded + base["fed_ord_taxable"]
total_taxable = base["fed_ord_taxable"] + base["fed_ltcg_taxable"]
prev_limit = 0.0

for limit, rate in p_selected["ltcg_brackets"]:
    if base["fed_ord_taxable"] >= limit:
        prev_limit = limit
        continue
        
    start_in_bracket = max(base["fed_ord_taxable"], prev_limit)
    cat_name = f"LTCG {int(rate*100)}%"
    
    if total_taxable > start_in_bracket:
        chunk = min(total_taxable, limit) - start_in_bracket
        blocks.append({
            "Row": "LTCG",
            "Start": curr_ltcg_x,
            "End": curr_ltcg_x + chunk,
            "Category": cat_name,
            "Type": "Actual",
            "Label": f"{int(rate*100)}%"
        })
        curr_ltcg_x += chunk
        
        if total_taxable < limit and limit != float("inf"):
            phantom_amt = limit - total_taxable
            blocks.append({
                "Row": "LTCG",
                "Start": curr_ltcg_x,
                "End": curr_ltcg_x + phantom_amt,
                "Category": cat_name,
                "Type": "Phantom",
                "Label": "Capacity"
            })
            break
    else:
        if limit != float("inf"):
            phantom_amt = limit - start_in_bracket
            blocks.append({
                "Row": "LTCG",
                "Start": curr_ltcg_x,
                "End": curr_ltcg_x + phantom_amt,
                "Category": cat_name,
                "Type": "Phantom",
                "Label": "Capacity"
            })
        break
    prev_limit = limit

df_blocks = pd.DataFrame(blocks)
if not df_blocks.empty:
    df_blocks["Middle"] = (df_blocks["Start"] + df_blocks["End"]) / 2.0
    df_blocks["Width"] = df_blocks["End"] - df_blocks["Start"]

# Determine dynamic X-axis bounds (scale to just past the next unachieved cliff)
next_cliff = None
for limit, _, _ in p_selected["irmaa_tiers"]:
    if limit > base["magi"] and limit != float("inf"):
        next_cliff = limit
        break

if not next_cliff:
    next_cliff = base["magi"] * 1.05
    
x_axis_max = max(base["magi"] * 1.05, next_cliff + 15000)

x_scale = alt.Scale(domain=[0, x_axis_max], clamp=True)
y_scale = alt.Scale(domain=["Deductions", "Ordinary", "LTCG"])

df_actual = df_blocks[df_blocks["Type"] == "Actual"] if not df_blocks.empty else pd.DataFrame()
df_phantom = df_blocks[df_blocks["Type"] == "Phantom"] if not df_blocks.empty else pd.DataFrame()
df_labels = df_blocks[df_blocks["Width"] >= 4000] if not df_blocks.empty else pd.DataFrame()

chart_actual = alt.Chart(df_actual).mark_bar(size=30, cornerRadius=2).encode(
    x=alt.X("Start:Q", scale=x_scale, title="Modified Adjusted Gross Income (MAGI)", 
            axis=alt.Axis(format="$s", labelFontSize=14, titleFontSize=15, grid=True)),
    x2=alt.X2("End:Q"),
    y=alt.Y("Row:N", scale=y_scale, title="", 
            axis=alt.Axis(labels=True, ticks=False, labelPadding=10, labelFontSize=15, labelFontWeight="bold")),
    color=alt.Color("Category:N", scale=alt.Scale(scheme="tableau10"), legend=None),
    tooltip=[
        alt.Tooltip("Category:N", title="Tax Tier"),
        alt.Tooltip("Start:Q", title="Start MAGI", format="$,.0f"),
        alt.Tooltip("End:Q", title="End MAGI", format="$,.0f"),
        alt.Tooltip("Width:Q", title="Span", format="$,.0f")
    ]
)

chart_phantom = alt.Chart(df_phantom).mark_bar(size=30, fillOpacity=0.12, strokeWidth=1.5, strokeDash=[4, 4]).encode(
    x=alt.X("Start:Q", scale=x_scale),
    x2=alt.X2("End:Q"),
    y=alt.Y("Row:N", scale=y_scale),
    color=alt.Color("Category:N", scale=alt.Scale(scheme="tableau10"), legend=None),
    stroke=alt.Color("Category:N", scale=alt.Scale(scheme="tableau10"), legend=None),
    tooltip=[
        alt.Tooltip("Category:N", title="Available Capacity"),
        alt.Tooltip("Start:Q", title="Current Position", format="$,.0f"),
        alt.Tooltip("End:Q", title="Bracket Cap", format="$,.0f"),
        alt.Tooltip("Width:Q", title="Remaining Room", format="$,.0f")
    ]
)

chart_labels = alt.Chart(df_labels).mark_text(align="center", baseline="middle", color="white", fontSize=13, fontWeight="bold").encode(
    x=alt.X("Middle:Q", scale=x_scale),
    y=alt.Y("Row:N", scale=y_scale),
    text=alt.Text("Label:N")
)

rules_data = [{"Name": "NIIT Threshold", "Value": p_selected["niit_threshold"]}]
for limit, _, name in p_selected["irmaa_tiers"]:
    if limit != float("inf"):
        rules_data.append({"Name": f"Medicare {name.split()[1]}", "Value": limit})

rule_chart = alt.Chart(pd.DataFrame(rules_data)).mark_rule(strokeDash=[4, 4], color="#e63946", strokeWidth=1.5).encode(
    x=alt.X("Value:Q", scale=x_scale),
    tooltip=[alt.Tooltip("Name:N", title="Cliff"), alt.Tooltip("Value:Q", title="MAGI", format="$,.0f")]
)

st.altair_chart((chart_actual + chart_phantom + chart_labels + rule_chart).properties(height=240), use_container_width=True)

st.divider()

# ---------------------------------------------------------
# SLIVER ANALYSIS
# ---------------------------------------------------------
st.subheader("Sliver Analysis")
col_ord_add, col_ord_sub, col_ltcg_add, col_ltcg_sub = st.columns(4)

with col_ord_add:
    st.markdown("#### Ordinary Income")
    st.metric(label="Add +$1,000", value=f"Costs ${up_ord_cost:,.0f}", delta=f"{up_ord_cost/10.0:.1f}% effective rate", delta_color="inverse")
    st.write(format_breakdown(base, up_ord))

with col_ord_sub:
    st.markdown("#### &nbsp;")
    st.metric(label="Reduce -$1,000", value=f"Saves ${dn_ord_save:,.0f}", delta=f"{dn_ord_save/10.0:.1f}% effective rate", delta_color="normal")
    st.write(format_breakdown(base, dn_ord))

with col_ltcg_add:
    st.markdown("#### Capital Gains")
    st.metric(label="Add +$1,000", value=f"Costs ${up_ltcg_cost:,.0f}", delta=f"{up_ltcg_cost/10.0:.1f}% effective rate", delta_color="inverse")
    st.write(format_breakdown(base, up_ltcg))

with col_ltcg_sub:
    st.markdown("#### &nbsp;")
    st.metric(label="Reduce -$1,000", value=f"Saves ${dn_ltcg_save:,.0f}", delta=f"{dn_ltcg_save/10.0:.1f}% effective rate", delta_color="normal")
    st.write(format_breakdown(base, dn_ltcg))

st.divider()

# ---------------------------------------------------------
# STATUS BOXES
# ---------------------------------------------------------
alert1, alert2 = st.columns(2)
with alert1:
    st.markdown(f"### Projected {PARAMS[tax_year]['irmaa_year']} Medicare Surcharge")
    if base["annual_irmaa"] == 0:
        st.success(
            f"**{base['tier_name']}**\n\n"
            f"Current MAGI is **${base['magi']:,.0f}**. You are **${base['depth_irmaa']:,.0f}** deep into this tier, "
            f"leaving **${base['headroom_irmaa']:,.0f}** in headroom before hitting Tier 1."
        )
    elif base["headroom_irmaa"] is not None:
        st.warning(
            f"**{base['tier_name']}**\n\n"
            f"Annual Surcharge is **${base['annual_irmaa']:,.0f}**. You are **${base['depth_irmaa']:,.0f}** past the previous cliff, "
            f"leaving **${base['headroom_irmaa']:,.0f}** in headroom before the next penalty jump."
        )
    else:
        st.error(
            f"**{base['tier_name']}**\n\n"
            f"Maximum bracket. Annual Surcharge is **${base['annual_irmaa']:,.0f}**. "
            f"You are **${base['depth_irmaa']:,.0f}** over the final cliff threshold."
        )

with alert2:
    st.markdown("### Net Investment Income Tax")
    nl = p_selected["niit_threshold"]
    if base["magi"] > nl and ltcg_in > 0:
        st.warning(
            f"**NIIT Active (3.8%)**\n\n"
            f"MAGI of **${base['magi']:,.0f}** exceeds the **${nl:,.0f}** limit. "
            f"**${base['niit_subject']:,.0f}** of investment income is penalized (**${base['niit_tax']:,.0f}** tax)."
        )
    elif base["magi"] > nl:
        st.info(
            f"**NIIT Clear**\n\n"
            f"MAGI of **${base['magi']:,.0f}** exceeds the limit, but there is **$0** of investment income to penalize."
        )
    else:
        st.success(
            f"**NIIT Exempt**\n\n"
            f"MAGI is **${base['magi']:,.0f}**. You have **${(nl - base['magi']):,.0f}** in headroom before the penalty applies."
        )

st.divider()

# ---------------------------------------------------------
# MARGINAL TAX CURVE
# ---------------------------------------------------------
st.subheader("Interactive Marginal Tax Curve")
st.caption("Plots the exact marginal tax cost to realize the next $1,000 of income across the spectrum.")

curve_axis = st.radio("Select sweep variable:", ["Ordinary Income (tIRA, Wages)", "Long-Term Capital Gains"], horizontal=True)

curve_data = []
test_range = range(0, 305000, 2500)

if "Ordinary" in curve_axis:
    for w in test_range:
        b_res = calculate_tax_scenario(tax_year, w, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
        u_res = calculate_tax_scenario(tax_year, w + 1000, ltcg_in, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
        m_rate = ((u_res["total_outflows"] - b_res["total_outflows"]) / 1000.0) * 100.0
        curve_data.append({"Income": w, "Marginal Rate (%)": m_rate})
    current_val = wages_in
else:
    for c in test_range:
        b_res = calculate_tax_scenario(tax_year, wages_in, c, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
        u_res = calculate_tax_scenario(tax_year, wages_in, c + 1000, ss_in, pretax_in, muni_in, fed_ded_val, nc_ded_val, nc_adj_in, filing_status, tp_65, sp_65)
        m_rate = ((u_res["total_outflows"] - b_res["total_outflows"]) / 1000.0) * 100.0
        curve_data.append({"Income": c, "Marginal Rate (%)": m_rate})
    current_val = ltcg_in

df_curve = pd.DataFrame(curve_data)
line_chart = alt.Chart(df_curve).mark_line(interpolate="step-after", strokeWidth=2.5, color="#1f77b4").encode(
    x=alt.X("Income:Q", title="Income Axis ($)", axis=alt.Axis(format="$s", labelFontSize=14, titleFontSize=15)),
    y=alt.Y("Marginal Rate (%):Q", scale=alt.Scale(domain=[0, max(60, df_curve["Marginal Rate (%)"].max())], clamp=True), axis=alt.Axis(labelFontSize=14, titleFontSize=15)),
    tooltip=[alt.Tooltip("Income:Q", title="Income Level", format="$,.0f"), alt.Tooltip("Marginal Rate (%):Q", title="Marginal Cost", format=".1f")]
)

current_marker = alt.Chart(pd.DataFrame({"x": [current_val]})).mark_rule(color="#e63946", strokeDash=[4, 4], strokeWidth=2).encode(x="x:Q")
st.altair_chart((line_chart + current_marker).properties(height=350), use_container_width=True)
