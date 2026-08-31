import numpy as np
import pandas as pd
from src.config.paths import (DDL_FACT_USER_EVENT_PATH, FACT_USER_EVENT_PARQUET_PATH, 
                              FACT_INVESTMENT_POSITION_PARQUET_PATH, DDL_FACT_INVESTMENT_POSITION_PATH, DDL_FACT_TRANSACTION_PATH, FACT_TRANSACTION_PARQUET_PATH)
from src.config.constants import (DEFAULT_TRANSACTION_START_DATE, DEFAULT_TRANSACTION_END_DATE, IMMEDIATE_LOGINS_TIME_FRAME, KYC_ACTIVATION_TIMEFRAME, USERS_MAKES_FIRST_INVESTMENT_AFTER_FUNDING,
                                  CUSTOMER_BEHAVIOUR_SEGMENT_MAP, FIRST_INVESTMENT_TYPE, EARLY_WITHDRAWAL_BEHAVIOUR, INVESTMENT_WITHDRAWAL_PROCESSING_TIME,
                                  MUTUAL_FUNDS_CUTOFF_DATE, TODAY, AMOUNT_INCREMENT
                                  )
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from src.logic.helper_functions import (update_last_login_timestamp, signup_completion_events, app_login_events, get_last_login, kyc_completion_events,
                                        wallet_activation_events, get_current_wallet_balance, review_plan_options_events, plan_selection_events, plan_ids_allocation, build_investment_creation_users_dataframe,
                                        investment_creation_events, get_customer_behaviour_segment, create_engagement_events, review_current_investment_events, create_wallet_funding_events,
                                        new_investment_creation)
from src.logic.EventContext import (load_event_context)


def generate_facts(conn, num_of_events):

    context = load_event_context(conn)

    create_fact_user_table = DDL_FACT_USER_EVENT_PATH.read_text()
    create_fact_investment_table = DDL_FACT_INVESTMENT_POSITION_PATH.read_text()
    create_fact_transaction_table = DDL_FACT_TRANSACTION_PATH.read_text()

    conn.execute(create_fact_user_table)
    conn.execute(create_fact_investment_table)
    conn.execute(create_fact_transaction_table)

    #populate all possible signups within the project duration
    users_data = conn.execute(f'''SELECT user_id, signup_date, kyc_completed, is_activated_user, wallet_activation_timeframe, customer_behaviour_segment, device_type FROM dim_user
     where signup_date >= '{DEFAULT_TRANSACTION_START_DATE}' order by signup_date''').df()
    
    user_wallet_data = conn.execute(f'''SELECT user_id, wallet_id, wallet_activated_at from dim_wallet''').df()

    plans_data = conn.execute('''SELECT * FROM dim_plan''').df()

    device_type_map = dict(zip(users_data["user_id"],users_data["device_type"]))

    event_type_lookup = conn.execute('''SELECT event_type_code, event_type_id FROM dim_event_type''').df()
    
    transaction_type_lookup = conn.execute('''SELECT transaction_type_code, transaction_type_id FROM dim_transaction_type''').df()
    
    event_type_map = dict(zip(event_type_lookup["event_type_code"],event_type_lookup["event_type_id"]))
    
    transaction_type_map = dict(zip(transaction_type_lookup["transaction_type_code"],transaction_type_lookup["transaction_type_id"]))
    
    wallet_id_map = dict(zip(user_wallet_data["user_id"],user_wallet_data["wallet_id"]))

    plan_id_map = dict(zip(plans_data["plan_id"],plans_data["tenure_days"]))

    event_time = np.empty(num_of_events, dtype=object)

    user_ids = np.empty(num_of_events, dtype=object)

    event_type_ids = np.empty(num_of_events, dtype=object)

    wallet_ids = np.empty(num_of_events, dtype=object)

    plan_ids = np.empty(num_of_events, dtype=object)

    device_types = np.empty(num_of_events, dtype=object)

    amount_invested = np.empty(num_of_events,dtype = object)

    is_money_movement_activities = np.empty(num_of_events, dtype=bool)

    transaction_type_ids = np.empty(num_of_events, dtype=object)

    transaction_ids = np.empty(num_of_events, dtype=object)

    investment_ids = np.empty(num_of_events, dtype=object)

    last_transaction_id = 0

    #event_ids = np.empty(num_of_events, dtype=np.int64)

    transaction_amounts = np.zeros(num_of_events, dtype=np.float64)
    transaction_statuses = np.empty(num_of_events, dtype = object)
    is_withdrawn_early = np.full(num_of_events,False,dtype=bool)
    early_withdrawal_dates = np.empty(num_of_events,dtype=object)
    early_withdrawal_date_id = np.empty(num_of_events, dtype=object)


    # new user signups
    total_signups = len(users_data)

    start_position = 0
    end_position = total_signups

    dtypes = np.array([device_type_map.get(uid) for uid in users_data["user_id"]])

    signup_completion_events(context, start_position, end_position, user_ids, users_data["user_id"], event_time, users_data["signup_date"],device_types, dtypes,event_type_ids)

    #new user logins
    new_users_logins = conn.execute(f'''SELECT user_id, signup_date, kyc_completed, is_activated_user, customer_behaviour_segment FROM dim_user
    where signup_date between '{DEFAULT_TRANSACTION_START_DATE}' and '{DEFAULT_TRANSACTION_END_DATE}' AND is_immediate_login = True order by signup_date''').df()
    
    immediate_login_timeframe = np.random.randint(IMMEDIATE_LOGINS_TIME_FRAME[0],IMMEDIATE_LOGINS_TIME_FRAME[1], size=len(new_users_logins))
    
    total_new_users = len(new_users_logins)

    start_position = total_signups
    end_position = start_position + total_new_users

    etime = [pd.Timestamp(sd) + timedelta(seconds=int(ro)) for sd, ro in zip(new_users_logins["signup_date"], immediate_login_timeframe)]
    uids = new_users_logins["user_id"]
    dtypes=[device_type_map.get(uid) for uid in uids]

    app_login_events(conn,context,start_position, end_position,
                     user_ids,uids,event_time,etime,device_types,dtypes, event_type_ids)
    
    #kyc_completed_users
    kyc_completed_users = users_data[users_data["kyc_completed"] == True].copy()

    signup_map = dict(zip(users_data["user_id"],users_data["signup_date"]))

    last_login_df = get_last_login(conn,kyc_completed_users["user_id"])
    uids = last_login_df["user_id"]
    last_login_time = last_login_df["last_login_at"]

    last_login_map  = dict(zip(
        uids,
        last_login_time
    ))

    kyc_activation_timeframe = np.empty(len(kyc_completed_users), dtype=object)
    
    unactivated_users_with_kyc = np.where(pd.isna(kyc_completed_users["wallet_activation_timeframe"]))[0]

    activated_users_with_kyc = np.where(~pd.isna(kyc_completed_users["wallet_activation_timeframe"]))[0]

    wallet_activation_timeframe = kyc_completed_users["wallet_activation_timeframe"].values

    kyc_activation_timeframe[unactivated_users_with_kyc] = np.random.randint(KYC_ACTIVATION_TIMEFRAME[0], KYC_ACTIVATION_TIMEFRAME[1], size=len(unactivated_users_with_kyc))
    kyc_activation_timeframe[activated_users_with_kyc] = wallet_activation_timeframe[activated_users_with_kyc] - 1000 #assuming wallet activation happens after KYC completion, we can set the KYC activation timeframe to be slightly less than the wallet activation timeframe for those users

    kyc_logins_timeframe = kyc_activation_timeframe - 300 #assuming KYC completion happens after the last login, we can set the KYC activation timeframe to be slightly more than the last login timeframe

    # start activation by logging in
    start_position = end_position
    end_position = start_position + len(kyc_completed_users)

    dtypes = [device_type_map.get(uid) for uid in kyc_completed_users["user_id"]]
    etime = [last_login_map.get(uid,signup_map.get(uid)) + timedelta(minutes=int(ro)) for uid, ro in zip(kyc_completed_users["user_id"], kyc_logins_timeframe)]

    app_login_events(conn, context, start_position, end_position, user_ids,kyc_completed_users["user_id"],event_time,etime,device_types,dtypes,event_type_ids)


    #activate kyc
    start_position = end_position
    end_position = start_position + len(kyc_completed_users)
    
    etime = [signup_map.get(uid) + timedelta(minutes=int(ro)) for uid, ro in zip(kyc_completed_users["user_id"], kyc_activation_timeframe)]
    dtypes = np.array([device_type_map.get(uid) for uid in kyc_completed_users["user_id"]])

    kyc_completion_events(conn, context, start_position, end_position, user_ids, kyc_completed_users["user_id"], 
                          event_time, etime, device_types, dtypes, event_type_ids)


    #wallet activation
    wallet_activated_users = kyc_completed_users[~pd.isna(kyc_completed_users["wallet_activation_timeframe"])].copy()

    total_wallet_activated_users = len(wallet_activated_users)

    start_position = end_position
    end_position = start_position + total_wallet_activated_users

    uids = wallet_activated_users["user_id"]
    etime = [signup_map.get(uid,None) + timedelta(minutes=int(ro)) for uid, ro in zip(wallet_activated_users["user_id"], wallet_activated_users["wallet_activation_timeframe"])]
    dtypes = np.array([device_type_map.get(uid) for uid in wallet_activated_users["user_id"]])
    wids = [wallet_id_map.get(uid) for uid in wallet_activated_users["user_id"]]
    
    return_dict = wallet_activation_events(
        conn, context, start_position, end_position,user_ids, uids, event_time, etime,
    device_types, dtypes, event_type_ids, wallet_ids, wids, is_money_movement_activities, transaction_type_ids, transaction_ids, transaction_amounts,
    wallet_activated_users["amount_invested"],transaction_statuses, last_transaction_id
    )

    last_transaction_id = return_dict['last_transaction_id']
    end_position = return_dict['updated_end_position']
    

    #let's create the initial investment -- login, review_plan_options then drop off for some users, and for others, they will make an investment after reviewing the plan options. We will create a new dataframe to hold the users who made an investment and their corresponding investment details.

    #these users will just login and review plan options, but will not make an investment. We will create a new dataframe to hold the users who made an investment and their corresponding investment details.

    
    customer_subset_1 = wallet_activated_users.sample(frac = 0.55, random_state=1)
    customer_subset_1["last_login_at"] = get_last_login(conn, customer_subset_1["user_id"])

    total_customer_subset_1 = len(customer_subset_1)

    start_position = end_position
    end_position = start_position + total_customer_subset_1

    uids = customer_subset_1["user_id"]

    etime = [last_login + timedelta(minutes=np.random.randint(5, 80)) for last_login in customer_subset_1["last_login_at"]]
    dtypes = np.array([device_type_map.get(uid) for uid in customer_subset_1["user_id"]])
    app_login_events(conn, context, start_position, end_position, user_ids, uids, event_time,etime, device_types, dtypes, event_type_ids)


    start_position = end_position
    end_position = start_position + total_customer_subset_1

    uids = customer_subset_1["user_id"]
    dtypes = np.array([device_type_map.get(uid) for uid in customer_subset_1["user_id"]])

    review_plan_options_events(conn,context,start_position, end_position, user_ids, uids, event_time, event_type_ids, device_types, dtypes)

    # These are the users who will make an investment

    wallet_activated_users_df = build_investment_creation_users_dataframe(conn, wallet_activated_users)
    
    customer_subset_2 = wallet_activated_users_df[wallet_activated_users_df['makes_first_investment'] == True]

    customer_subset_2 = customer_subset_2.copy().reset_index(drop=True)

    total_customer_subset_2 = len(customer_subset_2)

    #The user creates first investment here

    #logs in first

    start_position = end_position
    end_position = start_position + total_customer_subset_2

    uids = customer_subset_2["user_id"]
    etime = [last_login + timedelta(minutes=np.random.randint(0, mtft)) for last_login,mtft in zip(customer_subset_2["last_login_at"],customer_subset_2["mins_to_first_investment"])]
    dtypes = np.array([device_type_map.get(uid) for uid in customer_subset_2["user_id"]])
    app_login_events(conn, context, start_position, end_position, user_ids, uids, event_time, etime, device_types, dtypes, event_type_ids)

    start_position = end_position
    end_position = start_position + total_customer_subset_2

    uids = customer_subset_2["user_id"]
    dtypes = np.array([device_type_map.get(uid) for uid in customer_subset_2["user_id"]])

    review_plan_options_events(conn,context, start_position, end_position, user_ids, uids, event_time, event_type_ids, device_types, dtypes)

    plan_review_time = event_time[start_position:end_position]

    start_position = end_position
    end_position = start_position + total_customer_subset_2

    uids = customer_subset_2["user_id"]
    dtypes = np.array([device_type_map.get(uid) for uid in customer_subset_2["user_id"]])
    

    plan_selected_df = plan_selection_events(context, start_position, end_position, 
                                                   user_ids, uids, event_time, plan_review_time, event_type_ids, device_types, dtypes)

    plan_selected_df = plan_selected_df.merge(customer_subset_2["first_investment_type"], how="inner", on="user_id")

    # investment creation events

    total_plan_selection_events = len(plan_selected_df)

    start_position = end_position
    end_position = start_position + total_plan_selection_events

    uids = plan_selected_df["user_id"]
    first_inv_type = plan_selected_df["first_investment_type"]
    plan_selection_time = plan_selected_df["plan_selection_time"]
    dtypes = [device_type_map.get(uid) for uid in uids]

    investment_creation_dict = investment_creation_events(conn, context, start_position, end_position, user_ids, uids, event_time, plan_selection_time, first_inv_type,
                                                          device_types, dtypes, is_money_movement_activities, transaction_ids, last_transaction_id, transaction_type_ids,
                                                          event_type_ids, plan_ids, transaction_amounts, amount_invested)

    last_transaction_id = investment_creation_dict["last_transaction_id"]
    all_investments_df = investment_creation_dict["all_investments_df"]

    
    customers_who_have_invested_df = get_last_login(conn, plan_selected_df["user_id"])
    cbs_df = get_customer_behaviour_segment(conn, customers_who_have_invested_df["user_id"])

    customers_who_have_invested_df = customers_who_have_invested_df.merge(cbs_df, how = "inner", on="user_id")


    active_users_subset = customers_who_have_invested_df[
    (customers_who_have_invested_df["customer_behaviour_segment"] == "High_Engagement_High_Balance")
    |
    (customers_who_have_invested_df["customer_behaviour_segment"] == "High_Engagement_Low_Balance")
    |
    (customers_who_have_invested_df["customer_behaviour_segment"] == "Moderate_Engagement_High_Balance")
    |
    (customers_who_have_invested_df["customer_behaviour_segment"] == "Moderate_Engagement_Low_Balance")
].copy()

    low_activity_users_subset = customers_who_have_invested_df[
        (customers_who_have_invested_df["customer_behaviour_segment"] == "Low_Engagement_High_Balance")
    |
    (customers_who_have_invested_df["customer_behaviour_segment"] == "Low_Engagement_Low_Balance")
    ]

    
    active_users_sample = active_users_subset.sample(frac=0.9, random_state = 1)

    low_activity_users_sample = low_activity_users_subset.sample(frac=0.65, random_state = 1)

    engagement_sample_df = pd.concat(
    [active_users_sample, low_activity_users_sample],
    ignore_index=True)


    engagement_dict = create_engagement_events(engagement_sample_df)

    login_engagement_events = engagement_dict['login_events']
    engagement_events = engagement_dict['engagement_events']
    wallet_funding_events = engagement_dict['wallet_funding_events']
    new_investment_creation_events = engagement_dict['investment_events']


    start_position = end_position
    end_position = start_position + len(login_engagement_events)

    uids = login_engagement_events['user_id']
    etime = login_engagement_events['event_time']
    dtypes = [device_type_map.get(uid) for uid in login_engagement_events['user_id']]

    app_login_events(conn, context, start_position, end_position, user_ids, uids, event_time, etime, device_types, dtypes, event_type_ids)

    start_position = end_position
    end_position = start_position + len(engagement_events)

    uids = engagement_events['user_id']
    etime = engagement_events['event_time']
    dtypes = [device_type_map.get(uid) for uid in engagement_events['user_id']]

    updated_end_position = review_current_investment_events(conn, context, start_position, end_position, user_ids, uids, event_time, etime, device_types, dtypes, event_type_ids)

    start_position = updated_end_position
    end_position = start_position + len(wallet_funding_events)

    return_dict = create_wallet_funding_events(conn, context, start_position, end_position, user_ids, wallet_funding_events['user_id'], event_time, wallet_funding_events['event_time'], last_transaction_id,
                                                device_types, [device_type_map.get(uid) for uid in wallet_funding_events['user_id']], is_money_movement_activities, event_type_ids,
                                                transaction_type_ids, transaction_ids, transaction_amounts)

    last_transaction_id = return_dict['last_transaction_id']
    updated_end_position = return_dict['updated_end_position']

    start_position = updated_end_position
    end_position = start_position + len(new_investment_creation_events)

    uids = new_investment_creation_events['user_id']
    etime = new_investment_creation_events['event_time']
    dtypes = [device_type_map.get(uid) for uid in new_investment_creation_events['user_id']]
    inv_type = new_investment_creation_events['investment_type']

    return_dict = new_investment_creation(conn, context, start_position, end_position, user_ids, uids, event_time, etime, inv_type, device_types, dtypes, 
                                          is_money_movement_activities, transaction_ids, last_transaction_id, transaction_type_ids, event_type_ids, plan_ids, transaction_amounts, amount_invested)

    
    last_transaction_id = return_dict["last_transaction_id"]
    all_investments_df = pd.concat(
    [all_investments_df, return_dict["all_investments_df"]],
    ignore_index=True
)
    end_position = return_dict["updated_end_position"]



    all_investments_df["investment_status"] = np.select([all_investments_df["investment_maturity_date"] < pd.Timestamp.today()],
    ["Matured"],default="Active")

    tenure_days_mask = all_investments_df["tenure_days"].notna()

    all_investments_df.loc[tenure_days_mask,"investment_maturity_date_id"] = np.array([int(pd.Timestamp(ts).strftime('%Y%m%d'))for ts in all_investments_df.loc[tenure_days_mask,"investment_maturity_date"]], dtype=np.int32)

    
    #let's split into vestable investments and saleable investments
    vestable_investments_df = all_investments_df[(all_investments_df["tenure_days"].notna()) & (all_investments_df["investment_status"] == "Matured")].copy()

    saleable_investments = all_investments_df[pd.isna(all_investments_df["tenure_days"]) & (all_investments_df["investment_start_date"] <= MUTUAL_FUNDS_CUTOFF_DATE)].copy()

    saleable_investments_df = saleable_investments.sample(frac=0.65,random_state=42)

    active_investments_df = all_investments_df[(all_investments_df["tenure_days"].notna()) & (all_investments_df["investment_status"] == "Active")].copy()


    # simulate early withdrawal requests for vestable investments based on customer behaviour segment probabilities
    vestable_investments_df["requests_early_withdrawal"] = [
        np.random.random()
    <= CUSTOMER_BEHAVIOUR_SEGMENT_MAP[segment]["early_withdrawal_probability"]
    for segment in vestable_investments_df["customer_behaviour_segment"]]

    early_withdrawal_mask = vestable_investments_df["requests_early_withdrawal"] == True
    vested_invested_mask = vestable_investments_df["requests_early_withdrawal"] == False

    vestable_investments_df.loc[early_withdrawal_mask,"investment_status"] = "Withdrawn Early"
    vestable_investments_df.loc[vested_invested_mask,"investment_status"] = "Redeemed"


    #let's create the simulate early investment events
    
    vestable_investments_df.loc[early_withdrawal_mask,"days_before_maturity"] = [
    int(
        np.random.triangular(
            EARLY_WITHDRAWAL_BEHAVIOUR[plan_name]["left"],
            EARLY_WITHDRAWAL_BEHAVIOUR[plan_name]["mode"],
            EARLY_WITHDRAWAL_BEHAVIOUR[plan_name]["right"]
        )
    )
    for plan_name in vestable_investments_df.loc[
        early_withdrawal_mask,
        "plan_name"
    ]]

    vestable_investments_df.loc[early_withdrawal_mask,"withdrawal_request_date"] = (vestable_investments_df.loc[
        early_withdrawal_mask,
        "investment_maturity_date"
    ] - pd.to_timedelta(
                  vestable_investments_df.loc[
        early_withdrawal_mask,
        "days_before_maturity"
    ],unit = "D"))

    minutes_before_request = np.random.randint(
    1,
    31,
    size=early_withdrawal_mask.sum())

    vestable_investments_df.loc[early_withdrawal_mask,"withdrawal_request_login_time"] = (vestable_investments_df.loc[
        early_withdrawal_mask,
        "withdrawal_request_date"
    ] - pd.to_timedelta(minutes_before_request,unit = "m"))

    #early withdrawal events

    start_position = end_position
    end_position = start_position + early_withdrawal_mask.sum()

    user_ids[start_position:end_position] = vestable_investments_df.loc[early_withdrawal_mask,"user_id"]
    event_time[start_position:end_position] = vestable_investments_df.loc[early_withdrawal_mask,"withdrawal_request_login_time"]
    event_type_ids[start_position:end_position] = [event_type_map.get("app_login") for _ in range(early_withdrawal_mask.sum())]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in vestable_investments_df.loc[early_withdrawal_mask,"user_id"]]
    update_last_login_timestamp(conn, user_ids[start_position:end_position], event_time[start_position:end_position])

    start_position = end_position
    end_position = start_position + early_withdrawal_mask.sum()

    user_ids[start_position:end_position] = vestable_investments_df.loc[early_withdrawal_mask,"user_id"]
    event_time[start_position:end_position] = vestable_investments_df.loc[early_withdrawal_mask,"withdrawal_request_date"]
    event_type_ids[start_position:end_position] = [event_type_map.get("request_early_withdrawal") for _ in range(early_withdrawal_mask.sum())]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in vestable_investments_df.loc[early_withdrawal_mask,"user_id"]]

    
    #early withdrawal requests moves money to the wallet - model the "investment_proceeds_wallet_transfer"
    start_position = end_position
    end_position = start_position + early_withdrawal_mask.sum()

    user_ids[start_position:end_position] = vestable_investments_df.loc[early_withdrawal_mask,"user_id"]
    event_time[start_position:end_position] = (vestable_investments_df.loc[early_withdrawal_mask,"withdrawal_request_date"] + pd.to_timedelta(INVESTMENT_WITHDRAWAL_PROCESSING_TIME,unit='m'))
    event_type_ids[start_position:end_position] = [event_type_map.get("investment_proceeds_wallet_transfer") for _ in range(early_withdrawal_mask.sum())]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in vestable_investments_df.loc[early_withdrawal_mask,"user_id"]]
    wallet_ids[start_position:end_position] = [wallet_id_map.get(uid) for uid in vestable_investments_df.loc[early_withdrawal_mask,"user_id"]]
    is_money_movement_activities[start_position:end_position] = True
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, 1 + early_withdrawal_mask.sum() +  last_transaction_id)
    last_transaction_id = transaction_ids[start_position:end_position].max()
    amount_invested[start_position:end_position] = vestable_investments_df.loc[early_withdrawal_mask,"amount_invested"]
    transaction_type_ids[start_position:end_position] = [transaction_type_map.get("investment_proceeds_transfer") for _ in range(early_withdrawal_mask.sum())]
    vestable_investments_df.loc[early_withdrawal_mask,"investment_status"] = "Redeemed"
    investment_ids[start_position:end_position] = vestable_investments_df.loc[early_withdrawal_mask,"investment_id"]
    transaction_amounts[start_position:end_position] = vestable_investments_df.loc[early_withdrawal_mask,"amount_invested"]
    transaction_statuses[start_position:end_position] = ["success" for _ in range(len(vestable_investments_df.loc[early_withdrawal_mask,"amount_invested"]))]
    is_withdrawn_early[start_position:end_position] = True
    withdrawal_date[start_position:end_position] = event_time[start_position:end_position]
    early_withdrawal_investment_ids = investment_ids[start_position:end_position]
    early_withdrawal_dates = event_time[start_position:end_position]

    vestable_investments_df["is_withdrawn_early"] = np.full(len(vestable_investments_df),False,dtype=bool)
    vestable_investments_df["early_withdrawal_date"] = np.empty(len(vestable_investments_df),dtype=object)
    saleable_investments_df["is_withdrawn_early"] = np.full(len(saleable_investments_df),False,dtype=bool)
    saleable_investments_df["early_withdrawal_date"] = np.empty(len(saleable_investments_df),dtype=object)
    active_investments_df["is_withdrawn_early"] = np.full(len(active_investments_df),False,dtype=bool)
    active_investments_df["early_withdrawal_date"] = np.empty(len(active_investments_df),dtype=object)


    vestable_investments_df.loc[vestable_investments_df["investment_id"].isin(early_withdrawal_investment_ids),"is_withdrawn_early"] = True
    vestable_investments_df.loc[vestable_investments_df["investment_id"].isin(early_withdrawal_investment_ids),"early_withdrawal_date"] = early_withdrawal_dates


    #model investment vests transactions for matured investments
    start_position = end_position
    end_position = start_position + vested_invested_mask.sum()

    user_ids[start_position:end_position] = vestable_investments_df.loc[vested_invested_mask,"user_id"]
    event_time[start_position:end_position] = (vestable_investments_df.loc[vested_invested_mask,"investment_maturity_date"])
    event_type_ids[start_position:end_position] = [event_type_map.get("investment_vests") for _ in range(vested_invested_mask.sum())]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in vestable_investments_df.loc[vested_invested_mask,"user_id"]]

    #model investment proceeds wallet transfer for transactions with matured investments
    start_position = end_position
    end_position = start_position + vested_invested_mask.sum()

    user_ids[start_position:end_position] = vestable_investments_df.loc[vested_invested_mask,"user_id"]
    event_time[start_position:end_position] = (vestable_investments_df.loc[vested_invested_mask,"investment_maturity_date"])
    event_type_ids[start_position:end_position] = [event_type_map.get("investment_proceeds_wallet_transfer") for _ in range(vested_invested_mask.sum())]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in vestable_investments_df.loc[vested_invested_mask,"user_id"]]

    wallet_ids[start_position:end_position] = [wallet_id_map.get(uid) for uid in vestable_investments_df.loc[vested_invested_mask,"user_id"]]
    is_money_movement_activities[start_position:end_position] = True
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, 1 + vested_invested_mask.sum() +  last_transaction_id)
    last_transaction_id = transaction_ids[start_position:end_position].max()
    amount_invested[start_position:end_position] = vestable_investments_df.loc[vested_invested_mask,"amount_invested"]
    transaction_type_ids[start_position:end_position] = [transaction_type_map.get("investment_proceeds_transfer") for _ in range(vested_invested_mask.sum())]
    vestable_investments_df.loc[vested_invested_mask,"investment_status"] = "Redeemed"
    investment_ids[start_position:end_position] = vestable_investments_df.loc[vested_invested_mask,"investment_id"]
    transaction_amounts[start_position:end_position] = vestable_investments_df.loc[vested_invested_mask,"amount_invested"]
    transaction_statuses[start_position:end_position] = ["success" for _ in range(len(vestable_investments_df.loc[vested_invested_mask,"amount_invested"]))]


    # now let's model asset sales
    eligible_saleable_investments = saleable_investments_df[(pd.Timestamp.today() - saleable_investments_df["investment_start_date"]) > pd.Timedelta(days=200)]
    saleable_investments_df_subset = eligible_saleable_investments.sample(frac=0.45).copy()
    saleable_investments_df_subset["days_held"] = (pd.Timestamp.today() - saleable_investments_df_subset["investment_start_date"]).dt.days

    saleable_investments_df_subset["days_held_before_sale"] = [
    int(
        np.random.triangular(
            30,
            min(180, days_held),
            days_held
        )
    )
    for days_held in saleable_investments_df_subset["days_held"]
]

    saleable_investments_df_subset["redemption_request_date"] = (
    saleable_investments_df_subset["investment_start_date"]
    +
    pd.to_timedelta(saleable_investments_df_subset["days_held_before_sale"],unit="D"))

    saleable_investments_df_subset["redemption_request_login_date"] = (
    saleable_investments_df_subset["redemption_request_date"]
    -
    pd.to_timedelta(5,unit="m"))

    saleable_investments_df_subset["review_current_investment_date"] = (
    saleable_investments_df_subset["redemption_request_login_date"]
    +
    pd.to_timedelta(3,unit="m"))

    saleable_investments_df_subset["redemption_request_processing_date"] = (
        saleable_investments_df_subset["redemption_request_date"]
    +
    pd.to_timedelta(24,unit="h")
    )

    saleable_investments_df_subset["investment_status"] = "Redeemed"

    #let's model the login first
    start_position = end_position
    end_position = start_position + len(saleable_investments_df_subset)

    user_ids[start_position:end_position] = saleable_investments_df_subset["user_id"].values
    event_time[start_position:end_position] = saleable_investments_df_subset["redemption_request_login_date"]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in saleable_investments_df_subset["user_id"]]
    event_type_ids[start_position:end_position] = [event_type_map.get("app_login") for _ in range(len(saleable_investments_df_subset))]
    update_last_login_timestamp(conn, user_ids[start_position:end_position], event_time[start_position:end_position])
    

    #current investment review events
    start_position = end_position
    end_position = start_position + len(saleable_investments_df_subset)

    user_ids[start_position:end_position] = saleable_investments_df_subset["user_id"].values
    event_time[start_position:end_position] = saleable_investments_df_subset["review_current_investment_date"]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in saleable_investments_df_subset["user_id"]]
    event_type_ids[start_position:end_position] = [event_type_map.get("review_current_investment") for _ in range(len(saleable_investments_df_subset))]

    start_position = end_position
    end_position = start_position + len(saleable_investments_df_subset)

    user_ids[start_position:end_position] = saleable_investments_df_subset["user_id"].values
    event_time[start_position:end_position] = saleable_investments_df_subset["redemption_request_date"]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in saleable_investments_df_subset["user_id"]]
    event_type_ids[start_position:end_position] = [event_type_map.get("assets_sale") for _ in range(len(saleable_investments_df_subset))]
    investment_ids[start_position:end_position] = saleable_investments_df_subset["investment_id"].values
    saleable_investments_df_subset["investment_maturity_date"] = saleable_investments_df_subset["redemption_request_date"]

    start_position = end_position
    end_position = start_position + len(saleable_investments_df_subset)

    user_ids[start_position:end_position] = saleable_investments_df_subset["user_id"].values
    event_time[start_position:end_position] = saleable_investments_df_subset["redemption_request_processing_date"]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in saleable_investments_df_subset["user_id"]]
    event_type_ids[start_position:end_position] = [event_type_map.get("investment_proceeds_wallet_transfer") for _ in range(len(saleable_investments_df_subset))]
    investment_ids[start_position:end_position] = saleable_investments_df_subset["investment_id"].values
    is_money_movement_activities[start_position:end_position] = True
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + 1 + len(saleable_investments_df_subset))
    transaction_type_ids[start_position:end_position] = [transaction_type_map.get("investment_proceeds_transfer") for _ in range(len(saleable_investments_df_subset))]
    wallet_ids[start_position:end_position] = [wallet_id_map.get(uid) for uid in saleable_investments_df_subset["user_id"].values]
    amount_invested[start_position:end_position] = saleable_investments_df_subset["amount_invested"].values
    last_transaction_id = transaction_ids[start_position:end_position].max()
    transaction_amounts[start_position:end_position] = saleable_investments_df_subset["amount_invested"].values
    transaction_statuses[start_position:end_position] = ["success" for _ in range(len(saleable_investments_df_subset))]


    redeemed_ids = saleable_investments_df_subset["investment_id"]

    saleable_investments_df.loc[
    saleable_investments_df["investment_id"].isin(redeemed_ids),
    "investment_status"] = "Redeemed"



    saleable_updates = (
    saleable_investments_df_subset[
        ["investment_id", "investment_maturity_date"]
    ]
    .set_index("investment_id")
)

    saleable_investments_df["investment_maturity_date"] = (
    saleable_investments_df["investment_id"]
    .map(saleable_updates["investment_maturity_date"])
    .fillna(saleable_investments_df["investment_maturity_date"])
)

    all_investments_df = pd.concat([active_investments_df, vestable_investments_df, saleable_investments_df], ignore_index = True)

    redeemed_mask = all_investments_df["investment_status"] == "Redeemed"

    redemption_investments_df = all_investments_df.loc[redeemed_mask].copy()
    redeemed_investments_events_df = redemption_investments_df.sample(frac=0.9, random_state=42)
    remaining_investments_df = redemption_investments_df.drop(redeemed_investments_events_df.index)

    redeemed_investments_events_df["redemption_date"] = redeemed_investments_events_df["investment_maturity_date"] + pd.to_timedelta(1440,unit='m')
    redeemed_investments_events_df["days_until_wallet_withdrawal"] = np.random.triangular(
    left=1,
    mode=14,
    right=90,
    size=len(redeemed_investments_events_df)
).astype(int)
    
    random_offset = np.random.randint(2,15, size=len(remaining_investments_df))

    remaining_investments_df["redemption_date"] = remaining_investments_df["investment_maturity_date"] + pd.to_timedelta(1440, unit="m")
    remaining_investments_df["days_until_first_withdrawal_trial"] = np.random.triangular(
    left=1,
    mode=14,
    right=90,
    size=len(remaining_investments_df)
).astype(int)
    
    remaining_investments_df["final_withdrawal_date"] = remaining_investments_df["redemption_date"] + pd.to_timedelta(remaining_investments_df["days_until_first_withdrawal_trial"], unit="D") + pd.to_timedelta(random_offset,unit="D")
    remaining_investments_df["withdrawal_login_time"] = remaining_investments_df["final_withdrawal_date"] - pd.to_timedelta(5,unit="m")
    remaining_investments_df["final_withdrawal_trial_date"] = remaining_investments_df["redemption_date"] + pd.to_timedelta(remaining_investments_df["days_until_first_withdrawal_trial"], unit="D")
    remaining_investments_df["withdrawal_trial_login_time"] = remaining_investments_df["final_withdrawal_trial_date"] - pd.to_timedelta(5,unit="m")
    

    #let's model the wallet withdrawals
    start_position = end_position
    end_position = start_position + len(redeemed_investments_events_df)

    is_money_movement_activities[start_position:end_position] = True
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1,len(redeemed_investments_events_df) + last_transaction_id + 1)
    last_transaction_id = transaction_ids[start_position:end_position].max()
    transaction_type_ids[start_position:end_position] = [transaction_type_map.get("wallet_withdrawal") for _ in range(len(redeemed_investments_events_df))]
    event_time[start_position:end_position] = redeemed_investments_events_df["redemption_date"] + pd.to_timedelta(redeemed_investments_events_df["days_until_wallet_withdrawal"],unit="D")
    user_ids[start_position:end_position] = redeemed_investments_events_df["user_id"].values
    wallet_ids[start_position:end_position] = [wallet_id_map.get(uid) for uid in redeemed_investments_events_df["user_id"]]
    amount_invested[start_position:end_position] = redeemed_investments_events_df["amount_invested"]
    event_type_ids[start_position:end_position] = [event_type_map.get("wallet_withdrawal") for _ in range(len(redeemed_investments_events_df))]
    transaction_statuses[start_position:end_position] = ["success" for _ in range(len(redeemed_investments_events_df))]
    transaction_amounts[start_position:end_position] = redeemed_investments_events_df["amount_invested"]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in redeemed_investments_events_df["user_id"].values]

    #let's model withdrawal failures and withdrawal successes after
    start_position = end_position
    end_position = start_position + len(remaining_investments_df)

    #login and withdrawal failure simulation first
    user_ids[start_position:end_position] = remaining_investments_df["user_id"].values
    event_time[start_position:end_position] = remaining_investments_df["withdrawal_trial_login_time"]
    event_type_ids[start_position:end_position] = [event_type_map.get("app_login") for _ in range(len(remaining_investments_df))]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in remaining_investments_df["user_id"].values]
    update_last_login_timestamp(conn, user_ids[start_position:end_position], event_time[start_position:end_position])

    start_position = end_position
    end_position = start_position + len(remaining_investments_df)

    user_ids[start_position:end_position] = remaining_investments_df["user_id"].values
    event_time[start_position:end_position] = remaining_investments_df["final_withdrawal_trial_date"]
    event_type_ids[start_position:end_position] = [event_type_map.get("withdrawal_failed") for _ in range(len(remaining_investments_df))]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in remaining_investments_df["user_id"].values]
    is_money_movement_activities[start_position:end_position] = [True for _ in range(len(remaining_investments_df))]
    transaction_type_ids[start_position:end_position] = [transaction_type_map.get("wallet_withdrawal") for _ in range(len(remaining_investments_df))]
    transaction_statuses[start_position:end_position] = ["failure" for _ in range(len(remaining_investments_df))]
    transaction_amounts[start_position:end_position] = remaining_investments_df["amount_invested"]
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + 1 + len(remaining_investments_df))
    last_transaction_id = transaction_ids[start_position:end_position].max()
    wallet_ids[start_position:end_position] = [wallet_id_map.get(uid) for uid in remaining_investments_df["user_id"].values]

    #let's model successful withdrawals now
    start_position = end_position
    end_position = start_position + len(remaining_investments_df)

    user_ids[start_position:end_position] = remaining_investments_df["user_id"].values
    event_time[start_position:end_position] = remaining_investments_df["withdrawal_login_time"]
    event_type_ids[start_position:end_position] = [event_type_map.get("app_login") for _ in range(len(remaining_investments_df))]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in remaining_investments_df["user_id"].values]
    update_last_login_timestamp(conn, user_ids[start_position:end_position], event_time[start_position:end_position])

    start_position = end_position
    end_position = start_position + len(remaining_investments_df)

    user_ids[start_position:end_position] = remaining_investments_df["user_id"].values
    event_time[start_position:end_position] = remaining_investments_df["final_withdrawal_date"]
    event_type_ids[start_position:end_position] = [event_type_map.get("wallet_withdrawal") for _ in range(len(remaining_investments_df))]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in remaining_investments_df["user_id"].values]
    is_money_movement_activities[start_position:end_position] = [True for _ in range(len(remaining_investments_df))]
    transaction_type_ids[start_position:end_position] = [transaction_type_map.get("wallet_withdrawal") for _ in range(len(remaining_investments_df))]
    transaction_statuses[start_position:end_position] = ["success" for _ in range(len(remaining_investments_df))]
    transaction_amounts[start_position:end_position] = remaining_investments_df["amount_invested"]
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, len(remaining_investments_df) + last_transaction_id + 1)
    last_transaction_id = transaction_ids[start_position:end_position].max()
    wallet_ids[start_position:end_position] = [wallet_id_map.get(uid) for uid in remaining_investments_df["user_id"].values]

    total_events = end_position
    

    #invesment df
    main_df = pd.DataFrame({
        "user_id":user_ids[:total_events],
        "event_type_id":event_type_ids[:total_events],
        "wallet_id":wallet_ids[:total_events],
        "plan_id":plan_ids[:total_events],
        "event_time":event_time[:total_events],
        "device_type":device_types[:total_events],
        "is_money_movement_activity":is_money_movement_activities[:total_events],
        "transaction_type_id":transaction_type_ids[:total_events],
        "transaction_id":transaction_ids[:total_events],
        "investment_id":investment_ids[:total_events],
        "transaction_status":transaction_statuses[:total_events],
        "transaction_amount":transaction_amounts[:total_events],
        "is_withdrawn_early":is_withdrawn_early[:total_events],
        "early_withdrawal_date":withdrawal_date[:total_events]
    })

    main_df["event_date_id"] = np.array([
    int(pd.Timestamp(ts).strftime('%Y%m%d'))
    for ts in main_df["event_time"]
    ], dtype=np.int32)

    print("Missing event_time:", np.sum(pd.isna(event_time[:total_events])))

    missing_idx = np.where(pd.isna(event_time[:total_events]))[0]
    print(missing_idx[:20])

    bad_rows = main_df[
    main_df["event_time"].map(lambda x: not isinstance(x, pd.Timestamp))
]

    print(bad_rows[[
    "event_time",
    "event_type_id",
    "user_id",
    "investment_id",
    "transaction_id"
]])

    print(main_df["event_time"].map(type).value_counts())

    print(
    main_df.loc[
        main_df["event_time"].map(lambda x: not isinstance(x, pd.Timestamp)),
        ["event_type_id", "event_time", "transaction_id", "investment_id"]
    ]
)
    main_df = main_df.sort_values(by='event_time').reset_index(drop=True)

    money_mov_mask = main_df["transaction_id"].notna()

    main_df.loc[money_mov_mask,"transaction_id"] = np.arange(968, money_mov_mask.sum() + 968)
    
    transactions_df = main_df[main_df["transaction_id"].notna()].copy()

    transaction_events_df = pd.DataFrame({
        "transaction_id":transactions_df["transaction_id"],
        "wallet_id":transactions_df["wallet_id"],
        "transaction_type_id":transactions_df["transaction_type_id"],
        "transaction_amount":transactions_df["transaction_amount"],
        "transaction_status": transactions_df["transaction_status"],
        "transaction_timestamp":transactions_df["event_time"],
        "transaction_date_id":transactions_df["event_date_id"]
    })

    conn.register("tr_events",transaction_events_df)

    conn.execute('''INSERT INTO fact_transaction SELECT * FROM tr_events''')

    conn.execute(f'''
                    COPY fact_transaction TO '{FACT_TRANSACTION_PARQUET_PATH}' (FORMAT PARQUET)
    ''')

    investment_maturity_mask = all_investments_df["investment_maturity_date"].notna()
    all_investments_df["investment_maturity_date_id"] = np.empty(len(all_investments_df["investment_maturity_date"]),dtype=object)
    all_investments_df.loc[investment_maturity_mask,"investment_maturity_date_id"] = np.array([int(pd.Timestamp(ts).strftime('%Y%m%d')) for ts in all_investments_df.loc[investment_maturity_mask,"investment_maturity_date"]
    ], dtype=np.int32)

    early_withdrawals = all_investments_df["is_withdrawn_early"] == True
    all_investments_df["early_withdrawal_date_id"] = np.empty(len(all_investments_df),dtype=object)

    all_investments_df.loc[early_withdrawals,"early_withdrawal_date_id"] = np.array([int(pd.Timestamp(ts).strftime('%Y%m%d')) for ts in all_investments_df.loc[early_withdrawals,"early_withdrawal_date"]],dtype=np.int32)

    investment_positions_df = pd.DataFrame({
        "investment_id":all_investments_df["investment_id"],
        "user_id":all_investments_df["user_id"],
        "wallet_id":all_investments_df["wallet_id"],
        "plan_id":all_investments_df["plan_id"],
        "amount_invested":all_investments_df["amount_invested"],
        "investment_start_date":all_investments_df["investment_start_date"],
        "investment_start_date_id": np.array([int(pd.Timestamp(ts).strftime('%Y%m%d')) for ts in all_investments_df["investment_start_date"]
    ], dtype=np.int32),
        "investment_maturity_date":all_investments_df["investment_maturity_date"],
        "investment_maturity_date_id":all_investments_df["investment_maturity_date_id"],
    "investment_status":all_investments_df["investment_status"],
    "is_withdrawn_early":all_investments_df["is_withdrawn_early"],
    "early_withdrawal_date":all_investments_df["early_withdrawal_date"],
    "early_withdrawal_date_id":all_investments_df["early_withdrawal_date_id"]
    })

    conn.register("investment_df",investment_positions_df)

    conn.execute('''INSERT INTO FACT_INVESTMENT_POSITION SELECT * FROM INVESTMENT_DF''')

    conn.execute(f'''COPY FACT_INVESTMENT_POSITION TO '{FACT_INVESTMENT_POSITION_PARQUET_PATH}' (FORMAT PARQUET) ''')

    df_raw = pd.DataFrame({
        "user_id":user_ids[:total_events],
        "event_type_id":event_type_ids[:total_events],
        "wallet_id":wallet_ids[:total_events],
        "plan_id":plan_ids[:total_events],
        "event_time":event_time[:total_events],
        "event_date_id":np.array([
    int(pd.Timestamp(ts).strftime('%Y%m%d'))
    for ts in event_time[:total_events]
    ], dtype=np.int32),
        "device_type":device_types[:total_events],
        "is_money_movement_activity":is_money_movement_activities[:total_events],
        "transaction_type_id":transaction_type_ids[:total_events],
        "transaction_id":transaction_ids[:total_events],
        "investment_id":investment_ids[:total_events]
    })

    df_raw = df_raw.sort_values(
    by='event_time'
    ).reset_index(drop=True)

    df_raw['event_id'] = np.arange(
    1,
    len(df_raw) + 1
    )

    df_raw = df_raw[[
        "event_id",
        "user_id",
        "event_type_id",
        "wallet_id",
        "plan_id",
        "event_time",
        "event_date_id",
        "device_type",
        "is_money_movement_activity",
        "transaction_type_id",
        "transaction_id",
        "investment_id"
    ]]

    conn.register("df_raw",df_raw)

    conn.execute('''INSERT INTO fact_user_event SELECT * FROM df_raw''')

    conn.execute(f'''COPY FACT_USER_EVENT TO '{FACT_USER_EVENT_PARQUET_PATH}' (FORMAT PARQUET) ''')