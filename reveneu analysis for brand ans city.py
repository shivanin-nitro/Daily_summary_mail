import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from helper import execute_copy_query_via_bastion

# =============================
# CONFIGURATION
# =============================
#BRAND_LIST = ["Tuco Kids","Eume","Imagimake","Forest Essentials","Nuvie","Tea Culture of the World","Bambino","Jimmy's","Soulflower","Kilobeaters","Chaayos","Gala","Oyo Baby","Winston","Ecoright","Nish Hair","Freecultr","Spinbot"]
CITIES = []
BRAND_LIST = ["Gala", "Winston", "Ecoright", "Nish Hair", "Freecultr", "Spinbot"]

SAVE_PATH = r"C:\Users\User1\Desktop\autmation codes\availability\insghts from reveue code"
os.makedirs(SAVE_PATH, exist_ok=True)

today = datetime.now()
start_date = (today - timedelta(days=4)).strftime('%Y-%m-%d')
end_date = today.strftime('%Y-%m-%d')

START_DATE = f"{start_date} 18:30:00"
END_DATE = f"{end_date} 18:30:00"

def calculate_inventory_flow(inv_list):
    inv = np.array(inv_list)
    if len(inv) < 2:
        return pd.Series([0, 0])
    diffs = np.diff(inv)
    sold = -np.sum(diffs[diffs < 0])
    restocked = np.sum(diffs[diffs > 0])
    return pd.Series([sold, restocked])

def run_revenue_analysis():
    for BRAND_NAME in BRAND_LIST:
        print(f"\n🚀 Processing Revenue Insights for: {BRAND_NAME}")
        
        raw_temp_gz = os.path.join(SAVE_PATH, f"{BRAND_NAME}_raw_data.csv.gz")
        output_excel = os.path.join(SAVE_PATH, f"{BRAND_NAME}_Revenue_Insights.xlsx")

        query = f"""
        WITH target_categories AS (
            SELECT DISTINCT "categoryId", "subCategoryId"
            FROM "BlinkitProduct"
            WHERE "name" ILIKE '%{BRAND_NAME}%'
        )
        SELECT
            bpm."createdAt" AS date,
            bp.id AS productid,
            bp."name" AS product,
            bp.unit,
            bp."brandId" AS brand,
            bc."categoryName",
            bc."subCategoryName",
            bpm.inventory,
            bm."name" AS merchantname,
            bm."cityName" AS city,
            bp.mrp,
            bpm.discount,
            bpm.price
        FROM "BlinkitProductMerchant" bpm
        JOIN "BlinkitProduct" bp ON bpm."productId" = bp.id
        JOIN "BlinkitMerchant" bm ON bpm."merchantId" = bm.id
        JOIN "BlinkitCategory" bc ON bc."categoryId" = bp."categoryId" AND bc."subCategoryId" = bp."subCategoryId"
        JOIN target_categories tc ON bp."categoryId" = tc."categoryId" AND bp."subCategoryId" = tc."subCategoryId"
        WHERE bpm."createdAt" BETWEEN '{START_DATE}' AND '{END_DATE}'
        """

        success, message, _ = execute_copy_query_via_bastion(query, raw_temp_gz)

        if not success:
            print(f"❌ Query Failed for {BRAND_NAME}: {message}")
            continue

        try:
            # FIX: Use sep="|" because your CSV uses pipe separators.
            # skiprows=[1] specifically skips the dashed line (Row 2) while keeping Row 1 as header.
            df = pd.read_csv(
                raw_temp_gz, 
                compression="gzip", 
                sep="|",
                skiprows=[1], 
                engine='python',
                on_bad_lines='skip'
            )
            
            # Clean up: Remove empty columns created by leading/trailing pipes
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df.columns = df.columns.str.lower().str.strip()

            # Verify the column exists
            if 'date' not in df.columns:
                print(f"❌ Column 'date' not found. Available: {list(df.columns)}")
                continue

            # Data Pre-processing
            df["date"] = pd.to_datetime(df["date"], errors='coerce')
            df = df.dropna(subset=['date']) # Remove any remaining separator rows
            
            for col in ["inventory", "price", "discount"]:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            df = df.sort_values(["productid", "merchantname", "date"])

            # Grouping for Inventory Flow
            grouped = df.groupby(["productid", "merchantname"]).agg({
                "product": "first",
                "brand": "first",
                "city": "first",
                "price": "median",
                "discount": "mean",
                "inventory": list
            }).reset_index()

            grouped[['sold', 'restocked']] = grouped['inventory'].apply(calculate_inventory_flow)
            grouped["revenue"] = grouped["sold"] * grouped["price"]
            
            data = grouped[grouped["sold"] > 0].copy()

            if data.empty:
                print(f"⚠️ No actual sales found for {BRAND_NAME}")
                continue

            # Generate Insight Tables
            brand_rev = data.groupby("brand")["revenue"].sum().reset_index()
            brand_rev["market_share_%"] = (brand_rev["revenue"] / brand_rev["revenue"].sum() * 100).round(2)
            top_brands = brand_rev.sort_values("revenue", ascending=False)

            city_rev = data.groupby("city")["revenue"].sum().reset_index()
            city_rev = city_rev[city_rev["city"].isin(CITIES)]
            city_rev["city_contribution_%"] = (city_rev["revenue"] / city_rev["revenue"].sum() * 100).round(2)

            prod_table = data.groupby(["brand", "product"]).agg({
                "revenue": "sum", "price": "mean", "sold": "sum"
            }).reset_index()
            prod_table = prod_table.sort_values("revenue", ascending=False).head(20)

            # Save to Excel
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                top_brands.to_excel(writer, sheet_name='Brand Market Share', index=False)
                city_rev.to_excel(writer, sheet_name='City Revenue Contribution', index=False)
                prod_table.to_excel(writer, sheet_name='Top 20 Products', index=False)
                data.to_excel(writer, sheet_name='Raw Sales Data', index=False)
                
            print(f"✅ Insights saved to: {output_excel}")

        except Exception as e:
            print(f"❌ Error processing {BRAND_NAME}: {e}")

if __name__ == "__main__":
    run_revenue_analysis()