# 🎯 Blinkit Data Extraction Pipeline

A fully automated pipeline to extract, combine, and process Blinkit product availability data with inventory change calculations.

## 📋 Overview

This pipeline extracts fresh data every run from a PostgreSQL database (via Bastion host), combines it locally, calculates inventory metrics, and cleans up intermediate files automatically.

### Key Features

- ✅ **Automated extraction** of BlinkitProduct, BlinkitMerchant, BlinkitCategory
- ✅ **Availability data** extraction with optimized indexed queries
- ✅ **Local data combination** (no database joins)
- ✅ **Inventory calculations** (sold units, restocked units)
- ✅ **Automatic cleanup** (deletes intermediates, keeps raw + processed files)
- ✅ **Organized folder structure** (dated folders for each extraction)
- ✅ **Single command execution** (fully automated)

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file with database credentials:
```env
BASTION_HOST=your_bastion_host
BASTION_USER=your_bastion_user
DB_HOST=your_db_host
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PORT=5432
DB_PASS=your_db_password
```

**Note**: `.env` is in `.gitignore` - keep it local and never commit credentials!

### Run the Pipeline

```bash
python main.py
```

That's it! The entire pipeline runs automatically in one command.

---

## 📊 Pipeline Workflow

### Step 1: Extract Base Data
**File**: `extract_base_data.py`

Extracts fresh reference data every run:
- **BlinkitProduct** → `bp.csv.gz`
- **BlinkitMerchant** → `bm.csv.gz`
- **BlinkitCategory** → `bc.csv.gz`

**Location**: `cwd/data/{start_date}-{end_date}/`

### Step 2: Extract Availability Data
**File**: `extract_availability.py`

Extracts BlinkitProductMerchant availability data:
- **Query**: Uses indexed range scan (`>` and `<` for better performance)
- **Date Range**: Configurable (default: 2026-02-09 to 2026-02-10)
- **Output**: `availability_TIMESTAMP.csv.gz`

**Location**: Same dated folder as Step 1

### Step 3: Combine & Process
**File**: `combine_and_process.py`

1. **Load** all base data (BP, BM, BC)
2. **Load** availability data
3. **Join locally**:
   - Availability ← Product (on productid)
   - + Merchant (on merchantid)
   - + Category (on categoryId, subCategoryId)
4. **Save combined raw file** (before grouping)
5. **Group** by productid + merchantid
6. **Calculate inventory metrics**:
   - `sold_inventory`: Total units sold
   - `restocked_inventory`: Total units restocked
7. **Save combined raw file**: `combined_raw_TIMESTAMP.csv` (before grouping)
8. **Save final output**: `combined_processed_TIMESTAMP.csv` (with inventory calculations)
9. **Clean up** intermediate files (local + Bastion)

**Location**: Same dated folder

**Output Files Kept**:
- `combined_raw_TIMESTAMP.csv` - Raw combined data (for reference/debugging)
- `combined_processed_TIMESTAMP.csv` - Final processed data with inventory metrics

---

## 🗂️ Folder Structure

```
cwd/
├── main.py                          # Master pipeline runner
├── extract_base_data.py             # Extract BP, BM, BC
├── extract_availability.py          # Extract availability
├── combine_and_process.py           # Combine & calculate
├── helper.py                        # Database utilities
├── requirements.txt                 # Dependencies
├── .env                             # Database credentials (gitignored)
├── .gitignore                       # Git ignore rules
├── README.md                        # This file
└── data/
    └── 2026-02-09-2026-02-10/      # Dated folder
        ├── bp.csv.gz                # (deleted after processing)
        ├── bm.csv.gz                # (deleted after processing)
        ├── bc.csv.gz                # (deleted after processing)
        ├── availability_*.csv.gz    # (deleted after processing)
        ├── combined_raw_*.csv       # (deleted after processing)
        └── combined_processed_*.csv # ✅ FINAL OUTPUT (kept)
```

---

## ⚙️ Configuration

### Change Date Range

Edit the `start_date` and `end_date` in all three extraction scripts:

**extract_base_data.py** (line ~11)
```python
start_date = "2026-02-09 18:30:00.00"
end_date = "2026-02-10 18:30:00.00"
```

**extract_availability.py** (line ~10)
```python
start_date = "2026-02-09 18:30:00.00"
end_date = "2026-02-10 18:30:00.00"
```

**combine_and_process.py** (line ~14)
```python
start_date = "2026-02-09 18:30:00.00"
end_date = "2026-02-10 18:30:00.00"
```

**⚠️ IMPORTANT**: Keep dates synchronized across all three files!

---

## 📊 Output Format

The final `combined_processed_*.csv` contains:

| Column | Type | Description |
|--------|------|-------------|
| `productid` | int | Product ID |
| `merchantid` | int | Merchant ID |
| `product` | str | Product name |
| `unit` | str | Product unit (e.g., "500ml") |
| `brand` | int | Brand ID |
| `categoryName` | str | Category name |
| `subCategoryName` | str | Subcategory name |
| `merchantname` | str | Merchant name |
| `pincode` | str | Merchant pincode |
| `city` | str | Merchant city |
| `mrp` | float | Maximum retail price |
| `date` | list | All timestamps in date range |
| `inventory` | list | Inventory levels over time |
| `discount` | list | Discounts over time |
| `price` | float | Median price |
| `sold_inventory` | int | **Total units sold** (calculated) |
| `restocked_inventory` | int | **Total units restocked** (calculated) |

---

## 🔄 How Data is Combined

### Join Sequence

```
Availability Data
    ↓ (join on productid)
+ BlinkitProduct
    ↓ (join on merchantid)
+ BlinkitMerchant
    ↓ (join on categoryId, subCategoryId)
+ BlinkitCategory
    ↓
Combined Data (all fields merged)
    ↓ (group by productid, merchantid)
Final Grouped Data
    ↓ (calculate inventory changes)
Final Output
```

### Why Local Joins?

- ✅ Reduces database load
- ✅ Faster than server-side joins
- ✅ More scalable
- ✅ Easier to debug and modify

---

## 📈 Inventory Calculation Logic

For each product-merchant combination:

```python
sold_inventory = sum(
    inventory[i-1] - inventory[i] 
    for i where inventory[i-1] > inventory[i]
)

restocked_inventory = sum(
    inventory[i] - inventory[i-1]
    for i where inventory[i] > inventory[i-1]
)
```

Example:
```
Inventory over time: [10, 8, 5, 7, 6]
Sold: (10→8)=2 + (8→5)=3 + (7→6)=1 = 6 units
Restocked: (5→7)=2 units
```

---

## 🧹 Cleanup Process

After processing, the pipeline automatically:

1. **Deletes locally**:
   - `bp.csv.gz` (BlinkitProduct)
   - `bm.csv.gz` (BlinkitMerchant)
   - `bc.csv.gz` (BlinkitCategory)
   - `availability_*.csv.gz` (Availability data)

2. **Keeps locally** (for reference/debugging):
   - `combined_raw_*.csv` (Raw combined data before grouping)

3. **Deletes from Bastion** (via SSH):
   - All extracted files
   - Pattern-based deletion (`availability_*.csv.gz`, etc.)

**Final output files**:
- `combined_raw_*.csv` (Raw data - kept for reference)
- `combined_processed_*.csv` (Final processed data with inventory calculations)

---

## 🔍 Database Query Details

### Base Data Extraction

Simple `SELECT` queries on static tables:
```sql
SELECT id, name, unit, brandId, categoryId, subCategoryId, mrp FROM "BlinkitProduct"
SELECT id, name, pincode, cityName FROM "BlinkitMerchant"
SELECT categoryId, subCategoryId, categoryName, subCategoryName FROM "BlinkitCategory"
```

### Availability Data Extraction

Optimized indexed range query:
```sql
SELECT createdAt, productId, merchantId, inventory, discount, price
FROM "BlinkitProductMerchant"
WHERE createdAt > '2026-02-09 18:30:00.00' 
  AND createdAt < '2026-02-10 18:30:00.00'
ORDER BY productId, merchantId, createdAt
```

**Why `>` and `<` instead of `BETWEEN`?**
- Better index utilization
- More efficient range scans
- Clearer query optimization hints

---

## 🐛 Troubleshooting

### Error: `.env` file not found
```bash
# Create .env with your database credentials
cat > .env << EOF
BASTION_HOST=...
BASTION_USER=...
DB_HOST=...
DB_NAME=...
DB_USER=...
DB_PORT=5432
DB_PASS=...
EOF
```

### Error: Product file not found
- Ensure `extract_base_data.py` runs first
- Check if dated folder was created: `cwd/data/YYYY-MM-DD-YYYY-MM-DD/`

### Error: No availability data found
- Run `extract_availability.py` explicitly
- Verify date range is correct
- Check database connection

### Slow processing
- This is expected! Inventory calculation is O(n*m) where:
  - n = number of product-merchant combinations
  - m = number of timestamps per combination
- Progress indicator shows every 10% completion

---

## 📝 Dependencies

```
pandas
psycopg2
sqlalchemy
python-dotenv
```

Install with:
```bash
pip install -r requirements.txt
```

---

## 🔐 Security

- ✅ `.env` is gitignored (credentials never committed)
- ✅ Uses SSH tunnel via Bastion host
- ✅ Credentials stored locally only
- ✅ Database password not logged

---

## 📖 Usage Examples

### Basic usage (default dates)
```bash
python main.py
```

### Custom date range

1. Update `start_date` and `end_date` in all three files
2. Run:
```bash
python main.py
```

### Extract only base data
```bash
python extract_base_data.py
```

### Extract only availability
```bash
python extract_availability.py
```

### Combine only (manual)
```bash
python combine_and_process.py
```

---

## 📊 Performance

| Step | Time | Notes |
|------|------|-------|
| Extract BP | 2-5 min | Depends on data size |
| Extract BM | 1-2 min | Usually fast |
| Extract BC | <1 min | Small table |
| Extract Availability | 5-10 min | Depends on date range |
| Combine & Group | 2-5 min | Fast locally |
| Calculate Inventory | 2-5 min | O(n*m) complexity |
| **Total** | **15-30 min** | Fully automated |

---

## 🎯 Next Steps

1. ✅ Clone repository
2. ✅ Create `.env` with credentials
3. ✅ Install dependencies: `pip install -r requirements.txt`
4. ✅ Run pipeline: `python main.py`
5. ✅ Check output: `data/YYYY-MM-DD-YYYY-MM-DD/combined_processed_*.csv`

---

## 📞 Support

For issues or questions:
1. Check the Troubleshooting section
2. Review log messages (they show exactly what happened)
3. Verify `.env` configuration
4. Check database connectivity

---

## 📄 License

This project is part of the Zodiac Scripts collection.

---

**Last Updated**: 11 February 2026
