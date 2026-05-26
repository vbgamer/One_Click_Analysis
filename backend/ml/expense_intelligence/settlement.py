from __future__ import annotations

from collections import defaultdict

import pandas as pd


def optimize_settlements(df: pd.DataFrame) -> dict:
    """
    Minimize group settlement transactions from payer/participant-like data.

    If no participant column exists, this still returns payer contribution
    balances as a diagnostic rather than inventing fake split obligations.
    """
    if "payer" not in df or "amount" not in df:
        return {"status": "insufficient_data", "transactions": [], "message": "Need payer and amount fields."}

    paid = df.groupby("payer")["amount"].sum().to_dict()
    participants = sorted([p for p in paid.keys() if p and p != "unknown"])
    if len(participants) < 2:
        return {
            "status": "insufficient_group_data",
            "transactions": [],
            "balances": paid,
            "message": "At least two payers are needed for settlement optimization.",
        }

    total = sum(paid.values())
    fair_share = total / len(participants)
    balances = {p: round(paid.get(p, 0) - fair_share, 2) for p in participants}

    creditors = [[p, amt] for p, amt in balances.items() if amt > 0.01]
    debtors = [[p, -amt] for p, amt in balances.items() if amt < -0.01]
    transactions = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor, owes = debtors[i]
        creditor, gets = creditors[j]
        amount = round(min(owes, gets), 2)
        transactions.append({"from": debtor, "to": creditor, "amount": amount})
        debtors[i][1] = round(owes - amount, 2)
        creditors[j][1] = round(gets - amount, 2)
        if debtors[i][1] <= 0.01:
            i += 1
        if creditors[j][1] <= 0.01:
            j += 1

    return {
        "status": "ok",
        "total_group_spend": round(total, 2),
        "fair_share": round(fair_share, 2),
        "balances": balances,
        "transactions": transactions,
        "optimization": "Greedy net-balance minimization; transaction count is at most debtors + creditors - 1.",
    }
