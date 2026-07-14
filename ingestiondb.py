import os
import time
import logging
import pandas as pd
from sqlalchemy import create_engine

# ==========================================
# Create Logs Folder (if it doesn't exist)
# ==========================================
os.makedirs("../logs", exist_ok=True)

# ==========================================
# Logging Configuration
# ==========================================
logging.basicConfig(
    filename="../logs/ingestion_db.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)

# ==========================================
# Database Connection
# ==========================================
engine = create_engine("sqlite:///inventory.db")

# ==========================================
# Function to Ingest Data into SQLite
# ==========================================
def ingest_db(df, table_name, engine, mode):
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists=mode,
        index=False
    )

# ==========================================
# Load All CSV Files
# ==========================================
def load_raw_data():

    start_time = time.time()

    CHUNK_SIZE = 10000

    logging.info("=" * 60)
    logging.info("Data Ingestion Started")

    for file in os.listdir():

        if file.endswith(".csv"):

            table_name = os.path.splitext(file)[0]

            print(f"\nProcessing {file}")
            logging.info(f"Started processing {file}")

            first_chunk = True
            total_rows = 0

            for chunk in pd.read_csv(file, chunksize=CHUNK_SIZE):

                ingest_db(
                    chunk,
                    table_name,
                    engine,
                    "replace" if first_chunk else "append"
                )

                total_rows += len(chunk)

                if total_rows % 100000 == 0 or first_chunk:
                    print(f"Inserted {total_rows:,} rows into {table_name}")

                first_chunk = False

            print(f"Finished {table_name}")

            logging.info(
                f"{table_name} imported successfully | Total Rows: {total_rows:,}"
            )

    end_time = time.time()

    total_time = (end_time - start_time) / 60

    print(f"\nTotal Time Taken : {total_time:.2f} Minutes")

    logging.info("=" * 60)
    logging.info("Data Ingestion Completed Successfully")
    logging.info(f"Total Time Taken : {total_time:.2f} Minutes")
    logging.info("=" * 60)


if __name__ == "__main__":
    load_raw_data()