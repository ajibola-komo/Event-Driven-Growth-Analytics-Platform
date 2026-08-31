import duckdb as db
import numpy as np
from src.generators.dimensions.dim_user import generate_users
from src.generators.dimensions.dim_product import generate_products
from src.generators.dimensions.dim_event_type import generate_event_types
from src.generators.dimensions.dim_date import generate_dates
from src.snowflake_setup.create_snowflake_tables import create_snowflake_bronze_tables
from dotenv import load_dotenv
from src.storage.adls_upload import upload_to_adls
from src.storage.adls_to_snowflake_upload import upload_from_adls_to_snowflake
from src.run_dbt.run_dbt import run_dbt_models
from src.generators.dimensions.dim_plan import generate_dim_plan
from src.generators.dimensions.dim_wallet import generate_list_of_wallets
from src.generators.facts.facts_tables import generate_facts
from src.generators.dimensions.dim_transaction_type import generate_transaction_types
from storage.adls_upload import upload_to_gcs
from storage.adls_to_snowflake_upload import upload_from_gcs_to_snowflake
from src.config.paths import DB_DIR, FINFLOW_DB_PATH

load_dotenv()

def create():
    create_snowflake_bronze_tables()
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with db.connect(FINFLOW_DB_PATH) as conn:
        generate_dates(conn)
        generate_products(conn)
        generate_event_types(conn)
        generate_dim_plan(conn)
        generate_users(conn,5000)
        generate_list_of_wallets(conn)
        generate_transaction_types(conn)
        generate_facts(conn,6000000)

    
    #upload_parquet_files()
    #upload_from_s3_to_snowflake()
    upload_to_adls()
    upload_from_adls_to_snowflake()
    run_dbt_models()


create()
