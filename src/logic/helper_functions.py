import pandas as pd
import numpy as np
from datetime import timedelta



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


def signup_completion_events(context, start_position, end_position, user_ids, uids, event_times,event_time,device_types,dtypes,event_type_ids ):
    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position]= event_time
    device_types[start_position:end_position] = dtypes

    event_type_ids[start_position:end_position] = context.signup_completed_event_type_id


def app_login_events(conn,context, start_position, end_position, user_ids, uids, event_times,event_time,device_types,dtypes,event_type_ids):
    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position]= event_time
    device_types[start_position:end_position] = dtypes

    event_type_ids[start_position:end_position] = context.app_login_event_type_id

    update_last_login_timestamp(conn, uids,event_time)


def get_last_login(conn, uids):

    uids_df = pd.DataFrame({"user_id": uids})

    conn.register('uids_df',uids_df)

    login_info = conn.execute(''' SELECT
            u.user_id,
            u.last_login_at
        FROM dim_user AS u
        INNER JOIN uids_df AS ids
            ON u.user_id = ids.user_id ''').df()

    conn.unregister('uids_df')

    return login_info

def kyc_completion_events(conn,context,start_position, end_position, user_ids, uids, 
                          event_times,event_time,device_types,dtypes,event_type_ids):

    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position]= event_time
    device_types[start_position:end_position] = dtypes
    
    
    event_type_ids[start_position:end_position] = context.kyc_completed_event_type_id

    kyc_activation_df = pd.DataFrame({
        'user_id':uids,
        'kyc_completion_date':event_time
    })

    conn.register('kyc_activation_df',kyc_activation_df)

    conn.execute(''' UPDATE dim_user d set kyc_completed = true, kyc_completion_date = k.kyc_completion_date from kyc_activation_df k where d.user_id = k.user_id  ''')

    conn.unregister('kyc_activation_df')


def wallet_activation_events(conn, context, start_position, end_position, 
                             user_ids, uids, event_times, event_time, device_types,dtypes,
                             event_type_ids, wallet_ids, wids, is_money_movement_activity,
                            transaction_type_ids, transaction_ids, transaction_amounts,tran_amount, 
                            transaction_statuses, last_transaction_id):

    
    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position] = event_time
    device_types[start_position:end_position] = dtypes

    
    event_type_ids[start_position:end_position] = context.wallet_funded_event_type_id

    
    transaction_type_ids[start_position:end_position] = context.wallet_funding_transaction_type_id

    wallet_ids[start_position:end_position] = wids

    is_money_movement_activity[start_position:end_position] = True

    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + len(uids) + 1)

    tran_ids = transaction_ids[start_position:end_position]

    transaction_amounts[start_position:end_position] = tran_amount

    transaction_statuses[start_position:end_position] = "success"

    last_transaction_id = transaction_ids[start_position:end_position].max()

    update_wallet_balance(conn, uids, tran_amount, tran_ids, event_time)

    return last_transaction_id


def update_wallet_balance(conn, uids, transaction_amount, transaction_ids, event_time):

    wallet_activation_df = pd.DataFrame({
            'user_id':uids,
            'transaction_amount':transaction_amount,
            'last_transaction_id':transaction_ids,
            'last_updated_at':event_time
        })
    
    conn.register('wallet_activation_df', wallet_activation_df)
    
    conn.execute(''' UPDATE fact_wallet_balance as f set current_balance = current_balance + w.transaction_amount,
                        last_updated_at = w.last_updated_at, updated_at = w.last_updated_at, last_updated_at_id = CAST(strftime(w.last_updated_at, '%Y%m%d') AS BIGINT),
                        last_transaction_id = w.last_transaction_id from wallet_activation_df as w WHERE f.user_id = w.user_id 
              ''') 
    
    conn.unregister('wallet_activation_df')

def get_current_wallet_balance(conn, uids):

    uids_df = pd.DataFrame({
        'user_id':uids
    })

    conn.register('uids_df',uids_df)

    try:
        current_balances = conn.execute('''SELECT w.user_id, w.current_balance from fact_wallet_balance w inner join
        uids_df u on w.user_id = u.user_id ''').df()
    finally:
        conn.unregister('uids_df')

    return current_balances

def review_plan_options_events(conn, context, start_position, end_position, user_ids, uids, event_times, event_type_ids, device_types, dtypes):

    login_info = get_last_login(conn, uids)

    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position] = [last_login + timedelta(minutes=np.random.randint(2, 5)) for last_login in login_info["last_login_at"]]
    device_types[start_position:end_position] = dtypes
    event_type_ids[start_position:end_position] = context.review_plan_options_event_type_id

def plan_selection_events(conn, context, start_position, end_position, user_ids, uids, event_time, plan_review_time, event_type_ids, device_types, dtypes):

    random_offset = np.random.randint(1,3,size=len(uids))
    plan_selection_time = [review_time + timedelta(minutes=ro) for review_time, ro in zip(plan_review_time, random_offset)]

    user_ids[start_position:end_position] = uids
    event_time[start_position:end_position] = plan_selection_time
    event_type_ids[start_position:end_position] = context.plan_selected_event_type_id
    device_types[start_position:end_position] = dtypes

    plan_selection_df = pd.DataFrame({
        'user_id':uids,
        'plan_selection_time':plan_selection_time
    })

    return plan_selection_df






    

