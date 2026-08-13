import pandas as pd
import numpy as np

def update_last_login_timestamp(conn, user_ids, last_login):

    logins_df = pd.DataFrame({
        'user_id':user_ids,
        'last_login_at':last_login
    })

    conn.register('logins_df',logins_df)

    conn.execute('''
            UPDATE dim_user d set last_login_at = a.last_login_at from logins_df a where d.user_id = a.user_id
    ''')

    conn.unregister('logins_df')


def signup_completion_events(conn,start_position, end_position, user_ids, uids, event_times,event_time,device_types,dtypes,event_type_ids ):
    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position]= event_time
    device_types[start_position:end_position] = dtypes

    event_type_id = conn.execute('''select event_type_id from dim_event_type where event_type_code = 'signup_completed' ''').fetchone()[0]
    event_type_ids[start_position:end_position] = event_type_id


def app_login_events(conn,start_position, end_position, user_ids, uids, event_times,event_time,device_types,dtypes,event_type_ids):
    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position]= event_time
    device_types[start_position:end_position] = dtypes

    event_type_id = conn.execute('''select event_type_id from dim_event_type where event_type_code = 'app_login' ''').fetchone()[0]
    event_type_ids[start_position:end_position] = event_type_id

    update_last_login_timestamp(conn, uids,event_time)


def get_last_login(conn, uids):

    conn.register('uids',uids)

    login_info = conn.execute(''' SELECT
            u.user_id,
            u.last_login_at
        FROM dim_user AS u
        INNER JOIN uids AS ids
            ON u.user_id = ids.user_id ''').df()

    conn.unregister('uids')

    return login_info

def kyc_completion_events(conn,start_position, end_position, user_ids, uids, event_times,event_time,device_types,dtypes,event_type_ids):

    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position]= event_time
    device_types[start_position:end_position] = dtypes
    
    event_type_id = conn.execute('''select event_type_id from dim_event_type where event_type_code = 'kyc_completed' ''').fetchone()[0]
    event_type_ids[start_position:end_position] = event_type_id

    kyc_activation_df = pd.DataFrame({
        'user_id':uids,
        'kyc_completion_date':event_time
    })

    conn.register('kyc_activation_df',kyc_activation_df)

    conn.execute(''' UPDATE dim_user d set kyc_completed = true, kyc_completion_date = k.kyc_completion_date from kyc_activation_df k where d.user_id = k.user_id  ''')

    conn.unregister('kyc_activation_df')


def wallet_activation_events(conn, start_position, end_position, user_ids, uids, event_times, event_time, device_types,dtypes,event_type_ids, wallet_ids, wids, is_money_movement_activity, transaction_type_ids, transaction_ids, transaction_amounts,tran_amount, transaction_statuses):

    last_transaction_id = conn.execute(''' SELECT coalesce(max(transaction_id),0) from fact_transaction ''').fetchone()[0]

    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position] = event_time
    device_types[start_position:end_position] = dtypes

    event_type_id = conn.execute('''select event_type_id from dim_event_type where event_type_code = 'wallet_funded' ''').fetchone()[0]
    event_type_ids[start_position:end_position] = event_type_id

    transaction_type_id = conn.execute(''' select transaction_type_id from dim_transaction_type where transaction_type_code = 'wallet_funding' ''').fetchone()[0]
    transaction_type_ids[start_position:end_position] = transaction_type_id

    wallet_ids[start_position:end_position] = wids

    is_money_movement_activity[start_position:end_position] = True

    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + len(uids) + 1)

    transaction_amounts[start_position:end_position] = tran_amount

    transaction_statuses[start_position:end_position] = "success"

    last_transaction_id = transaction_ids[start_position:end_position].max()

    return last_transaction_id
