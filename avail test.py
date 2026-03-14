import os
import pandas as pd
from datetime import datetime, timedelta
from helper import execute_copy_query_via_bastion

# ================= CONFIG =================
BASE_PATH = r"C:\Users\User1\Desktop\autmation codes\availability\zodiac-scripts-main\AVAIL"
os.makedirs(BASE_PATH, exist_ok=True)

FINAL_EXCEL = os.path.join(BASE_PATH, "Availability_Daily_Trend_Pro.xlsx")
RAW_DATA_GZ = os.path.join(BASE_PATH, "C_availability_export.csv.gz")

BRAND_KEYWORDS = ["Chaayos"]

# ================= DYNAMIC DATE LOGIC =================
today = datetime.now()
yesterday = (today - timedelta(days=1)).replace(hour=18, minute=30, second=0)
seven_days_ago = (yesterday - timedelta(days=6))

start_date_str = seven_days_ago.strftime('%Y-%m-%d 18:30:00')
end_date_str = yesterday.strftime('%Y-%m-%d 18:30:00')

# ================= SQL QUERY =================
brand_filter = " OR ".join([f"bp.name ILIKE '%{k}%'" for k in BRAND_KEYWORDS])

copy_query = f"""
\\pset format csv
\\pset tuples_only off
SELECT
    bp."brandId" AS brandid,
    bp.id AS productid,
    bp.name AS product_name,
    bm."cityName" AS city,
    bm.name AS store_name,
    bpm.inventory,
    DATE(bpm."createdAt") as report_date
FROM "BlinkitProductMerchant" bpm
JOIN "BlinkitProduct" bp ON bp.id = bpm."productId"
JOIN "BlinkitMerchant" bm ON bm.id = bpm."merchantId"
WHERE bpm."createdAt" BETWEEN TIMESTAMP '{start_date_str}' AND TIMESTAMP '{end_date_str}'
AND ({brand_filter});
"""

def process_data():
    print(f"🚀 Fetching data for period: {seven_days_ago.date()} to {yesterday.date()}")
    success, message, _ = execute_copy_query_via_bastion(copy_query, RAW_DATA_GZ)

    if not success or os.path.getsize(RAW_DATA_GZ) < 100:
        print("❌ No data returned or query failed.")
        return

    # ================= LOAD & PIVOT =================
    df = pd.read_csv(RAW_DATA_GZ, compression="gzip", skiprows=1, engine="python", on_bad_lines="skip")
    df.columns = df.columns.str.strip().str.lower()
    df["is_available"] = (df["inventory"] > 0).astype(int)
    
    # Create pivot
    pivot_df = df.pivot_table(
        index=['brandid', 'productid', 'product_name', 'city', 'store_name'],
        columns='report_date',
        values='is_available',
        aggfunc='mean'
    ).reset_index()

    # Get Avg Qty
    avg_qty = df.groupby(['productid', 'store_name'])['inventory'].mean().reset_index().rename(columns={'inventory': 'Avg Qty'})
    final_df = pivot_df.merge(avg_qty, on=['productid', 'store_name'], how='left')

    # Identify Date Columns and Sort (Latest Date First)
    date_cols = sorted([c for c in pivot_df.columns if '-' in str(c)], reverse=True)
    static_cols = ['brandid', 'productid', 'product_name', 'city', 'store_name', 'Avg Qty']
    final_df = final_df[static_cols + date_cols]

    # SORTING: High to Low based on the LATEST date
    latest_date = date_cols[0]
    final_df = final_df.sort_values(by=[latest_date, 'product_name'], ascending=[False, True])

    # ================= PRO EXCEL FORMATTING =================
    print("📝 Applying Professional Formatting...")
    with pd.ExcelWriter(FINAL_EXCEL, engine="xlsxwriter") as writer:
        final_df.to_excel(writer, sheet_name="Availability Report", index=False)
        
        workbook = writer.book
        worksheet = writer.sheets["Availability Report"]
        worksheet.hide_gridlines(2) # Remove Gridlines

        # --- FORMAT DEFINITIONS ---
        # Header: Bold, centered, solid border
        header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#F2F2F2'})
        
        # Data Body: Dotted internal borders (style 3 or 7 in xlsxwriter)
        base_fmt = workbook.add_format({'bottom': 3, 'top': 3, 'left': 3, 'right': 3, 'align': 'left'})
        
        # Column Formats
        pct_fmt = workbook.add_format({'num_format': '0%', 'align': 'center', 'bottom': 3, 'top': 3, 'left': 3, 'right': 3})
        num_fmt = workbook.add_format({'align': 'center', 'bottom': 3, 'top': 3, 'left': 3, 'right': 3})
        
        # Heatmap Colors (with dotted borders)
        red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'bottom': 3, 'top': 3, 'left': 3, 'right': 3})
        yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500', 'bottom': 3, 'top': 3, 'left': 3, 'right': 3})
        green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'bottom': 3, 'top': 3, 'left': 3, 'right': 3})

        # --- APPLY LAYOUT ---
        rows = len(final_df)
        cols = len(final_df.columns)

        # Apply Headers
        for col_num, value in enumerate(final_df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)

        # Apply Body Dotted Borders & Column Widths
        worksheet.set_column('A:B', 10, num_fmt)     # IDs
        worksheet.set_column('C:C', 35, base_fmt)    # Product Name
        worksheet.set_column('D:E', 20, base_fmt)    # City/Store
        worksheet.set_column('F:F', 12, num_fmt)     # Avg Qty
        
        # Apply Date Column Formatting & Heatmap
        start_date_col = len(static_cols)
        for c in range(start_date_col, cols):
            worksheet.set_column(c, c, 12, pct_fmt)
            # Conditional Heatmap
            worksheet.conditional_format(1, c, rows, c,
                {'type': 'cell', 'criteria': '<', 'value': 0.50, 'format': red})
            worksheet.conditional_format(1, c, rows, c,
                {'type': 'cell', 'criteria': 'between', 'minimum': 0.50, 'maximum': 0.79, 'format': yellow})
            worksheet.conditional_format(1, c, rows, c,
                {'type': 'cell', 'criteria': '>=', 'value': 0.80, 'format': green})

        # Freeze Panes (Keep headers and names visible)
        worksheet.freeze_panes(1, 3)

    print(f"✅ DONE! Report ready at: {FINAL_EXCEL}")

if __name__ == "__main__":
    process_data()