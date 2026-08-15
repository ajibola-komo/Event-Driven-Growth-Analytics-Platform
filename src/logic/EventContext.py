from dataclasses import dataclass

@dataclass
class EventContext:
    signup_completed_event_type_id: int
    app_login_event_type_id: int
    kyc_completed_event_type_id: int
    wallet_funded_event_type_id:int
    review_plan_options_event_type_id:int
    plan_selected_event_type_id:int
    savings_plan_created_event_type_id:int
    investment_plan_created_event_type_id:int
    review_current_investment_event_type_id:int
    request_early_withdrawal_event_type_id: int
    investment_vests_event_type_id:int
    investment_proceeds_wallet_transfer_event_type_id:int
    wallet_withdrawal_event_type_id:int
    assets_sale_event_type_id:int
    wallet_funding_failed_event_type_id:int
    withdrawal_failed_event_type_id:int

    wallet_funding_transaction_type_id: int
    wallet_withdrawal_transaction_type_id: int
    investment_funding_transaction_type_id: int
    investment_proceeds_transfer_transaction_type_id: int


def load_event_context(conn):


    event_types = dict(conn.execute(''' SELECT event_type_code, event_type_id from dim_event_type ''').fetchall())

    transaction_types = dict(conn.execute(''' SELECT transaction_type_id, transaction_type_code from dim_transaction_type ''').fetchall())

    try:
        return EventContext(
           signup_completed_event_type_id =  event_types["signup_completed"],
           app_login_event_type_id = event_types["app_login"],
           kyc_completed_event_type_id = event_types["kyc_completed"],
           wallet_funded_event_type_id=event_types["wallet_funded"],
           review_plan_options_event_type_id=event_types["review_plan_options"],
           plan_selected_event_type_id=event_types["plan_selected"],
           savings_plan_created_event_type_id=event_types["savings_plan_created"],
           investment_plan_created_event_type_id=event_types["investment_plan_created"],
           review_current_investment_event_type_id=event_types["review_current_investment"],
           request_early_withdrawal_event_type_id=event_types["request_early_withdrawal"],
           investment_vests_event_type_id=event_types["investment_vests"],
           investment_proceeds_wallet_transfer_event_type_id=event_types["investment_proceeds_wallet_transfer"],
           wallet_withdrawal_event_type_id=event_types["wallet_withdrawal"],
           assets_sale_event_type_id=event_types["assets_sale"],
           wallet_funding_failed_event_type_id=event_types["wallet_funding_failed"],
           withdrawal_failed_event_type_id=event_types["withdrawal_failed"],

           wallet_funding_transaction_type_id=transaction_types["wallet_funding"],
           wallet_withdrawal_transaction_type_id=transaction_types["wallet_withdrawal"],
           investment_funding_transaction_type_id=transaction_types["investment_funding"],
           investment_proceeds_transfer_transaction_type_id=transaction_types["investment_proceeds_transfer"],

    )
    except KeyError as e:
        raise ValueError(f"Missing lookup value in dimension table: {e.args[0]}")