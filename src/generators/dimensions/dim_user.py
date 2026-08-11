import numpy as np
import pandas as pd
import faker as fk
import re
from src.config.constants import (CUSTOMER_PERSONA_MAP, EMAIL_DOMAIN, GENDER, GENDER_WEIGHTS, ACQUISITION_CHANNELS,
                                  CHANNEL_WEIGHTS, IS_ACTIVATED_USER, CUSTOMER_BEHAVIOUR_SEGMENT, 
                                  CUSTOMER_BEHAVIOUR_SEGMENT_MAP, DEVICE_TYPES
                                  )
from src.config.paths import (DDL_DIM_USER_PATH, USERS_PARQUET_PATH)
from src.logic.location_distribution import get_location_distribution
from src.logic.persona_age_income_distribution import get_age_persona_income_distribution
from src.logic.signup_distribution import get_signup_distribution


def generate_users(conn, num_of_users):
    #read the DDL SQL file and execute it to create the dim_user table
    create_db = DDL_DIM_USER_PATH.read_text()

    conn.execute(create_db)

    #generate fake user data using faker library
    fake_gb = fk.Faker('en_GB')
    fake_ie = fk.Faker('en_IE')

    #user_id = np.arange(1, num_of_users + 1)
    gender = np.random.choice(GENDER, num_of_users, p=GENDER_WEIGHTS)
    customer_first_names = np.empty(num_of_users, dtype=object)
    customer_last_names = np.empty(num_of_users, dtype=object)

    location_data = get_location_distribution(num_of_users)
    regions = location_data['regions']
    cities = location_data['cities']
    countries = location_data['countries']
    
    uk_male_customers = np.where((gender == 'Male') & (countries == 'UK'))[0]
    uk_female_customers = np.where((gender == 'Female') & (countries == 'UK'))[0]
    uk_other_customers = np.where((gender == 'Other') & (countries == 'UK'))[0]
    ie_male_customers = np.where((gender == 'Male') & (countries == 'Ireland'))[0]
    ie_female_customers = np.where((gender == 'Female') & (countries == 'Ireland'))[0]
    ie_other_customers = np.where((gender == 'Other') & (countries == 'Ireland'))[0]

    #male names assignment based on nationality
    customer_first_names[uk_male_customers] = [fake_gb.first_name_male() for _ in range(len(uk_male_customers))]
    customer_last_names[uk_male_customers] = [fake_gb.last_name_male() for _ in range(len(uk_male_customers))]
    customer_first_names[ie_male_customers] = [fake_ie.first_name_male() for _ in range(len(ie_male_customers))]
    customer_last_names[ie_male_customers] = [fake_ie.last_name_male() for _ in range(len(ie_male_customers))]

    #female names assignment based on nationality
    customer_first_names[uk_female_customers] = [fake_gb.first_name_female() for _ in range(len(uk_female_customers))]
    customer_last_names[uk_female_customers] = [fake_gb.last_name_female() for _ in range(len(uk_female_customers))]
    customer_first_names[ie_female_customers] = [fake_ie.first_name_female() for _ in range(len(ie_female_customers))]
    customer_last_names[ie_female_customers] = [fake_ie.last_name_female() for _ in range(len(ie_female_customers))]

    #other names assignment based on nationality
    customer_first_names[uk_other_customers] = [fake_gb.first_name_nonbinary() for _ in range(len(uk_other_customers))]
    customer_last_names[uk_other_customers] = [fake_gb.last_name_nonbinary() for _ in range(len(uk_other_customers))]
    customer_first_names[ie_other_customers] = [fake_ie.first_name_nonbinary() for _ in range(len(ie_other_customers))]
    customer_last_names[ie_other_customers] = [fake_ie.last_name_nonbinary() for _ in range(len(ie_other_customers))]


    first_name = np.array([re.sub(r'[^a-z]', '', name.lower())
                                for name in customer_first_names])
    last_name = np.array([re.sub(r'[^a-z]', '', name.lower())
                               for name in customer_last_names])
    email_ids = np.empty(num_of_users, dtype=object)
    email_domains = np.random.choice(EMAIL_DOMAIN, num_of_users)
    random_suffix = np.arange(
    1,
    num_of_users + 1
)
    email_ids = [f"{first_name[i].lower()}.{last_name[i].lower()}{random_suffix[i]}{email_domains[i]}" for i in range(num_of_users)]

    

    demographics = get_age_persona_income_distribution(num_of_users)

    customer_personas = np.array(demographics['persona'])

    reported_annual_incomes = np.array(demographics['income'])

    is_activated_user = np.array(demographics['is_activated_user'])


    wallet_activation_timeframe = np.array(demographics['wallet_activation_timeframe'])


    acquisition_channels = [np.random.choice(ACQUISITION_CHANNELS, p = CUSTOMER_PERSONA_MAP[cp]['acquisition_channels_weights']) for cp in customer_personas]

    kyc_completed = np.full(num_of_users, False) #initialize with False, will update to True for users who completed KYC
    active_mask = is_activated_user == True
    inactive_mask = is_activated_user == False
    kyc_completed[active_mask] = True #assuming all activated users completed KYC, this will set kyc_completed to True for those users
    kyc_completed[~active_mask] = np.random.choice([True, False], size=(~active_mask).sum(), p=[0.3, 0.7])
    
    date_of_birth = np.array(demographics['birth_date'])
    signup_date = get_signup_distribution(date_of_birth)
    birth_date_id = [int(pd.Timestamp(date_of_birth[i]).strftime('%Y%m%d')) for i in range(num_of_users)]
    signup_date_id = [int(pd.Timestamp(signup_date[i]).strftime('%Y%m%d')) for i in range(num_of_users)]

    customer_behaviour_segment = [np.random.choice(CUSTOMER_BEHAVIOUR_SEGMENT, p = CUSTOMER_PERSONA_MAP[cp]['customer_behavioural_segment'])for cp in customer_personas]
    device_types = [np.random.choice(DEVICE_TYPES, p = CUSTOMER_BEHAVIOUR_SEGMENT_MAP[bh]["device_type"]) for bh in customer_behaviour_segment]

    is_immediate_login = np.empty(num_of_users, dtype=bool)

    is_immediate_login[active_mask] = np.random.choice([True, False], size=active_mask.sum(), p=[1, 0])
    is_immediate_login[inactive_mask] = np.random.choice([True, False], size=(~active_mask).sum(), p=[0.7, 0.3])

    supposed_activation_dates = np.empty(num_of_users,dtype=object)

    signup_date = pd.to_datetime(signup_date)

    supposed_activation_dates[active_mask] = signup_date[active_mask] + pd.to_timedelta(wallet_activation_timeframe[active_mask],unit="m")

    kyc_completion_timeframe = np.empty(num_of_users, dtype=object)
    kyc_completion_dates = np.empty(num_of_users, dtype=object)

    kyc_completed_mask = (kyc_completed == True) & (is_activated_user == False)

    kyc_completion_timeframe[active_mask] = [np.random.randint(120,  activation_timeframe - 100) for activation_timeframe in wallet_activation_timeframe[active_mask]]
    kyc_completion_dates[active_mask] = signup_date[active_mask] + pd.to_timedelta(kyc_completion_timeframe[active_mask],unit="m")

    kyc_completion_timeframe[kyc_completed_mask] = [np.random.randint(120,  800) for _ in range(kyc_completed_mask.sum())]
    kyc_completion_dates[kyc_completed_mask] = signup_date[kyc_completed_mask] + pd.to_timedelta(kyc_completion_timeframe[kyc_completed_mask],unit="m")

    last_login_at = signup_date
    created_at = signup_date
    last_updated_at = signup_date
    

    df_raw = pd.DataFrame({
        'first_name': customer_first_names,
        'last_name': customer_last_names,
        'country': countries,
        'region': regions,
        'city': cities,
        'email_address': email_ids,
        'reported_annual_income':reported_annual_incomes,
        'acquisition_channel':acquisition_channels,
        'device_type':device_types,
        'customer_persona':customer_personas,
        'kyc_completed': kyc_completed,
        'date_of_birth': date_of_birth,
        'birth_date_id': birth_date_id,
        'signup_date': signup_date,
        'signup_date_id': signup_date_id,
        'is_activated_user': is_activated_user,
        'wallet_activation_timeframe': wallet_activation_timeframe,
        'customer_behaviour_segment':customer_behaviour_segment,
        'is_immediate_login': is_immediate_login,
        'supposed_activation_date':supposed_activation_dates,
        'kyc_completion_date': kyc_completion_dates,
        'last_login_at': last_login_at,
        'created_at': created_at,
        'last_updated_at': last_updated_at
    })

    df_raw = df_raw.sort_values(
    by='signup_date'
    ).reset_index(drop=True)

    df_raw['user_id'] = np.arange(
    1,
    len(df_raw) + 1
    )

    df_raw = df_raw[[
    'user_id',
    'first_name',
    'last_name',
    'country',
    'region',
    'city',
    'email_address',
    'reported_annual_income',
    'acquisition_channel',
    'device_type',
    'customer_persona',
    'kyc_completed',
    'date_of_birth',
    'birth_date_id',
    'signup_date',
    'signup_date_id',
    'is_activated_user',
    'wallet_activation_timeframe',
    'customer_behaviour_segment',
    'is_immediate_login',
    'supposed_activation_date',
    'kyc_completion_date',
    'last_login_at',
    'created_at',
    'last_updated_at'
]]

    #write the generated data to a parquet file
    conn.register('df_raw', df_raw)
    conn.execute('''INSERT INTO dim_user SELECT * FROM df_raw''')

    conn.execute(f'''COPY (
                        SELECT user_id, first_name, last_name, country, region, city, email_address, reported_annual_income,
                        acquisition_channel, device_type, customer_persona, kyc_completed, date_of_birth, birth_date_id, signup_date, signup_date_id, 
                        customer_behaviour_segment, last_login_at, created_at, last_updated_at
                        from dim_user )
                 TO '{USERS_PARQUET_PATH}' (FORMAT PARQUET) ''')

