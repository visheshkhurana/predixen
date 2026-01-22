"""
Company Knowledge Base (CKB) Storage Layer.

Persists and retrieves CKB data for the multi-agent copilot system.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.copilot.agents.base import CompanyKnowledgeBase

logger = logging.getLogger(__name__)


class CKBStorage:
    """
    Storage layer for Company Knowledge Base.
    
    Stores CKB data in the company's metadata field and provides
    methods for reading, updating, and versioning the knowledge base.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_ckb(self, company_id: int) -> Optional[CompanyKnowledgeBase]:
        """Retrieve CKB for a company."""
        
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return None
        
        ckb = CompanyKnowledgeBase(
            company_id=company.id,
            company_name=company.name or "",
            industry=company.industry or "",
            stage=company.stage or "",
            currency=company.currency or "USD"
        )
        
        metadata = company.metadata_json or {}
        ckb_data = metadata.get("ckb", {})
        
        if ckb_data:
            ckb.overview = ckb_data.get("overview", {})
            ckb.financials = ckb_data.get("financials", {})
            ckb.market = ckb_data.get("market", {})
            ckb.strategy = ckb_data.get("strategy", {})
            ckb.icp = ckb_data.get("icp", {})
            ckb.competitors = ckb_data.get("competitors", [])
            ckb.risks = ckb_data.get("risks", [])
            ckb.decisions_made = ckb_data.get("decisions_made", [])
        
        ckb = self._enrich_from_truth_scan(ckb, company_id)
        
        return ckb
    
    def save_ckb(self, ckb: CompanyKnowledgeBase) -> bool:
        """Save CKB to database."""
        
        company = self.db.query(Company).filter(
            Company.id == ckb.company_id
        ).first()
        
        if not company:
            logger.error(f"Company {ckb.company_id} not found")
            return False
        
        metadata = company.metadata_json or {}
        
        metadata["ckb"] = {
            "overview": ckb.overview,
            "financials": ckb.financials,
            "market": ckb.market,
            "strategy": ckb.strategy,
            "icp": ckb.icp,
            "competitors": ckb.competitors,
            "risks": ckb.risks,
            "decisions_made": ckb.decisions_made,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        company.metadata_json = metadata
        self.db.commit()
        
        logger.info(f"Saved CKB for company {ckb.company_id}")
        return True
    
    def update_ckb_section(
        self, 
        company_id: int, 
        section: str, 
        data: Any
    ) -> bool:
        """Update a specific section of the CKB."""
        
        ckb = self.get_ckb(company_id)
        if not ckb:
            return False
        
        valid_sections = [
            "overview", "financials", "market", "strategy",
            "icp", "competitors", "risks", "decisions_made"
        ]
        
        if section not in valid_sections:
            logger.error(f"Invalid CKB section: {section}")
            return False
        
        setattr(ckb, section, data)
        return self.save_ckb(ckb)
    
    def add_decision(
        self, 
        company_id: int, 
        decision: Dict[str, Any]
    ) -> bool:
        """Add a decision to the CKB history."""
        
        ckb = self.get_ckb(company_id)
        if not ckb:
            return False
        
        decision["timestamp"] = datetime.utcnow().isoformat()
        ckb.decisions_made.append(decision)
        
        if len(ckb.decisions_made) > 50:
            ckb.decisions_made = ckb.decisions_made[-50:]
        
        return self.save_ckb(ckb)
    
    def _enrich_from_truth_scan(
        self, 
        ckb: CompanyKnowledgeBase, 
        company_id: int
    ) -> CompanyKnowledgeBase:
        """Enrich CKB with latest Truth Scan data."""
        
        truth_scan = self.db.query(TruthScan).filter(
            TruthScan.company_id == company_id
        ).order_by(TruthScan.created_at.desc()).first()
        
        if not truth_scan:
            return ckb
        
        ts_data = truth_scan.outputs_json or {}
        metrics = ts_data.get("metrics", {})
        
        if metrics:
            ckb.financials.update({
                "pnl": {
                    "revenue": metrics.get("monthly_revenue"),
                    "gross_margin": metrics.get("gross_margin"),
                    "operating_margin": metrics.get("operating_margin"),
                },
                "cashflow": {
                    "burn_rate": metrics.get("net_burn"),
                    "runway_months": metrics.get("runway_months")
                },
                "balance_sheet": {
                    "cash_balance": metrics.get("cash_balance")
                },
                "truth_scan_id": truth_scan.id,
                "computed_at": truth_scan.created_at.isoformat()
            })
        
        return ckb
    
    def get_context_for_copilot(
        self, 
        company_id: int
    ) -> Dict[str, Any]:
        """Get full context for copilot processing."""
        
        ckb = self.get_ckb(company_id)
        if not ckb:
            return {}
        
        company = self.db.query(Company).filter(
            Company.id == company_id
        ).first()
        
        truth_scan = self.db.query(TruthScan).filter(
            TruthScan.company_id == company_id
        ).order_by(TruthScan.created_at.desc()).first()
        
        context = {
            "ckb": ckb,
            "has_document": False,
            "extracted_financials": None,
            "truth_scan": None
        }
        
        if truth_scan:
            context["truth_scan"] = truth_scan.outputs_json
        
        return context
