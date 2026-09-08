import pandas as pd
import numpy as np
from datetime import timedelta
from src.config.constants import (CUSTOMER_BEHAVIOUR_SEGMENT_MAP, USERS_MAKES_FIRST_INVESTMENT_AFTER_FUNDING, FIRST_INVESTMENT_TYPE, TODAY, EARLY_WITHDRAWAL_BEHAVIOUR,
                                    INVESTMENT_WITHDRAWAL_PROCESSING_TIME)
from duckdb import DuckDBPyConnection
from dateutil.relativedelta import relativedelta
from src.logic.EventContext import (load_event_context)

def update_last_login_timestamp(conn: DuckDBPyConnection,
                                user_ids: list[int],
                                last_login: list[pd.Timestamp]) -> None:


    if len(user_ids) != len(last_login):
        raise ValueError("user_ids and last_login must have the same length.")

    logins_df = pd.DataFrame({
        'user_id':user_ids,
        'last_login_at':last_login
    })

    conn.register('logins_df',logins_df)

    conn.execute('''
            UPDATE dim_user d set last_login_at = a.last_login_at from logins_df a where d.user_id = a.user_id
    ''')

    conn.unregister('logins_df')

def signup_completion_events(context: any, start_position: int, end_position: int, user_ids: list, uids: list[int], event_times: list, event_time: list[pd.Timestamp], device_types: list, dtypes: list[str], event_type_ids: list) -> None: 
    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position]= event_time
    device_types[start_position:end_position] = dtypes

    event_type_ids[start_position:end_position] = [context.signup_completed_event_type_id] * len(uids)

def app_login_events(conn: DuckDBPyConnection, context: any, start_position: int, end_position: int, user_ids: list, uids: list[int], event_times: list, event_time: list[pd.Timestamp], device_types: list, dtypes: list[str], event_type_ids: list) -> None:
    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position]= event_time
    device_types[start_position:end_position] = dtypes

    event_type_ids[start_position:end_position] = [context.app_login_event_type_id] * len(uids)

    update_last_login_timestamp(conn, uids,event_time)

def get_last_login(conn: DuckDBPyConnection, uids: list[int]) -> pd.DataFrame:

    """
        Returns the login_info dataframe with the following attributes:
            - user_id
            - last_login_at
    """

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

def kyc_completion_events(conn: DuckDBPyConnection,context:any,start_position:int, end_position:int, user_ids:list[int], uids:list[int], 
                          event_times:list[pd.Timestamp],event_time:list[pd.Timestamp],device_types:list[str],dtypes:list[str],
                          event_type_ids:list[int]) -> None:

    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position]= event_time
    device_types[start_position:end_position] = dtypes
    
    event_type_ids[start_position:end_position] = [context.kyc_completed_event_type_id] * len(uids)

    kyc_activation_df = pd.DataFrame({
        'user_id':uids,
        'kyc_completion_date':event_time
    })

    conn.register('kyc_activation_df',kyc_activation_df)

    conn.execute(''' UPDATE dim_user d set kyc_completed = true, kyc_completion_date = k.kyc_completion_date from kyc_activation_df k where d.user_id = k.user_id  ''')

    conn.unregister('kyc_activation_df')

def wallet_activation_events(conn: DuckDBPyConnection, context: any, start_position:int, end_position:int, 
                             user_ids:list[int], uids:list[int], event_times:list[pd.Timestamp], event_time:list[pd.Timestamp], device_types:list[str],dtypes:list[str],
                             event_type_ids:list[int], wallet_ids:list[int], wids:list[int], is_money_movement_activity:list[bool],
                            transaction_type_ids:list[int], transaction_ids:list[int], transaction_amounts:list[float], 
                            transaction_statuses:list[str], last_transaction_id:int) -> dict:

    """
        This method creates the wallet activation events i.e. a registered user's first funding.
        This methods calls:
            1) app_login_events() function to login first
            2) generate_wallet_funding_amount() function to create the funding amounts based on the user's customer behaviour segment.
            3) update_wallet_balance() function to update the fact_wallet_balance table with the updated transaction amounts.
            4) activate_wallet() to update the dim_wallet table
        
        Returns the last_transaction_id after updating the wallet balance for the given users.
    
    """

    #first we need to get the customer behaviour segment to generate the transaction amount for each user

    login_times = [et - timedelta(minutes = np.random.randint(4,8)) for et in event_time]

    app_login_events(conn, context, start_position, end_position, user_ids, uids, event_times, login_times, device_types, dtypes, event_type_ids)

    start_position = end_position
    end_position = start_position + len(uids)

    tran_amount = generate_wallet_funding_amounts(conn, uids)
    
    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position] = event_time
    device_types[start_position:end_position] = dtypes

    
    event_type_ids[start_position:end_position] = [context.wallet_funded_event_type_id] * len(uids)

    
    transaction_type_ids[start_position:end_position] = [context.wallet_funding_transaction_type_id] * len(uids)

    wallet_ids[start_position:end_position] = wids

    is_money_movement_activity[start_position:end_position] = True

    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + len(uids) + 1)

    tran_ids = transaction_ids[start_position:end_position]

    transaction_amounts[start_position:end_position] = tran_amount

    transaction_statuses[start_position:end_position] = ["success"] * len(uids)

    last_transaction_id = transaction_ids[start_position:end_position].max()

    update_wallet_balance(conn, uids, tran_amount, tran_ids, event_time)

    activate_wallet(conn, uids, event_time)

    updated_end_position = end_position

    return {
        'last_transaction_id':last_transaction_id,
        'updated_end_position':updated_end_position
        }

def update_wallet_balance(conn:DuckDBPyConnection, uids:list[int], transaction_amount:list[float], transaction_ids:list[int], event_time:list[pd.Timestamp]) -> None:

    """
        This function updates the fact_wallet_balance table with the updated transaction amounts for the given users.
    """

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

def activate_wallet(conn, uids, funding_time):

    activation_df = pd.DataFrame({

        'user_id':uids,
        'event_time':funding_time

    })

    conn.register('activation_df', activation_df)

    conn.execute('''update dim_wallet as w set wallet_activated_at = a.event_time, last_updated_at = a.event_time, wallet_activated_at_id = CAST(strftime(a.event_time, '%Y%m%d') AS BIGINT) 
        from activation_df as a where w.user_id = a.user_id
    ''')

    conn.unregister('activation_df')

def deduct_wallet_balance(conn:DuckDBPyConnection, uids:list[int], transaction_amount:list[float], transaction_ids:list[int], event_time:list[pd.Timestamp]) -> None:

    transactions_data_df = pd.DataFrame({
        'user_id':uids,
        'transaction_amount':transaction_amount,
        'transaction_id':transaction_ids,
        'last_updated_at':event_time
    })

    conn.register('transactions_df',transactions_data_df)

    conn.execute('''
            UPDATE fact_wallet_balance AS f SET current_balance = f.current_balance - t.transaction_amount, last_updated_at = t.last_updated_at, 
            updated_at = t.last_updated_at, last_updated_at_id = CAST(strftime(t.last_updated_at, '%Y%m%d') AS BIGINT),
                                    last_transaction_id = w.last_transaction_id FROM transactions_df AS t WHERE f.user_id = t.user_id''')

    conn.unregister('transactions_df')

def get_current_wallet_balance(conn:DuckDBPyConnection, uids:list[int]) -> pd.DataFrame:

    """
        This function returns the current wallet balance for the given users.
        It returns a data frame with the following attributes:
            - user_id
            - current_balance    
    """

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
    event_type_ids[start_position:end_position] = [context.review_plan_options_event_type_id] * len(uids)

def plan_selection_events(context:any, start_position:int, end_position:int, user_ids:list[int], uids:list[int], event_time:list[pd.Timestamp], plan_review_time:list[pd.Timestamp], event_type_ids:list[int], device_types:list[int], dtypes:list[int]) -> pd.DataFrame:


    """
        This function generates the plan selection events and returns a dataframe with the following attributes:
            - user_id
            - plan_selection_time   
        """

    random_offset = np.random.randint(1,3,size=len(uids))
    plan_selection_time = [review_time + timedelta(minutes=ro) for review_time, ro in zip(plan_review_time, random_offset)]

    user_ids[start_position:end_position] = uids
    event_time[start_position:end_position] = plan_selection_time
    event_type_ids[start_position:end_position] = [context.plan_selected_event_type_id] * len(uids)
    device_types[start_position:end_position] = dtypes

    plan_selection_df = pd.DataFrame({
        'user_id':uids,
        'plan_selection_time':plan_selection_time
    })

    return plan_selection_df


def plan_ids_allocation(conn:DuckDBPyConnection, context:any, uids:list[int], investment_type:list[str], plan_selection_time:list[pd.Timestamp]) -> pd.DataFrame:


    """
        Returns a dataframe with the following attributes:
            - user_id
            - investment_type
            - plan_id
            - plan_name
            - plan_selection_time
            - event_type_ids(the event type ids are already pre-allocated)
            - transaction_type_ids (the transaction type ids are already pre-allocated)
    """

    savings_plans = conn.execute('''select plan_id, plan_name, plan_weight from dim_plan where plan_category = 'Savings' ''').df()

    investment_plans = conn.execute('''select plan_id, plan_name, plan_weight from dim_plan where plan_category = 'Investments' ''').df()

    total_plans = len(uids)

    plan_id = np.empty(total_plans, dtype=np.int64)

    event_type_ids = np.empty(total_plans, dtype=np.int64)

    transaction_types_ids = [context.investment_funding_transaction_type_id] * total_plans

    plan_ids_allocation_df = pd.DataFrame({
        'user_id':uids,
        'investment_type':investment_type,
        'plan_id':plan_id,
        'plan_selection_time':plan_selection_time,
        'event_type_id':event_type_ids,
        'transaction_type_id':transaction_types_ids
    })

    savings_mask = plan_ids_allocation_df["investment_type"] == "Savings"
    investment_mask = plan_ids_allocation_df["investment_type"] == "Investment"

    plan_ids_allocation_df.loc[savings_mask,"plan_id"] = np.random.choice(savings_plans["plan_id"], 
                                                                           p = savings_plans["plan_weight"] / savings_plans["plan_weight"].sum(),
                                                                           size=savings_mask.sum())
                                                                           

    plan_ids_allocation_df.loc[savings_mask,"event_type_id"] = context.savings_plan_created_event_type_id
    plan_ids_allocation_df.loc[investment_mask,"event_type_id"] = context.investment_plan_created_event_type_id


    plan_ids_allocation_df.loc[investment_mask, "plan_id"] = np.random.choice(investment_plans["plan_id"], 
                                                                           p = investment_plans["plan_weight"] / investment_plans["plan_weight"].sum(),
                                                                           size = investment_mask.sum())

    conn.register('plan_ids_allocation_df', plan_ids_allocation_df)

    plan_names = conn.execute('''SELECT f.user_id, f.plan_id, p.plan_name from dim_plan p inner join plan_ids_allocation_df f on p.plan_id = f.plan_id''').df()

    plan_ids_allocation_df = plan_ids_allocation_df.merge(plan_names, how="inner", on=["user_id","plan_id"])

    conn.unregister('plan_ids_allocation_df')

    return plan_ids_allocation_df


def investment_creation_events(conn: DuckDBPyConnection, context:any, start_position:int, end_position:int, user_ids:list[int],uids:list[int], wallet_ids:list[int], event_times:list[pd.Timestamp], 
                               plan_selection_time:list[pd.Timestamp], investment_type:list[str], device_types:list[str], dtypes:list[str], 
                               is_money_movement_activities:list[bool], transaction_ids:list[int], last_transaction_id:int, 
                               transaction_type_ids:list[int], event_type_ids:list[int], plan_ids:list[int], transaction_amounts:list[float], amount_invested:list[float], transaction_statuses:list[str]) -> dict:

    """
        Return a dataframe with the following attributes:
            - user_id
            - wallet_id
            - plan_id
            - amount_invested
            - expected_maturity_date
            - investment_start_date
            - investment_start_date_id
            - investment_maturity_date
            - investment_maturity_date_id
            - investment_status
            - is_withdrawn_early
            - penalty_amount
            - amount_paid_out
            - early_withdrawal_date
            - early_withdrawal_date_id
            - created_at
            - last_updated_at
    
    """

    plan_ids_allocation_df = plan_ids_allocation(conn, context,uids, investment_type, plan_selection_time)
    plan_ids_allocation_df["plan_creation_time"] = [plan_ids_allocation_df["plan_selection_time"] + pd.to_timedelta(np.random.randint(3,6),unit="m")]
    plan_attributes_df = get_plan_attributes(conn, plan_ids_allocation_df["user_id"], plan_ids_allocation_df["plan_id"],plan_ids_allocation_df["plan_creation_time"])

    plan_ids_allocation_df = plan_ids_allocation_df.merge(plan_attributes_df, how="inner", on=["user_id","plan_id"])
    investment_amount_df = create_investment_amount(conn,uids)
    plan_ids_allocation_df = plan_ids_allocation_df.merge(investment_amount_df,how="inner",on="user_id")

    plan_ids_allocation_df['expected_maturity_value'] = plan_ids_allocation_df['amount_invested'] * (1 + (plan_ids_allocation_df['interest_rate'] / 100) * plan_ids_allocation_df['tenure_days']/365)


    user_ids[start_position:end_position] = plan_ids_allocation_df["user_id"]
    wallet_ids[start_position:end_position] = plan_ids_allocation_df["user_id"]
    event_times[start_position:end_position] = plan_ids_allocation_df["plan_creation_time"]
    device_types[start_position:end_position] = dtypes
    is_money_movement_activities[start_position:end_position] = True
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + 1 + len(plan_ids_allocation_df))
    transaction_type_ids[start_position:end_position] = plan_ids_allocation_df["transaction_type_id"]
    event_type_ids[start_position:end_position] = plan_ids_allocation_df["event_type_id"]
    plan_ids[start_position:end_position] = plan_ids_allocation_df["plan_id"]
    transaction_amounts[start_position:end_position] = plan_ids_allocation_df['amount_invested']
    amount_invested[start_position:end_position] = plan_ids_allocation_df['amount_invested']
    transaction_statuses[start_position:end_position] = ["success"] * len(plan_ids_allocation_df)

    deduct_wallet_balance(conn, plan_ids_allocation_df["user_id"], plan_ids_allocation_df['amount_invested'], transaction_ids[start_position:end_position], plan_ids_allocation_df["plan_creation_time"])

    # build dataframe

    all_investments_df = pd.DataFrame({
        'user_id': plan_ids_allocation_df["user_id"],
        'wallet_id':plan_ids_allocation_df["wallet_id"],
        'plan_id':plan_ids_allocation_df["plan_id"],
        'amount_invested':plan_ids_allocation_df["amount_invested"],
        'tenure_days':plan_ids_allocation_df["tenure_days"],
        'expected_maturity_value':plan_ids_allocation_df['expected_maturity_value'],
        'investment_start_date':plan_ids_allocation_df['investment_start_date'],
        'investment_start_date_id':(plan_ids_allocation_df['investment_start_date'].dt.strftime("%Y%m%d").astype(int)),
        'investment_maturity_date':plan_ids_allocation_df['investment_maturity_date'],
        'investment_maturity_date_id':(plan_ids_allocation_df['investment_maturity_date'].dt.strftime("%Y%m%d").astype(int))
    })

    last_transaction_id = transaction_ids[start_position:end_position].max()

    all_investments_df['investment_status'] = ["Active"] * len(all_investments_df)
    all_investments_df['is_withdrawn_early'] = [False] * len(all_investments_df)
    all_investments_df['penalty_amount'] = 0.0
    all_investments_df['amount_paid_out'] = 0.0
    all_investments_df['early_withdrawal_date'] = pd.NaT
    all_investments_df['early_withdrawal_date_id'] = pd.NA
    all_investments_df['created_at'] = all_investments_df['investment_start_date']
    all_investments_df['last_updated_at'] = all_investments_df['investment_start_date']
    
    return {
        'all_investments_df':all_investments_df, 'last_transaction_id':last_transaction_id
    }
    

def get_customer_behaviour_segment(conn: DuckDBPyConnection, uids: list[int]) -> pd.DataFrame:

    """
    Returns a dataframe with the following attributes:
        - user_id
        - customer_behaviour_segment
    """

    user_ids_df = pd.DataFrame({
        'user_id':uids
    })

    conn.register('user_ids_df', user_ids_df)

    try:
        cbs_df = conn.execute(''' SELECT f.user_id, customer_behaviour_segment from dim_user u inner join user_ids_df f on u.user_id = f.user_id ''').df()

    finally:
        conn.unregister('user_ids_df')

    return cbs_df

def get_plan_attributes(conn:DuckDBPyConnection, uids:list[int], plan_ids:list[int], plan_creation_time:list[pd.Timestamp]) -> pd.DataFrame:

    """
        Returns a dataframe with the following attributes:

        - user_id
        - wallet_id
        - customer_behaviour_segment
        - plan_id
        - tenure_days
        - interest_rate
        - investment_start_date
        - investment_maturity_date
    """

    plan_ids_df = pd.DataFrame({
        'user_id':uids,
        'plan_id':plan_ids,
        'investment_start_date':plan_creation_time
    })

    conn.register('plan_ids_df',plan_ids_df)

    try:
        plan_attributes_df = conn.execute(''' SELECT f.user_id, w.wallet_id, d.customer_behaviour_segment, f.plan_id, p.tenure_days, 
                                              case when p.tenure_days is null then null else p.interest_rate_min end as interest_rate, f.investment_start_date, 
                                              case when p.tenure_days is null then null else f.investment_start_date + (p.tenure_days * INTERVAL '1 DAY')
                                              end as investment_maturity_date
                from dim_plan as p inner join plan_ids_df f on p.plan_id = f.plan_id
                inner join dim_user as d on d.user_id = f.user_id
                inner join dim_wallet as w on d.user_id = w.user_id
                   ''').df()
    finally:
        conn.unregister('plan_ids_df')

    return plan_attributes_df

def generate_wallet_funding_amounts(conn: DuckDBPyConnection, uids:list[int]) -> list[float]:

    """
        Returns a list of transaction amounts generated based on the user's behaviour segment
        
    """

    cbs_df = get_customer_behaviour_segment(conn, uids)

    cbs_map = dict(zip(cbs_df["user_id"], cbs_df["customer_behaviour_segment"]))

    tran_amount = [int(np.random.triangular(
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cbs_map[uid]]["average_wallet_funding_amount"][0],
        np.mean(CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cbs_map[uid]]["average_wallet_funding_amount"]),
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cbs_map[uid]]["average_wallet_funding_amount"][1],
    )) for uid in uids]

    return tran_amount

def build_investment_creation_users_dataframe(conn:DuckDBPyConnection, wallet_activated_users_dataframe:pd.DataFrame) -> pd.DataFrame:



    cbf = get_customer_behaviour_segment(conn, wallet_activated_users_dataframe["user_id"])

    wallet_activated_users_dataframe["customer_behaviour_segment"] = cbf["customer_behaviour_segment"]

    wallet_activated_users_dataframe["last_login_at"] = get_last_login(conn,wallet_activated_users_dataframe["user_id"] )

    probability_of_making_first_investment = [
        np.random.choice(USERS_MAKES_FIRST_INVESTMENT_AFTER_FUNDING,p=CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cp]['wallet_to_investment_conversion_probability'])
        for cp in wallet_activated_users_dataframe["customer_behaviour_segment"]
    ]
    
    mins_to_first_investment = [
        np.random.randint(
            CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cp]['mins_to_first_investment'][0], #after wallet funding
            CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cp]['mins_to_first_investment'][1] + 1
        )
        for cp in wallet_activated_users_dataframe["customer_behaviour_segment"]
    ]
    
    first_investment_type = [np.random.choice(
            FIRST_INVESTMENT_TYPE,
            p= CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cp][
                'first_investment_type_probability'
            ]
        )
        for cp in wallet_activated_users_dataframe["customer_behaviour_segment"]]
    
    wallet_activated_users_dataframe['makes_first_investment'] = probability_of_making_first_investment
    
    wallet_activated_users_dataframe['mins_to_first_investment'] = mins_to_first_investment
    
    wallet_activated_users_dataframe['first_investment_type'] = first_investment_type

    return wallet_activated_users_dataframe
    
def create_investment_amount(conn:DuckDBPyConnection, uids:list[int]) -> pd.DataFrame:

    """
        Returns a dataframe with the following attributes:
            - user_id
            - amount_invested
    """

    cbs_df = get_customer_behaviour_segment(conn,uids)

    cbs_df['investment_percentage'] = cbs_df['customer_behaviour_segment'].apply(
    lambda segment: np.random.uniform(
        *CUSTOMER_BEHAVIOUR_SEGMENT_MAP[segment]['investment_percentage']
    ))

    investments_df = get_current_wallet_balance(conn,uids)

    investments_df = investments_df.merge(cbs_df, how="inner", on="user_id")

    investments_df['amount_invested'] = (investments_df['current_balance'] * investments_df['investment_percentage']).round(2)

    investments_df = investments_df.drop(columns=['customer_behaviour_segment','investment_percentage','current_balance'])

    return investments_df

def create_engagement_events(engagement_sample_df:pd.DataFrame) -> dict:

    """
        Returns a data dictionary with the following events:
            - login_events - Returns (user_id and event_time)
            - engagement_events - Returns (user_id and event_time)
            - wallet_funding_events - Returns (user_id and event_time)
            - investment_events - Returns (user_id, event_time and investment_type)
    """

    #logins, review_plan_options, wallet fundings and investment creation

    
    login_events = []
    engagement_events = []
    wallet_funding_events = []
    investment_events = []

    for _, customer in engagement_sample_df.iterrows():

        simulation_start = customer["last_login_at"]
        simulation_end = TODAY

        delta = relativedelta(simulation_end, simulation_start)

        months = max(1,delta.years * 12 + delta.months)

        monthly_logins = np.random.randint(*CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_logins"],size=months)

        cbs = customer["customer_behaviour_segment"]


        for idx in range(months):

            current_month_start = (simulation_start + relativedelta(months=idx))
            
            current_month_end = min(current_month_start + relativedelta(months=1),simulation_end)
            
            days_in_month = (current_month_end - current_month_start).days

            if days_in_month <= 0:
                continue

            days_range = [0,days_in_month]
            hours_range = [0,24]
            minutes_range = [0,60]
            seconds_range = [0,60]
            

            number_of_logins_this_month = monthly_logins[idx]

            number_of_reviews_this_month = np.random.randint(
            max(1, int(number_of_logins_this_month * 0.15)),
            max(2, int(number_of_logins_this_month * 0.4)) + 1)

            number_of_wallet_fundings_this_month = np.random.randint(*CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cbs]['monthly_wallet_fundings'])

            number_of_investments_creations_this_month = np.random.randint(*CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cbs]['monthly_investment_position_creation'])

            login_times_this_month = [current_month_start + timedelta(days=np.random.randint(*days_range), hours=np.random.randint(*hours_range), 
                                                                      minutes=np.random.randint(*minutes_range), seconds=np.random.randint(*seconds_range)) for _ in range(number_of_logins_this_month)]

            review_times_this_month = [current_month_start + timedelta(days=np.random.randint(*days_range), hours=np.random.randint(*hours_range), minutes=np.random.randint(*minutes_range),
                                                                       seconds=np.random.randint(*seconds_range)) for _ in range(number_of_reviews_this_month)]



            for login_time in login_times_this_month:

                login_events.append({
                    'user_id':customer["user_id"],
                    'event_time':login_time
                })


            for review_time in review_times_this_month:

                engagement_events.append({
                    'user_id': customer["user_id"],
                    'event_time':review_time
                })

            if number_of_wallet_fundings_this_month <= 0:
                continue
            else:
                for _ in range(number_of_wallet_fundings_this_month):
                    wallet_funding_time = current_month_start + timedelta(days = np.random.randint(*days_range), hours=np.random.randint(*hours_range),
                                                                           minutes=np.random.randint(*minutes_range),seconds=np.random.randint(*seconds_range))
                    wallet_funding_events.append({
                        'user_id':customer['user_id'],
                        'event_time':wallet_funding_time
                    })
            

            if number_of_investments_creations_this_month <= 0:
                continue
            for _ in range(number_of_investments_creations_this_month):
                    investment_creation_time = current_month_start + timedelta(days = np.random.randint(*days_range), hours=np.random.randint(*hours_range),
                                                                           minutes=np.random.randint(*minutes_range),seconds=np.random.randint(*seconds_range))
                    investment_type = np.random.choice(FIRST_INVESTMENT_TYPE, p = CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cbs]['investment_type_probability'])
                    investment_events.append({
                                    'user_id':customer['user_id'],
                                    'event_time':investment_creation_time,
                                    'investment_type':investment_type
                                })

    return {
        'login_events':login_events,
        'engagement_events':engagement_events,
        'wallet_funding_events':wallet_funding_events,
        'investment_events':investment_events
    }

def review_current_investment_events(conn:DuckDBPyConnection, context:any, start_position:int, end_position:int, user_ids:list[int], uids:list[int], event_times:list[pd.Timestamp],
                                     review_time:list[pd.Timestamp], device_types:list[int], dtypes:list[int], event_type_ids:list[int]) -> int:
                        
    """
        Returns the new event end_position
    """

    login_time = [review - timedelta(minutes = np.random.randint(0,2)) for review in review_time]

    app_login_events(conn, context, start_position, end_position,user_ids, uids, event_times, login_time, device_types, dtypes, event_type_ids)

    start_position = end_position
    end_position = start_position + len(uids)

    user_ids[start_position:end_position] = uids
    event_times[start_position:end_position] = review_time
    device_types[start_position:end_position] = dtypes
    event_type_ids[start_position:end_position] = [context.review_current_investment_event_type_id] * len(uids)

    updated_end_position = end_position

    return updated_end_position
            
def create_wallet_funding_events(conn:DuckDBPyConnection, context:any, start_position:int, end_position:int, user_ids:list[int], uids:list[int], wallet_ids:list[int], event_times:list[pd.Timestamp],
                                 funding_time:list[pd.Timestamp], last_transaction_id:int, device_types, dtypes, is_money_movement_activity:list[bool], event_type_ids:list[int], 
                                 transaction_type_ids:list[int], transaction_ids:list[int], transaction_amounts:list[float]) -> dict:


    login_time = [ft - timedelta(minutes = np.random.randint(4,10)) for ft in funding_time]

    app_login_events(conn, context, start_position, end_position, user_ids, uids, event_times, login_time, device_types, dtypes, event_type_ids )

    start_position = end_position
    end_position = start_position + len(uids)

    user_ids[start_position:end_position] = uids
    wallet_ids[start_position:end_position] = uids
    event_times[start_position:end_position] = funding_time
    is_money_movement_activity[start_position:end_position] = [True] * len(uids)
    device_types[start_position:end_position] = dtypes
    event_type_ids[start_position:end_position] = [context.wallet_funded_event_type_id] * len(uids)

    tran_amounts = generate_wallet_funding_amounts(conn, uids)

    transaction_type_ids[start_position:end_position] = [context.wallet_funding_transaction_type_id] * len(uids)
    transaction_amounts[start_position:end_position] = tran_amounts
    is_money_movement_activity[start_position:end_position] = [True] * len(uids)
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + len(uids) + 1)
    last_transaction_id = transaction_ids.max()

    update_wallet_balance(conn, uids, tran_amounts, transaction_ids[start_position:end_position], funding_time)

    return {
        "last_transaction_id": last_transaction_id,
        "updated_end_position": end_position}

def new_investment_creation(conn:DuckDBPyConnection, context:any, start_position:int, end_position:int, user_ids:list[int], uids:list[int], wallet_ids:list[int], event_times:list[pd.Timestamp],
                               plan_creation_time:list[pd.Timestamp], investment_type:list[str], device_types:list[str], dtypes:list[str], 
                               is_money_movement_activities:list[bool], transaction_ids:list[int], last_transaction_id:int, 
                               transaction_type_ids:list[int], event_type_ids:list[int], plan_ids:list[int], transaction_amounts:list[float], amount_invested:list[float]) -> dict:

    """
        This function creates new investment creation events for the given users.
        It returns a dictionary with the following attributes:
            - all_investment_df: A dataframe with the following attributes:
                - user_id
                - wallet_id
                - plan_id
                - amount_invested,
                - tenure_days
                - expected_maturity_value
                - investment_start_date
                - investment_start_date_id
                - investment_maturity_date
                - investment_maturity_date_id
                - investment_status
                - is_withdrawn_early
                - penalty_amount
                - amount_paid_out
                - early_withdrawal_date
                - early_withdrawal_date_id
                - created_at
                - last_updated_at
            - last_transaction_id: The last transaction id after creating the new investment creation events.
    """

    login_time = [pst - timedelta(minutes = np.random.randint(20,35)) for pst in plan_creation_time]

    app_login_events(conn, context, start_position, end_position, user_ids, uids, event_times, login_time, device_types, dtypes, event_type_ids)

    start_position = end_position
    end_position = start_position + len(uids)

    review_time = [lt + timedelta(minutes = np.random.randint(2,5)) for lt in login_time]

    review_plan_options_events(conn, context, start_position, end_position, user_ids, uids, event_times, review_time, event_type_ids, device_types, dtypes)

    start_position = end_position
    end_position = start_position + len(uids)

    plan_selection_df = plan_selection_events(context, start_position, end_position, user_ids, uids, event_times, review_time, event_type_ids, device_types, dtypes)

    plan_selection_time = plan_selection_df["plan_selection_time"].tolist()

    start_position = end_position
    end_position = start_position + len(uids)

    investment_creation_dict = investment_creation_events(conn, context, start_position, end_position, user_ids, uids, wallet_ids, event_times,
                                                          plan_selection_time, investment_type, device_types, dtypes,
                                                          is_money_movement_activities, transaction_ids, last_transaction_id,
                                                          transaction_type_ids, event_type_ids, plan_ids,
                                                          transaction_amounts, amount_invested)


    last_transaction_id = investment_creation_dict['last_transaction_id']
    all_investments_df = investment_creation_dict['all_investment_df']
    updated_end_position = end_position

    return {
        'last_transaction_id':last_transaction_id,
        'all_investments_df':all_investments_df,
        'updated_end_position':updated_end_position

    }

def early_withdrawal_requests_events(conn:DuckDBPyConnection,context:any, start_position:int, end_position:int, user_ids:list[int], wallet_ids:list[int], 
                                     is_money_movement_activity:list[bool], last_transaction_id:int, event_times:list[pd.Timestamp], device_types:list[str], dtypes:list[str], 
                                     early_withdrawal_requests_df:pd.DataFrame, event_type_ids:list[int], transaction_types_ids:list[int],transaction_ids:list[int], 
                                     transaction_amounts:list[float], transaction_statuses:list[str]) -> dict:



    requests_withdrawal_days_before_maturity = [
    int(
        np.random.triangular(
            EARLY_WITHDRAWAL_BEHAVIOUR[plan_name]["left"],
            EARLY_WITHDRAWAL_BEHAVIOUR[plan_name]["mode"],
            EARLY_WITHDRAWAL_BEHAVIOUR[plan_name]["right"]
        )
    )
    for plan_name in early_withdrawal_requests_df[
        "plan_name"
    ]]

    early_withdrawal_requests_df['withdrawal_request_date'] = ([early_withdrawal_requests_df['investment_maturity_date'] - timedelta(days=ro) for ro in requests_withdrawal_days_before_maturity ])


    #review_current_plans

    early_withdrawal_requests_df['review_current_investment_time'] = (early_withdrawal_requests_df['withdrawal_request_date'] - timedelta(minutes = 8))
    early_withdrawal_requests_df['days_held'] = (early_withdrawal_requests_df['withdrawal_request_date'] - early_withdrawal_requests_df['investment_start_date']).dt.days

    early_withdrawal_requests_df['expected_total_interest'] = early_withdrawal_requests_df['expected_maturity_value'] - early_withdrawal_requests_df['amount_invested']
    early_withdrawal_requests_df['interest_accrued'] = early_withdrawal_requests_df['expected_total_interest'] * (early_withdrawal_requests_df['days_held'] / early_withdrawal_requests_df['tenure_days'])

    updated_end_position = review_current_investment_events(conn, context, start_position, end_position, user_ids, early_withdrawal_requests_df['user_id'], event_times, early_withdrawal_requests_df['review_current_investment_time'],
                                     device_types, dtypes, event_type_ids)


    #request withdrawal
    start_position = updated_end_position
    end_position = start_position + len(early_withdrawal_requests_df)

    user_ids[start_position:end_position] = early_withdrawal_requests_df['user_id']
    event_times[start_position:end_position] = early_withdrawal_requests_df['withdrawal_request_date']
    event_type_ids[start_position:end_position] = [context.request_early_withdrawal_event_type_id] * len(early_withdrawal_requests_df)
    device_types[start_position:end_position] = dtypes

    #investment_proceeds_wallet_transfer
    start_position = end_position
    end_position = start_position + len(early_withdrawal_requests_df)

    user_ids[start_position:end_position] = early_withdrawal_requests_df['user_id']
    event_times[start_position:end_position] = early_withdrawal_requests_df['withdrawal_request_date'] + timedelta(minutes = INVESTMENT_WITHDRAWAL_PROCESSING_TIME)
    is_money_movement_activity[start_position:end_position] = [True] * len(early_withdrawal_requests_df)
    event_type_ids[start_position:end_position] = [context.investment_proceeds_wallet_transfer_event_type_id] * len(early_withdrawal_requests_df)
    transaction_types_ids[start_position:end_position] = [context.investment_proceeds_transfer_transaction_type_id] * len(early_withdrawal_requests_df)
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + 1 + len(early_withdrawal_requests_df))    
    device_types[start_position:end_position] = dtypes
    last_transaction_id = transaction_ids[start_position:end_position].max()
    wallet_ids[start_position:end_position] = early_withdrawal_requests_df['user_id']
    early_withdrawal_requests_df['penalty_amount'] = (early_withdrawal_requests_df['interest_accrued']  * (early_withdrawal_requests_df['penalty_rate_pct'] / 100))
    transaction_amounts[start_position:end_position] = ((early_withdrawal_requests_df['amount_invested'] + early_withdrawal_requests_df['interest_accrued'])  - early_withdrawal_requests_df['penalty_amount'])
    early_withdrawal_requests_df['investment_status'] = "Redeemed"
    transaction_statuses[start_position:end_position] = ["Success"] * len(early_withdrawal_requests_df)

    early_withdrawal_requests_df['is_withdrawn_early'] = True
    early_withdrawal_requests_df['amount_paid_out'] = ((early_withdrawal_requests_df['amount_invested'] + early_withdrawal_requests_df['interest_accrued'])  - early_withdrawal_requests_df['penalty_amount'])
    early_withdrawal_requests_df['early_withdrawal_date'] = early_withdrawal_requests_df['withdrawal_request_date']
    early_withdrawal_requests_df['early_withdrawal_date_id'] = (early_withdrawal_requests_df['withdrawal_request_date'].dt.strftime("%Y%m%d").astype(int))
    early_withdrawal_requests_df['last_updated_at'] = event_times[start_position:end_position]
    early_withdrawal_requests_df['created_at'] = early_withdrawal_requests_df['investment_start_date']
    early_withdrawal_requests_df['wallet_id'] = early_withdrawal_requests_df['user_id']

    early_withdrawal_df = pd.DataFrame({
        'user_id':early_withdrawal_requests_df['user_id'],
        'wallet_id':early_withdrawal_requests_df['wallet_id'],
        'plan_id':early_withdrawal_requests_df['plan_id'],
        'amount_invested':early_withdrawal_requests_df['amount_invested'],
        'expected_maturity_value':early_withdrawal_requests_df['expected_maturity_value'],
        'investment_start_date':early_withdrawal_requests_df['investment_start_date'],
        'investment_start_date_id':early_withdrawal_requests_df['investment_start_date_id'],
        'investment_maturity_date':early_withdrawal_requests_df['investment_maturity_date'],
        'investment_maturity_date_id':early_withdrawal_requests_df['investment_maturity_date_id'],
        'investment_status':early_withdrawal_requests_df['investment_status'],
        'is_withdrawn_early':early_withdrawal_requests_df['is_withdrawn_early'],
        'penalty_amount':early_withdrawal_requests_df['penalty_amount'],
        'amount_paid_out':early_withdrawal_requests_df['amount_paid_out'],
        'early_withdrawal_date':early_withdrawal_requests_df['early_withdrawal_date'],
        'early_withdrawal_date_id':early_withdrawal_requests_df['early_withdrawal_date_id'],
        'created_at':early_withdrawal_requests_df['created_at'],
        'last_updated_at':early_withdrawal_requests_df['last_updated_at'],
    })

    updated_end_position= end_position

    update_wallet_balance(conn, early_withdrawal_requests_df['user_id'], early_withdrawal_requests_df['amount_paid_out'],
                          transaction_ids[start_position:end_position],event_times[start_position:end_position]  )

    return {
        'last_transaction_id':last_transaction_id,
        'updated_end_position':updated_end_position,
        'early_withdrawal_df':early_withdrawal_df
    }

def vested_investments_events(context:any, start_position:int, end_position:int, user_ids:list[int], event_time:list[pd.Timestamp], event_type_ids:list[int], device_types:list[str], dtypes:list[str],
                              vestable_investment_df:pd.DataFrame) -> None:


    user_ids[start_position:end_position] = vestable_investment_df['user_id']
    event_type_ids[start_position:end_position] = [context.investment_vests_event_type_id] * len(vestable_investment_df)
    device_types[start_position:end_position] = dtypes
    event_time[start_position:end_position] = vestable_investment_df['investment_maturity_date']


def vested_investments_proceeds_transfer_events(conn:DuckDBPyConnection, context:any, start_position:int, end_position:int, user_ids:list[int], event_time:list[pd.Timestamp], 
                                                wallet_ids:list[int], last_transaction_id:int,is_money_movement_activity:list[bool],transaction_type_ids:list[int], transaction_ids:list[int], 
                                                transaction_amounts:list[float], transaction_statuses:list[str],
                                                event_type_ids:list[int], device_types:list[str], dtypes:list[str], 
                                                vested_investment_df:pd.DataFrame) -> dict:

    user_ids[start_position:end_position] = vested_investment_df['user_id']
    wallet_ids[start_position:end_position] = vested_investment_df['user_id']
    is_money_movement_activity[start_position:end_position] = [True] * len(vested_investment_df)
    event_type_ids[start_position:end_position] = [context.investment_proceeds_wallet_transfer_event_type_id] * len(vested_investment_df)
    device_types[start_position:end_position] = dtypes
    transaction_type_ids[start_position:end_position] = [context.investment_proceeds_transfer_transaction_type_id] * len(vested_investment_df)
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + 1 + len(vested_investment_df))
    transaction_amounts[start_position:end_position] = vested_investment_df['expected_maturity_value']
    transaction_statuses[start_position:end_position] = ["Success"] * len(vested_investment_df)
    event_time[start_position:end_position] = vested_investment_df['investment_maturity_date'] + timedelta(minutes = INVESTMENT_WITHDRAWAL_PROCESSING_TIME)
    vested_investment_df['investment_status'] = "Redeemed"
    vested_investment_df['amount_paid_out'] = vested_investment_df['expected_maturity_value']
    vested_investment_df['is_withdrawn_early'] = False
    vested_investment_df['early_withdrawal_date'] = None
    vested_investment_df['early_withdrawal_date_id'] = None
    vested_investment_df['last_updated_at'] = event_time[start_position:end_position]
    vested_investment_df['created_at'] = vested_investment_df['investment_start_date']
    vested_investment_df['wallet_id'] = vested_investment_df['user_id']

    last_transaction_id = transaction_ids[start_position:end_position].max()

    update_wallet_balance(conn,vested_investment_df['user_id'], vested_investment_df['amount_paid_out'],
                          transaction_ids[start_position:end_position],event_time[start_position:end_position]  )

    return {
        'last_transaction_id':last_transaction_id,
        'vested_investment_df':vested_investment_df
    }
        
def assets_sale_events(context:any, start_position:int, end_position:int, user_ids:list[int], event_time:list[pd.Timestamp], event_type_ids:list[int], device_types:list[str], dtypes:list[str],
                        saleable_investments_df:pd.DataFrame) -> None:

    user_ids[start_position:end_position] = saleable_investments_df['user_id']
    event_time[start_position:end_position] = saleable_investments_df['redemption_request_date']
    event_type_ids[start_position:end_position] = [context.assets_sale_event_type_id] * len(saleable_investments_df)
    device_types[start_position:end_position] = dtypes

def assets_sale_investment_proceeds_wallet_transfer_events(conn:DuckDBPyConnection, context:any, start_position:int, end_position:int, user_ids:list[int], wallet_ids:list[int],
                                                    event_time:list[pd.Timestamp], device_types:list[str], dtypes, transaction_type_ids:list[int], transaction_ids:list[int],
                                                    last_transaction_id:int, event_type_ids, is_money_movement_activity:list[bool], transaction_amounts:list[float], transaction_statuses:list[str],
                                                    saleable_investment_df:pd.DataFrame) -> dict:

    saleable_investment_df = saleable_investment_df.copy()

    user_ids[start_position:end_position] = saleable_investment_df['user_id']
    event_time[start_position:end_position] = (saleable_investment_df['redemption_request_date'] + timedelta(minutes=INVESTMENT_WITHDRAWAL_PROCESSING_TIME))
    is_money_movement_activity[start_position:end_position] = [True] * len(saleable_investment_df)
    device_types[start_position:end_position] = dtypes
    event_type_ids[start_position:end_position] = [context.investment_proceeds_wallet_transfer_event_type_id] * len(saleable_investment_df)
    transaction_type_ids[start_position:end_position] = [context.investment_proceeds_transfer_transaction_type_id] * len(saleable_investment_df)
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + 1 + len(saleable_investment_df))
    last_transaction_id = transaction_ids[start_position:end_position].max()
    wallet_ids[start_position:end_position] = saleable_investment_df['user_id']

    #get interest rate
    saleable_investment_df['interest_rate'] = np.random.randint(8,19,size=len(saleable_investment_df))
    saleable_investment_df['amount_paid_out'] = saleable_investment_df['amount_invested'] * (1 + (saleable_investment_df['interest_rate']/100))
    transaction_amounts[start_position:end_position] = saleable_investment_df['amount_paid_out']
    transaction_statuses[start_position:end_position] = ["success"] * len(saleable_investment_df)
    saleable_investment_df['investment_status'] = ["Redeemed"] * len(saleable_investment_df)
    saleable_investment_df['is_withdrawn_early'] = False
    saleable_investment_df['penalty_amount'] = 0.0
    saleable_investment_df['early_withdrawal_date'] = None
    saleable_investment_df['early_withdrawal_date_id'] = None
    saleable_investment_df['created_at'] = saleable_investment_df['investment_start_date']
    saleable_investment_df['last_updated_at'] = event_time[start_position:end_position]

    update_wallet_balance(conn, saleable_investment_df['user_id'], transaction_amounts[start_position:end_position], transaction_ids[start_position:end_position], event_time[start_position:end_position])

    return {
        'last_transaction_id': last_transaction_id,
        'saleable_investments_df':saleable_investment_df
    }




    








        





    

