from datetime import datetime, timedelta
import re
import pandas as pd
from src.filters import TARGET_METROS, LINK_LI, LINK_WEB, Q_COMM_NAME
import json

def extract_name_from_email(email):
    local = email.split("@")[0].split(".")[0]
    return re.sub(r"\d+", "", local).capitalize() or "Team"

def generate_date():
    today     = datetime.now()
    yesterday = (today - timedelta(days=1)).date()

    avail_target_s = (today - timedelta(days=3)).date()
    avail_comp_s   = (today - timedelta(days=6)).date()
    avail_comp_e   = (today - timedelta(days=4)).date()

    sov_target_s = (today - timedelta(days=2)).date()
    sov_target_e = (today - timedelta(days=1)).date()
    sov_comp_s   = (today - timedelta(days=8)).date()
    sov_comp_e   = (today - timedelta(days=3)).date()

    avail_base_str  = f"{avail_target_s.strftime('%d %b')} - {yesterday.strftime('%d %b %Y')}"
    avail_delta_str = f"{avail_comp_s.strftime('%d %b')} - {avail_comp_e.strftime('%d %b %Y')}"
    sov_base_str    = f"{sov_target_s.strftime('%d %b')} - {sov_target_e.strftime('%d %b %Y')}"
    sov_delta_str   = f"{sov_comp_s.strftime('%d %b')} - {sov_comp_e.strftime('%d %b %Y')}"

    return today, yesterday, avail_target_s, avail_comp_s, avail_comp_e, sov_target_s, sov_target_e, sov_comp_s, sov_comp_e, avail_base_str, avail_delta_str, sov_base_str, sov_delta_str



def generate_availability_html_table(df,avail_target_s, avail_comp_s, avail_comp_e):
    filtered_df = df[df["city"].isin(TARGET_METROS)].copy()
    if filtered_df.empty:
        return "<p style='color:#718096; text-align:center;'>No Availability data</p>"

    avail_p1 = (
        filtered_df[pd.to_datetime(filtered_df["report_date"]).dt.date >= avail_target_s]
        .pivot_table(index="city", columns="brandid", values="is_avail", aggfunc="mean")
        .fillna(0) * 100
    )
    avail_p2 = (
        filtered_df[
            (pd.to_datetime(filtered_df["report_date"]).dt.date >= avail_comp_s) &
            (pd.to_datetime(filtered_df["report_date"]).dt.date <= avail_comp_e)
        ]
        .pivot_table(index="city", columns="brandid", values="is_avail", aggfunc="mean")
        .fillna(0) * 100
    )

    html_df = pd.DataFrame(index=avail_p1.index)
    for col in avail_p1.columns:
        cells = []
        for city in avail_p1.index:
            val      = avail_p1.at[city, col]
            prev_val = avail_p2.at[city, col] if (col in avail_p2.columns and city in avail_p2.index) else 0
            delta    = val - prev_val
            color    = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
            sign     = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
            cells.append(
                f"{int(round(val))}%<br>"
                f"<span style='color:{color}; font-size:11px; font-weight:600;'>"
                f"{sign}{delta:.2f}%</span>"
            )
        html_df[col] = cells

    return (
        html_df.reset_index()
        .to_html(index=False, border=0, justify="center", classes="sov_table", escape=False)
    )

def generate_sov_html_table(df, brand, comps, sov_target_s, sov_target_e, sov_comp_s, sov_comp_e):
    df["cdate_parsed"] = pd.to_datetime(df["cdate"]).dt.date
    search_list = [brand] + comps

    df_target = df[(df["cdate_parsed"] >= sov_target_s) & (df["cdate_parsed"] <= sov_target_e)]
    df_comp   = df[(df["cdate_parsed"] >= sov_comp_s)   & (df["cdate_parsed"] <= sov_comp_e)]

    def get_sov_metrics(data_frame):
        if data_frame.empty:
            return pd.DataFrame()
        grouped = data_frame.groupby("brandid").agg({
            "overall_impressions": "sum",
            "organic_impressions": "sum",
            "ad_impressions":      "sum",
        })
        metrics = pd.DataFrame(index=grouped.index)
        metrics["Overall SOV"] = (grouped["overall_impressions"] / grouped["overall_impressions"].sum() * 100).fillna(0)
        metrics["Organic SOV"] = (grouped["organic_impressions"] / grouped["organic_impressions"].sum() * 100).fillna(0)
        metrics["Ad SOV"]      = (grouped["ad_impressions"]      / grouped["ad_impressions"].sum()      * 100).fillna(0)
        return metrics

    m_target = get_sov_metrics(df_target)
    m_comp   = get_sov_metrics(df_comp)

    if m_target.empty:
        return "<p style='color:#718096; text-align:center;'>No SOV data available for selected period</p>"

    final_view = m_target[m_target.index.isin(search_list)].copy()
    final_view = final_view.sort_values("Overall SOV", ascending=False)

    for col in ["Organic SOV", "Ad SOV", "Overall SOV"]:
        formatted = []
        for b_id in final_view.index:
            val   = final_view.at[b_id, col]
            prev  = m_comp.at[b_id, col] if b_id in m_comp.index else 0
            delta = val - prev
            color = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
            sign  = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
            formatted.append(
                f"{val:.2f}%<br>"
                f"<span style='color:{color}; font-size:11px; font-weight:600;'>"
                f"{sign}{delta:.2f}%</span>"
            )
        final_view[col] = formatted

    return (
        final_view.reset_index()
        .rename(columns={"brandid": "Brand"})
        .to_html(index=False, border=0, justify="center", classes="sov_table", escape=False)
    )


def generate_ai_insights(brand, df_avail, comps, groq_client, avail_target_s, avail_comp_s, avail_comp_e):
    """
    Returns ONLY the Executive Summary block (3 sentences).
    Key Insights and Immediate Action Required have been removed.
    """
    df_avail["report_date_parsed"] = pd.to_datetime(df_avail["report_date"]).dt.date

    df_p1 = df_avail[df_avail["report_date_parsed"] >= avail_target_s]
    df_p2 = df_avail[
        (df_avail["report_date_parsed"] >= avail_comp_s) &
        (df_avail["report_date_parsed"] <= avail_comp_e)
    ]

    brand_p1 = df_p1[df_p1["brandid"] == brand]
    brand_p2 = df_p2[df_p2["brandid"] == brand]

    if brand_p1.empty:
        return "No recent data available for AI insights."

    overall_p1    = brand_p1["is_avail"].mean() * 100
    overall_p2    = brand_p2["is_avail"].mean() * 100 if not brand_p2.empty else 0
    overall_delta = overall_p1 - overall_p2

    if overall_delta >= 3:       momentum = "strong positive"
    elif overall_delta >= 0.5:   momentum = "mild positive"
    elif overall_delta >= -0.5:  momentum = "flat"
    elif overall_delta >= -3:    momentum = "mild decline"
    else:                        momentum = "sharp decline"

    sku_p1   = brand_p1.groupby("product_name")["is_avail"].mean() * 100
    zero_skus = sku_p1[sku_p1 == 0].index.tolist()

    comp_metrics = []
    if comps:
        comp_df = df_p1[df_p1["brandid"].isin(comps)]
        if not comp_df.empty:
            comp_avail = comp_df.groupby("brandid")["is_avail"].mean() * 100
            comp_metrics = [
                {"competitor": name, "availability": round(val, 1),
                 "gap_vs_brand": round(val - overall_p1, 1)}
                for name, val in comp_avail.sort_values(ascending=False).items()
            ]

    leading_comp = comp_metrics[0] if comp_metrics else None

    metrics = {
        "brand": brand,
        "overall_availability": {
            "current_pct":  round(overall_p1, 1),
            "previous_pct": round(overall_p2, 1),
            "delta_pct":    round(overall_delta, 1),
            "momentum":     momentum,
        },
        "completely_oos_skus": zero_skus[:3],
        "leading_competitor":  leading_comp,
    }

    prompt = f"""You are a senior business intelligence analyst writing a daily performance briefing for {brand}'s sales team.
    Your tone is sharp, direct, and commercial.

    Write a concise Executive Summary in 3 sentences that covers all the key data points given below.
    Use ONLY the data in the JSON below. Do not invent numbers or names.
    DATA: {json.dumps(metrics, indent=2)}

    RULES:
    - For ANY drop or decline value, prefix it inside brackets as [[DOWN: X%]].
    - For ANY gain or increase value, prefix it as [[UP: X%]].
    - For neutral metrics (counts, percentages used as data points), use plain [[X]].
    - Do NOT put product names inside [[ ]] — only wrap % and numeric values.
    - No markdown, asterisks, bold, bullet symbols, or emojis anywhere.
    - Skip any line whose data field is null or missing.
    - Keep total output under 200 words.
    """

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ⚠️  Groq API Error: {e}")
        return "Insight generation temporarily unavailable."
    

def generate_sov_insights(brand, df_sov, comps, groq_client, sov_target_s, sov_target_e, sov_comp_s, sov_comp_e):
    """
    Returns 3 data-driven SOV insight points for our brand only.
    Covers: Paid vs Organic shift, competitor gap, SOV trend direction.
    """
    if df_sov is None or df_sov.empty:
        return ""

    df_sov["cdate_parsed"] = pd.to_datetime(df_sov["cdate"]).dt.date

    df_target = df_sov[(df_sov["cdate_parsed"] >= sov_target_s) & (df_sov["cdate_parsed"] <= sov_target_e)]
    df_comp_p = df_sov[(df_sov["cdate_parsed"] >= sov_comp_s)   & (df_sov["cdate_parsed"] <= sov_comp_e)]

    brand_t = df_target[df_target["brandid"] == brand]
    brand_c = df_comp_p[df_comp_p["brandid"] == brand]

    if brand_t.empty:
        return ""

    total_overall_t  = df_target["overall_impressions"].sum()
    total_organic_t  = df_target["organic_impressions"].sum()
    total_ad_t       = df_target["ad_impressions"].sum()

    brand_overall_t  = brand_t["overall_impressions"].sum()
    brand_organic_t  = brand_t["organic_impressions"].sum()
    brand_ad_t       = brand_t["ad_impressions"].sum()

    overall_sov_t    = round(brand_overall_t / total_overall_t * 100, 2)  if total_overall_t  else 0
    organic_sov_t    = round(brand_organic_t / total_organic_t * 100, 2)  if total_organic_t  else 0
    ad_sov_t         = round(brand_ad_t      / total_ad_t      * 100, 2)  if total_ad_t       else 0

    # Previous period
    total_overall_c  = df_comp_p["overall_impressions"].sum()
    total_organic_c  = df_comp_p["organic_impressions"].sum()
    total_ad_c       = df_comp_p["ad_impressions"].sum()

    brand_overall_c  = brand_c["overall_impressions"].sum() if not brand_c.empty else 0
    brand_organic_c  = brand_c["organic_impressions"].sum() if not brand_c.empty else 0
    brand_ad_c       = brand_c["ad_impressions"].sum()      if not brand_c.empty else 0

    overall_sov_c    = round(brand_overall_c / total_overall_c * 100, 2) if total_overall_c else 0
    organic_sov_c    = round(brand_organic_c / total_organic_c * 100, 2) if total_organic_c else 0
    ad_sov_c         = round(brand_ad_c      / total_ad_c      * 100, 2) if total_ad_c      else 0

    delta_overall    = round(overall_sov_t - overall_sov_c, 2)
    delta_organic    = round(organic_sov_t - organic_sov_c, 2)
    delta_ad         = round(ad_sov_t      - ad_sov_c,      2)

    # Leading competitor
    comp_sov_data = []
    if comps:
        comp_rows = df_target[df_target["brandid"].isin(comps)]
        if not comp_rows.empty:
            for c in comps:
                c_imp = comp_rows[comp_rows["brandid"] == c]["overall_impressions"].sum()
                c_sov = round(c_imp / total_overall_t * 100, 2) if total_overall_t else 0
                comp_sov_data.append({"name": c, "sov": c_sov})
            comp_sov_data.sort(key=lambda x: x["sov"], reverse=True)

    leading = comp_sov_data[0] if comp_sov_data else None

    metrics = {
        "brand": brand,
        "period": f"{sov_target_s} to {sov_target_e}",
        "overall_sov":          overall_sov_t,
        "organic_sov":          organic_sov_t,
        "ad_sov":               ad_sov_t,
        "delta_overall_sov":    delta_overall,
        "delta_organic_sov":    delta_organic,
        "delta_ad_sov":         delta_ad,
        "leading_competitor":   leading,
        "gap_vs_leader":        round(overall_sov_t - leading["sov"], 2) if leading else None,
    }

    # compute ad-to-organic ratio for the prompt
    ad_organic_ratio = round(ad_sov_t / organic_sov_t, 1) if organic_sov_t else None
    ad_grew_faster   = (abs(delta_ad) > abs(delta_organic)) if delta_overall != 0 else False

    prompt = f"""You are a senior e-commerce growth analyst writing a sharp, opinionated SOV briefing for {brand}'s category team.
Your tone is direct, commercial, and analytical — like a consultant presenting to a brand's leadership.
Use ONLY the JSON data below. Do not invent numbers or brand names.

DATA:
{json.dumps(metrics, indent=2)}
ad_to_organic_ratio: {ad_organic_ratio}
ad_grew_faster_than_organic: {ad_grew_faster}

Follow the structure below for each insight, and label them with the provided labels or your own based on the data:

1 — Paid vs. Organic Split: 
Label this point with a verdict like "Buying its Growth" or "Organically Led" based on whether ad_sov is significantly higher than organic_sov.
State the ad SOV and organic SOV & cover all aspects of the Split.

2 — Overall SOV Trend:
Label the phase: "Growth Phase", "Declining", or "Holding Steady" based on delta_overall_sov.
State overall SOV and the delta vs prior period.
Give insights based upon the trend.

3 — Gap vs. Leading Competitor:
State the exact gap between {brand} and the leading competitor using gap_vs_leader.
Give a commercial interpretation — what does bridging this gap require?
Comment on whether {brand} needs to convert its ad spend into organic "stickiness" or if it is already organically competitive.

RULES:
- For ANY drop/decline value, use [[DOWN: X%]] — renderer colours it red.
- For ANY gain/increase value, use [[UP: X%]] — renderer colours it green.
- For neutral data points (plain %, counts), use [[X%]] or [[X]].
- Do NOT wrap brand names, competitor names, or label text in [[ ]].
- No markdown, no asterisks, no bold (**/__ ), no bullet symbols, no emojis.
- Keep total output under 200 words.
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ⚠️  Groq SOV Insights Error: {e}")
        return ""
    

def generate_avail_insights(brand, df_avail, comps, brand_ad_sov=0.0, groq_client=None, avail_target_s=None, avail_comp_s=None, avail_comp_e=None):
    """
    Returns 3 data-driven availability insight points for our brand only.
    Covers: cities below 70%, inventory diagnosis (High Demand / Supply Gap /
    Dark Store Inefficiency), estimated SOV impact of low availability.
    """
    df_avail["report_date_parsed"] = pd.to_datetime(df_avail["report_date"]).dt.date

    df_p1 = df_avail[
        (df_avail["report_date_parsed"] >= avail_target_s) &
        (df_avail["brandid"] == brand)
    ]

    if df_p1.empty:
        return ""

    # ── City-level availability ───────────────────────────────────────────────
    city_avail = (
        df_p1[df_p1["city"].isin(TARGET_METROS)]
        .groupby("city")["is_avail"].mean() * 100
    ).round(1)

    cities_below_70 = city_avail[city_avail < 70].sort_values()
    below_70_list   = [
        {"city": city, "avail_pct": float(val)}
        for city, val in cities_below_70.items()
    ]

    overall_avail = round(df_p1["is_avail"].mean() * 100, 1)

    # ── Inventory diagnosis per city ─────────────────────────────────────────
    # avg_inventory > 0 but is_avail low  → Dark Store Inefficiency
    # avg_inventory ~ 0 across all stores → Supply Gap
    # avg_inventory was higher previously → High Demand rundown

    df_p2 = df_avail[
        (df_avail["report_date_parsed"] >= avail_comp_s) &
        (df_avail["report_date_parsed"] <= avail_comp_e) &
        (df_avail["brandid"] == brand)
    ]

    diagnosis_data = []
    for city, row in cities_below_70.items():
        city_rows_p1 = df_p1[df_p1["city"] == city]
        city_rows_p2 = df_p2[df_p2["city"] == city] if not df_p2.empty else pd.DataFrame()

        avg_inv_p1   = city_rows_p1["inventory"].mean() if "inventory" in city_rows_p1.columns else 0
        avg_inv_p2   = city_rows_p2["inventory"].mean() if (not city_rows_p2.empty and "inventory" in city_rows_p2.columns) else 0

        stores_with_inv  = (city_rows_p1["inventory"] > 0).sum()
        total_stores_c   = len(city_rows_p1)
        stores_with_inv_pct = round(stores_with_inv / total_stores_c * 100, 1) if total_stores_c else 0

        if avg_inv_p1 > 5 and stores_with_inv_pct < float(row):
            diagnosis = "Dark Store Inefficiency"
            reason    = f"avg inventory of {round(avg_inv_p1,1)} units exists but only {stores_with_inv_pct}% of stores show it as available"
        elif avg_inv_p1 <= 2 and avg_inv_p2 > avg_inv_p1 + 2:
            diagnosis = "High Demand"
            reason    = f"avg inventory dropped from {round(avg_inv_p2,1)} to {round(avg_inv_p1,1)} units vs prior period"
        else:
            diagnosis = "Supply Gap"
            reason    = f"avg inventory is only {round(avg_inv_p1,1)} units across all stores"

        diagnosis_data.append({
            "city":        city,
            "avail_pct":   float(row),
            "diagnosis":   diagnosis,
            "detail":      reason,
        })

    # ── Estimated SOV impact ─────────────────────────────────────────────────
    # Heuristic: each 10% drop in availability in a tier-1 city (Mumbai, Delhi,
    # Bengaluru, Hyderabad) is weighted 1.5x vs other metros.
    TIER1 = {"Mumbai", "Delhi", "Bengaluru", "Hyderabad"}
    sov_impact_score = 0.0
    for entry in diagnosis_data:
        drop      = max(0, 70 - entry["avail_pct"])
        weight    = 1.5 if entry["city"] in TIER1 else 1.0
        sov_impact_score += (drop / 10) * weight

    if sov_impact_score >= 4:
        impact_level = "high"
    elif sov_impact_score >= 2:
        impact_level = "moderate"
    else:
        impact_level = "low"

    # pass through ad_sov if available from caller — set via generate_avail_insights signature
    metrics = {
        "brand":                      brand,
        "overall_availability_pct":   overall_avail,
        "cities_below_70_pct":        below_70_list,
        "all_metro_availability":     [
            {"city": city, "avail_pct": float(val), "delta_pct": round(float(val) - float(
                (df_p2[df_p2["city"] == city]["is_avail"].mean() * 100)
                if (not df_p2.empty and city in df_p2["city"].values) else val
            ), 1)}
            for city, val in city_avail.items()
        ],
        "inventory_diagnosis":        diagnosis_data[:4],
        "estimated_sov_impact_level": impact_level,
        "sov_impact_score":           round(sov_impact_score, 1),
        "tier1_cities_below_70":      [e for e in diagnosis_data if e["city"] in {"Mumbai", "Delhi", "Bengaluru", "Hyderabad"}],
        "brand_ad_sov":               brand_ad_sov,
    }

    prompt = f"""You are a senior e-commerce growth analyst writing a sharp, opinionated availability briefing for {brand}'s sales team.
Your tone is direct, commercial, and analytical — like a consultant flagging real business risk.
Use ONLY the JSON data below. Do not invent numbers, city names, or diagnoses.

DATA:
{json.dumps(metrics, indent=2)}

Write exactly 3 insight points numbered 1, 2, 3.
Each point has a short label followed by 2–4 sentences of narrative analysis.

1 — Regional Hotspots:
Identify which cities are below 70% availability and label them as "Red Zone."
State exact availability % for each city and its delta vs prior period using [[DOWN:]] or [[UP:]].
For cities above 70% but showing declining trends, call them out as warning signs with their delta.
Compare against the brand's network average.

2 — Inventory Diagnosis:
Write this as a paragraph with sub-labels for each diagnosis type found in the data:
- "High Demand (Efficiency Leak):" — inventory ran down due to sales velocity, often seen as a positive but a stock risk.
- "Supply Gap:" — stock never arrived or is consistently absent, a supply chain failure.
- "Dark Store Inefficiency:" — inventory physically exists but is not surfaced to users, a last-mile or listing issue.
Only include the diagnosis types that actually appear in inventory_diagnosis. Use city names and specific % from the data.

3 — Estimated SOV Impact:
Use tier1_cities_below_70 and brand_ad_sov from the data.
For each Tier-1 city with low availability, call out the risk explicitly:
  - If brand_ad_sov is high (>5%) and the city is below 70%, flag it as "HIGH RISK — wasted ad spend: you are paying for clicks that cannot convert."
  - If the city is declining but above 70%, flag as "MODERATE — watch zone."
Use [[X]] HIGH RISK and [[DOWN:]] MODERATE as labels in your output.
Close with one sentence on what the combined sov_impact_score means for organic visibility.

RULES:
- For ANY drop/decline value, use [[DOWN: X%]] — renderer colours it red.
- For ANY gain/increase value, use [[UP: X%]] — renderer colours it green.
- For risk labels and neutral data (availability levels, counts), use [[X]] — renderer shows green pill.
- Do NOT wrap city names, brand names, or diagnosis labels in [[ ]] — only wrap numeric values and risk-level labels.
- No markdown, no asterisks, no bold (**/__ ), no bullet symbols, no emojis.
- Keep total output under 250 words.
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=650,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ⚠️  Groq Avail Insights Error: {e}")
        return ""
    
def format_insight_html(text):
    """
    [[DOWN: X%]]  → red bold text
    [[UP: X%]]    → green bold text
    [[X]]         → green pill badge
    """
    # Step 1: directional tags
    text = re.sub(
        r'\[\[DOWN:\s*(.+?)\]\]',
        lambda m: f'<span style="color:#dc2626; font-weight:700;">{m.group(1).strip()}</span>',
        text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\[\[UP:\s*(.+?)\]\]',
        lambda m: f'<span style="color:#16a34a; font-weight:700;">{m.group(1).strip()}</span>',
        text, flags=re.IGNORECASE
    )

    # Step 2: remaining [[value]] → green pill badge
    def pill(m):
        val = m.group(1).strip()
        return (
            f'<span style="display:inline-block; background-color:#f0fdf4; '
            f'color:#15803d; font-weight:700; padding:1px 8px; border-radius:4px; '
            f'border:1px solid #bbf7d0; font-size:13px; white-space:nowrap;">{val}</span>'
        )
    text = re.sub(r'\[\[(.+?)\]\]', pill, text)

    # Step 3: line-by-line rendering
    lines      = text.strip().splitlines()
    html_parts = []
    i          = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        if line.startswith("Executive Summary"):
            html_parts.append(
                '<p style="font-size:13px; font-weight:700; color:#1e293b; '
                'margin:0 0 6px 0;">Executive Summary:</p>'
            )

        elif re.match(r'^[1-3]\.\s', line):
            html_parts.append(
                f'<p style="font-size:13px; color:#334155; line-height:1.7; '
                f'margin:0 0 6px 0;">{line}</p>'
            )

        else:
            html_parts.append(
                f'<p style="font-size:13px; color:#334155; line-height:1.7; '
                f'margin:0 0 6px 0;">{line}</p>'
            )

        i += 1

    return "\n".join(html_parts)


def build_email_html(brand, person_name, ai_content,
                     sov_html, sov_insights_html,
                     avail_html, avail_insights_html,
                     unsub_link,avail_base_str, avail_delta_str, sov_base_str, sov_delta_str,yesterday,Q_COMM_NAME, DASHBOARD_URL):
    return f"""
        <html><head><style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f0f2f5; margin:0; padding:0; }}
            .container {{ max-width: 700px; margin: 40px auto; background-color: #ffffff; border-radius: 4px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .header {{ background-color: #70DD44; padding: 35px 25px; text-align: center; color: #000; }}
            .content {{ padding: 30px; color: #3c4858; line-height: 1.5; }}
            .context-box {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 25px 0; font-size: 13px; }}
            .insight-section {{ border-left: 4px solid #70DD44; padding-left: 20px; margin: 25px 0; }}
            .sub-insight-box {{
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 16px 20px;
                margin-top: 16px;
            }}
            .sub-insight-label {{
                font-size: 11px;
                font-weight: 700;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                margin: 0 0 10px 0;
            }}
            .sov_table {{ width: 100%; border-collapse: collapse; font-size: 12px; border: 1px solid #e2e8f0; text-align: center; margin-top: 15px; }}
            .sov_table th {{ background-color: #f1f5f9; padding: 12px; border-bottom: 2px solid #e2e8f0; }}
            .sov_table td {{ padding: 12px; border-bottom: 1px solid #f1f5f9; }}
        </style></head><body>
            <div style="background-color: #f0f2f5; padding: 40px 20px; text-align: center;">
                <img src="cid:logo" width="190" style="margin-bottom: 25px;">
                <div class="container" style="text-align: left;">
                    <div class="header">
                        <h2 style="margin:0; font-size:15px; font-weight:500;">Daily summary for</h2>
                        <h1 style="margin:10px 0; font-size:32px; font-weight:900;">{brand}</h1>
                        <div style="background-color: #ffffff; padding: 8px 24px; border-radius: 20px; display: inline-block; font-weight: 500;">Platform : {Q_COMM_NAME}</div>
                    </div>
                    <div class="content">
                        <p>Hello {person_name},</p>
                        <p>We are excited to share the performance updates of last 24 hours for your <b>{Q_COMM_NAME}</b> store. This is a summarised view of key performance indicators around SOV &amp; Availability. For a detailed view please login to your <a href="{DASHBOARD_URL}" style="color: #3182ce; font-weight:600;">Zodiac Dashboard</a>. Help us improve with your feedback and inputs by responding to this email.</p>

                        <!-- Executive Summary -->
                        <div class="insight-section">
                            <h3 style="margin-top:0; font-size:16px;">Executive Summary</h3>
                            <div style="font-size:14px; line-height:1.6;">
                                {format_insight_html(ai_content)}
                            </div>
                        </div>

                        <!-- Comparison Period Context -->
                        <div class="context-box">
                            <p><b>Comparison periods used to calculate ▲/▼ changes in the tables below:</b></p>
                            <p><strong>1. Share of Voice (SOV)</strong></p>
                            <ul>
                                <li><strong>Base Data:</strong> Last 1-day ({yesterday})</li>
                                <li><strong>Delta (%):</strong> Compared against previous 6-day average ({sov_delta_str})</li>
                            </ul>
                            <p><strong>2. Top Metro-wise Availability</strong></p>
                            <ul>
                                <li><strong>Base Data:</strong> Last 3-day average ({avail_base_str})</li>
                                <li><strong>Delta (%):</strong> Compared against previous 3-day average ({avail_delta_str})</li>
                            </ul>
                        </div>

                        <!-- SOV Section -->
                        <h3 style="font-size:14px; font-weight:700;">1. Brand-wise Share of Voice (SOV)</h3>
                        {sov_html}

                        <!-- SOV Insights -->
                        {f'''<div class="sub-insight-box">
                            <p class="sub-insight-label">&#128200;&nbsp; SOV Insights</p>
                            {format_insight_html(sov_insights_html)}
                        </div>''' if sov_insights_html else ''}

                        <!-- Availability Section -->
                        <h3 style="font-size:14px; font-weight:700; margin-top:30px;">2. Top Metro-wise Availability Report</h3>
                        {avail_html}

                        <!-- Availability Insights -->
                        {f'''<div class="sub-insight-box">
                            <p class="sub-insight-label">&#128205;&nbsp; Availability Insights</p>
                            {format_insight_html(avail_insights_html)}
                        </div>''' if avail_insights_html else ''}

                    </div>
                </div>
                <div class="footer">
                    <div class="social-icons" style="margin-bottom: 16px;">
                        <a href="{LINK_LI}"><img src="cid:li"></a>
                        <a href="{LINK_WEB}"><img src="cid:web"></a>
                    </div>
                    <div style="font-size:12px; color:#475569; font-weight:600; margin-bottom:10px;">© 2026 Zodiac by Nitro</div>
                    <div style="font-size: 12px; color: #64748b;">Don't wish to stay in the know-how?<a href="{unsub_link}" target="_blank" style="color: #475569;"> Unsubscribe</a></div>
                </div>
                <p style="font-size:12px; color:#64748b; margin-top: 20px;">© 2026 Zodiac by Nitro</p>
            </div>
        </body></html>
"""