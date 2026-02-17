import numpy as np
import yfinance as yf
import math

def first_not_nan(lst):
    for x in lst:
        if x is None:
            continue
        # handles float('nan')
        if isinstance(x, float) and math.isnan(x):
            continue
        return x
    return None  # or raise ValueError("No non-NaN values found")


def _last4(ticker, statement, row_name, n=4):
    t = yf.Ticker(ticker)
    df = {
        "income": t.income_stmt,
        "cashflow": t.cashflow,
        "balance": t.balance_sheet
    }[statement]

    return df.loc[row_name].iloc[:n].tolist()

def _rate_calc(target_list, rev_list):
    filtered_target, filtered_rev = [], []

    for i in range(min(len(target_list), len(rev_list))):
        if not (math.isnan(target_list[i]) or math.isnan(rev_list[i])):
            filtered_target.append(target_list[i])
            filtered_rev.append(rev_list[i])

    return abs(
        sum(filtered_target[i] / filtered_rev[i] for i in range(len(filtered_target)))
        / len(filtered_target)
    )

def metrics(ticker="MSFT"):
    company = yf.Ticker(ticker)
    #income_annual = company.income_stmt
    #balance_annual = company.balance_sheet
    #cashflow_annual = company.cashflow


    rev_list = _last4(ticker, "income", "Total Revenue")
    EBITDA_list = _last4(ticker, "income", "EBITDA")
    tax_provision_list = _last4(ticker, "income", "Tax Provision")
    pre_tax_income_list = _last4(ticker, "income", "Pretax Income")
    D_and_A_list = _last4(ticker, "cashflow", "Depreciation And Amortization")
    capex_list = _last4(ticker, "cashflow", "Capital Expenditure")
    delta_work_cap_list = _last4(ticker, "cashflow","Change In Working Capital")
    net_debt_list = _last4(ticker, "balance", "Net Debt") #i dont need all 4 of these
    oustanding_shares_list = _last4(ticker, "balance", "Share Issued") #i dont need all 4 of these
    beta = company.info.get("beta")
    
    rev_growth_rate = 0
    divisor = 0
    for i in range(len(rev_list)):
        if (i < len(rev_list) - 1) and not math.isnan(rev_list[i]) and not math.isnan(rev_list[i + 1]):
            divisor += 1
            rev_growth_rate += 1 - (rev_list[i] / rev_list[i + 1])
            if i == (len(rev_list) - 2):
                rev_growth_rate = abs(rev_growth_rate / divisor)

    EBITDA_margin_rate = _rate_calc(target_list=EBITDA_list, rev_list=rev_list)
    tax_rate = _rate_calc(target_list=tax_provision_list, rev_list=pre_tax_income_list)
    D_and_A_rate = _rate_calc(target_list=D_and_A_list, rev_list=rev_list)
    capex_rate = _rate_calc(target_list=capex_list, rev_list=rev_list)
    delta_work_cap_rate = _rate_calc(target_list=delta_work_cap_list, rev_list=rev_list)

    return {
        "revenue": first_not_nan(rev_list) / 1e+09,
        "beta": beta,
        "net_debt": first_not_nan(net_debt_list) / 1e+09,
        "outstanding_shares": first_not_nan(oustanding_shares_list) / 1e+09,
        "rev_growth_rate": rev_growth_rate,
        "EBITDA_margin_rate": EBITDA_margin_rate,
        "tax_rate": tax_rate,
        "D_and_A_rate": D_and_A_rate,
        "capex_rate": capex_rate,
        "delta_work_cap_rate": delta_work_cap_rate
    }
   

def DF_FCFF(period=10, risk_free=0.04, ERP=0.0417, growth_decay=0.01, terminal=0.025, rev_growth_manual=0.0, capex_rate_manual=0.0, **metrics):
    #all numbers should be in billions
    revenue = metrics["revenue"]
    beta = metrics["beta"]
    net_debt = metrics["net_debt"]
    oustanding_shares = metrics["outstanding_shares"]
    rev_growth_rate = metrics["rev_growth_rate"]
    if rev_growth_manual != 0.0: rev_growth_rate = rev_growth_manual
    EBITDA_margin_path = metrics["EBITDA_margin_rate"]
    tax_rate = metrics["tax_rate"]
    D_and_A_rate = metrics["D_and_A_rate"]
    capex_rate = metrics["capex_rate"]
    if capex_rate_manual != 0.0: capex_rate = capex_rate_manual
    delta_work_cap_rate = metrics["delta_work_cap_rate"]

    discount_rate = risk_free + (beta*ERP)

    period_PV = 0
    terminal_PV = 0

    curr = revenue

    for i in range(period):
        if (rev_growth_rate - growth_decay) > terminal: 
            rev_growth_rate = rev_growth_rate - growth_decay

        curr = curr*(1 + rev_growth_rate)
        EBIDTA_curr = curr * EBITDA_margin_path
        D_and_A_curr = curr * D_and_A_rate
        capex_curr = curr * capex_rate
        delta_work_cap_curr = curr * delta_work_cap_rate
        EBIDt = EBIDTA_curr - D_and_A_curr
        FCFF_curr = EBIDt*(1-tax_rate) + D_and_A_curr - capex_curr - delta_work_cap_curr
        period_PV += FCFF_curr / (1 + discount_rate)**(i + 1)
        # Terminal at end of year N (period)
        if i == period - 1:
            FCFF_period_plus_one = FCFF_curr * (1 + terminal)  # simplest: grow last FCFF by terminal g
            TV_period = FCFF_period_plus_one / (discount_rate - terminal)

            # FIX #2: discount TV by (1+r)^N, not (1+r)^(N+1)
            terminal_PV = TV_period / (1 + discount_rate) ** period
  
    Estimated_EV = period_PV + terminal_PV

    if math.isnan(net_debt):
        equity = Estimated_EV
    else:
        equity = Estimated_EV - net_debt

    fair_value = equity / oustanding_shares

    return fair_value



print("MICROSOFT FAIR VALUE:")
MSFT_metrics = metrics(ticker="MSFT")
Microsoft = DF_FCFF(growth_decay=0.01, terminal=0.04, rev_growth_manual=0.18, **MSFT_metrics)
print(Microsoft)
print('\n')

print("INTUIT FAIR VALUE:")
INTU_metrics = metrics(ticker="INTU")

intuit = DF_FCFF(terminal=0.03, rev_growth_manual=0.16, **INTU_metrics)
print(intuit)
print('\n')

print("SAP FAIR VALUE:")
SAP_metrics = metrics(ticker="SAP")

sap = DF_FCFF(rev_growth_manual=0.12, **SAP_metrics)
print(sap)
print('\n')

print("ServiceNow FAIR VALUE:")
NOW_metrics = metrics(ticker="NOW")

servicenow = DF_FCFF(terminal=0.03, **NOW_metrics)
print(servicenow)
print('\n')

print("Google FAIR VALUE:")
HUBS_metrics = metrics(ticker="GOOGL")
print(HUBS_metrics)
hubspot = DF_FCFF(terminal=0.03, **HUBS_metrics)
print(hubspot)
print('\n')

print("Amazon FAIR VALUE:")
AMZN_metrics = metrics(ticker="AMZN")
print(AMZN_metrics)
amazon = DF_FCFF(terminal=0.03, rev_growth_manual=0.17, capex_rate_manual=0.08, **AMZN_metrics)
print(amazon)
print('\n')

print("NVIDIA FAIR VALUE:")
NVDA_metrics = metrics(ticker="NVDA")
print(NVDA_metrics)
nvidia = DF_FCFF(terminal=0.03, **NVDA_metrics)
print(nvidia)
print('\n')

print("McDonalds FAIR VALUE:")
MCD_metrics = metrics(ticker="MCD")
print(MCD_metrics)
mcdonalds = DF_FCFF(**MCD_metrics)
print(mcdonalds)
print('\n')



'''
revenue=19.43, tax_rate=0.205, D_and_A_rate=0.042, capex_rate=0.006, delta_work_cap_rate = 0.015,
        period=10, rev_growth_rate=0.15, EBITDA_margin_path=0.29, terminal=0.025, risk_free=0.04, beta=1.065, ERP=0.05,
        net_debt=3.089, oustanding_shares=0.278,
        growth_decay=0.01


revenue=305.453
tax_rate=0.186
D_and_A_rate=0.128
capex_rate=0.272
delta_work_cap_rate = 0.0147
period=10
rev_growth_rate=0.16
EBITDA_margin_path=0.615
terminal=0.035
risk_free=0.04
beta=1.019
ERP=0.05
net_debt=12.9
oustanding_shares=7.46
growth_decay=0.005
'''