import numpy as np
import pandas as pd
from src.config.paths import (DDL_DIM_WALLET_PATH, WALLETS_PARQUET_PATH)
from src.config.constants import (DEFAULT_TRANSACTION_START_TIMESTAMP, DEFAULT_TRANSACTION_END_TIMESTAMP)
from datetime import timedelta

def generate_list_of_wallets(conn):
    create_db = DDL_DIM_WALLET_PATH.read_text()

    conn.execute(create_db)

    users_data = conn.execute('''
            SELECT * FROM dim_user order by signup_date ASC
    ''').df()

    total_users = len(users_data)

    wallet_ids = np.arange(1, total_users + 1)

    user_ids = users_data["user_id"]

    wallet_created_at = users_data["signup_date"]

    assert wallet_created_at.notna().all(), "Wallet creation date cannot be null"

    is_activated_user = users_data["is_activated_user"]

    assert is_activated_user.notna().all(),"Activation status cannot be null"

    active_mask = np.where(is_activated_user == True)[0]
    inactive_mask = np.where(is_activated_user == False)[0]

    activation_timeframe = users_data["wallet_activation_timeframe"]

    assert (activation_timeframe[active_mask] > 0).all(), "activation timeframe must be greater than 0"

    wallet_activated_at = np.empty(
        total_users,
        dtype=object
    )


    wallet_activated_at[active_mask] = np.array([ca + pd.to_timedelta(int(ro),unit="m") for ca,ro in zip(wallet_created_at[active_mask], activation_timeframe[active_mask])])
    wallet_activated_at[inactive_mask] = None

    assert (wallet_created_at[active_mask] < wallet_activated_at[active_mask]).all(),"Wallet cannot be activated before creation"

    wallet_activated_at_id = np.empty(total_users,
        dtype=object)

    wallet_created_at_id = [int(pd.Timestamp(wallet_created_at[i]).strftime('%Y%m%d')) for i in range(total_users)]
    wallet_activated_at_id[active_mask] = [int(pd.Timestamp(i).strftime('%Y%m%d')) for i in wallet_activated_at[active_mask]]

    wallet_currency = "GBP"

    created_at = wallet_created_at
    last_updated_at = created_at

    df_raw = pd.DataFrame({
        'wallet_id':wallet_ids,
        'user_id':user_ids,
        'wallet_currency':wallet_currency,
        'wallet_created_at':wallet_created_at,
        'wallet_activated_at':wallet_activated_at,
        'wallet_created_at_id':wallet_created_at_id,
        'wallet_activated_at_id':wallet_activated_at_id,
        'created_at':created_at,
        'last_updated_at':last_updated_at
    })
    conn.register('df_raw', df_raw)

    conn.execute('''INSERT into dim_wallet select * from df_raw''')

    conn.execute(f'''COPY dim_wallet to '{WALLETS_PARQUET_PATH}' (FORMAT PARQUET) ''')

    






    