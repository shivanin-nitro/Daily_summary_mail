import os
import pandas as pd
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
# Assuming helper is in your directory
from helper import execute_copy_query_via_bastion

# ================= CONFIG =================
SENDER_EMAIL = "shivani.n@getnitro.co"
SENDER_PASSWORD = "nyul zpkf euji sjwk"
CC_EMAILS = ["shivani.n@getnitro.co"]

BRAND_EMAILS = {
    "ZAVYA": "shivaninagar918@gmail.com",
    "PINQ POLKA": "sargam.s@getnitro.co",
    "Tuco Kids": "shivaninagar918@gmail.com",
    "Nutrabay": "shivaninagar918@gmail.com",
    "Eume": "shivaninagar918@gmail.com",
    "Imagimake": "shivaninagar918@gmail.com",
    "Forest Essentials": "shivaninagar918@gmail.com",
    "Nuvie": "shivaninagar918@gmail.com",
    "Chaayos": "shivaninagar918@gmail.com",
    "Kilobeaters": "shivaninagar918@gmail.com",
    "Bambino": "shivaninagar918@gmail.com",
    "Jimmy''s": "shivaninagar918@gmail.com"
}

COMPETITORS = {
    "Zavya": ["GIVA","Palmonas","CLARA"," Unniyarcha","Shaya by Caratlane"],
    "PINQ POLKA":[ "Sanfe" ,  "Underneat" ,"Bare Wear","Boldfit" , "Sirona"],
    "Tuco Kids":["LuvLap", "Aveeno", "Sebamed", "Toyshine"],
    "Eume":["Daily Objects", "Nasher Miles", "Mokobara", "Urban Jungle"],
    "Imagimake":["Toyshine", "Wembley", "Skillmatics", "Funskool"],
    "Nutrabay": ["The Whole Truth", "MuscleBlaze", "TrueBasics", "SuperYou"],
    "Forest Essentials": ["Dot & Key", "Minimalist", "Foxtale", "Cetaphil"],
    "Bambino": ["Hommade", "Ching''s Secret", "Tata Sampann", "Whole Farm", "Disano"],
    "Nuvie": [ "Amul", "Nescafe", "Cavin''s", "Mother Dairy", "Sleepy Owl"],
    "Chaayos": ["Brooke Bond Red Label", "Wagh Bakri", "Lipton", "Society"],
    "Kilobeaters": ["RiteBite", "SuperYou", "The Whole Truth", "Crax"],
    "Jimmy''s" : ["paper boat", "Schweppes","Absolut Mixers","Sepoy & Co."]
}

TARGET_METROS = ["Pune","Delhi" ,"Mumbai","UP-NCR","UP-HR","Hyderabad","Bengaluru"]
ALL_BRANDS = ["Zavya","Nutrabay","PINQ POLKA","Tuco Kids","Eume","Imagimake","Forest Essentials","Nuvie","Bambino","Jimmy''s","Soulflower","Kilobeaters","Chaayos","Gala","Oyo Baby","Winston","Ecoright","Nish Hair","Freecultr","Spinbot"]

DEFAULT_RECIPIENT = "shivani.n@getnitro.co"
BASE_PATH = r"C:\Users\User1\Desktop\autmation codes\availability\AVAIL"
os.makedirs(BASE_PATH, exist_ok=True)

# ================= DATE SETUP =================
today = datetime.now()
yesterday = (today - timedelta(days=1)).date()
seven_days_ago = (yesterday - timedelta(days=6))
date_range_list = [(seven_days_ago + timedelta(days=x)) for x in range(7)]
date_range_str = f"{seven_days_ago.strftime('%d %b')} - {yesterday.strftime('%d %b %Y')}"

# SOV DATES: Target (Last 3 days window), Comparison (Previous 6 days window)
sov_target_start = (today - timedelta(days=2)).date()
sov_target_end = yesterday
sov_comp_start = (today - timedelta(days=8)).date()
sov_comp_end = (today - timedelta(days=3)).date()

sov_date_str = f"{sov_target_start.strftime('%d %b')} - {sov_target_end.strftime('%d %b %Y')}"
sov_comp_str = f"{sov_comp_start.strftime('%d %b')} - {sov_comp_end.strftime('%d %b %Y')}"

# AVAILABILITY DATES (Last 3 days vs Previous 3 days)
avail_target_start = yesterday - timedelta(days=2)
avail_comp_start = yesterday - timedelta(days=5)
avail_comp_end = yesterday - timedelta(days=3)

avail_target_str = f"{avail_target_start.strftime('%d %b')} - {yesterday.strftime('%d %b %Y')}"
avail_comp_str = f"{avail_comp_start.strftime('%d %b')} - {avail_comp_end.strftime('%d %b %Y')}"

# ================= QUERIES =================
def get_avail_query(brand_name, competitor_list):
        search_list = [brand_name] + competitor_list
        brand_filter = f"bp.\"brandId\" IN ({', '.join([repr(b) for b in search_list])})"
        return f"""
         \pset format csv
         \pset tuples_only off
         SELECT bp."brandId" AS brandid, bp.id AS productid, bp.name AS product_name, 
             bm."cityName" AS city, bm.name AS store_name, bpm.inventory, 
             DATE(bpm."createdAt") as report_date
         FROM "BlinkitProductMerchant" bpm
         JOIN "BlinkitProduct" bp ON bp.id = bpm."productId"
         JOIN "BlinkitMerchant" bm ON bm.id = bpm."merchantId"
         WHERE bpm."createdAt" BETWEEN TIMESTAMP '{seven_days_ago.strftime('%Y-%m-%d')} 18:30:00.00'
         AND TIMESTAMP '{yesterday.strftime('%Y-%m-%d')} 18:30:00.00'
         AND {brand_filter}
        """

def get_sov_query(brand_name):
    return f"""
        \pset format csv
        \pset tuples_only off
        WITH base AS (
            SELECT cdate, keywordid, brandid, cityname, categoryid, subcategoryid,
                   SUM(COALESCE(overall_impressions,0)) AS overall_impressions,
                   SUM(COALESCE(organic_impressions,0)) AS organic_impressions,
                   SUM(COALESCE(ad_impressions,0)) AS ad_impressions
            FROM blinkit_impressions
            WHERE cdate >= '{sov_comp_start.strftime('%Y-%m-%d')} 18:30:00.00'
            AND cdate <= '{sov_target_end.strftime('%Y-%m-%d')} 18:30:00.00'
            AND (categoryid, subcategoryid) IN (
                SELECT DISTINCT categoryid, subcategoryid FROM blinkitproduct WHERE brandid = '{brand_name}'
            )
            GROUP BY 1,2,3,4,5,6
        )
        SELECT * FROM base
    """

def generate_availability_html_table(df):
    filtered_df = df[df['city'].isin(TARGET_METROS)].copy()
    if filtered_df.empty:
        return "<p style='color:#718096; text-align:center;'>No Availability data</p>"

    # Safely get max date in dataset to prevent 0% errors
    latest_date = filtered_df['report_date'].max()

    # Define date ranges: X = Last 3 days, Y = Previous 3 days
    p1_dates = [latest_date - timedelta(days=i) for i in range(3)]
    p2_dates = [latest_date - timedelta(days=i) for i in range(3, 6)]

    df_p1 = filtered_df[filtered_df['report_date'].isin(p1_dates)]
    df_p2 = filtered_df[filtered_df['report_date'].isin(p2_dates)]

    avail_p1 = df_p1.pivot_table(index='city', columns='brandid', values='is_avail', aggfunc='mean').fillna(0) * 100
    avail_p2 = df_p2.pivot_table(index='city', columns='brandid', values='is_avail', aggfunc='mean').fillna(0) * 100

    html_df = pd.DataFrame(index=avail_p1.index)

    for col in avail_p1.columns:
        formatted_cols = []
        for city in avail_p1.index:
            val = avail_p1.at[city, col] if city in avail_p1.index else 0
            prev_val = avail_p2.at[city, col] if (col in avail_p2.columns and city in avail_p2.index) else 0
            
            delta = val - prev_val
            color = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
            sign = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
            
            cell_html = f"{int(round(val))}%<br><span style='color:{color}; font-size: 11px; font-weight:600;'>{sign}{delta:.2f}%</span>"
            formatted_cols.append(cell_html)
        html_df[col] = formatted_cols

    html_df = html_df.reset_index()
    html_df.columns.name = None
    if 'brandid' in html_df.columns:
        html_df = html_df.drop(columns=['brandid'])
    
    return html_df.to_html(index=False, border=0, justify='center', classes='sov_table', escape=False)

# ================= PIPELINE =================
def run_pipeline():
    for brand in ALL_BRANDS:
        print(f"\n🚀 Processing {brand}")
        comps = COMPETITORS.get(brand, [])
        avail_xlsx = os.path.join(BASE_PATH, f"{brand}_Availability_Report.xlsx")
        sov_xlsx = os.path.join(BASE_PATH, f"{brand}_SOV_Analysis.xlsx")
        temp_avail = os.path.join(BASE_PATH, f"{brand}_avail.csv.gz")
        temp_sov = os.path.join(BASE_PATH, f"{brand}_sov.csv.gz")

        success_a, _, _ = execute_copy_query_via_bastion(get_avail_query(brand, comps), temp_avail)
        success_s, _, _ = execute_copy_query_via_bastion(get_sov_query(brand), temp_sov)

        # ================= 1. AVAILABILITY PROCESS =================
        avail_html = "<p style='color:#718096; text-align:center;'>No Availability data</p>"
        if success_a and os.path.getsize(temp_avail) > 150:
            df_a = pd.read_csv(temp_avail, compression="gzip", skiprows=1)
            df_a.columns = df_a.columns.str.strip().str.lower()
            df_a["is_avail"] = (df_a["inventory"] > 0).astype(float)
            df_a['report_date'] = pd.to_datetime(df_a['report_date']).dt.date

            avail_html = generate_availability_html_table(df_a)
            brand_only_df = df_a[df_a['brandid'] == brand].copy()
            
            with pd.ExcelWriter(avail_xlsx, engine="xlsxwriter") as writer:
                pivot = brand_only_df.pivot_table(
                    index=['brandid','productid','product_name','city','store_name'],
                    columns='report_date', values='is_avail', aggfunc='mean'
                )

                pivot = pivot.reindex(columns=date_range_list)
                pivot = pivot.ffill(axis=1).fillna("PNA")
                pivot = pivot.reset_index()

                pivot.to_excel(writer, sheet_name="Availability", index=False)
                
                workbook = writer.book
                worksheet = writer.sheets["Availability"]
                
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1, 'align': 'center'})
                border_fmt = workbook.add_format({'border': 1, 'align': 'center'})
                pna_fmt = workbook.add_format({'bg_color': '#F4CCCC', 'font_color': '#980000', 'border': 1})
                red_fmt = workbook.add_format({'bg_color': '#F4CCCC', 'font_color': '#980000', 'border': 1, 'num_format': '0%'})
                yellow_fmt = workbook.add_format({'bg_color': '#FFF2CC', 'font_color': '#BF9000', 'border': 1, 'num_format': '0%'})
                green_fmt = workbook.add_format({'bg_color': '#D9EAD3', 'font_color': '#38761D', 'border': 1, 'num_format': '0%'})

                worksheet.hide_gridlines(2)
                
                for col_num, value in enumerate(pivot.columns.values):
                    worksheet.write(0, col_num, str(value), header_fmt)
                    worksheet.set_column(col_num, col_num, 15, border_fmt)

                rows = len(pivot)
                cols = len(pivot.columns)
                date_range_cells = f"F2:{xlsxwriter_col_name(cols-1)}{rows+1}"
                
                worksheet.conditional_format(date_range_cells, {'type': 'text', 'criteria': 'containing', 'value': 'PNA', 'format': pna_fmt})
                worksheet.conditional_format(date_range_cells, {'type': 'cell', 'criteria': '<', 'value': 0.5, 'format': red_fmt})
                worksheet.conditional_format(date_range_cells, {'type': 'cell', 'criteria': 'between', 'minimum': 0.5, 'maximum': 0.79, 'format': yellow_fmt})
                worksheet.conditional_format(date_range_cells, {'type': 'cell', 'criteria': '>=', 'value': 0.8, 'format': green_fmt})

        # ================= 2. SOV PROCESS =================
        sov_html = "<p style='color:#718096; text-align:center;'>No SOV data</p>" # Safe-guard fallback
        if success_s and os.path.getsize(temp_sov) > 150:
            df_s = pd.read_csv(temp_sov, compression="gzip", skiprows=1, engine="python", on_bad_lines="skip")
            df_s.columns = df_s.columns.str.strip().str.lower()
            df_s['cdate_parsed'] = pd.to_datetime(df_s['cdate'], errors='coerce').dt.date

            # Split data into Target (3 days) and Comp (6 days)
            df_s_target = df_s[(df_s['cdate_parsed'] >= sov_target_start) & (df_s['cdate_parsed'] <= sov_target_end)]
            df_s_comp = df_s[(df_s['cdate_parsed'] >= sov_comp_start) & (df_s['cdate_parsed'] <= sov_comp_end)]

            if not df_s_target.empty:
                brand_table = df_s_target.groupby("brandid").agg({"overall_impressions":"sum", "organic_impressions":"sum", "ad_impressions":"sum"}).reset_index()
                for col in ["overall", "organic", "ad"]:
                    brand_table[f"{col}_sov_%"] = (brand_table[f"{col}_impressions"] / brand_table[f"{col}_impressions"].sum()) * 100
                
                brand_table_clean = brand_table[["brandid","organic_sov_%","ad_sov_%","overall_sov_%"]].sort_values("overall_sov_%", ascending=False)
                
                city_brand = df_s_target.groupby(["cityname","brandid"]).agg({"overall_impressions":"sum", "organic_impressions":"sum", "ad_impressions":"sum"}).reset_index()
                city_totals = city_brand.groupby("cityname")[["overall_impressions","organic_impressions","ad_impressions"]].transform("sum")
                city_brand["overall_sov_%"] = (city_brand["overall_impressions"] / city_totals["overall_impressions"]) * 100
                city_brand["organic_sov_%"] = (city_brand["organic_impressions"] / city_totals["organic_impressions"]) * 100
                city_brand["ad_sov_%"] = (city_brand["ad_impressions"] / city_totals["ad_impressions"]) * 100
                city_brand = city_brand[["cityname","brandid","organic_sov_%","ad_sov_%","overall_sov_%"]].sort_values(["cityname","overall_sov_%"], ascending=[True,False])

                # Calculate SOV for the comparison period (previous 6 days)
                brand_comp = df_s_comp.groupby("brandid").agg({"overall_impressions":"sum", "organic_impressions":"sum", "ad_impressions":"sum"}).reset_index()
                for col in ["overall", "organic", "ad"]:
                    brand_comp[f"{col}_sov_%"] = (brand_comp[f"{col}_impressions"] / brand_comp[f"{col}_impressions"].sum()) * 100
                
                brand_comp_idx = brand_comp.set_index("brandid")

                html_sov_df = brand_table_clean[brand_table_clean["brandid"].isin([brand] + comps)].copy()

                for col in ["organic_sov_%", "ad_sov_%", "overall_sov_%"]:
                    formatted_vals = []
                    for idx, row in html_sov_df.iterrows():
                        brand_id = row['brandid']
                        x_val = row[col]
                        y_val = brand_comp_idx.at[brand_id, col] if brand_id in brand_comp_idx.index else 0
                        
                        delta = x_val - y_val
                        color = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
                        sign = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
                        
                        formatted_vals.append(f"{x_val:.2f}%<br><span style='color:{color}; font-size: 11px; font-weight:600;'>{sign}{delta:.2f}%</span>")
                    html_sov_df[col] = formatted_vals

                html_sov_df.rename(columns={'brandid': 'Brand', 'organic_sov_%': 'Organic SOV', 'ad_sov_%': 'Ad SOV', 'overall_sov_%': 'Overall SOV'}, inplace=True)
                sov_html = html_sov_df.to_html(index=False, border=0, justify='center', classes='sov_table', escape=False)

                with pd.ExcelWriter(sov_xlsx, engine="xlsxwriter") as writer:
                    brand_table_clean.to_excel(writer, sheet_name="Brand_SOV", index=False)
                    city_brand.to_excel(writer, sheet_name="City_Brand_SOV", index=False)
                    
                    workbook = writer.book
                    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#CFE2F3', 'border': 1, 'align': 'center'})
                    data_fmt = workbook.add_format({'border': 1})

                    for sheet_name in ["Brand_SOV", "City_Brand_SOV"]:
                        ws = writer.sheets[sheet_name]
                        ws.hide_gridlines(2)
                        df_to_format = brand_table_clean if sheet_name == "Brand_SOV" else city_brand
                        for col_num, value in enumerate(df_to_format.columns.values):
                            ws.write(0, col_num, value, header_fmt)
                            ws.set_column(col_num, col_num, 18, data_fmt)

        # ================= EMAIL SENDER =================
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Cc'] = SENDER_EMAIL, BRAND_EMAILS.get(brand, DEFAULT_RECIPIENT), ", ".join(CC_EMAILS)
        msg['Subject'] = f"Performance Summary: {brand} – {yesterday.strftime('%b %d, %Y')}"

        body = f"""
        <html>
        <head>
            <style>
                body {{ margin: 0; padding: 0; background-color: #f4f5f7; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
                .email-wrapper {{ background-color: #f4f5f7; padding: 40px 20px; }}
                .email-container {{ max-width: 800px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); overflow: hidden; }}
                
                .email-header {{ background-color: #F8CB46; color: #000000; padding: 35px 20px; text-align: center; }}
                .email-header h2 {{ margin: 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #4A5568; font-weight: 600; }}
                .email-header h1 {{ margin: 10px 0 20px 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }}
                .date-badge {{ background-color: #000000; color: #ffffff; padding: 6px 20px; border-radius: 20px; font-size: 13px; font-weight: 700; display: inline-block; }}
                
                .email-body {{ padding: 35px; color: #4a5568; line-height: 1.6; }}
                .greeting {{ font-size: 16px; font-weight: 600; color: #2d3748; margin-bottom: 12px; }}
                .intro-text {{ font-size: 14px; margin-bottom: 30px; color: #4A5568; }}
                
                .context-box {{ background-color: #F7FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 15px 20px; margin-top: 15px; font-size: 13px; }}
                .context-box p {{ margin: 0 0 8px 0; color: #2d3748; }}
                .context-box ul {{ margin: 0 0 15px 0; padding-left: 20px; color: #4A5568; }}
                .context-box ul:last-child {{ margin-bottom: 0; }}
                
                .section-title {{ font-size: 16px; font-weight: 700; color: #2d3748; margin-bottom: 15px; border-bottom: 2px solid #edf2f7; padding-bottom: 8px; }}
                
                .sov_table {{ width: 100%; border-collapse: collapse; margin-bottom: 40px; font-size: 13px; border: 1px solid #E2E8F0; border-radius: 6px; overflow: hidden; }}
                .sov_table th {{ background-color: #F7FAFC; color: #4A5568; padding: 14px 10px; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; border-bottom: 1px solid #E2E8F0; text-align: center; }}
                .sov_table td {{ padding: 12px 10px; border-bottom: 1px solid #EDF2F7; text-align: center; vertical-align: middle; color: #2D3748; font-weight: 500; }}
                .sov_table tbody tr:last-child td {{ border-bottom: none; }}
                
                .footer {{ background-color: #F7FAFC; padding: 25px 35px; text-align: center; font-size: 13px; color: #718096; border-top: 1px solid #E2E8F0; }}
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <div class="email-container">
                    
                    <div class="email-header">
                        <h2>BLINKIT DIGITAL SHELF</h2>
                        <h1>{brand}</h1>
                        <span class="date-badge">{yesterday.strftime('%b %d, %Y')}</span>
                    </div>
                    
                    <div class="email-body">
                        <div class="greeting">Hello Team,</div>
                        <div class="intro-text">
                            <p style="margin-top: 0;">We are excited to bring you today's performance update. To help you clearly track trends, here is a breakdown of the comparison periods used to calculate the percentage changes (▲/▼) in the tables below:</p>
                            
                            <div class="context-box">
                                <p><strong>1. Share of Voice (SOV)</strong></p>
                                <ul>
                                    <li><strong>Base Data:</strong> Last 1-day average ({yesterday})</li>
                                    <li><strong>Delta (%):</strong> Compared against previous 6-day average ({sov_comp_str})</li>
                                </ul>
                                
                                <p><strong>2. Top Metro-wise Availability</strong></p>
                                <ul>
                                    <li><strong>Base Data:</strong> Last 3-day average ({avail_target_str})</li>
                                    <li><strong>Delta (%):</strong> Compared against previous 3-day average ({avail_comp_str})</li>
                                </ul>
                            </div>
                        </div>
                        
                        <div class="section-title">1. Brand-wise Share of Voice (SOV)</div>
                        {sov_html}
                        
                        <div class="section-title">2. Top Metro-wise Availability Report</div>
                        {avail_html}
                        
                        <div class="intro-text" style="margin-top: 20px; font-size: 13px; color: #718096; text-align: center;">
                            <i>* Detailed Excel reports containing the full 7-day view ({date_range_str}) are attached for deeper analysis.</i>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <b>Shivani Nagar</b><br>
                        Business Analyst<br><br>
                        Hope you find this useful! Your feedback helps us improve. You can reply directly to this email if you need a deeper dive into these metrics.
                    </div>
                    
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        for file in [avail_xlsx, sov_xlsx]:
            if os.path.exists(file):
                with open(file,"rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(file))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file)}"'
                    msg.attach(part)

        try:
            with smtplib.SMTP("smtp.gmail.com",587) as server:
                server.starttls()
                server.login(SENDER_EMAIL,SENDER_PASSWORD)
                server.send_message(msg)
            print(f"✅ Email sent for {brand}")
        except Exception as e:
            print("❌ Email error:", e)

def xlsxwriter_col_name(n):
    """Helper to convert column index to Excel letters (0->A, 5->F)"""
    string = ""
    while n >= 0:
        n, remainder = divmod(n, 26)
        string = chr(65 + remainder) + string
        n -= 1
    return string

if __name__ == "__main__":
    run_pipeline()

