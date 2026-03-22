from datetime import timedelta

def get_avail_query(brand_name, competitor_list, yesterday, today):
    search_list  = [brand_name] + competitor_list
    brand_filter = f"""bp.brandId IN ({', '.join([repr(b) for b in search_list])})"""
    return f"""
        SELECT bp.brandId AS brandid, bp.id AS productid, bp.name AS product_name, 
        bm.cityName AS city, bm.name AS store_name, bpm.inventory, 
        toDate(bpm.createdAt) as report_date
        FROM BlinkitProductMerchant bpm
        JOIN BlinkitProduct bp ON bp.id = toInt32(bpm.productId)
        JOIN BlinkitMerchant bm ON bm.id = toInt32(bpm.merchantId)
        WHERE bpm.createdAt >= '{(yesterday - timedelta(days=2)).strftime('%Y-%m-%d')} 00:00:00'
        AND bpm.createdAt <= '{today.strftime('%Y-%m-%d')} 23:59:59'
        AND {brand_filter}
    """

def get_sov_query(brand_name, yesterday, today):
    return f"""
    WITH
    (
        SELECT groupArrayDistinct(toString(categoryId))
        FROM BlinkitProduct
        WHERE brandId = '{brand_name}'
    ) AS category_list,
    (
        SELECT groupArrayDistinct(toString(subCategoryId))
        FROM BlinkitProduct
        WHERE brandId = '{brand_name}'
    ) AS subcategory_list

SELECT
    cdate AS cDate,
    keywordid AS keywordId,
    brandid AS brandId,
    cityname AS cityName,
    categoryid AS categoryId,
    subcategoryid AS subCategoryId,
    sumMerge(overall_impressions) AS overallImpressions,
    sumMerge(organic_impressions) AS organicImpressions,
    sumMerge(ad_impressions) AS adImpressions

FROM BlinkitImpressions

WHERE 
    cdate >= '{(yesterday - timedelta(days=3)).strftime('%Y-%m-%d')}'
    AND cdate <= '{today.strftime('%Y-%m-%d')}'
    AND has(category_list, toString(categoryid)) 
    AND has(subcategory_list, toString(subcategoryid))

GROUP BY
    cdate,
    keywordid,
    brandid,
    cityname,
    categoryid,
    subcategoryid
"""