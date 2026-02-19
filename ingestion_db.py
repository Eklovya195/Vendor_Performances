import pandas as pd
import os
from sqlalchemy import create_engine
import logging

# --- Set up custom logger ---
logger = logging.getLogger("ingestion_db_logger")
logger.setLevel(logging.DEBUG)

# Avoid adding multiple handlers if already set
if not logger.handlers:
    os.makedirs("logs", exist_ok=True)
    file_handler = logging.FileHandler("logs/ingestion_db.log", mode="a", encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# --- Database engine ---
engine = create_engine('sqlite:///inventory.db')

def ingest_db(df, table_name, engine):
    '''This function ingests a DataFrame into the database'''
    df.to_sql(table_name, con=engine, if_exists='replace', index=False)
    logger.info(f'Table {table_name} ingested successfully.')

def load_raw_data():
    '''This function loads CSVs from the data folder and ingests them into the DB'''
    import time
    start = time.time()

    for file in os.listdir('data'):
        if file.endswith('.csv'):
            df = pd.read_csv(os.path.join('data', file))
            logger.info(f'Ingesting file: {file}')
            ingest_db(df, file[:-4], engine)

    end = time.time()
    total_time = (end - start) / 60
    logger.info('------- Ingestion Complete -------')
    logger.info(f'Total time taken: {total_time:.2f} minutes')

if __name__ == '__main__':
    load_raw_data()
