from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = PROJECT_ROOT / "raw"

EXPORT_DIR = DATA_DIR / "exports"
PARQUET_DIR = EXPORT_DIR / "parquet"
DB_DIR = PROJECT_ROOT / "db"
FINFLOW_DB_PATH = DB_DIR / "finflow.db"

RAW_DIM_EVENT_TYPE_PATH = RAW_DIR / "dim_event_type.csv"
RAW_DIM_PRODUCT_PATH = RAW_DIR / "dim_product.csv"
RAW_DIM_PLAN_PATH = RAW_DIR / "dim_plan.csv"
RAW_DIM_TRANSACTION_TYPE_PATH = RAW_DIR / "dim_transaction_type.csv"

# SQL PATHS
SQL_DIR = PROJECT_ROOT / "sql"
DDL_SQL_DIR = SQL_DIR / "ddl"
SNOWFLAKE_SQL_DIR = SQL_DIR / "snowflake_ddl"
DDL_DIM_DIR = DDL_SQL_DIR / "dimensions"
DDL_FACT_DIR = DDL_SQL_DIR / "facts"

SNOWFLAKE_DDL_DIM_DIR = SNOWFLAKE_SQL_DIR / "dimensions"
SNOWFLAKE_DDL_FACT_DIR = SNOWFLAKE_SQL_DIR / "facts"

#dimensions
DDL_DIM_EVENT_TYPE_PATH = DDL_DIM_DIR / "dim_event_type.sql"
DDL_DIM_TRANSACTION_TYPE_PATH = DDL_DIM_DIR / "dim_transaction_type.sql"
DDL_DIM_PRODUCT_PATH = DDL_DIM_DIR / "dim_product.sql"
DDL_DIM_USER_PATH = DDL_DIM_DIR / "dim_user.sql"
DDL_DIM_WALLET_PATH = DDL_DIM_DIR / "dim_wallet.sql"
DDL_DIM_DATE_PATH = DDL_DIM_DIR / "dim_date.sql"
DDL_DIM_PLAN_PATH = DDL_DIM_DIR / "dim_plan.sql"

#facts
DDL_FACT_USER_EVENT_PATH = DDL_FACT_DIR / "fact_user_event.sql"
DDL_FACT_INVESTMENT_POSITION_PATH = DDL_FACT_DIR / "fact_investment_position.sql"
DDL_FACT_TRANSACTION_PATH = DDL_FACT_DIR / "fact_transaction.sql"
DDL_FACT_WALLET_BALANCE_PATH = DDL_FACT_DIR / "fact_wallet_balance.sql"

#snowflake dimesion definition
SNOWFLAKE_DIM_EVENT_TYPE_PATH = SNOWFLAKE_DDL_DIM_DIR / "dim_event_type.sql"
SNOWFLAKE_DIM_TRANSACTION_TYPE_PATH = SNOWFLAKE_DDL_DIM_DIR / "dim_transaction_type.sql"
SNOWFLAKE_DIM_PRODUCT_PATH = SNOWFLAKE_DDL_DIM_DIR / "dim_product.sql"
SNOWFLAKE_DIM_USER_PATH = SNOWFLAKE_DDL_DIM_DIR / "dim_user.sql"
SNOWFLAKE_DIM_WALLET_PATH = SNOWFLAKE_DDL_DIM_DIR / "dim_wallet.sql"
SNOWFLAKE_DIM_DATE_PATH = SNOWFLAKE_DDL_DIM_DIR / "dim_date.sql"
SNOWFLAKE_DIM_PLAN_PATH = SNOWFLAKE_DDL_DIM_DIR / "dim_plan.sql"


#snowflake fact definition
SNOWFLAKE_FACT_USER_EVENT_PATH = SNOWFLAKE_DDL_FACT_DIR / "fact_user_event.sql"
SNOWFLAKE_FACT_INVESTMENT_POSITION_PATH = SNOWFLAKE_DDL_FACT_DIR / "fact_investment_position.sql"
SNOWFLAKE_FACT_TRANSACTION_PATH = SNOWFLAKE_DDL_FACT_DIR / "fact_transaction.sql"
SNOWFLAKE_FACT_WALLET_BALANCE_PATH = SNOWFLAKE_DDL_FACT_DIR / "fact_wallet_balance.sql"


SNOWFLAKE_DDL_PATHS = [SNOWFLAKE_DIM_EVENT_TYPE_PATH, SNOWFLAKE_DIM_PRODUCT_PATH,  SNOWFLAKE_DIM_TRANSACTION_TYPE_PATH,
                    SNOWFLAKE_DIM_USER_PATH, SNOWFLAKE_DIM_WALLET_PATH, SNOWFLAKE_DIM_DATE_PATH, SNOWFLAKE_DIM_PLAN_PATH, 
                    SNOWFLAKE_FACT_USER_EVENT_PATH, SNOWFLAKE_FACT_INVESTMENT_POSITION_PATH, SNOWFLAKE_FACT_TRANSACTION_PATH, SNOWFLAKE_FACT_WALLET_BALANCE_PATH]

#parquet paths
DATES_PARQUET_PATH = PARQUET_DIR / "dim_date.parquet"
PRODUCTS_PARQUET_PATH = PARQUET_DIR / "dim_product.parquet"
USERS_PARQUET_PATH = PARQUET_DIR / "dim_user.parquet"
WALLETS_PARQUET_PATH = PARQUET_DIR / "dim_wallet.parquet"
EVENT_TYPES_PARQUET_PATH = PARQUET_DIR / "dim_event_type.parquet"
TRANSACTION_TYPE_PARQUET_PATH = PARQUET_DIR / "dim_transaction_type.parquet"
PLANS_PARQUET_PATH = PARQUET_DIR / "dim_plan.parquet"
FACT_USER_EVENT_PARQUET_PATH = PARQUET_DIR / "fact_user_event.parquet"
FACT_INVESTMENT_POSITION_PARQUET_PATH = PARQUET_DIR / "fact_investment_position.parquet"
FACT_TRANSACTION_PARQUET_PATH = PARQUET_DIR / "fact_transaction.parquet"
FACT_WALLET_BALANCE_PARQUET_PATH = PARQUET_DIR / "fact_wallet_balance.parquet"


#s3
S3_BUCKET_NAME = "finflow-s3-bucket"

LOCAL_FILE_PATHS = [DATES_PARQUET_PATH, PRODUCTS_PARQUET_PATH, USERS_PARQUET_PATH, EVENT_TYPES_PARQUET_PATH, PLANS_PARQUET_PATH, WALLETS_PARQUET_PATH, TRANSACTION_TYPE_PARQUET_PATH,
                    FACT_TRANSACTION_PARQUET_PATH, FACT_INVESTMENT_POSITION_PARQUET_PATH, FACT_WALLET_BALANCE_PARQUET_PATH, FACT_USER_EVENT_PARQUET_PATH 
                       ]



S3_KEYS = [
    "dim_date.parquet", "dim_product.parquet", "dim_user.parquet", "dim_event_type.parquet","dim_plan.parquet","dim_wallet.parquet",  "dim_transaction_type.parquet",
    "fact_transaction.parquet","fact_investment_position.parquet","fact_wallet_balance.parquet","fact_user_event.parquet"
]

TABLE_NAMES = ["dim_date","dim_product","dim_user","dim_event_type","dim_plan","dim_wallet","dim_transaction_type","fact_transaction","fact_investment_position","fact_wallet_balance","fact_user_event"]

ADLS_FILE_NAMES = [
    "dim_date.parquet", "dim_product.parquet", "dim_user.parquet", "dim_event_type.parquet","dim_plan.parquet","dim_wallet.parquet",  "dim_transaction_type.parquet",
    "fact_transaction.parquet","fact_investment_position.parquet","fact_wallet_balance.parquet","fact_user_event.parquet"
]

# "fact_user_event.parquet", "fact_investment_position.parquet","fact_transaction.parquet"

# FACT_USER_EVENT_PARQUET_PATH, FACT_INVESTMENT_POSITION_PARQUET_PATH, FACT_TRANSACTION_PARQUET_PATH