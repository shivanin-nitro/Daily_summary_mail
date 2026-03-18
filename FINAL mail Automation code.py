'''groq api : 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
code from automation_mail.py'''


import os
import pandas as pd
import smtplib
import imaplib
import time
import re
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
import urllib.parse

# Assuming helper is in your directory
from helper import execute_copy_query_via_bastion

# ================= CONFIG =================
SENDER_EMAIL = "shilpa.bhat@getnitro.co.in"

#testing : shipla's app password 
SENDER_PASSWORD = "jmds njdo nasx zdjm"

CC_EMAILS = ["zodiac@getnitro.co","pratik@getnitro.co","shivansh.s@getnitro.co","parijat@getnitro.co","shilpa@getnitro.co","shivani.n@getnitro.co"]
#CC_EMAILS = ["shivani.n@getnitro.co"]

DASHBOARD_URL = "https://z.nitrocommerce.ai/login" 
Q_COMM_NAME = "Blinkit" 

# LOCAL PATHS
BASE_PATH = r"C:\Users\User1\Desktop\autmation codes\availability\AVAIL"

#uncoment this for brand's mail data
BRAND_NAME_MAPPING_PATH = r"C:\Users\User1\Desktop\autmation codes\Brands main.xlsx"

#smample mails data
#BRAND_NAME_MAPPING_PATH = r"C:\Users\User1\Desktop\autmation codes\test.xlsx"

os.makedirs(BASE_PATH, exist_ok=True)

IMAGE_PATHS = {
    "logo": r"C:\Users\User1\Desktop\autmation codes\Logos\brand logo.png",
    "li": r"C:\Users\User1\Desktop\autmation codes\Logos\linkdin icon.png",
    "web": r"C:\Users\User1\Desktop\autmation codes\Logos\brand icon.png"
}

# SOCIAL LINKS
LINK_FB = "" 
LINK_LI = "https://www.linkedin.com/showcase/zodiac-by-nitro/posts/?feedView=all"
LINK_TW = ""
LINK_IG = ""
LINK_WEB = "https://zodiac.nitrocommerce.ai/"

COMPETITORS = {   
    "Zavya": ["GIVA", "Palmonas", "CLARA", "Unniyarcha", "Shaya by Caratlane"],
    "PINQ POLKA": ["Sanfe", "Underneat", "Bare Wear", "Boldfit", "Sirona"],
    "Tuco Kids": ["LuvLap", "Aveeno", "Sebamed","Cetaphile" ,"Toyshine"],
    "Eume": ["Daily Objects", "Nasher Miles", "Mokobara", "Urban Jungle"],
    "Imagimake": ["Toyshine", "Wembley", "Skillmatics", "Funskool"],
    "Bambino": ["Hommade", "Ching''s Secret", "Tata Sampann", "Whole Farm", "Disano"],
    "Nuvie": ["Amul", "Nescafe", "Cavin''s", "Mother Dairy", "Sleepy Owl"],
    "Kilobeaters": ["RiteBite", "SuperYou", "The Whole Truth", "Crax"],
    "Jimmy''s": ["paper boat", "Schweppes", "Absolut Mixers", "Sepoy & Co."],
    "Soulflower": ["Airwick","Ambi Pur","AuraCam","Aromahpure","Godrej Aer"],
    "Chaayos" : ["Brooke Bond Red Label", "Tata Tea Gold","Wagh Bakri", "Lipton", "Society"],
    "Winston" : ["Havells", "Vega","Philips","Bombay Shaving Company"],
    "Ecoright" : ["Teal By Chumbak", "Caprese","Lavie","Zouk"],
    "Tea Culture of the World" : ["Vadham","Twinings","Pukka","Flurys"]
}

# #test purpose
# BRAND_EMAILS = {
#     "Zavya": [
#         "shivaninagar918@gmail.com",
#         "nshivani380@gmail.com"],
#     "PINQ POLKA": [
#         "shivaninagar918@gmail.com" ]
# }

#all brand mail
BRAND_EMAILS = {
    "ZAVYA": ["zavya.priyanshu@gmail.com","yash@zavya.co"],
    "PINQ POLKA": ["shushila@pinq.co"],
    "Tuco Kids": ["samarth@tucokids.com","anshuman@tucokids.com"],
    "Eume": ["customercare@eumeworld.com","pranay@eumeworld.com"],
    "Imagimake": ["srinath@imagimake.com","Aditya@imagimake.com","sukhpreet@imagimake.com"],
    "Nuvie": ["sales@nugainwellness.in"],
    "Chaayos": ["nishant.s@chaayos.com","agarwal@chaayos.com"],
    "Bambino": ["headmt@bambinoagro.com"],
    "Jimmy''s": ["Abhinav.mahajan@radioheadbrands.com"],
    "Winston" : ["hemant@winstonindia.com"],
    "Freecultr" : ["komal.aggarwal@freecultr.com","sourabh.yadav@freecultr.com"],
    "Ecoright" : ["hardeep@ecoright.com","rahul.upadhyay@ecoright.com","ecominternal@ecorightbags.com","karan@ecoright.com"],
    "Tea Culture of the World": ["akshay.joshi@teacultureoftheworld.com"],
    "Oyo Baby": ["online12@bnmretail.com"],
    "Nish Hair" : ["channelmanager@nishhair.com","marketing@nishhair.com"],
    "Soulflower": ["ishani@soulflower.in","ritik@soulflower.in"],
    "The Theater Project" :["akash@thetheatreproject.co.in"].
    "Outlaw": ["suman@outlawsfashion.com"],
    "Kilobeaters" : ["kishan@kilobeaters.com"]
        }


TARGET_METROS = ["Pune", "Delhi", "Mumbai", "UP-NCR", "UP-HR", "Hyderabad", "Bengaluru"]

ALL_BRANDS = ["Zavya",  "PINQ POLKA", "Tuco Kids", "Eume", "Imagimake", 
               "Nuvie", "Bambino", "Jimmy''s", "Soulflower", 
              "Kilobeaters", "Chaayos","Winston","Ecoright",
              "Tea Culture of the World"]

DEFAULT_RECIPIENT = ["shilpa.bhat@getnitro.co.in"]


# ================= DATE SETUP =================
today = datetime.now()
yesterday = (today - timedelta(days=1)).date()
date_range_str = f"{yesterday.strftime('%d %b %Y')}"
six_days_ago = (yesterday - timedelta(days=5)) 

sov_target_start = (today - timedelta(days=2)).date()
sov_target_end = yesterday
sov_comp_start = (today - timedelta(days=8)).date()
sov_comp_end = (today - timedelta(days=3)).date()
sov_comp_str = f"{sov_comp_start.strftime('%d %b')} - {sov_comp_end.strftime('%d %b %Y')}"

avail_target_start = yesterday - timedelta(days=3)
avail_comp_start = yesterday - timedelta(days=5)
avail_comp_end = yesterday - timedelta(days=3)
avail_target_str = f"{avail_target_start.strftime('%d %b')} - {yesterday.strftime('%d %b %Y')}"
avail_comp_str = f"{avail_comp_start.strftime('%d %b')} - {avail_comp_end.strftime('%d %b %Y')}"

#for html date
sov_comp_s = (today - timedelta(days=7)).date()
sov_comp_e = (today - timedelta(days=2)).date()
sov_delta_str = f"{sov_comp_s.strftime('%d %b')} - {sov_comp_e.strftime('%d %b %Y')}" #for sov date

avail_target_s = (today - timedelta(days=3)).date()
avail_target_e = yesterday
avail_base_str = f"{avail_target_s.strftime('%d %b')} - {yesterday.strftime('%d %b %Y')}"

avail_comp_s = (today - timedelta(days=6)).date()
avail_comp_e = (today - timedelta(days=4)).date()
avail_delta_str = f"{avail_comp_s.strftime('%d %b')} - {avail_comp_e.strftime('%d %b %Y')}"

# ================= HELPERS =================
def extract_name_from_email(email):
    local_part = email.split('@')[0].split('.')[0]
    clean_name = re.sub(r'\d+', '', local_part).capitalize()
    return clean_name if clean_name else "Team"

def get_avail_query(brand_name, competitor_list):
    search_list = [brand_name] + competitor_list
    brand_filter = f"bp.\"brandId\" IN ({', '.join([repr(b) for b in search_list])})"
    return f"""
        \\pset format csv
        \\pset tuples_only off
        SELECT bp."brandId" AS brandid, bp.id AS productid, bp.name AS product_name, 
        bm."cityName" AS city, bm.name AS store_name, bpm.inventory, 
        DATE(bpm."createdAt") as report_date
        FROM "BlinkitProductMerchant" bpm
        JOIN "BlinkitProduct" bp ON bp.id = bpm."productId"
        JOIN "BlinkitMerchant" bm ON bm.id = bpm."merchantId"
        WHERE bpm."createdAt" BETWEEN TIMESTAMP '{six_days_ago.strftime('%Y-%m-%d')} 18:30:00.00'
        AND TIMESTAMP '{yesterday.strftime('%Y-%m-%d')} 18:30:00.00'
        AND {brand_filter}
    """

def get_sov_query(brand_name):
    return f"""
        \\pset format csv
        \\pset tuples_only off
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

    latest_date = filtered_df['report_date'].max()
    p1_dates = [latest_date - timedelta(days=i) for i in range(3)]
    p2_dates = [latest_date - timedelta(days=i) for i in range(3, 6)]

    df_p1 = filtered_df[filtered_df['report_date'].isin(p1_dates)]
    df_p2 = filtered_df[filtered_df['report_date'].isin(p2_dates)]

    if df_p1.empty:
         return "<p style='color:#718096; text-align:center;'>No Availability data for current period</p>"

    avail_p1 = df_p1.pivot_table(index='city', columns='brandid', values='is_avail', aggfunc='mean').fillna(0) * 100
    avail_p2 = df_p2.pivot_table(index='city', columns='brandid', values='is_avail', aggfunc='mean').fillna(0) * 100

    html_df = pd.DataFrame(index=avail_p1.index)
    for col in avail_p1.columns:
        formatted_cols = []
        for city in avail_p1.index:
            val = avail_p1.at[city, col]
            prev_val = avail_p2.at[city, col] if (col in avail_p2.columns and city in avail_p2.index) else 0
            delta = val - prev_val
            color = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
            sign = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
            cell_html = f"{int(round(val))}%<br><span style='color:{color}; font-size: 11px; font-weight:600;'>{sign}{delta:.2f}%</span>"
            formatted_cols.append(cell_html)
        html_df[col] = formatted_cols

    html_df = html_df.reset_index()
    return html_df.to_html(index=False, border=0, justify='center', classes='sov_table', escape=False)

# ================= PIPELINE =================
def run_pipeline():
    # UPDATED: Mapping logic to support multiple emails for a brand
    brand_email_lookup = {}
    try:
        df_mapping = pd.read_excel(BRAND_NAME_MAPPING_PATH)
        for _, row in df_mapping.iterrows():
            b = str(row['Brand']).strip().upper()
            n = str(row['name']).strip()
            
            if b not in brand_email_lookup:
                brand_email_lookup[b] = {}
                
            # If the mail column exists and is not empty, map the exact email to the name
            if 'mail' in row and pd.notna(row['mail']):
                m = str(row['mail']).strip().lower()
                if m and m != 'nan':
                    brand_email_lookup[b][m] = n
                else:
                    brand_email_lookup[b]['DEFAULT'] = n
            else:
                # If no email provided for this row, save it as the default fallback
                brand_email_lookup[b]['DEFAULT'] = n
                
        print("✅ Brand-Name mapping loaded successfully.")
    except Exception as e:
        print(f"⚠️ Warning: Could not load name mapping from Excel: {e}")

    for brand in ALL_BRANDS:
        print(f"\n🚀 Processing {brand}")
        
        missing_data = [] 
        
        # Fetch recipients list
        recipients = BRAND_EMAILS.get(brand, DEFAULT_RECIPIENT)
        if isinstance(recipients, str): recipients = [recipients]

        comps = COMPETITORS.get(brand, [])
        avail_xlsx = os.path.join(BASE_PATH, f"{brand}_Availability_Report.xlsx")
        sov_xlsx = os.path.join(BASE_PATH, f"{brand}_SOV_Analysis.xlsx")
        temp_avail = os.path.join(BASE_PATH, f"{brand}_avail.csv.gz")
        temp_sov = os.path.join(BASE_PATH, f"{brand}_sov.csv.gz")

        execute_copy_query_via_bastion(get_avail_query(brand, comps), temp_avail)
        execute_copy_query_via_bastion(get_sov_query(brand), temp_sov)

        # Availability processing...
        avail_html = "<p style='color:#718096; text-align:center;'>No Availability data</p>"
        if os.path.exists(temp_avail) and os.path.getsize(temp_avail) > 150:
            df_a = pd.read_csv(temp_avail, compression="gzip", skiprows=1)
            df_a.columns = df_a.columns.str.strip().str.lower()
            df_a["is_avail"] = (df_a["inventory"] > 0).astype(float)
            df_a['report_date'] = pd.to_datetime(df_a['report_date']).dt.date
            avail_html = generate_availability_html_table(df_a)
            brand_only_df = df_a[df_a['brandid'] == brand].copy()
            yesterday_df = brand_only_df[brand_only_df['report_date'] == yesterday].copy()
            
            if not yesterday_df.empty:
                excel_df = yesterday_df[['productid', 'product_name', 'store_name', 'city', 'inventory']].copy()
                excel_df.rename(columns={'inventory': f'Stock ({yesterday.strftime("%d %b")})', 'city': 'city_name'}, inplace=True)
                excel_df['In Stock/OOS'] = (excel_df[f'Stock ({yesterday.strftime("%d %b")})'] > 0).astype(int)
                excel_df['dark store count'] = 1684
                excel_df['Availability %'] = 0 
                with pd.ExcelWriter(avail_xlsx, engine="xlsxwriter") as writer:
                    excel_df.to_excel(writer, sheet_name="Availability", index=False)
                    workbook, worksheet = writer.book, writer.sheets["Availability"]
                    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1, 'align': 'center'})
                    percent_fmt = workbook.add_format({'num_format': '0%', 'border': 1, 'align': 'center'})
                    for col_num, value in enumerate(excel_df.columns.values):
                        worksheet.write(0, col_num, value, header_fmt)
                        worksheet.set_column(col_num, col_num, 18)
                    for i in range(len(excel_df)):
                        row_idx = i + 2 
                        formula = f'=IFERROR(COUNTIFS($A:$A,$A{row_idx},$D:$D,$D{row_idx},$F:$F,1)/COUNTIFS($A:$A,$A{row_idx},$D:$D,$D{row_idx}),0)'
                        worksheet.write_formula(i + 1, 7, formula, percent_fmt)

        if "No Availability data" in avail_html:
            missing_data.append("2. Top Metro-wise Availability Report")

        # SOV processing...
        sov_html = "<p style='color:#718096; text-align:center;'>No SOV data</p>" 
        if os.path.exists(temp_sov) and os.path.getsize(temp_sov) > 150:
            df_s = pd.read_csv(temp_sov, compression="gzip", skiprows=1, engine="python", on_bad_lines="skip")
            df_s.columns = df_s.columns.str.strip().str.lower()
            df_s['cdate_parsed'] = pd.to_datetime(df_s['cdate'], errors='coerce').dt.date
            df_s_target = df_s[(df_s['cdate_parsed'] >= sov_target_start) & (df_s['cdate_parsed'] <= sov_target_end)]
            df_s_comp = df_s[(df_s['cdate_parsed'] >= sov_comp_start) & (df_s['cdate_parsed'] <= sov_comp_end)]
            if not df_s_target.empty:
                # -------------------------------------------------------------
                # 1. Calculate overall brand SOV
                # -------------------------------------------------------------
                brand_table = df_s_target.groupby("brandid").agg({"overall_impressions": "sum", "organic_impressions": "sum", "ad_impressions": "sum"}).reset_index()
                for col in ["overall", "organic", "ad"]:
                    brand_table[f"{col}_sov_%"] = (brand_table[f"{col}_impressions"] / brand_table[f"{col}_impressions"].sum()) * 100
                brand_table_clean = brand_table[["brandid", "organic_sov_%", "ad_sov_%", "overall_sov_%"]].fillna(0).sort_values("overall_sov_%", ascending=False)
                
                brand_comp = df_s_comp.groupby("brandid").agg({"overall_impressions": "sum", "organic_impressions": "sum", "ad_impressions": "sum"}).reset_index()
                for col in ["overall", "organic", "ad"]: 
                    brand_comp[f"{col}_sov_%"] = (brand_comp[f"{col}_impressions"] / brand_comp[f"{col}_impressions"].sum()) * 100
                brand_comp_idx = brand_comp.set_index("brandid")
                
                # -------------------------------------------------------------
                # 2. Calculate City-level brand SOV
                # -------------------------------------------------------------
                city_brand = df_s_target.groupby(["cityname", "brandid"]).agg({"overall_impressions": "sum", "organic_impressions": "sum", "ad_impressions": "sum"}).reset_index()
                for col in ["overall", "organic", "ad"]:
                    # Get the total impressions for each city to calculate the percentage
                    city_totals = city_brand.groupby("cityname")[f"{col}_impressions"].transform("sum")
                    city_brand[f"{col}_sov_%"] = (city_brand[f"{col}_impressions"] / city_totals) * 100
                    
                city_brand_clean = city_brand[["cityname", "brandid", "organic_sov_%", "ad_sov_%", "overall_sov_%"]].fillna(0).sort_values(["cityname", "overall_sov_%"], ascending=[True, False])
                
                # -------------------------------------------------------------
                # 3. Create the multi-sheet SOV Excel File 
                # -------------------------------------------------------------
                with pd.ExcelWriter(sov_xlsx, engine="xlsxwriter") as writer:
                    brand_table_clean.to_excel(writer, sheet_name="Brand_SOV", index=False)
                    city_brand_clean.to_excel(writer, sheet_name="City_Brand_SOV", index=False)
                
                # -------------------------------------------------------------
                # 4. Create the HTML Table for the email body
                # -------------------------------------------------------------
                html_sov_df = brand_table_clean[brand_table_clean["brandid"].isin([brand] + comps)].copy()
                for col in ["organic_sov_%", "ad_sov_%", "overall_sov_%"]:
                    formatted_vals = []
                    for idx, row in html_sov_df.iterrows():
                        brand_id, x_val = row['brandid'], row[col]
                        y_val = brand_comp_idx.at[brand_id, col] if brand_id in brand_comp_idx.index else 0
                        delta = x_val - y_val
                        color = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
                        sign = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
                        formatted_vals.append(f"{x_val:.2f}%<br><span style='color:{color}; font-size: 11px; font-weight:600;'>{sign}{delta:.2f}%</span>")
                    html_sov_df[col] = formatted_vals
                html_sov_df.rename(columns={'brandid': 'Brand', 'organic_sov_%': 'Organic SOV', 'ad_sov_%': 'Ad SOV', 'overall_sov_%': 'Overall SOV'}, inplace=True)
                sov_html = html_sov_df.to_html(index=False, border=0, justify='center', classes='sov_table', escape=False)

        if "No SOV data" in sov_html:
            missing_data.append("1. Brand-wise Share of Voice (SOV)")

        # ================= SEND OR DRAFT LOGIC FOR EACH RECIPIENT =================
        # UPDATED: Loop through each recipient and send/draft individual emails
        for recipient_email in recipients:
            recipient_email = recipient_email.strip().lower()
            
            # Lookup exact name for this specific email, fallback to default, or auto-extract
            brand_dict = brand_email_lookup.get(brand.upper(), {})
            if recipient_email in brand_dict:
                person_name = brand_dict[recipient_email]
            elif 'DEFAULT' in brand_dict:
                person_name = brand_dict['DEFAULT']
            else:
                person_name = extract_name_from_email(recipient_email)

            msg = MIMEMultipart('mixed')
            msg_related = MIMEMultipart('related')
            msg.attach(msg_related)
            
            # Use the individual recipient_email here instead of a comma-separated list
            msg['From'] = SENDER_EMAIL
            msg['To'] = recipient_email
            msg['Cc'] = ", ".join(CC_EMAILS)
            msg['Subject'] = f"Performance Summary: {brand} – {yesterday.strftime('%b %d, %Y')}"

            WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx0WU-dzumV8Fr9hxoT-mqnfxAF3K641qIe7isFGhPOTU6NOF6-HtW4OA4ovbh317Lg/exec"
            unsub_link = f"{WEB_APP_URL}?email={urllib.parse.quote(recipient_email)}&brand={urllib.parse.quote(brand)}"
            
            msg.add_header('List-Unsubscribe', f'<{unsub_link}>')

            body = f"""
            <html>
            <head>
                <style>
                    body {{ margin: 0; padding: 0; background-color: #f0f2f5; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}
                    .email-wrapper {{ background-color: #f0f2f5; padding: 40px 20px; text-align: center; }}
                    .email-container {{ max-width: 700px; margin: 0 auto; background-color: #ffffff; border-radius: 4px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: left; }}
                    .email-header {{ background-color: #ffffff; padding: 30px 20px 10px 20px; text-align: center; }}
                    .header-box {{ background-color: #70DD44; color: #2D333F; padding: 35px 25px; border-radius: 8px; }}
                    .email-body {{ padding: 30px; color: #3c4858; line-height: 1.5; }}
                    .context-box {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 30px; font-size: 13px; }}
                    .sov_table {{ width: 100%; border-collapse: collapse; font-size: 12px; border: 1px solid #e2e8f0; text-align: center; }}
                    .sov_table th {{ background-color: #f1f5f9; padding: 12px; border-bottom: 2px solid #e2e8f0; }}
                    .sov_table td {{ padding: 12px; border-bottom: 1px solid #f1f5f9; }}
                    .footer {{ background-color: transparent; padding: 30px 20px; text-align: center; }}
                    .social-icons img {{ width: 22px; height: 22px; margin: 0 10px; opacity: 0.7; }}
                </style>
            </head>
            <body>
                <div class="email-wrapper">
                    <img src="cid:logo" alt="Zodiac Logo" style="width:190px; margin: 0 auto 26px auto; display:block;">
                    <div class="email-container">
                        <div class="email-header">
                            <div class="header-box">
                                <h2 style="margin:0; font-size:15px; font-weight:500; color:#000000;">Daily summary for</h2>                      
                                <h1 style="margin:10px 0 15px 0; font-size:32px; font-weight:900; color:#000000; letter-spacing:-0.5px;">{brand}</h1>            
                                <div style="background-color: #ffffff; color: #000000; padding: 8px 24px; border-radius: 20px; font-size: 15px; font-weight: 500; display: inline-block;">Platform : {Q_COMM_NAME}</div>
                            </div>
                        </div>
                        <div class="email-body">
                            <p>Hello {person_name},</p>
                            <p style="font-size: 14px;">We are excited to share the performance updates of last 24 hours for your <b>{Q_COMM_NAME}</b> store. This is a summarised view of key performance indicators around SOV & Availability. For a detailed view please login to your <a href="{DASHBOARD_URL}" style="color: #3182ce; font-weight:600;">Zodiac Dashboard</a>. Help us improve with your feedback and inputs by responding to this email.</p>
                            <div class="context-box">
                                <p><b>Here is a breakdown of the comparison periods used to calculate the percentage changes (▲/▼) in the tables below:</b></p>
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
                            <div style="font-weight:700; margin-bottom:15px;">1. Brand-wise Share of Voice (SOV)</div>
                            {sov_html}
                            <div style="font-weight:700; margin:30px 0 15px 0;">2. Top Metro-wise Availability Report</div>
                            {avail_html}
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
                </div>
            </body>
            </html>
            """
            msg_related.attach(MIMEText(body, 'html'))

            for key, path in IMAGE_PATHS.items():
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        img = MIMEImage(f.read())
                        img.add_header('Content-ID', f'<{key}>')
                        msg_related.attach(img)

            for file in [avail_xlsx, sov_xlsx]:
                if os.path.exists(file):
                    with open(file, "rb") as f:
                        part = MIMEApplication(f.read(), Name=os.path.basename(file))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file)}"'
                        msg.attach(part)

            if len(missing_data) > 0:
                try:
                    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
                        imap.login(SENDER_EMAIL, SENDER_PASSWORD)
                        imap.append("[Gmail]/Drafts", r'\Draft', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                    print(f"✅ Saved draft to {person_name} ({recipient_email}) for {brand} (Missing: {', '.join(missing_data)})")
                except Exception as e: print(f"❌ Draft error to {recipient_email} for {brand}: {e}")
            else:
                try:
                    with smtplib.SMTP("smtp.gmail.com", 587) as server:
                        server.starttls()
                        server.login(SENDER_EMAIL, SENDER_PASSWORD)
                        server.send_message(msg)
                    print(f"✅ Email sent to {person_name} ({recipient_email}) for {brand}")
                except Exception as e: print(f"❌ Email error to {recipient_email} for {brand}: {e}")

if __name__ == "__main__":
    run_pipeline()