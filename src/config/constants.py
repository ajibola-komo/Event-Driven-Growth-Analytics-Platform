from datetime import date, datetime, time, timedelta, timezone
import pandas as pd


TIMEZONE = "UTC"

TODAY = pd.Timestamp.today()

CURRENT_DATE = TODAY.date()

# Signup range
DEFAULT_SIGNUP_START_DATE = date(2016, 1, 1)
DEFAULT_SIGNUP_END_DATE = TODAY - timedelta(days=1)

DEFAULT_SIGNUP_START_TIMESTAMP = datetime.combine(DEFAULT_SIGNUP_START_DATE, time.min, tzinfo=timezone.utc)
DEFAULT_SIGNUP_END_TIMESTAMP = datetime.combine(DEFAULT_SIGNUP_END_DATE, time.max, tzinfo=timezone.utc)

# Transaction range
CURRENT_YEAR = TODAY.year
CURRENT_MONTH = TODAY.month

DEFAULT_TRANSACTION_START_DATE = date(CURRENT_YEAR - 3, 1, 1)
DEFAULT_TRANSACTION_END_DATE = TODAY - timedelta(days=1)

DEFAULT_TRANSACTION_START_TIMESTAMP = datetime.combine(DEFAULT_TRANSACTION_START_DATE, time.min, tzinfo=timezone.utc)
DEFAULT_TRANSACTION_END_TIMESTAMP = datetime.combine(DEFAULT_TRANSACTION_END_DATE, time.max, tzinfo=timezone.utc)


#dim_user constants
EMAIL_DOMAIN = ["@example.com","abc.com","xyz.com","test.com","demo.com"]
GENDER = ["Male", "Female", "Other"]
GENDER_WEIGHTS = [0.48, 0.48, 0.04]  # Assuming a distribution of 48%

LOCATION_MAP = {
    "UK": {
        "regions": {"Greater London":{
            "region_weight": 0.3,  # Assuming 30% of UK users are from Greater London
            "cities": ["London"],
            "weights": [1.0]  # Assuming all users in Greater London are from London
        }, 
        "Wales": {
            "region_weight": 0.15,
            "cities": ["Cardiff", "Swansea", "Newport"],
            "weights": [0.5, 0.3, 0.2]
        },
        "Scotland": {
            "region_weight": 0.15,
            "cities": ["Edinburgh", "Glasgow", "Aberdeen"],
            "weights": [0.4, 0.4, 0.2]
        },
        "North West": {
            "region_weight": 0.1,
            "cities": ["Manchester", "Liverpool", "Chester"],
            "weights": [0.5, 0.3, 0.2]
        },
        "South East": {
            "region_weight": 0.1,
            "cities": ["Brighton", "Reading", "Southampton"],
            "weights": [0.4, 0.35, 0.25]
        },
        "Midlands": {
            "region_weight": 0.2,
            "cities": ["Birmingham", "Coventry", "Leicester", "Nottingham"],
            "weights": [0.45, 0.2, 0.2, 0.15]
        }
    }},
    "Ireland": {
        "regions": {"Dublin Region":{
            "region_weight": 0.4,  # Assuming 40% of Ireland users are from Dublin Region   
            "cities": ["Dublin"],
            "weights": [1.0]  # Assuming all users in Dublin Region are from Dublin
        }, "Rest of Ireland": {
            "region_weight": 0.6,
            "cities": ["Cork", "Galway", "Limerick", "Waterford"],
            "weights": [0.4, 0.25, 0.2, 0.15]
        }}
    }
}

COUNTRIES_LIST = ["UK", "Ireland"]
COUNTRIES_WEIGHTS = [0.8, 0.2]  # Assuming 80% of users are from the UK and 20% from Ireland
AGE_BUCKETS = ["18-24", "25-34", "35-44", "45-54", "55-65"]
AGE_WEIGHTS = [0.20, 0.35, 0.25, 0.15, 0.05]
CUSTOMER_BEHAVIOUR_SEGMENT = [
    'High_Engagement_High_Balance',
    'High_Engagement_Low_Balance',
    'Moderate_Engagement_High_Balance',
    'Moderate_Engagement_Low_Balance',
    'Low_Engagement_High_Balance',
    'Low_Engagement_Low_Balance'
]

DEVICE_TYPES = ["ios","android"]

CUSTOMER_PERSONA_MAP = {
    'Starter Investor':{
        'age_range':[18,31],
        'income_range':[18000,50000],
        'wallet_activation_weight':[0.25,0.75], #25% activate wallet immediately, 75% delay activation
        'mins_to_first_funding':[25920,36000] ,#between 18 and 25 days
        'acquisition_channels_weights': [0.15,0.4,0.2,0.05,0.1,0.1], #higher weight on paid social and referral program
        'customer_behavioural_segment':[0.02,0.55, 0.03, 0.2,0, 0.2]
    },
    'Goal-Oriented Saver':{
        'age_range':[25,56],
        'income_range':[25000,90000],
        'wallet_activation_weight':[0.45,0.55],
        'mins_to_first_funding':[14400,21600], #between 10 and 15 days
        'acquisition_channels_weights': [0.3,0.15,0.2,0.15,0.1,0.1],
        'customer_behavioural_segment':[0.03,0.15, 0.1, 0.45,0.07, 0.2]
    },
    'Wealth Builder':{
        'age_range':[25,61],
        'income_range':[40000,150000],
        'wallet_activation_weight':[0.7,0.3],
        'mins_to_first_funding':[4320,10080], #between 3 and 7 days
        'acquisition_channels_weights': [0.25,0.1,0.2,0.2,0.1,0.15],
        'customer_behavioural_segment':[0.2,0.05, 0.45, 0.1,0.15, 0.05]
    },
    'Active Investor':{
        'age_range':[25,66],
        'income_range':[60000,120000],
        'wallet_activation_weight':[0.85,0.15],
        'mins_to_first_funding':[1440,4320], #between 1 and 3 days
        'acquisition_channels_weights': [0.2,0.1,0.15,0.3,0.15,0.1],
        'customer_behavioural_segment':[0.7,0.05, 0.15, 0.05,0.05, 0]
    },
    'Capital Preserver':{
        'age_range':[45,66],
        'income_range':[70000,150000],
        'wallet_activation_weight':[0.5,0.5],
        'mins_to_first_funding':[10080,20160], #between 7 and 14 days
        'acquisition_channels_weights': [0.3,0.05,0.25,0.25,0.05,0.1],
        'customer_behavioural_segment':[0.05,0, 0.35, 0,0.6, 0]
    }
}
CUSTOMER_PERSONAS = list(CUSTOMER_PERSONA_MAP.keys()) 
CUSTOMER_PERSONA_WEIGHTS = [0.25,0.3,0.25,0.1,0.1]
IS_ACTIVATED_USER = [True, False]

ACQUISITION_CHANNELS = ['Organic Search','Paid Social','Referral Program','Direct Traffic','Paid Search','Partnerships']
CHANNEL_WEIGHTS = [0.25,0.2,0.2,0.15,0.1,0.1]



#events simulation
POST_SIGN_UP_IMMEDIATE_LOGINS = 0.45
POST_SIGN_UP_SAME_DAY_LOGINS = 0.25
POST_SIGN_UP_DELAYED_LOGINS = 0.3

KYC_ACTIVATION_TIMEFRAME = [1440, 10080]  # minutes - between 1 and 7 days

IMMEDIATE_LOGINS_TIME_FRAME = [60,300] #seconds
SAME_DAY_LOGINS_TIME_FRAME = [18000,86400] #seconds
DELAYED_LOGINS_TIME_FRAME = [86400,604800] #seconds
UNACTIVATED_USERS_TIME_FRAME = [600,1209600] #seconds
WALLET_ACTIVATION_SUBSET = 0.6
IMMEDIATE_ACTIVATION_SUBSET = 0.2

IMMEDIATE_WALLET_ACTIVATION_TIME_FRAME = [600,3600] #seconds - between 10 minutes and 1 hour
DELAYED_WALLET_ACTIVATION_LOGIN_TIME_FRAME = [3600,10080] #seconds - between 1 hour and 7 days
DELAYED_WALLET_ACTIVATION_TIME_FRAME = [600,3600] #seconds - between 10 minutes and 1 hour

#fact investment position
INVESTMENT_RISK_PROFILE = ['Low','Medium','High']

FIRST_INVESTMENT_TYPE = ['Savings','Investments']

CUSTOMER_BEHAVIOUR_SEGMENT_MAP = {

    'High_Engagement_High_Balance':{
        'monthly_logins':[20,40],
        'monthly_wallet_fundings':[2,5],
        'average_investment_amount': [5000,50000],
        'monthly_investment_position_creation':[0,3],
        'retention_probability':0.95,
        'early_withdrawal_probability':0.05,
        'avg_wallet_balance_multiplier':2.5,
        'wallet_to_investment_conversion_probability':[0.95,0.05], #95% chance they make an investment after funding their wallet, 5% chance they don't make an investment
        'mins_to_first_investment':[1440,14400], #between 1 and 10 days after wallet funding
        'first_investment_type_probability':[0.7,0.3], #70% chance their first investment is a savings product, 30% chance it's an investment product
        'device_type':[0.65,0.35],
        'investment_type_probability':[0.2,0.8],
        'investment_percentage':[0.7,0.95]
    },

    'High_Engagement_Low_Balance':{
        'monthly_logins':[15,30],
        'monthly_wallet_fundings':[1,4],
        'average_investment_amount':[250,5000],
        'monthly_investment_position_creation':[0,3],
        'retention_probability':0.85,
        'early_withdrawal_probability':0.15,
        'avg_wallet_balance_multiplier':0.5,
        'wallet_to_investment_conversion_probability':[0.85,0.15], #85% chance they make an investment after funding their wallet, 15% chance they don't make an investment
        'mins_to_first_investment':[4320,14400], #between 3 and 10 days after wallet funding
        'first_investment_type_probability':[0.6,0.4], #60% chance their first investment is a savings product, 40% chance it's an investment product
        'device_type':[0.3,0.7],
        'investment_type_probability':[0.2,0.8],
        'investment_percentage':[0.6,0.85]
    },

    'Moderate_Engagement_High_Balance':{
        'monthly_logins':[8,15],
        'monthly_wallet_fundings':[1,3],
        'average_investment_amount':[2500,25000],
        'monthly_investment_position_creation':[0,2],
        'retention_probability':0.92,
        'early_withdrawal_probability':0.08,
        'avg_wallet_balance_multiplier':2.0,
        'wallet_to_investment_conversion_probability':[0.9,0.1], #90% chance they make an investment after funding their wallet, 10% chance they don't make an investment
        'mins_to_first_investment':[10080,30240], #between 7 and 21 days after wallet funding
        'first_investment_type_probability':[0.5,0.5], #50% chance their first investment is a savings product, 50% chance it's an investment product
        'device_type':[0.6,0.4],
        'investment_type_probability':[0.5,0.5],
        'investment_percentage':[0.6,0.85]
    },

    'Moderate_Engagement_Low_Balance':{
        'monthly_logins':[4,10],
        'monthly_wallet_fundings':[0,2],
        'average_investment_amount':[100,2500],
        'monthly_investment_position_creation':[0,2],
        'retention_probability':0.75,
        'early_withdrawal_probability':0.20,
        'avg_wallet_balance_multiplier':0.7,
        'wallet_to_investment_conversion_probability':[0.75,0.25], #75% chance they make an investment after funding their wallet, 25% chance they don't make an investment
        'mins_to_first_investment':[10080,20160], #between 7 and 14 days after wallet funding
        'first_investment_type_probability':[0.6,0.4], #40% chance their first investment is a savings product, 60% chance it's an investment product
        'device_type':[0.25,0.75],
        'investment_type_probability':[0.5,0.5],
        'investment_percentage':[0.5,0.75]
    },

    'Low_Engagement_High_Balance':{
        'monthly_logins':[1,3],
        'monthly_wallet_fundings':[0,1],
        'average_investment_amount':[10000,100000],
        'monthly_investment_position_creation':[0,3],
        'retention_probability':0.90,
        'early_withdrawal_probability':0.10,
        'avg_wallet_balance_multiplier':3.0,
        'wallet_to_investment_conversion_probability':[0.9,0.1], #90% chance they make an investment after funding their wallet, 10% chance they don't make an investment
        'mins_to_first_investment':[20160,43200], #between 14 and 30 days after wallet funding
        'first_investment_type_probability':[0.3,0.7], #30% chance their first investment is a savings product, 70% chance it's an investment product
        'device_type':[0.55,0.45],
        'investment_type_probability':[0.5,0.5],
        'investment_percentage':[0.7,0.9]
    },

    'Low_Engagement_Low_Balance':{
        'monthly_logins':[0,2],
        'monthly_wallet_fundings':[0,1],
        'average_investment_amount':[50,1000],
        'monthly_investment_position_creation':[0,2],
        'retention_probability':0.50,
        'early_withdrawal_probability':0.30,
        'avg_wallet_balance_multiplier':0.3,
        'wallet_to_investment_conversion_probability':[0.5,0.5], #50% chance they make an investment after funding their wallet, 50% chance they don't make an investment
        'mins_to_first_investment':[43200,64800], #between 14 and 45 days after wallet funding
        'first_investment_type_probability':[0.8,0.2], #20% chance their first investment is a savings product, 80% chance it's an investment product
        'device_type':[0.2,0.8],
        'investment_type_probability':[0.5,0.5],
        'investment_percentage':[0.5,0.7]
    }
}

USERS_MAKES_FIRST_INVESTMENT_AFTER_FUNDING = [True,False]

EARLY_WITHDRAWAL_BEHAVIOUR = {
    "flex_save": {
        "left": 1,
        "mode": 15,
        "right": 30
    },
    "fixed_save": {
        "left": 1,
        "mode": 30,
        "right": 60
    },
    "treasury_bills": {
        "left": 1,
        "mode": 45,
        "right": 90
    }
}

INVESTMENT_WITHDRAWAL_PROCESSING_TIME = 1440

MUTUAL_FUNDS_CUTOFF_DATE = TODAY - pd.to_timedelta(90,unit="D")

AMOUNT_INCREMENT = 50





