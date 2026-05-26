"""
Expense Intelligence package.

This layer is intentionally separate from the generic AutoML/reporting code.
It contains domain-specific financial intelligence primitives that are
explainable, validated, and safe to expose in production APIs.
"""

from .orchestrator import run_expense_intelligence

__all__ = ["run_expense_intelligence"]
