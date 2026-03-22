import os
import urllib.parse
import smtplib
import imaplib

import pandas as pd
import numpy as np

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

from groq import Groq
from src.bastion_connection import (
    open_clickhouse_connection,
    execute_clickhouse_query,
    close_clickhouse_connection
)
from src.logging_config import setup_logging,get_logger
from dotenv import load_dotenv
import os
from src.filters import ALL_BRANDS, COMPETITORS, BRAND_EMAILS, DEFAULT_RECIPIENT, WEB_APP_URL, Q_COMM_NAME
from src.query_created import get_avail_query, get_sov_query
from src.helper import build_email_html, generate_ai_insights, generate_sov_html_table, generate_availability_html_table, generate_sov_insights, generate_avail_insights, extract_name_from_email,generate_date
load_dotenv()

setup_logging("daily_summary_mail")
logger = get_logger("daily_summary_mail")

api_key   = os.getenv("GROQ_API_KEY")
groq_client    = Groq(api_key=api_key)

SENDER_EMAIL   = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD= os.getenv("SENDER_PASSWORD")
CC_EMAILS      = ["shivani.n@getnitro.co"]

DASHBOARD_URL  = os.getenv("DASHBOARD_URL")

BASE_PATH = os.getcwd()
BRAND_NAME_MAPPING_PATH = os.path.join(BASE_PATH, "test.xlsx")
os.makedirs(BASE_PATH, exist_ok=True)

IMAGE_PATHS = {
    "logo": os.path.join(BASE_PATH, "images", "logo.png"),
    "li":   os.path.join(BASE_PATH, "images", "linkdin_icon.png"),
    "web":  os.path.join(BASE_PATH, "images", "brand_icon.png"),
}

RAW_AVAIL_PATH = os.path.join(BASE_PATH, "raw_data", "availability")
RAW_SOV_PATH = os.path.join(BASE_PATH, "raw_data", "sov")
AVAIL_PATH = os.path.join(BASE_PATH, "data", "availability")
SOV_PATH = os.path.join(BASE_PATH, "data", "sov")


def run_pipeline():
    """
    Main pipeline function that fetches data, processes it, and sends email summaries.
    This function is called directly and can be used by cron jobs.
    """
    logger.info("=" * 60)
    logger.info("🚀  Starting Daily Summary Mail Pipeline")
    logger.info("=" * 60)
    
    try:
        os.makedirs(AVAIL_PATH, exist_ok=True)
        os.makedirs(SOV_PATH, exist_ok=True)
        os.makedirs(RAW_AVAIL_PATH, exist_ok=True)
        os.makedirs(RAW_SOV_PATH, exist_ok=True)
        logger.info(f"Created directories: {AVAIL_PATH}, {SOV_PATH}, {RAW_AVAIL_PATH}, {RAW_SOV_PATH}")
        
        logger.info("Establishing ClickHouse connection...")
        open_clickhouse_connection()
        logger.info("✅  ClickHouse connection established")
        
        logger.info("Generating date parameters...")
        today, yesterday, avail_target_s, avail_comp_s, avail_comp_e, sov_target_s, sov_target_e, sov_comp_s, sov_comp_e, avail_base_str, avail_delta_str, sov_base_str, sov_delta_str = generate_date()
        logger.info(f"Today: {today}, Yesterday: {yesterday}")
        logger.info(f"Availability Target Period: {avail_target_s} to {avail_comp_e}")
        logger.info(f"SOV Target Period: {sov_target_s} to {sov_comp_e}")
        
        logger.info(f"Processing {len(ALL_BRANDS)} brands: {ALL_BRANDS}")
        
        for brand in ALL_BRANDS:
            logger.info(f"\n{'='*60}")
            logger.info(f"🚀  Processing: {brand}")
            logger.info(f"{'='*60}")

            comps = COMPETITORS.get(brand, [])
            logger.debug(f"Competitors for {brand}: {comps}")

            temp_avail = os.path.join(AVAIL_PATH, f"{brand}_avail.csv.gz")
            temp_sov   = os.path.join(SOV_PATH, f"{brand}_sov.csv.gz")
            avail_xlsx = os.path.join(AVAIL_PATH, f"{brand}_Availability_Report.xlsx")
            sov_xlsx   = os.path.join(SOV_PATH, f"{brand}_SOV_Analysis.xlsx")

            logger.info("  📥  Fetching availability data...")
            success, df_a, message = execute_clickhouse_query(get_avail_query(brand, comps, yesterday, today))

            if success:   
                df_a.to_csv(f"{RAW_AVAIL_PATH}/availability_{brand}_{yesterday}.csv", index=False)
                logger.info(f"  ✅  Availability data saved to {RAW_AVAIL_PATH}/availability_{brand}_{yesterday}.csv")
            else:
                logger.error(f"  ❌  Failed to fetch availability data: {message}")
                continue


            logger.info(f"  ✅  Availability data fetched: {len(df_a)} rows")

            logger.info("  📥  Fetching SOV data...")
            success, df_s, message = execute_clickhouse_query(get_sov_query(brand, yesterday, today))

            if success:
                df_s.to_csv(f"{RAW_SOV_PATH}/sov_{brand}_{yesterday}.csv", index=False)
                logger.info(f"  ✅  SOV data saved to {RAW_SOV_PATH}/sov_{brand}_{yesterday}.csv")
            else:
                logger.error(f"  ❌  Failed to fetch SOV data: {message}")
                continue

            logger.info(f"  ✅  SOV data fetched: {len(df_s)} rows")

            avail_html          = ""
            sov_html            = ""
            ai_content          = ""
            sov_insights_text   = ""
            avail_insights_text = ""
            _brand_ad_sov       = 0.0

            # ── Load SOV first so brand_ad_sov is available for avail insights ───
            logger.info("  🔄  Processing SOV...")
            df_s.columns = df_s.columns.astype(str).str.strip().str.lower()

            sov_html = generate_sov_html_table(df_s, brand, comps, sov_target_s, sov_target_e, sov_comp_s, sov_comp_e)
            logger.debug("  ✅  SOV HTML table generated")

            logger.info("  🤖  Generating SOV Insights...")
            sov_insights_text = generate_sov_insights(brand, df_s, comps, groq_client, sov_target_s, sov_target_e, sov_comp_s, sov_comp_e)
            logger.debug("  ✅  SOV insights generated")

            # compute brand ad_sov for passing into avail insights
            _sov_t    = df_s[(pd.to_datetime(df_s["cdate"]).dt.date >= sov_target_s) &
                                (pd.to_datetime(df_s["cdate"]).dt.date <= sov_target_e)]
            _total_ad = _sov_t["ad_impressions"].sum()
            _brand_ad = _sov_t[_sov_t["brandid"] == brand]["ad_impressions"].sum()
            _brand_ad_sov = round(_brand_ad / _total_ad * 100, 2) if _total_ad else 0.0
            logger.debug(f"  Brand {brand} Ad SOV: {_brand_ad_sov}%")

            df_s.head(5000).to_excel(sov_xlsx, index=False)
            logger.info(f"  💾  Saved: {sov_xlsx}")

            logger.info("  🔄  Processing availability...")
            df_a.columns = df_a.columns.astype(str).str.strip().str.lower()
            df_a["is_avail"]    = (df_a["inventory"] > 0).astype(float)
            df_a["report_date"] = pd.to_datetime(df_a["report_date"]).dt.date

            avail_html = generate_availability_html_table(df_a, avail_target_s, avail_comp_s, avail_comp_e)
            logger.debug("  ✅  Availability HTML table generated")

            logger.info("  🤖  Generating Executive Summary...")
            ai_content = generate_ai_insights(brand, df_a, comps, groq_client, avail_target_s, avail_comp_s, avail_comp_e)
            logger.debug("  ✅  Executive summary generated")

            logger.info("  🤖  Generating Availability Insights...")
            avail_insights_text = generate_avail_insights(brand, df_a, comps, brand_ad_sov=_brand_ad_sov, groq_client=groq_client, avail_target_s=avail_target_s, avail_comp_s=avail_comp_s, avail_comp_e=avail_comp_e)
            logger.debug("  ✅  Availability insights generated")

            (
                df_a[(df_a["brandid"] == brand) & (df_a["report_date"] == yesterday)]
                .to_excel(avail_xlsx, index=False)
            )
            logger.info(f"  💾  Saved: {avail_xlsx}")

            # ── Email ─────────────────────────────────────────────────────────────
            recipients = BRAND_EMAILS.get(brand, DEFAULT_RECIPIENT)
            logger.info(f"  📧  Preparing to send emails to {len(recipients)} recipient(s)")
            
            for recipient_email in recipients:
                logger.info(f"  📧  Sending to {recipient_email}...")

                try:
                    person_name = extract_name_from_email(recipient_email)
                    unsub_link  = (
                        f"{WEB_APP_URL}"
                        f"?email={urllib.parse.quote(recipient_email)}"
                        f"&brand={urllib.parse.quote(brand)}"
                    )

                    msg     = MIMEMultipart("mixed")
                    msg_rel = MIMEMultipart("related")
                    msg.attach(msg_rel)

                    msg["Subject"] = f"Performance Summary: {brand} – {yesterday.strftime('%b %d, %Y')}"
                    msg["To"]      = recipient_email
                    msg["From"]    = SENDER_EMAIL
                    msg["Cc"]      = ", ".join(CC_EMAILS)
                    logger.debug(f"  Email headers set for {recipient_email}")

                    body_html = build_email_html(
                        brand, person_name, ai_content,
                        sov_html, sov_insights_text,
                        avail_html, avail_insights_text,
                        unsub_link, avail_base_str, avail_delta_str, sov_base_str, sov_delta_str,
                        yesterday, Q_COMM_NAME, DASHBOARD_URL
                    )
                    msg_rel.attach(MIMEText(body_html, "html"))
                    logger.debug(f"  HTML body attached for {recipient_email}")

                    for cid, img_path in IMAGE_PATHS.items():
                        if os.path.exists(img_path):
                            with open(img_path, "rb") as f:
                                img = MIMEImage(f.read())
                                img.add_header("Content-ID", f"<{cid}>")
                                msg_rel.attach(img)
                            logger.debug(f"  Image {cid} attached from {img_path}")
                        else:
                            logger.warning(f"  Image file not found: {img_path}")

                    for f_path in [avail_xlsx, sov_xlsx]:
                        if os.path.exists(f_path):
                            with open(f_path, "rb") as f:
                                part = MIMEApplication(f.read(), Name=os.path.basename(f_path))
                                part["Content-Disposition"] = (
                                    f'attachment; filename="{os.path.basename(f_path)}"'
                                )
                                msg.attach(part)
                            logger.debug(f"  File {os.path.basename(f_path)} attached")
                        else:
                            logger.warning(f"  File not found: {f_path}")

                    with smtplib.SMTP("smtp.gmail.com", 587) as server:
                        server.starttls()
                        server.login(SENDER_EMAIL, SENDER_PASSWORD)
                        server.send_message(msg)
                    logger.info(f"  ✅  Email sent → {recipient_email}")
                    
                except Exception as e:
                    logger.error(f"  ❌  Failed to send to {recipient_email}: {e}", exc_info=True)

        logger.info(f"\n{'='*60}")
        logger.info("✅  Pipeline complete.")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.critical(f"❌  Pipeline failed with critical error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Closing ClickHouse connection...")
        close_clickhouse_connection()
        logger.info("✅  ClickHouse connection closed")


if __name__ == "__main__":
    run_pipeline()