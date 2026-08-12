import numpy as np
import pandas as pd
from src.config.paths import (DDL_FACT_USER_EVENT_PATH, FACT_USER_EVENT_PARQUET_PATH, 
                              FACT_INVESTMENT_POSITION_PARQUET_PATH, DDL_FACT_INVESTMENT_POSITION_PATH, DDL_FACT_TRANSACTION_PATH, FACT_TRANSACTION_PARQUET_PATH)
from src.config.constants import (DEFAULT_TRANSACTION_START_DATE, DEFAULT_TRANSACTION_END_DATE, IMMEDIATE_LOGINS_TIME_FRAME, KYC_ACTIVATION_TIMEFRAME, USERS_MAKES_FIRST_INVESTMENT_AFTER_FUNDING,
                                  CUSTOMER_BEHAVIOUR_SEGMENT_MAP, FIRST_INVESTMENT_TYPE, EARLY_WITHDRAWAL_BEHAVIOUR, INVESTMENT_WITHDRAWAL_PROCESSING_TIME,
                                  MUTUAL_FUNDS_CUTOFF_DATE, TODAY
                                  )
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from src.logic.helper_functions import (update_last_login_timestamp, signup_completion_events, app_login_events, get_last_login)


def generate_facts(conn, num_of_events):

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

    signup_completion_events(conn,
                             start_position, 
                             end_position, 
                             user_ids, 
                             users_data["user_id"], 
                             event_time, 
                             users_data["signup_date"],
                             device_types, 
                             dtypes,
                             event_type_ids)

    

    #new user logins
    new_users_logins = conn.execute(f'''SELECT user_id, signup_date, kyc_completed, is_activated_user, customer_behaviour_segment FROM dim_user
    where signup_date between '{DEFAULT_TRANSACTION_START_DATE}' and '{DEFAULT_TRANSACTION_END_DATE}' AND is_immediate_login = True order by signup_date''').df()
    
    immediate_login_timeframe = np.random.randint(IMMEDIATE_LOGINS_TIME_FRAME[0],IMMEDIATE_LOGINS_TIME_FRAME[1], size=len(new_users_logins))
    
    total_new_users = len(new_users_logins)

    start_position = total_signups
    end_position = start_position + total_new_users

    etime = [pd.Timestamp(sd) + timedelta(seconds=int(ro)) for sd, ro in zip(new_users_logins["signup_date"], immediate_login_timeframe)]
    uids = new_users_logins["signup_date"]
    dtypes=[device_type_map.get(uid) for uid in uids]

    app_login_events(conn,start_position, end_position,
                     user_ids,uids,event_time,etime,device_types,dtypes, event_type_ids)
    
    #kyc_completed_users
    kyc_completed_users = users_data[users_data["kyc_completed"] == True].copy()

    signup_map = dict(zip(
    users_data["user_id"],
    users_data["signup_date"]
))

    
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

    dtypes = [device_type_map.get(uid) for uid in kyc_completed_users["device_type"]]
    etime = [last_login_map.get(uid,signup_map.get(uid)) + timedelta(minutes=int(ro)) for uid, ro in zip(kyc_completed_users["user_id"], kyc_logins_timeframe)]

    app_login_events(conn, start_position, end_position, user_ids,kyc_completed_users["user_id"],event_time,etime,device_types,dtypes,event_type_ids)


    #activate kyc
    start_position = end_position
    end_position = start_position + len(kyc_completed_users)

    
    etime = [last_login_map.get(uid,signup_map.get(uid)) + timedelta(minutes=int(ro)) for uid, ro in zip(kyc_completed_users["user_id"], kyc_activation_timeframe)]
    event_type_ids[start_kyc_activation_completion:end_kyc_activation_completion] = event_type_map.get("kyc_completed")
    device_types[start_kyc_activation_completion:end_kyc_activation_completion] = np.array([device_type_map.get(uid) for uid in kyc_completed_users["user_id"]])

    

    #wallet activation
    wallet_activated_users = kyc_completed_users[~pd.isna(kyc_completed_users["wallet_activation_timeframe"])].copy()

    segment_customers = dict(zip(
        users_data["user_id"],
        users_data["customer_behaviour_segment"]
    ))

    wallet_activated_users["customer_behaviour_segment"] = wallet_activated_users["user_id"].map(segment_customers)

    wallet_activated_users["amount_invested"] = np.array([
        np.random.randint(CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["average_investment_amount"][0],
            CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["average_investment_amount"][1]
            
        )
        for bh in wallet_activated_users["customer_behaviour_segment"]
    ])

    total_wallet_activated_users = len(wallet_activated_users)

    start_wallet_activations = end_kyc_activation_completion
    end_wallet_activations = start_wallet_activations + total_wallet_activated_users

    user_ids[start_wallet_activations:end_wallet_activations] = wallet_activated_users["user_id"]
    event_time[start_wallet_activations:end_wallet_activations] = [signup_map.get(uid,None) + timedelta(minutes=int(ro)) for uid, ro in zip(wallet_activated_users["user_id"], wallet_activated_users["wallet_activation_timeframe"])]
    event_type_ids[start_wallet_activations:end_wallet_activations] = event_type_map.get("wallet_funded")
    is_money_movement_activities[start_wallet_activations:end_wallet_activations] = True
    wallet_ids[start_wallet_activations:end_wallet_activations] = [wallet_id_map.get(uid) for uid in wallet_activated_users["user_id"]]
    transaction_type_ids[start_wallet_activations:end_wallet_activations] = [transaction_type_map.get("wallet_funding") for _ in range(len(wallet_activated_users))]
    transaction_ids[start_wallet_activations:end_wallet_activations] = np.arange(1, total_wallet_activated_users + 1)
    amount_invested[start_wallet_activations:end_wallet_activations] = wallet_activated_users["amount_invested"]
    last_transaction_id = transaction_ids[start_wallet_activations:end_wallet_activations].max()
    device_types[start_wallet_activations:end_wallet_activations] = np.array([device_type_map.get(uid) for uid in wallet_activated_users["user_id"]])
    transaction_statuses[start_wallet_activations:end_wallet_activations] = ["success" for _ in range(total_wallet_activated_users)]
    transaction_amounts[start_wallet_activations:end_wallet_activations] = wallet_activated_users["amount_invested"]

    wallet_activated_users_df = pd.DataFrame(
        {
            "user_id": user_ids[start_wallet_activations:end_wallet_activations],
            "last_login_time": event_time[start_wallet_activations:end_wallet_activations],
            "current_wallet_balance": amount_invested[start_wallet_activations:end_wallet_activations]
        }
    )

    #let's create the initial investment -- login, review_plan_options then drop off for some users, and for others, they will make an investment after reviewing the plan options. We will create a new dataframe to hold the users who made an investment and their corresponding investment details.

    wallet_activated_users_df = pd.DataFrame({
        "user_id": wallet_activated_users_df["user_id"],
        "customer_behaviour_segment": wallet_activated_users_df["user_id"].map(segment_customers),
        "last_login_time": wallet_activated_users_df["last_login_time"],
        "current_wallet_balance":wallet_activated_users_df["current_wallet_balance"]
        })
    
    customer_subset_1 = wallet_activated_users_df.sample(frac = 0.55, random_state=1)

    total_customer_subset_1 = len(customer_subset_1)

    #these users will just login and review plan options, but will not make an investment. We will create a new dataframe to hold the users who made an investment and their corresponding investment details.

    start_position = end_wallet_activations
    end_position = start_position + total_customer_subset_1

    user_ids[start_position:end_position] = customer_subset_1["user_id"]
    event_time[start_position:end_position] = [last_login + timedelta(minutes=np.random.randint(5, 80)) for last_login in customer_subset_1["last_login_time"]]
    event_type_ids[start_position:end_position] = event_type_map.get("app_login")
    device_types[start_position:end_position] = np.array([device_type_map.get(uid) for uid in customer_subset_1["user_id"]])
    update_last_login_timestamp(conn, customer_subset_1["user_id"], event_time[start_position:end_position])

    login_time_for_review_plan_options = event_time[start_position:end_position]

    start_position = end_position
    end_position = start_position + total_customer_subset_1

    user_ids[start_position:end_position] = customer_subset_1["user_id"]
    event_time[start_position:end_position] = [last_login + timedelta(minutes=np.random.randint(2, 5)) for last_login in login_time_for_review_plan_options]
    event_type_ids[start_position:end_position] = event_type_map.get("review_plan_options")
    device_types[start_position:end_position] = np.array([device_type_map.get(uid) for uid in customer_subset_1["user_id"]])

    customer_behaviour_segment_wallet_activated_users = wallet_activated_users_df['customer_behaviour_segment']

    probability_of_making_first_investment = [
    np.random.choice(USERS_MAKES_FIRST_INVESTMENT_AFTER_FUNDING,p=CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cp]['wallet_to_investment_conversion_probability'])
    for cp in customer_behaviour_segment_wallet_activated_users
]

    mins_to_first_investment = [
    np.random.randint(
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cp]['mins_to_first_investment'][0],
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cp]['mins_to_first_investment'][1] + 1
    )
    for cp in customer_behaviour_segment_wallet_activated_users
]

    first_investment_type = [np.random.choice(
        FIRST_INVESTMENT_TYPE,
        p= CUSTOMER_BEHAVIOUR_SEGMENT_MAP[cp][
            'first_investment_type_probability'
        ]
    )
    for cp in customer_behaviour_segment_wallet_activated_users]

    wallet_activated_users_df['makes_first_investment'] = probability_of_making_first_investment

    wallet_activated_users_df['mins_to_first_investment'] = mins_to_first_investment

    wallet_activated_users_df['first_investment_type'] = first_investment_type

    customer_subset_2 = wallet_activated_users_df[wallet_activated_users_df['makes_first_investment'] == True]

    customer_subset_2 = customer_subset_2.copy().reset_index(drop=True)

    total_customer_subset_2 = len(customer_subset_2)

    start_position = end_position
    end_position = start_position + total_customer_subset_2

    user_ids[start_position:end_position] = customer_subset_2["user_id"]
    event_time[start_position:end_position] = [last_login + timedelta(minutes=np.random.randint(0, mtft)) for last_login,mtft in zip(customer_subset_2["last_login_time"],customer_subset_2["mins_to_first_investment"])]
    event_type_ids[start_position:end_position] = event_type_map.get("app_login")
    device_types[start_position:end_position] = np.array([device_type_map.get(uid) for uid in customer_subset_2["user_id"]])
    update_last_login_timestamp(conn, customer_subset_2["user_id"], event_time[start_position:end_position])

    login_time_for_review_plan_options_2 = event_time[start_position:end_position]

    start_position = end_position
    end_position = start_position + total_customer_subset_2

    user_ids[start_position:end_position] = customer_subset_2["user_id"]
    event_time[start_position:end_position] = [last_login + timedelta(minutes=np.random.randint(2, 5)) for last_login in login_time_for_review_plan_options_2]
    event_type_ids[start_position:end_position] = event_type_map.get("review_plan_options")
    device_types[start_position:end_position] = np.array([device_type_map.get(uid) for uid in customer_subset_2["user_id"]])

    last_review_time_for_investment = event_time[start_position:end_position]

    start_position = end_position
    end_position = start_position + total_customer_subset_2

    user_ids[start_position:end_position] = customer_subset_2["user_id"]
    event_time[start_position:end_position] = [last_review + timedelta(minutes=np.random.randint(1, 3)) for last_review in last_review_time_for_investment]
    event_type_ids[start_position:end_position] = event_type_map.get("plan_selected")
    device_types[start_position:end_position] = np.array([device_type_map.get(uid) for uid in customer_subset_2["user_id"]])


    last_plan_selected_time = event_time[start_position:end_position]

    start_position = end_position
    end_position = start_position + total_customer_subset_2

    user_ids[start_position:end_position] = customer_subset_2["user_id"]
    event_time[start_position:end_position] = [last_review + timedelta(minutes=np.random.randint(3,5)) for last_review in last_plan_selected_time]
    device_types[start_position:end_position] = np.array([device_type_map.get(uid) for uid in customer_subset_2["user_id"]])

    investment_type_event_type = [
    "savings_plan_created"
    if inv == "Savings"
    else "investment_plan_created"
    for inv in customer_subset_2["first_investment_type"]
    ]

    print("Absent invesment type selections",pd.isna(investment_type_event_type).sum())
    
    event_type_ids[start_position:end_position] = [event_type_map.get(inv) for inv in investment_type_event_type]
    is_money_movement_activities[start_position:end_position] = True
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id +  len(customer_subset_2) + 1)
    transaction_type_ids[start_position:end_position] = [transaction_type_map.get("investment_funding") for _ in range(len(customer_subset_2))]
    investment_ids[start_position:end_position] = np.arange(1000, 1000 + len(customer_subset_2))
    last_investment_id = investment_ids[start_position:end_position].max()

    customer_subset_2['select_plan_ids'] = np.empty(len(customer_subset_2),dtype=object)

    savings_plans = conn.execute('''SELECT * FROM dim_plan WHERE plan_category = 'Savings' ''').df()
    print("Savings Plans: ",savings_plans["plan_id"])
    investment_plans = conn.execute('''SELECT * FROM dim_plan WHERE plan_category = 'Investments' ''').df()
    print("Investement Plans: ",investment_plans["plan_id"])

    savings_mask = customer_subset_2["first_investment_type"] == 'Savings'
    investments_mask = customer_subset_2["first_investment_type"] == 'Investments'
    print("First Investment Type Unique Values", customer_subset_2["first_investment_type"].unique())

    customer_subset_2.loc[savings_mask,'select_plan_ids'] = [np.random.choice(savings_plans["plan_id"], 
                                            p = savings_plans["plan_weight"] / savings_plans["plan_weight"].sum())
                                     for _ in range(savings_mask.sum())]
    customer_subset_2.loc[investments_mask,'select_plan_ids'] = [np.random.choice(investment_plans["plan_id"], 
                                        p = investment_plans["plan_weight"] / investment_plans["plan_weight"].sum())
                                         for _ in range(investments_mask.sum())]

    plan_ids[start_position:end_position] = customer_subset_2['select_plan_ids']
    print(customer_subset_2['select_plan_ids'])
    wallet_ids[start_position:end_position] = [wallet_id_map.get(uid) for uid in customer_subset_2["user_id"]]
    investment_pct = np.random.uniform(
    0.5,
    0.95,
    len(customer_subset_2)
)
    amount_invested[start_position:end_position] = (customer_subset_2["current_wallet_balance"].values * investment_pct)

    transaction_statuses[start_position:end_position] = ["success" for _ in range(len(customer_subset_2))]
    transaction_amounts[start_position:end_position] = (customer_subset_2["current_wallet_balance"].values * investment_pct)
    updated_balance = customer_subset_2["current_wallet_balance"].values - transaction_amounts[start_position:end_position]

    last_transaction_id = transaction_ids[start_position:end_position].max()

    balance_map = dict(
        zip(
            customer_subset_2["user_id"].values,
            updated_balance
        )
    )

    mask = wallet_activated_users_df["user_id"].isin(balance_map)

    wallet_activated_users_df.loc[mask,"current_wallet_balance"] = wallet_activated_users_df.loc[mask,"user_id"].map(balance_map)

    customers_who_have_invested_df = pd.DataFrame({
        "user_id": user_ids[start_position:end_position],
        "last_login_time":event_time[start_position:end_position],
        "customer_behaviour_segment":customer_subset_2["customer_behaviour_segment"]
    })

    avg_number_of_logins_per_month = np.array([
    np.random.randint(
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["monthly_logins"][0],
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["monthly_logins"][1] + 1
    )
    for bh in customers_who_have_invested_df["customer_behaviour_segment"]
])
    

    customers_who_have_invested_df["monthly_logins"] = avg_number_of_logins_per_month

    monthly_portfolio_reviews = np.array([
    np.random.randint(
        max(1, int(logins * 0.3)),
        max(2, int(logins * 0.7))
    )
    for logins in avg_number_of_logins_per_month
])

    customers_who_have_invested_df["monthly_portfolio_reviews"] = monthly_portfolio_reviews

    monthly_wallet_fundings = np.array([
        np.random.randint(
           CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["monthly_wallet_fundings"][0],
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["monthly_wallet_fundings"][1] + 1
    )
    for bh in customers_who_have_invested_df["customer_behaviour_segment"]
    ])

    monthly_investment_position_creation = np.array([
        np.random.randint(
           CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["monthly_investment_position_creation"][0],
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["monthly_investment_position_creation"][1] + 1
    )
    for bh in customers_who_have_invested_df["customer_behaviour_segment"]
    ])

    monthly_savings_position_creation = np.array([
        np.random.randint(
           CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["monthly_savings_position_creation"][0],
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["monthly_savings_position_creation"][1] + 1
    )
    for bh in customers_who_have_invested_df["customer_behaviour_segment"]
    ])
    
    customers_who_have_invested_df["monthly_wallet_fundings"] = monthly_wallet_fundings

    customers_who_have_invested_df["monthly_plan_fundings"] = np.maximum(monthly_wallet_fundings - 2, 0)

    customers_who_have_invested_df["monthly_investment_position_creation"] = monthly_investment_position_creation

    customers_who_have_invested_df["monthly_savings_position_creation"] = monthly_savings_position_creation

    customers_who_have_invested_df["investment_low_bound"] = np.array([
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["average_investment_amount"][0]
        for bh in customers_who_have_invested_df["customer_behaviour_segment"]
    ])

    customers_who_have_invested_df["investment_high_bound"] = np.array([
        CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["average_investment_amount"][1]
        for bh in customers_who_have_invested_df["customer_behaviour_segment"]
    ])


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

    engagement_events = []

    for _, customer in active_users_sample.iterrows():


    # simulate one month after investment creation
        simulation_start = customer["last_login_time"]

        month_end = TODAY

        delta = relativedelta(month_end, simulation_start)

        months = max(1,delta.years * 12 + delta.months)

        monthly_logins = np.random.randint(
            CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_logins"][0],
            CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_logins"][1] + 1
        ,size=months)


        for idx in range(months):

            current_month_start = (simulation_start+ relativedelta(months=idx))

            current_month_end = (current_month_start+ relativedelta(months=1))

            days_in_month = (current_month_end- current_month_start).days

            
            monthly_reviews = np.random.randint(
            max(1, int(monthly_logins[idx] * 0.15)),
            max(2, int(monthly_logins[idx] * 0.4)) + 1
        )
    # Login events
            login_times = sorted([current_month_start + timedelta(days=np.random.randint(0, days_in_month),hours=np.random.randint(0, 24),minutes=np.random.randint(0, 60))
                for _ in range(monthly_logins[idx])])

            for login_time in login_times:
                engagement_events.append({"user_id": customer["user_id"],"event_time": login_time,"event_type": "app_login"})

    # Portfolio reviews must happen after a login
            if len(login_times) > 0:

                review_login_times = np.random.choice(
                login_times,
                size=min(monthly_reviews, len(login_times)),
                replace=False)

                for login_time in review_login_times:

                    review_time = login_time + timedelta(minutes=np.random.randint(1, 30))

                    engagement_events.append({
                "user_id": customer["user_id"],
                "event_time": review_time,
                "event_type": "review_current_investment"
            })

    engagement_events_df = pd.DataFrame(engagement_events)

    start_position = end_position
    end_position = start_position + len(engagement_events_df)

    user_ids[start_position:end_position] = (engagement_events_df["user_id"].values)

    event_time[start_position:end_position] = (engagement_events_df["event_time"])

    event_type_ids[start_position:end_position] = [event_type_map.get(event_type)for event_type in engagement_events_df["event_type"]]

    device_types[start_position:end_position] = [device_type_map.get(uid)for uid in engagement_events_df["user_id"]]
    
    #portfolio reviews for low activity users
    low_engagement_events = []


    for _, customer in low_activity_users_sample.iterrows():

    # simulate one month after investment creation
        simulation_start = customer["last_login_time"]

        delta = relativedelta(TODAY, simulation_start)

        months = max(1,delta.years * 12 + delta.months)

        for idx in range(months):

            month_start = (simulation_start + relativedelta(months=idx))

            month_end = (month_start + relativedelta(months=1))

            days_in_month = (month_end - month_start).days

            monthly_logins = np.random.randint(CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_logins"][0],CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_logins"][1] + 1)
            monthly_reviews = np.random.randint(max(1, int(monthly_logins * 0.3)),max(2, int(monthly_logins * 0.7)) + 1)

    # Login events
            login_times = sorted([
            month_start + timedelta(
            days=np.random.randint(0, days_in_month),
            hours=np.random.randint(0, 24),
            minutes=np.random.randint(0, 60)
            )for _ in range(monthly_logins)
        ])

            for login_time in login_times:
                low_engagement_events.append({
                "user_id": customer["user_id"],
                "event_time": login_time,
                "event_type": "app_login"})

    # Portfolio reviews must happen after a login
            if len(login_times) > 0:

                review_login_times = np.random.choice(login_times,size=min(monthly_reviews, len(login_times)),replace=False)

                for login_time in review_login_times:

                    review_time = login_time + timedelta(minutes=np.random.randint(1, 30))

                    low_engagement_events.append({
                    "user_id": customer["user_id"],
                    "event_time": review_time,
                    "event_type": "review_current_investment"})

    low_engagement_events_df = pd.DataFrame(low_engagement_events)

    print("Low Engagement Events:", len(low_engagement_events_df))

    
    start_position = end_position
    end_position = start_position + len(low_engagement_events_df)



    user_ids[start_position:end_position] = (low_engagement_events_df["user_id"].values)

    event_time[start_position:end_position] = (low_engagement_events_df["event_time"])

    event_type_ids[start_position:end_position] = [event_type_map.get(event_type)for event_type in low_engagement_events_df["event_type"]]

    device_types[start_position:end_position] = [device_type_map.get(uid)for uid in low_engagement_events_df["user_id"]]


    # let's simulate new investment creation

    wallet_funding_events = []
    new_investment_events = []
    new_investment_creation = []

    for _, customer in customers_who_have_invested_df.iterrows():

        simulation_start = customer["last_login_time"]

        simulation_end = TODAY

        delta = relativedelta(simulation_end, simulation_start)

        months = max(1, delta.years * 12 + delta.months)

        #print("currently running customer: ",customer["user_id"])

        investment_low_bound = CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["average_investment_amount"][0]
        investment_high_bound = CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["average_investment_amount"][1]

        for idx in range(months):
            
            
            month_start = (simulation_start + relativedelta(months=idx))

            month_end = (month_start + relativedelta(months=1))

            days_in_month = (month_end - month_start).days


            #number of wallet fundings for this month alone
            num_wallet_fundings = np.random.randint(CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_wallet_fundings"][0],CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_wallet_fundings"][1] + 1)

            #how many savings and investment positions will be created this month
            savings_position_creation = np.random.randint(CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_savings_position_creation"][0], CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_savings_position_creation"][1] + 1)

            investment_position_creation = np.random.randint(CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_investment_position_creation"][0], CUSTOMER_BEHAVIOUR_SEGMENT_MAP[customer["customer_behaviour_segment"]]["monthly_investment_position_creation"][1] + 1)

            #now we calculate the number of wallet fundings for this month alone, and for each funding, 
            # we will create a wallet funding event and decide whether it converts into an investment or not. 
            # If it does, we will create a review plan options event, a plan selected event, and a plan created event.
            for _ in range(num_wallet_fundings):

                funding_time = month_start + timedelta(
                days=np.random.randint(1, days_in_month + 1),
                hours=np.random.randint(0, 24),
                minutes=np.random.randint(0, 60))

                funding_amount = np.random.uniform(
                investment_low_bound,
                investment_high_bound
                )

        # Wallet funding event
                wallet_funding_events.append({
                "user_id": customer["user_id"],
                "event_time": funding_time,
                "event_type": "wallet_funded",
                "amount": funding_amount
                })

        # Decide whether funding converts into an investment
                segment = customer["customer_behaviour_segment"]

                makes_investment = np.random.choice([True, False], p=CUSTOMER_BEHAVIOUR_SEGMENT_MAP[segment]["wallet_to_investment_conversion_probability"])

                if not makes_investment:
                    continue

        # Review plans
                review_time = funding_time + timedelta(minutes=np.random.randint(5, 60))

        # Plan selected
                selection_time = review_time + timedelta(minutes=np.random.randint(1, 30))
            
                total_positions = (savings_position_creation + investment_position_creation)

                if total_positions == 0:
                    continue

        # Savings or Investment
                investment_type = np.random.choice(["Savings", "Investment"],p=[savings_position_creation /total_positions,
                investment_position_creation
                /total_positions
            ])

                creation_time = selection_time + timedelta(minutes=np.random.randint(1, 15))

                if investment_type == "Savings":

                    plan_id = np.random.choice(
                    savings_plans["plan_id"],
                    p=savings_plans["plan_weight"] / savings_plans["plan_weight"].sum())

                    event_type = "savings_plan_created"
                else:

                    plan_id = np.random.choice(
                    investment_plans["plan_id"],
                    p=investment_plans["plan_weight"] / investment_plans["plan_weight"].sum())
                    event_type = "investment_plan_created"

                new_investment_events.extend([
            {
                "user_id": customer["user_id"],
                "event_time": review_time,
                "event_type": "review_plan_options"
            },
            {
                "user_id": customer["user_id"],
                "event_time": selection_time,
                "event_type": "plan_selected"
            }
            ])


                new_investment_creation.extend([{
                "user_id": customer["user_id"],
                "event_time": creation_time,
                "event_type": event_type,
                "plan_id": plan_id,
                "amount_invested": funding_amount * 0.95
            }
        ])



    wallet_funding_events_df = pd.DataFrame(wallet_funding_events)
    new_investment_events_df = pd.DataFrame(new_investment_events)

    new_investment_creation_df = pd.DataFrame(new_investment_creation)

    new_investment_creation_df.sort_values(by="event_time",inplace=True)
    wallet_funding_events_df.sort_values(by="event_time",inplace=True)


    #get app logins first
    start_position = end_position
    end_position = start_position + len(wallet_funding_events_df)

    
    user_ids[start_position:end_position] = (wallet_funding_events_df["user_id"].values)

    login_times = wallet_funding_events_df["event_time"] - pd.to_timedelta(5,unit="m")

    event_time[start_position:end_position] = login_times
    event_type_ids[start_position:end_position] = [event_type_map.get("app_login") for _ in range(len(wallet_funding_events_df))]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in wallet_funding_events_df["user_id"]]
    update_last_login_timestamp(conn, user_ids[start_position:end_position], event_time[start_position:end_position])

    #now fund the wallets
    start_position = end_position
    end_position = start_position + len(wallet_funding_events_df)

    
    user_ids[start_position:end_position] = (wallet_funding_events_df["user_id"].values)

    login_times = wallet_funding_events_df["event_time"]

    event_time[start_position:end_position] = login_times
    event_type_ids[start_position:end_position] = [event_type_map.get("wallet_funded") for _ in range(len(wallet_funding_events_df))]
    wallet_ids[start_position:end_position] = [wallet_id_map.get(uid) for uid in wallet_funding_events_df["user_id"].values]
    is_money_movement_activities[start_position:end_position] = True
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + len(wallet_funding_events_df) + 1)
    transaction_type_ids[start_position:end_position] = [transaction_type_map.get("wallet_funding") for _ in range(len(wallet_funding_events_df))]
    last_transaction_id = transaction_ids[start_position:end_position].max()
    amount_invested[start_position:end_position] = wallet_funding_events_df["amount"]
    device_types[start_position:end_position] = [device_type_map.get(uid) for uid in wallet_funding_events_df["user_id"]]
    transaction_amounts[start_position:end_position] = wallet_funding_events_df["amount"]
    transaction_statuses[start_position:end_position] = ["success" for _ in range(len(wallet_funding_events_df))]
    
    #plan selections
    start_position = end_position
    end_position = start_position + len(new_investment_events_df)
    
    user_ids[start_position:end_position] = (new_investment_events_df["user_id"].values)

    event_time[start_position:end_position] = (new_investment_events_df["event_time"])

    event_type_ids[start_position:end_position] = [event_type_map.get(event_type)for event_type in new_investment_events_df["event_type"]]

    device_types[start_position:end_position] = [device_type_map.get(uid)for uid in new_investment_events_df["user_id"]]


    start_position = end_position
    end_position = start_position + len(new_investment_creation_df)

    user_ids[start_position:end_position] = (new_investment_creation_df["user_id"].values)

    event_time[start_position:end_position] = (new_investment_creation_df["event_time"])

    event_type_ids[start_position:end_position] = [event_type_map.get(event_type)for event_type in new_investment_creation_df["event_type"]]

    device_types[start_position:end_position] = [device_type_map.get(uid)for uid in new_investment_creation_df["user_id"]]

    plan_ids[start_position:end_position] = (new_investment_creation_df["plan_id"].values)

    wallet_ids[start_position:end_position] = [wallet_id_map.get(uid) for uid in new_investment_creation_df["user_id"].values]

    amount_invested[start_position:end_position] = (new_investment_creation_df["amount_invested"].values)

    is_money_movement_activities[start_position:end_position] = True
    transaction_ids[start_position:end_position] = np.arange(last_transaction_id + 1, last_transaction_id + len(new_investment_creation_df) + 1)
    transaction_type_ids[start_position:end_position] = [transaction_type_map.get("investment_funding") for _ in range(len(new_investment_creation_df))]
    last_transaction_id = transaction_ids[start_position:end_position].max()
    investment_ids[start_position:end_position] = np.arange(last_investment_id + 1, len(new_investment_creation_df) + last_investment_id + 1)
    last_investment_id = investment_ids[start_position:end_position].max()
    transaction_amounts[start_position:end_position] = new_investment_creation_df["amount_invested"]
    transaction_statuses[start_position:end_position] = ["success" for _ in range(len(new_investment_creation_df))]

    main_df = pd.DataFrame({
        "user_id":user_ids[:end_position],
        "event_type_id":event_type_ids[:end_position],
        "wallet_id":wallet_ids[:end_position],
        "plan_id":plan_ids[:end_position],
        "event_time":event_time[:end_position],
        "investment_id":investment_ids[:end_position],
        "transaction_id":transaction_ids[:end_position],
        "amount_invested":amount_invested[:end_position]
    })

    investments_subset_df = (main_df[~pd.isna(main_df["investment_id"])].copy())

    investment_plans = investments_subset_df["plan_id"]

    investments_subset_df["event_time"] = pd.to_datetime(investments_subset_df["event_time"])

    investments_subset_df["tenure_days"] = [plan_id_map.get(plan) for plan in investment_plans]

    investments_subset_df["tenure_days"] = pd.to_numeric(investments_subset_df["tenure_days"],errors="coerce")

    investments_subset_df["investment_start_date"] = investments_subset_df["event_time"]

    tenure_days_mask = investments_subset_df["tenure_days"].notna()

    investments_subset_df.loc[tenure_days_mask,"investment_maturity_date"] = investments_subset_df.loc[tenure_days_mask,"event_time"] + pd.to_timedelta(investments_subset_df.loc[tenure_days_mask,"tenure_days"], unit = 'D')

    investments_subset_df["investment_status"] = np.select([investments_subset_df["investment_maturity_date"] < pd.Timestamp.today()],
    ["Matured"],default="Active")

    investments_subset_df["investment_start_date_id"] = np.array([int(pd.Timestamp(ts).strftime('%Y%m%d'))for ts in investments_subset_df["investment_start_date"]], dtype=np.int32)

    investments_subset_df.loc[tenure_days_mask,"investment_maturity_date_id"] = np.array([int(pd.Timestamp(ts).strftime('%Y%m%d'))for ts in investments_subset_df.loc[tenure_days_mask,"investment_maturity_date"]], dtype=np.int32)

    plan_id_name_dict = dict(zip(
        plans_data["plan_id"],
        plans_data["plan_name"]
    ))

    cbh_id_map = dict(zip(
        users_data["user_id"],
        users_data["customer_behaviour_segment"]
    ))

    investments_subset_df["plan_name"] = [plan_id_name_dict.get(pid) for pid in investment_plans]

    investments_subset_df["customer_behaviour_segment"] = [cbh_id_map.get(uid) for uid in investments_subset_df["user_id"] ]

    #let's split into vestable invetsments and saleable investments
    vestable_investments_df = investments_subset_df[(investments_subset_df["tenure_days"].notna()) & (investments_subset_df["investment_status"] == "Matured")].copy()

    saleable_investments = investments_subset_df[pd.isna(investments_subset_df["tenure_days"]) & (investments_subset_df["investment_start_date"] <= MUTUAL_FUNDS_CUTOFF_DATE)].copy()

    saleable_investments_df = saleable_investments.sample(frac=0.65,random_state=42)

    active_investments_df = investments_subset_df[(investments_subset_df["tenure_days"].notna()) & (investments_subset_df["investment_status"] == "Active")].copy()


    # simulate early withdrawal requests for vestable investments based on customer behaviour segment probabilities
    vestable_investments_df["requests_early_withdrawal"] = [
        np.random.random()
    <= CUSTOMER_BEHAVIOUR_SEGMENT_MAP[segment]["early_withdrawal_probability"]
    for segment in vestable_investments_df["customer_behaviour_segment"]]

    early_withdrawal_mask = vestable_investments_df["requests_early_withdrawal"] == True
    vested_invested_mask = vestable_investments_df["requests_early_withdrawal"] == False

    vestable_investments_df.loc[early_withdrawal_mask,"investment_status"] = "Withdrawn Early"
    vestable_investments_df.loc[vested_invested_mask,"investment_status"] = np.random.choice(["Matured","Redeemed"], p = [0.25,0.75], size = vested_invested_mask.sum())


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