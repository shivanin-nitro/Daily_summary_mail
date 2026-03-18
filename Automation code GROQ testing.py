#GROQ_API_KEY = "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"

# import os
# import pandas as pd
# import numpy as np
# import smtplib
# import imaplib
# import time
# import re
# import json
# from datetime import datetime, timedelta
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.application import MIMEApplication
# from email.mime.image import MIMEImage
# import urllib.parse
# from groq import Groq

# # Assuming helper is in your directory
# from helper import execute_copy_query_via_bastion

# # ================= CONFIGURATION =================
# GROQ_API_KEY = "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"
# groq_client = Groq(api_key=GROQ_API_KEY)

# SENDER_EMAIL = "shivani.n@getnitro.co"
# SENDER_PASSWORD = "rkgc lqvr dvpp wnfa"
# CC_EMAILS = ["shivani.n@getnitro.co"]

# DASHBOARD_URL = "https://z.nitrocommerce.ai/login"
# Q_COMM_NAME = "Blinkit"
# BASE_PATH = r"C:\Users\User1\Desktop\autmation codes\availability\AVAIL"
# BRAND_NAME_MAPPING_PATH = r"C:\Users\User1\Desktop\autmation codes\test.xlsx"

# os.makedirs(BASE_PATH, exist_ok=True)

# IMAGE_PATHS = {
#     "logo": r"C:\Users\User1\Desktop\autmation codes\Logos\brand logo.png",
#     "li": r"C:\Users\User1\Desktop\autmation codes\Logos\linkdin icon.png",
#     "web": r"C:\Users\User1\Desktop\autmation codes\Logos\brand icon.png"
# }

# LINK_LI = "https://www.linkedin.com/showcase/zodiac-by-nitro/posts/?feedView=all"
# LINK_WEB = "https://zodiac.nitrocommerce.ai/"

# # ================= DATE SETUP =================
# today = datetime.now()
# yesterday = (today - timedelta(days=1)).date()

# # Availability Periods (3-day vs 3-day)
# avail_target_s = (yesterday - timedelta(days=2))
# avail_target_e = yesterday
# avail_comp_s = (yesterday - timedelta(days=5))
# avail_comp_e = (yesterday - timedelta(days=3))

# # SOV Periods (1-day vs 6-day average)
# sov_target_date = (yesterday - timedelta(days=5))
# sov_comp_s = (yesterday - timedelta(days=7))
# sov_comp_e = (yesterday - timedelta(days=2))

# # Display strings for Email
# sov_delta_str = f"{sov_comp_s.strftime('%d %b')} - {sov_comp_e.strftime('%d %b %Y')}"
# avail_base_str = f"{avail_target_s.strftime('%d %b')} - {yesterday.strftime('%d %b %Y')}"
# avail_delta_str = f"{avail_comp_s.strftime('%d %b')} - {avail_comp_e.strftime('%d %b %Y')}"

# # ================= BRAND CONFIG =================
# COMPETITORS = {
#     "Zavya": ["GIVA", "Palmonas", "CLARA", "Unniyarcha", "Shaya by Caratlane"],
#     "PINQ POLKA": ["Sanfe", "Underneat", "Bare Wear", "Boldfit", "Sirona"]
# }

# BRAND_EMAILS = {
#     "Zavya": ["shivaninagar918@gmail.com", "nshivani380@gmail.com"],
#     "PINQ POLKA": ["shivaninagar918@gmail.com"]
# }

# TARGET_METROS = ["Pune", "Delhi", "Mumbai", "UP-NCR", "UP-HR", "Hyderabad", "Bengaluru"]
# ALL_BRANDS = ["Zavya", "PINQ POLKA"]
# DEFAULT_RECIPIENT = ["shilpa.bhat@getnitro.co.in"]

# # ================= HELPERS =================
# def extract_name_from_email(email):
#     local_part = email.split('@')[0].split('.')[0]
#     clean_name = re.sub(r'\d+', '', local_part).capitalize()
#     return clean_name if clean_name else "Team"

# def get_avail_query(brand_name, competitor_list):
#     search_list = [brand_name] + competitor_list
#     brand_filter = f"bp.\"brandId\" IN ({', '.join([repr(b) for b in search_list])})"
#     return f"""
#         \\pset format csv
#         \\pset tuples_only off
#         SELECT bp."brandId" AS brandid, bp.id AS productid, bp.name AS product_name, 
#         bm."cityName" AS city, bm.name AS store_name, bpm.inventory, 
#         DATE(bpm."createdAt") as report_date
#         FROM "BlinkitProductMerchant" bpm
#         JOIN "BlinkitProduct" bp ON bp.id = bpm."productId"
#         JOIN "BlinkitMerchant" bm ON bm.id = bpm."merchantId"
#         WHERE bpm."createdAt" BETWEEN TIMESTAMP '{(yesterday - timedelta(days=7)).strftime('%Y-%m-%d')} 18:30:00' 
#         AND TIMESTAMP '{today.strftime('%Y-%m-%d')} 18:30:00'
#         AND {brand_filter}
#     """

# def get_sov_query(brand_name):
#     return f"""
#         \\pset format csv
#         \\pset tuples_only off
#         SELECT cdate, keywordid, brandid, cityname, categoryid, subcategoryid,
#                overall_impressions, organic_impressions, ad_impressions
#         FROM blinkit_impressions
#         WHERE cdate >= '{(yesterday - timedelta(days=8)).strftime('%Y-%m-%d')} 18:30:00' 
#         AND cdate <= '{today.strftime('%Y-%m-%d')} 18:30:00'
#         AND (categoryid, subcategoryid) IN (
#             SELECT DISTINCT categoryid, subcategoryid FROM blinkitproduct WHERE brandid = '{brand_name}'
#         )
#     """

# # ================= TABLE GENERATORS =================

# def generate_availability_html_table(df):
#     filtered_df = df[df['city'].isin(TARGET_METROS)].copy()
#     if filtered_df.empty: return "<p>No Data</p>"
    
#     p1_dates = pd.date_range(avail_target_s, avail_target_e)
#     p2_dates = pd.date_range(avail_comp_s, avail_comp_e)

#     df_p1 = filtered_df[pd.to_datetime(filtered_df['report_date']).dt.date.isin(p1_dates.date)]
#     df_p2 = filtered_df[pd.to_datetime(filtered_df['report_date']).dt.date.isin(p2_dates.date)]

#     avail_p1 = df_p1.pivot_table(index='city', columns='brandid', values='is_avail', aggfunc='mean').fillna(0) * 100
#     avail_p2 = df_p2.pivot_table(index='city', columns='brandid', values='is_avail', aggfunc='mean').fillna(0) * 100

#     html_df = pd.DataFrame(index=avail_p1.index)
#     for col in avail_p1.columns:
#         formatted_cols = []
#         for city in avail_p1.index:
#             val = avail_p1.at[city, col]
#             prev_val = avail_p2.at[city, col] if (col in avail_p2.columns and city in avail_p2.index) else 0
#             delta = val - prev_val
#             color = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
#             sign = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
#             formatted_cols.append(f"{int(round(val))}%<br><span style='color:{color}; font-size: 11px; font-weight:600;'>{sign}{delta:.2f}%</span>")
#         html_df[col] = formatted_cols
#     return html_df.reset_index().to_html(index=False, border=0, justify='center', classes='sov_table', escape=False)

# def generate_sov_html_table(df, brand, comps):
#     df['cdate_parsed'] = pd.to_datetime(df['cdate']).dt.date
#     search_list = [brand] + comps
    
#     df_target = df[df['cdate_parsed'] == sov_target_date]
#     df_comp = df[(df['cdate_parsed'] >= sov_comp_s) & (df['cdate_parsed'] <= sov_comp_e)]
    
#     def get_sov_metrics(data_frame):
#         grouped = data_frame.groupby('brandid').agg({
#             'overall_impressions': 'sum', 'organic_impressions': 'sum', 'ad_impressions': 'sum'
#         })
#         total_overall = grouped['overall_impressions'].sum()
#         total_organic = grouped['organic_impressions'].sum()
#         total_ad = grouped['ad_impressions'].sum()
        
#         metrics = pd.DataFrame(index=grouped.index)
#         metrics['Overall SOV'] = (grouped['overall_impressions'] / total_overall * 100).fillna(0)
#         metrics['Organic SOV'] = (grouped['organic_impressions'] / total_organic * 100).fillna(0)
#         metrics['Ad SOV'] = (grouped['ad_impressions'] / total_ad * 100).fillna(0)
#         return metrics

#     m_target = get_sov_metrics(df_target)
#     m_comp = get_sov_metrics(df_comp)
    
#     final_view = m_target[m_target.index.isin(search_list)].copy()
#     for col in ['Organic SOV', 'Ad SOV', 'Overall SOV']:
#         formatted = []
#         for b_id in final_view.index:
#             val = final_view.at[b_id, col]
#             prev = m_comp.at[b_id, col] if b_id in m_comp.index else 0
#             delta = val - prev
#             color = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
#             sign = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
#             formatted.append(f"{val:.2f}%<br><span style='color:{color}; font-size: 11px; font-weight:600;'>{sign}{delta:.2f}%</span>")
#         final_view[col] = formatted
    
#     return final_view.reset_index().rename(columns={'brandid': 'Brand'}).to_html(index=False, border=0, justify='center', classes='sov_table', escape=False)

# # ================= AI INSIGHTS =================
# def generate_ai_insights(brand, df_avail):
#     brand_df = df_avail[df_avail["brandid"] == brand]
#     metrics = {
#         "brand": brand,
#         "overall_availability": round(brand_df["is_avail"].mean()*100, 2),
#         "worst_stores": brand_df.groupby("store_name")["is_avail"].mean().sort_values().head(3).index.tolist(),
#         "sku_drops": brand_df.groupby("product_name")["is_avail"].mean().sort_values().head(3).index.tolist()
#     }
#     prompt = f"Retail expert. Data: {metrics}. Output: 2-sentence Executive Summary, 5 Key Insights (bullets), 1 Risk Flag."
#     try:
#         response = groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.2)
#         return response.choices[0].message.content
#     except: return "Summary currently unavailable."

# # ================= PIPELINE =================
# def run_pipeline():
#     for brand in ALL_BRANDS:
#         print(f"🚀 Processing {brand}...")
#         comps = COMPETITORS.get(brand, [])
#         temp_avail = os.path.join(BASE_PATH, f"{brand}_avail.csv.gz")
#         temp_sov = os.path.join(BASE_PATH, f"{brand}_sov.csv.gz")
#         avail_xlsx = os.path.join(BASE_PATH, f"{brand}_Availability_Report.xlsx")
#         sov_xlsx = os.path.join(BASE_PATH, f"{brand}_SOV_Analysis.xlsx")

#         execute_copy_query_via_bastion(get_avail_query(brand, comps), temp_avail)
#         execute_copy_query_via_bastion(get_sov_query(brand), temp_sov)

#         avail_html, sov_html, ai_content = "", "", ""
        
#         if os.path.exists(temp_avail):
#             df_a = pd.read_csv(temp_avail, compression="gzip", skiprows=1)
#             df_a.columns = df_a.columns.str.strip().str.lower()
#             df_a["is_avail"] = (df_a["inventory"] > 0).astype(float)
#             df_a['report_date'] = pd.to_datetime(df_a['report_date']).dt.date
            
#             avail_html = generate_availability_html_table(df_a)
#             ai_content = generate_ai_insights(brand, df_a)
#             # Filter Excel to prevent Size Limit Error
#             df_a[(df_a['brandid']==brand) & (df_a['report_date']==yesterday)].to_excel(avail_xlsx, index=False)

#         if os.path.exists(temp_sov):
#             df_s = pd.read_csv(temp_sov, compression="gzip", skiprows=1)
#             df_s.columns = df_s.columns.str.strip().str.lower()
#             sov_html = generate_sov_html_table(df_s, brand, comps)
#             df_s.head(5000).to_excel(sov_xlsx, index=False)

#         # Build Email
#         recipients = BRAND_EMAILS.get(brand, DEFAULT_RECIPIENT)
#         for recipient_email in recipients:
#             person_name = extract_name_from_email(recipient_email)
#             msg = MIMEMultipart("mixed")
#             msg_rel = MIMEMultipart("related")
#             msg.attach(msg_rel)
            
#             msg["Subject"] = f"Performance Summary: {brand} – {yesterday.strftime('%b %d, %Y')}"
#             msg["To"] = recipient_email
#             msg["From"] = SENDER_EMAIL
#             msg["Cc"] = ", ".join(CC_EMAILS)

#             body_html = f"""
#             <html>
#             <head>
#                 <style>
#                     body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #2D3748; }}
#                     .header-box {{ background-color: #70DD44; padding: 25px; border-radius: 8px; color: #000; text-align: center; }}
#                     .insight-box {{ background-color: #F7FAFC; border-left: 5px solid #70DD44; padding: 20px; margin: 20px 0; }}
#                     .sov_table {{ width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #E2E8F0; text-align: center; }}
#                     .sov_table th {{ background-color: #EDF2F7; padding: 12px; border-bottom: 2px solid #E2E8F0; }}
#                     .sov_table td {{ padding: 12px; border-bottom: 1px solid #E2E8F0; }}
#                 </style>
#             </head>
#             <body>
#                 <img src="cid:logo" width="180">
#                 <div class="header-box">
#                     <h2>Daily Summary: {brand}</h2>
#                     <p>Platform: {Q_COMM_NAME} | Date: {yesterday.strftime('%d %b %Y')}</p>
#                 </div>
                
#                 <p>Hello {person_name},</p>
#                 <p>We are excited to share the performance updates of last 24 hours for your <b>{Q_COMM_NAME}</b> store. This is a summarised view of key performance indicators around SOV & Availability.</p>

#                 <div class="insight-box">
#                     <h3 style="margin-top:0;">Executive Summary & Insights</h3>
#                     <p style="white-space: pre-wrap;">{ai_content}</p>
#                 </div>

#                 <div style="background-color: #f8fafc; padding: 15px; border: 1px solid #ddd; margin: 20px 0; font-size: 13px;">
#                     <b>1. Share of Voice (SOV):</b> Base: {yesterday} vs 6-day avg ({sov_delta_str})<br>
#                     <b>2. Metro-wise Availability:</b> Base: 3-day ({avail_base_str}) vs Prev: 3-day ({avail_delta_str})
#                 </div>

#                 <h3>1. Brand-wise Share of Voice (SOV)</h3>
#                 {sov_html}

#                 <h3>2. Top Metro-wise Availability Report</h3>
#                 {avail_html}

#                 <p>Full dataset attached. Login to <a href="{DASHBOARD_URL}">Zodiac Dashboard</a> for details.</p>
#                 <p>© 2026 Zodiac by Nitro</p>
#             </body>
#             </html>
#             """
#             msg_rel.attach(MIMEText(body_html, "html"))

#             # Attach Images and Excels
#             for k, p in IMAGE_PATHS.items():
#                 if os.path.exists(p):
#                     with open(p, 'rb') as f:
#                         img = MIMEImage(f.read()); img.add_header('Content-ID', f'<{k}>'); msg_rel.attach(img)
            
#             for file_path in [avail_xlsx, sov_xlsx]:
#                 if os.path.exists(file_path):
#                     with open(file_path, "rb") as f:
#                         part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
#                         part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
#                         msg.attach(part)

#             try:
#                 with smtplib.SMTP("smtp.gmail.com", 587) as server:
#                     server.starttls(); server.login(SENDER_EMAIL, SENDER_PASSWORD); server.send_message(msg)
#                 print(f"✅ Email sent to {recipient_email}")
#             except Exception as e: print(f"❌ Error: {e}")

# if __name__ == "__main__":
#     run_pipeline()


import os
import pandas as pd
import numpy as np
import smtplib
import imaplib
import time
import re
import json
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
import urllib.parse
from groq import Groq

# Assuming helper is in your directory
from helper import execute_copy_query_via_bastion

# ================= CONFIGURATION =================
GROQ_API_KEY = "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"
groq_client = Groq(api_key=GROQ_API_KEY)

SENDER_EMAIL = "shivani.n@getnitro.co"
SENDER_PASSWORD = "rkgc lqvr dvpp wnfa"
CC_EMAILS = ["shivani.n@getnitro.co"]

DASHBOARD_URL = "https://z.nitrocommerce.ai/login"
Q_COMM_NAME = "Blinkit"
BASE_PATH = r"C:\Users\User1\Desktop\autmation codes\availability\AVAIL"
BRAND_NAME_MAPPING_PATH = r"C:\Users\User1\Desktop\autmation codes\test.xlsx"

os.makedirs(BASE_PATH, exist_ok=True)

IMAGE_PATHS = {
    "logo": r"C:\Users\User1\Desktop\autmation codes\Logos\brand logo.png",
    "li": r"C:\Users\User1\Desktop\autmation codes\Logos\linkdin icon.png",
    "web": r"C:\Users\User1\Desktop\autmation codes\Logos\brand icon.png"
}
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx0WU-dzumV8Fr9hxoT-mqnfxAF3K641qIe7isFGhPOTU6NOF6-HtW4OA4ovbh317Lg/exec"
unsub_link = f"{WEB_APP_URL}?email={urllib.parse.quote(recipient_email)}&brand={urllib.parse.quote(brand)}"
            

LINK_LI = "https://www.linkedin.com/showcase/zodiac-by-nitro/posts/?feedView=all"
LINK_WEB = "https://zodiac.nitrocommerce.ai/"

# ================= DATE SETUP =================
today = datetime.now()
yesterday = (today - timedelta(days=1)).date()

# Availability Periods (3-day vs 3-day)
avail_target_s = (yesterday - timedelta(days=2))
avail_comp_s = (yesterday - timedelta(days=5))
avail_comp_e = (yesterday - timedelta(days=3))

# SOV Periods (1-day vs 6-day average)
sov_target_date = (yesterday - timedelta(days=2))
sov_comp_s = (yesterday - timedelta(days=7))
sov_comp_e = (yesterday - timedelta(days=2))

# Display strings for Email Header/Context
sov_delta_str = f"{sov_comp_s.strftime('%d %b')} - {sov_comp_e.strftime('%d %b %Y')}"
avail_base_str = f"{avail_target_s.strftime('%d %b')} - {yesterday.strftime('%d %b %Y')}"
avail_delta_str = f"{avail_comp_s.strftime('%d %b')} - {avail_comp_e.strftime('%d %b %Y')}"

# ================= BRAND CONFIG =================
COMPETITORS = {
    "Zavya": ["GIVA", "Palmonas", "CLARA", "Unniyarcha", "Shaya by Caratlane"],
    "PINQ POLKA": ["Sanfe", "Underneat", "Bare Wear", "Boldfit", "Sirona"],
    "Imagimake": ["Toyshine", "Wembley", "Skillmatics", "Funskool"]
}

BRAND_EMAILS = {
    "Zavya": ["shivaninagar918@gmail.com", "nshivani380@gmail.com"],
    "PINQ POLKA": ["shivaninagar918@gmail.com"],
    "Imagimake": ["shivaninagar918@gmail.com"]
}

TARGET_METROS = ["Pune", "Delhi", "Mumbai", "UP-NCR", "UP-HR", "Hyderabad", "Bengaluru"]
ALL_BRANDS = ["Zavya", "PINQ POLKA", "Imagimake"]
DEFAULT_RECIPIENT = ["shivani.n@getnitro.co"]

# ================= HELPERS =================
def extract_name_from_email(email):
    local_part = email.split('@')[0].split('.')[0]
    return re.sub(r'\d+', '', local_part).capitalize() if local_part else "Team"

def get_avail_query(brand_name, competitor_list):
    search_list = [brand_name] + competitor_list
    brand_filter = f"bp.\"brandId\" IN ({', '.join([repr(b) for b in search_list])})"
    return f"""\\pset format csv\n\\pset tuples_only off\nSELECT bp."brandId" AS brandid, bp.id AS productid, bp.name AS product_name, bm."cityName" AS city, bm.name AS store_name, bpm.inventory, DATE(bpm."createdAt") as report_date FROM "BlinkitProductMerchant" bpm JOIN "BlinkitProduct" bp ON bp.id = bpm."productId" JOIN "BlinkitMerchant" bm ON bm.id = bpm."merchantId" WHERE bpm."createdAt" BETWEEN TIMESTAMP '{(yesterday - timedelta(days=7)).strftime('%Y-%m-%d')} 18:30:00' AND TIMESTAMP '{today.strftime('%Y-%m-%d')} 18:30:00' AND {brand_filter}"""

def get_sov_query(brand_name):
    return f"""\\pset format csv\n\\pset tuples_only off\nSELECT cdate, brandid, overall_impressions, organic_impressions, ad_impressions FROM blinkit_impressions WHERE cdate >= '{(yesterday - timedelta(days=8)).strftime('%Y-%m-%d')} 18:30:00' AND cdate <= '{today.strftime('%Y-%m-%d')} 18:30:00' AND (categoryid, subcategoryid) IN (SELECT DISTINCT categoryid, subcategoryid FROM blinkitproduct WHERE brandid = '{brand_name}')"""

def generate_availability_html_table(df):
    filtered_df = df[df['city'].isin(TARGET_METROS)].copy()
    if filtered_df.empty: return "<p>No Data</p>"
    avail_p1 = filtered_df[pd.to_datetime(filtered_df['report_date']).dt.date >= avail_target_s].pivot_table(index='city', columns='brandid', values='is_avail', aggfunc='mean').fillna(0) * 100
    avail_p2 = filtered_df[(pd.to_datetime(filtered_df['report_date']).dt.date >= avail_comp_s) & (pd.to_datetime(filtered_df['report_date']).dt.date <= avail_comp_e)].pivot_table(index='city', columns='brandid', values='is_avail', aggfunc='mean').fillna(0) * 100
    html_df = pd.DataFrame(index=avail_p1.index)
    for col in avail_p1.columns:
        formatted_cols = []
        for city in avail_p1.index:
            val = avail_p1.at[city, col]
            prev_val = avail_p2.at[city, col] if (col in avail_p2.columns and city in avail_p2.index) else 0
            delta = val - prev_val
            color = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
            sign = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
            formatted_cols.append(f"{int(round(val))}%<br><span style='color:{color}; font-size: 11px; font-weight:600;'>{sign}{delta:.2f}%</span>")
        html_df[col] = formatted_cols
    return html_df.reset_index().to_html(index=False, border=0, justify='center', classes='sov_table', escape=False)

def generate_sov_html_table(df, brand, comps):
    df['cdate_parsed'] = pd.to_datetime(df['cdate']).dt.date
    search_list = [brand] + comps
    df_target = df[df['cdate_parsed'] == sov_target_date]
    df_comp = df[(df['cdate_parsed'] >= sov_comp_s) & (df['cdate_parsed'] <= sov_comp_e)]
    def get_sov_metrics(data_frame):
        grouped = data_frame.groupby('brandid').agg({'overall_impressions': 'sum', 'organic_impressions': 'sum', 'ad_impressions': 'sum'})
        total_overall = grouped['overall_impressions'].sum()
        metrics = pd.DataFrame(index=grouped.index)
        metrics['Overall SOV'] = (grouped['overall_impressions'] / total_overall * 100).fillna(0)
        metrics['Organic SOV'] = (grouped['organic_impressions'] / grouped['organic_impressions'].sum() * 100).fillna(0)
        metrics['Ad SOV'] = (grouped['ad_impressions'] / grouped['ad_impressions'].sum() * 100).fillna(0)
        return metrics
    m_target, m_comp = get_sov_metrics(df_target), get_sov_metrics(df_comp)
    final_view = m_target[m_target.index.isin(search_list)].copy()
    for col in ['Organic SOV', 'Ad SOV', 'Overall SOV']:
        formatted = []
        for b_id in final_view.index:
            val, prev = final_view.at[b_id, col], (m_comp.at[b_id, col] if b_id in m_comp.index else 0)
            delta = val - prev
            color = "#16a34a" if delta > 0 else "#dc2626" if delta < 0 else "#9ca3af"
            sign = "▲ +" if delta > 0 else "▼ " if delta < 0 else ""
            formatted.append(f"{val:.2f}%<br><span style='color:{color}; font-size: 11px; font-weight:600;'>{sign}{delta:.2f}%</span>")
        final_view[col] = formatted
    return final_view.reset_index().rename(columns={'brandid': 'Brand'}).to_html(index=False, border=0, justify='center', classes='sov_table', escape=False)

def generate_ai_insights(brand, df_avail):
    brand_df = df_avail[df_avail["brandid"] == brand]
    metrics = {"brand": brand, "overall_availability": round(brand_df["is_avail"].mean()*100, 2), "worst_stores": brand_df.groupby("store_name")["is_avail"].mean().sort_values().head(3).index.tolist(), "sku_drops": brand_df.groupby("product_name")["is_avail"].mean().sort_values().head(3).index.tolist()}
    prompt = f"Retail analysis for {brand}. Data: {metrics}. Output strictly as: Executive Summary: (2 sentences), Key Insights: (3 bullets), Risk Flag: (1 sentence). No markdown."
    try:
        response = groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return response.choices[0].message.content
    except: return "Summary unavailable."

# ================= PIPELINE =================
def run_pipeline():
    for brand in ALL_BRANDS:
        print(f"🚀 Processing {brand}...")
        comps = COMPETITORS.get(brand, [])
        temp_avail, temp_sov = os.path.join(BASE_PATH, f"{brand}_avail.csv.gz"), os.path.join(BASE_PATH, f"{brand}_sov.csv.gz")
        avail_xlsx, sov_xlsx = os.path.join(BASE_PATH, f"{brand}_Availability_Report.xlsx"), os.path.join(BASE_PATH, f"{brand}_SOV_Analysis.xlsx")
        execute_copy_query_via_bastion(get_avail_query(brand, comps), temp_avail)
        execute_copy_query_via_bastion(get_sov_query(brand), temp_sov)
        avail_html, sov_html, ai_content = "", "", ""
        if os.path.exists(temp_avail):
            df_a = pd.read_csv(temp_avail, compression="gzip", skiprows=1); df_a.columns = df_a.columns.str.strip().str.lower()
            df_a["is_avail"] = (df_a["inventory"] > 0).astype(float); df_a['report_date'] = pd.to_datetime(df_a['report_date']).dt.date
            avail_html = generate_availability_html_table(df_a); ai_content = generate_ai_insights(brand, df_a)
            df_a[(df_a['brandid']==brand) & (df_a['report_date']==yesterday)].to_excel(avail_xlsx, index=False)
        if os.path.exists(temp_sov):
            df_s = pd.read_csv(temp_sov, compression="gzip", skiprows=1); df_s.columns = df_s.columns.str.strip().str.lower()
            sov_html = generate_sov_html_table(df_s, brand, comps); df_s.head(5000).to_excel(sov_xlsx, index=False)
        
        for recipient_email in BRAND_EMAILS.get(brand, DEFAULT_RECIPIENT):
            person_name = extract_name_from_email(recipient_email)
            msg = MIMEMultipart("mixed"); msg_rel = MIMEMultipart("related"); msg.attach(msg_rel)
            msg["Subject"] = f"Performance Summary: {brand} – {yesterday.strftime('%b %d, %Y')}"; msg["To"] = recipient_email; msg["From"] = SENDER_EMAIL; msg["Cc"] = ", ".join(CC_EMAILS)
            body_html = f"""
            <html><head><style>
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f0f2f5; margin:0; padding:0; }}
                .container {{ max-width: 700px; margin: 40px auto; background-color: #ffffff; border-radius: 4px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .header {{ background-color: #70DD44; padding: 35px 25px; text-align: center; color: #000; }}
                .content {{ padding: 30px; color: #3c4858; line-height: 1.5; }}
                .context-box {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 25px 0; font-size: 13px; }}
                .insight-section {{ border-left: 4px solid #70DD44; padding-left: 20px; margin: 25px 0; }}
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
                            <p>We are excited to share the performance updates of last 24 hours for your <b>{Q_COMM_NAME}</b> store. This is a summarised view of key performance indicators around SOV & Availability. For a detailed view please login to your <a href="{DASHBOARD_URL}" style="color: #3182ce; font-weight:600;">Zodiac Dashboard</a>. Help us improve with your feedback and inputs by responding to this email.</p>
                            
                            <div class="insight-section">
                                <h3 style="margin-top:0; font-size:16px;">Executive Summary & Insights</h3>
                                <p style="white-space: pre-wrap; font-size: 14px;">{ai_content}</p>
                            </div>
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

                            <h3 style="font-size:14px; font-weight:700; margin-bottom:10px;">1. Brand-wise Share of Voice (SOV)</h3>
                            {sov_html}
                            <h3 style="font-size:14px; font-weight:700; margin-top:30px; margin-bottom:10px;">2. Top Metro-wise Availability Report</h3>
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

                    <p style="font-size:12px; color:#64748b; margin-top: 20px;">© 2026 Zodiac by Nitro</p>
                </div>
            </body>
            </html>"""
            msg_rel.attach(MIMEText(body_html, "html"))
            for k, p in IMAGE_PATHS.items():
                if os.path.exists(p):
                    with open(p, 'rb') as f:
                        img = MIMEImage(f.read()); img.add_header('Content-ID', f'<{k}>'); msg_rel.attach(img)
            for f_path in [avail_xlsx, sov_xlsx]:
                if os.path.exists(f_path):
                    with open(f_path, "rb") as f:
                        part = MIMEApplication(f.read(), Name=os.path.basename(f_path))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(f_path)}"'
                        msg.attach(part)
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls(); server.login(SENDER_EMAIL, SENDER_PASSWORD); server.send_message(msg)
            print(f"✅ Email sent to {recipient_email}")

if __name__ == "__main__":
    run_pipeline()