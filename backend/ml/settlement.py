"""
settlement.py — Settlement optimisation engine for Expense Intelligence System.

Functions
---------
optimize_settlement          : Minimum-cash-flow settlement algorithm.
build_payer_network          : Build a relationship graph of payers.
compute_contribution_fairness : Fairness metrics per payer.
"""

import json

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Optional: networkx
# ---------------------------------------------------------------------------
try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    _NX_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_col(df: pd.DataFrame, schema: dict, key: str) -> str | None:
    col = schema.get(key)
    return col if col and col in df.columns else None


def _min_cash_flow(balances: dict) -> list:
    """Greedy minimum-transactions settlement algorithm.

    Finds the minimum number of transactions to zero-out all balances.
    Positive balance = owed money; negative = owes money.

    Parameters
    ----------
    balances : dict
        {person: net_amount} (positive = creditor, negative = debtor).

    Returns
    -------
    list of dict
        Each entry: {payer, payee, amount}.
    """
    transactions: list = []
    debtors = sorted(
        [(p, -b) for p, b in balances.items() if b < -0.001],
        key=lambda x: -x[1],
    )
    creditors = sorted(
        [(p, b) for p, b in balances.items() if b > 0.001],
        key=lambda x: -x[1],
    )

    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor, debt = debtors[i]
        creditor, credit = creditors[j]
        settle = round(min(debt, credit), 2)
        transactions.append({"payer": debtor, "payee": creditor, "amount": settle})
        debt -= settle
        credit -= settle
        debtors[i] = (debtor, debt)
        creditors[j] = (creditor, credit)
        if debt < 0.001:
            i += 1
        if credit < 0.001:
            j += 1

    return transactions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def optimize_settlement(df: pd.DataFrame, schema: dict) -> dict:
    """Compute optimal settlement plan using minimum-cash-flow algorithm.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``balances``, ``optimal_transactions``,
        ``transaction_count_reduction``, ``total_to_settle``, ``available``.
    """
    payer_col = _get_col(df, schema, "payer_col")
    amount_col = _get_col(df, schema, "amount_col")

    if not payer_col:
        return {"available": False, "reason": "payer_col not found in schema/dataframe"}
    if not amount_col:
        return {"available": False, "reason": "amount_col not found in schema/dataframe"}

    try:
        df_work = df.copy()
        df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)
        df_work = df_work.dropna(subset=[payer_col])

        payers = df_work[payer_col].astype(str).unique().tolist()
        n = len(payers)
        if n < 2:
            return {
                "available": False,
                "reason": "Need at least 2 payers to compute settlement",
            }

        # Total paid by each person
        paid = df_work.groupby(payer_col)[amount_col].sum().to_dict()
        paid = {str(k): float(v) for k, v in paid.items()}

        total = sum(paid.values())
        fair_share = total / n

        # Net balance: positive = owed to this person, negative = owes others
        balances = {p: round(paid.get(p, 0) - fair_share, 2) for p in payers}

        optimal_transactions = _min_cash_flow(balances)
        total_to_settle = round(sum(t["amount"] for t in optimal_transactions), 2)

        # Naive transaction count (everyone pays everyone)
        naive_count = n * (n - 1) // 2
        reduction = max(0, naive_count - len(optimal_transactions))

        return {
            "available": True,
            "balances": balances,
            "paid_amounts": paid,
            "fair_share": round(fair_share, 2),
            "total_to_settle": total_to_settle,
            "optimal_transactions": optimal_transactions,
            "transaction_count_reduction": reduction,
            "n_transactions": len(optimal_transactions),
            "n_payers": n,
        }

    except Exception as e:
        return {"available": False, "reason": f"Settlement optimisation error: {e}"}


def build_payer_network(df: pd.DataFrame, schema: dict) -> dict:
    """Build a network graph of payer relationships.

    Each node is a payer; edges represent money flows after settlement.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``nodes`` (list), ``edges`` (list), ``available``.
        ``nodes``: [{"id", "label", "total_paid", "share"}]
        ``edges``:  [{"source", "target", "amount"}]
    """
    settlement = optimize_settlement(df, schema)
    if not settlement.get("available"):
        return settlement  # propagate error

    try:
        paid = settlement["paid_amounts"]
        total = sum(paid.values())
        nodes = [
            {
                "id": p,
                "label": p,
                "total_paid": round(float(paid.get(p, 0)), 2),
                "share": round(float(paid.get(p, 0)) / total * 100, 1) if total > 0 else 0,
            }
            for p in paid
        ]

        edges = [
            {
                "source": t["payer"],
                "target": t["payee"],
                "amount": t["amount"],
            }
            for t in settlement["optimal_transactions"]
        ]

        result = {"available": True, "nodes": nodes, "edges": edges}

        # Add networkx metrics if available
        if _NX_AVAILABLE:
            G = nx.DiGraph()
            for node in nodes:
                G.add_node(node["id"], **node)
            for edge in edges:
                G.add_edge(edge["source"], edge["target"], weight=edge["amount"])
            result["networkx_available"] = True
            result["density"] = round(nx.density(G), 4)

        return result

    except Exception as e:
        return {"available": False, "reason": f"Network build error: {e}"}


def compute_contribution_fairness(df: pd.DataFrame, schema: dict) -> dict:
    """Compute how fairly each person is contributing.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``fairness_score`` (0-100), ``per_person`` stats, ``available``.
    """
    payer_col = _get_col(df, schema, "payer_col")
    amount_col = _get_col(df, schema, "amount_col")

    if not payer_col or not amount_col:
        return {
            "available": False,
            "reason": "payer_col or amount_col not found",
        }

    try:
        df_work = df.copy()
        df_work[amount_col] = pd.to_numeric(df_work[amount_col], errors="coerce").fillna(0)
        df_work = df_work.dropna(subset=[payer_col])

        payer_stats = df_work.groupby(payer_col)[amount_col].agg(
            ["sum", "count", "mean"]
        )
        total = float(payer_stats["sum"].sum())
        n_payers = len(payer_stats)
        if n_payers < 1 or total <= 0:
            return {"available": False, "reason": "No valid payer-amount data"}

        fair_share = total / n_payers
        ideal_pct = 100 / n_payers

        per_person: dict = {}
        deviations = []
        for payer, row in payer_stats.iterrows():
            paid = float(row["sum"])
            pct = round(paid / total * 100, 1)
            deviation = abs(pct - ideal_pct)
            deviations.append(deviation)
            per_person[str(payer)] = {
                "total_paid": round(paid, 2),
                "transaction_count": int(row["count"]),
                "avg_transaction": round(float(row["mean"]), 2),
                "percentage_of_total": pct,
                "ideal_percentage": round(ideal_pct, 1),
                "deviation_from_fair": round(deviation, 1),
                "overpaying": paid > fair_share,
            }

        # Fairness score: 100 if all equal, decreases with total deviation
        mean_deviation = float(np.mean(deviations)) if deviations else 0
        fairness_score = max(0.0, round(100 - mean_deviation * 2, 1))

        return {
            "available": True,
            "fairness_score": fairness_score,
            "total_expenses": round(total, 2),
            "fair_share_per_person": round(fair_share, 2),
            "n_payers": n_payers,
            "per_person": per_person,
        }

    except Exception as e:
        return {"available": False, "reason": f"Fairness computation error: {e}"}
