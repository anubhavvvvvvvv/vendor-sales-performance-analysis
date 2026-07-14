import sqlite3
import pandas as pd
import logging
from ingestiondb import ingest_db

logging.basicConfig(
    filename="logs/get_vendor_summary.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)


def create_vendor_summary(conn):
    """
    Creates a consolidated vendor sales summary by merging
    purchases, purchase_prices, sales and vendor_invoice tables.
    """

    logging.info("Executing vendor summary SQL query...")

    vendor_sales_summary = pd.read_sql_query("""
    WITH FreightSummary AS (
        SELECT
            VendorNumber,
            SUM(Freight) AS FreightCost
        FROM vendor_invoice
        GROUP BY VendorNumber
    ),

    PurchaseSummary AS (
        SELECT
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            pp.Price AS ActualPrice,
            pp.Volume,
            SUM(p.Quantity) AS TotalPurchaseQuantity,
            SUM(p.Dollars) AS TotalPurchaseDollars
        FROM purchases p
        JOIN purchase_prices pp
            ON p.Brand = pp.Brand
        WHERE p.PurchasePrice > 0
        GROUP BY
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            pp.Price,
            pp.Volume
    ),

    SalesSummary AS (
        SELECT
            VendorNo,
            Brand,
            SUM(SalesQuantity) AS TotalSalesQuantity,
            SUM(SalesDollars) AS TotalSalesDollars,
            SUM(SalesPrice) AS TotalSalesPrice,
            SUM(ExciseTax) AS TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    )

    SELECT
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM PurchaseSummary ps
    LEFT JOIN SalesSummary ss
        ON ps.VendorNumber = ss.VendorNo
        AND ps.Brand = ss.Brand
    LEFT JOIN FreightSummary fs
        ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC;
    """, conn)

    logging.info(
        f"Vendor summary query executed successfully. Shape: {vendor_sales_summary.shape}"
    )

    return vendor_sales_summary


def clean_data(df):
    logging.info("Cleaning vendor summary data...")

    # Changing datatype
    df["Volume"] = df["Volume"].astype(float)

    # Filling missing values
    df.fillna(0, inplace=True)

    # Removing leading/trailing spaces
    df["VendorName"] = df["VendorName"].str.strip()
    df["Description"] = df["Description"].str.strip()

    # Creating new columns for better analysis
    df["GrossProfit"] = (
        df["TotalSalesDollars"]
        - df["TotalPurchaseDollars"]
    )

    df["ProfitMargin"] = (
        df["GrossProfit"]
        / df["TotalSalesDollars"]
    ) * 100

    df["StockTurnover"] = (
        df["TotalSalesQuantity"]
        / df["TotalPurchaseQuantity"]
    )

    df["SalesToPurchaseRatio"] = (
        df["TotalSalesDollars"]
        / df["TotalPurchaseDollars"]
    )

    logging.info("Data cleaning completed successfully.")

    return df


if __name__ == "__main__":

    conn = None

    try:

        logging.info("=" * 70)
        logging.info("Vendor Summary ETL Pipeline Started")

        # Creating database connection
        conn = sqlite3.connect(
            r"C:\Users\ASUS\Downloads\data\data\inventory.db"
        )

        logging.info("Database connection established.")

        # Creating Vendor Summary Table
        logging.info("Creating Vendor Summary Table.....")
        summary_df = create_vendor_summary(conn)
        logging.info(summary_df.head())
        logging.info(f"Vendor Summary Shape : {summary_df.shape}")

        # Cleaning Data
        logging.info("Cleaning Data.....")
        clean_df = clean_data(summary_df)
        logging.info(clean_df.head())
        logging.info(f"Clean Data Shape : {clean_df.shape}")

        # Ingesting Data
        logging.info("Ingesting Data.....")
        ingest_db(
            clean_df,
            "vendor_sales_summary_original",
            conn
        )

        logging.info(
            "vendor_sales_summary_original table created successfully."
        )

        logging.info("Vendor Summary ETL Pipeline Completed Successfully")

    except Exception as e:

        logging.exception(f"Pipeline Failed: {e}")

    finally:

        if conn:
            conn.close()
            logging.info("Database connection closed.")

        logging.info("=" * 70)