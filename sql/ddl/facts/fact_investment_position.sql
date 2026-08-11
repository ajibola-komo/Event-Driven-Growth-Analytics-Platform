CREATE OR REPLACE TABLE FACT_INVESTMENT_POSITION(
    investment_id bigint PRIMARY KEY,
    user_id bigint NOT NULL,
    wallet_id bigint NOT NULL,
    plan_id int NOT NULL,
    amount_invested decimal(18,2) NOT NULL,
    expected_maturity_value decimal(18,2), --Nullable for Mutual Funds
    investment_start_date timestamp NOT NULL,
    investment_start_date_id int NOT NULL,
    investment_maturity_date timestamp,
    investment_maturity_date_id int,
    investment_status varchar(20) NOT NULL,
    is_withdrawn_early boolean NOT NULL DEFAULT false,
    penalty_amount decimal(18,2),
    amount_paid_out decimal(18,2), -- Not populated until the investment is redeemed
    early_withdrawal_date timestamp,
    early_withdrawal_date_id int,
    created_at timestamp not null,
    last_updated_at timestamp not null,
    foreign key(user_id) references dim_user(user_id),
    foreign key(wallet_id) references dim_wallet(wallet_id),
    foreign key(plan_id) references dim_plan(plan_id),
    foreign key(investment_start_date_id) references dim_date(date_id),
    foreign key(investment_maturity_date_id) references dim_date(date_id),
    foreign key(early_withdrawal_date_id) references dim_date(date_id),
    check(amount_invested > 0),
    check (investment_status in ('Active', 'Redeemed', 'Matured', 'Withdrawn_Early'))
);