"""
Multi-agent system for decision support.
Each agent specializes in a domain (HR, Sales, Legal, Finance, Marketing, Supply Chain).
"""
from .base_agent import BaseAgent
from .hr_agent import HRAgent
from .sales_agent import SalesAgent
from .legal_agent import LegalAgent
from .finance_agent import FinanceAgent
from .marketing_agent import MarketingAgent
from .supply_chain_agent import SupplyChainAgent
from .manager_agent import ManagerAgent

__all__ = [
    "BaseAgent",
    "HRAgent",
    "SalesAgent",
    "LegalAgent",
    "FinanceAgent",
    "MarketingAgent",
    "SupplyChainAgent",
    "ManagerAgent",
]
