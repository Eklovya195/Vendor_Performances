import sqlite3
import pandas as pd
import logging
from ingestion_db import ingest_db
import os

# --- Set up custom logger ---
logger = logging.getLogger("get_vendor_summary_logger")
logger.setLevel(logging.DEBUG)

# Avoid multiple handlers
if not logger.handlers:
    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler("logs/get_vendor_summary.log", mode="a", encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def create_vendor_summary(conn):
    '''Merge tables to get vendor summary'''
    query = """
    WITH FreightSummary AS (
        SELECT VendorNumber, SUM(Freight) AS FreightCost
        FROM vendor_invoice
        GROUP BY VendorNumber
    ),
    PurchaseSummary AS (
        SELECT 
            p.VendorNumber, p.VendorName, p.Brand, p.Description,
            p.PurchasePrice, pp.Volume, pp.Price AS ActualPrice,
            SUM(p.Quantity) AS TotalPurchaseQuantity,
            SUM(p.Dollars) AS TotalPurchaseDollars
        FROM purchases AS p
        JOIN purchase_prices AS pp ON p.Brand = pp.Brand
        WHERE p.PurchasePrice > 0
        GROUP BY p.VendorNumber, p.VendorName, p.Brand, p.Description, p.PurchasePrice, pp.Price, pp.Volume
    ),
    SalesSummary AS (
        SELECT 
            VendorNo, Brand,
            SUM(SalesDollars) AS TotalSalesDollars,
            SUM(SalesPrice) AS TotalSalesPrice,
            SUM(SalesQuantity) AS TotalSalesQuantity,
            SUM(ExciseTax) AS TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    )
    SELECT
        ps.VendorNumber, ps.VendorName, ps.Brand, ps.Description,
        ps.PurchasePrice, ps.ActualPrice, ps.Volume,
        ps.TotalPurchaseQuantity, ps.TotalPurchaseDollars,
        ss.TotalSalesDollars, ss.TotalSalesPrice, ss.TotalSalesQuantity, ss.TotalExciseTax,
        fs.FreightCost
    FROM PurchaseSummary ps
    LEFT JOIN SalesSummary ss ON ps.VendorNumber = ss.VendorNo AND ps.Brand = ss.Brand
    LEFT JOIN FreightSummary fs ON ps.VendorNumber = fs.VendorNumber
    ORDER BY TotalPurchaseDollars DESC
    """
    return pd.read_sql_query(query, conn)

def clean_data(df):
    '''Clean the vendor summary DataFrame'''
    df['Volume'] = df['Volume'].astype(float)
    df.fillna(0, inplace=True)
    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()

    df['GrossProfit'] = df['TotalSalesDollars'] - df['TotalPurchaseDollars']
    df['profitMargin'] = (df['GrossProfit'] / df['TotalSalesDollars']) * 100
    df['StockTurnover'] = df['TotalSalesQuantity'] / df['TotalPurchaseQuantity']
    df['SalesToPurchaseRatio'] = df['TotalSalesDollars'] / df['TotalPurchaseDollars']

    return df

if __name__ == '__main__':
    conn = sqlite3.connect('inventory.db')

    logger.info("Creating Vendor Summary Table...")
    summary_df = create_vendor_summary(conn)
    logger.info("Vendor Summary Table Created")

    logger.info("Cleaning Data...")
    clean_df = clean_data(summary_df)
    logger.info("Data Cleaned")

    logger.info("Ingesting Data into DB...")
    ingest_db(clean_df, 'vendor_sales_summary', conn)
    logger.info("Ingestion Completed Successfully")
