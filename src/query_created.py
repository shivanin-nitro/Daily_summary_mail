from datetime import timedelta

def get_avail_query(brand_name, competitor_list, yesterday, today):
    search_list  = [brand_name] + competitor_list
    brand_filter = f"bp.\"brandId\" IN ({', '.join([repr(b) for b in search_list])})"
    return (
        "\\pset format csv\n\\pset tuples_only off\n"
        "SELECT bp.\"brandId\" AS brandid, bp.id AS productid, bp.name AS product_name, "
        "bm.\"cityName\" AS city, bm.name AS store_name, bpm.inventory, "
        "DATE(bpm.\"createdAt\") as report_date "
        "FROM \"BlinkitProductMerchant\" bpm "
        "JOIN \"BlinkitProduct\" bp ON bp.id = bpm.\"productId\" "
        "JOIN \"BlinkitMerchant\" bm ON bm.id = bpm.\"merchantId\" "
        f"WHERE bpm.\"createdAt\" BETWEEN "
        f"TIMESTAMP '{(yesterday - timedelta(days=1)).strftime('%Y-%m-%d')} 18:30:00' "
        f"AND TIMESTAMP '{today.strftime('%Y-%m-%d')} 18:30:00' "
        f"AND {brand_filter}"
    )

def get_sov_query(brand_name, yesterday, today):
    return (
        "\\pset format csv\n\\pset tuples_only off\n"
        "SELECT cdate, brandid, overall_impressions, organic_impressions, ad_impressions "
        "FROM blinkit_impressions "
        f"WHERE cdate >= '{(yesterday - timedelta(days=1)).strftime('%Y-%m-%d')} 18:30:00' "
        f"AND cdate <= '{today.strftime('%Y-%m-%d')} 18:30:00' "
        f"AND (categoryid, subcategoryid) IN ("
        f"SELECT DISTINCT categoryid, subcategoryid FROM blinkitproduct WHERE brandid = '{brand_name}')"
    )
