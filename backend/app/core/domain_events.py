"""Domain Event System v1.0 — Event-driven decoupling for CK_Missive.

Defines business events that flow across module boundaries:
- CaseCreated: PM Case 建案
- ProjectPromoted: PM Case 成案 → ContractProject
- QuotationConfirmed: ERP Quotation 確認
- BillingPaid: 收款確認 → 帳本入帳
- TenderAwarded: 標案決標
- DocumentReceived: 公文收文
"""
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    CASE_CREATED = "case.created"
    PROJECT_PROMOTED = "project.promoted"
    QUOTATION_CONFIRMED = "quotation.confirmed"
    BILLING_PAID = "billing.paid"
    TENDER_AWARDED = "tender.awarded"
    DOCUMENT_RECEIVED = "document.received"
    EXPENSE_APPROVED = "expense.approved"
    EXPENSE_LARGE_APPROVED = "expense.large_approved"
    MILESTONE_COMPLETED = "milestone.completed"
    EVOLUTION_COMPLETED = "agent.evolution_completed"


@dataclass
class DomainEvent:
    """Base domain event."""
    event_type: EventType
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = "ck_missive"
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)

    @classmethod
    def from_json(cls, data: str) -> "DomainEvent":
        d = json.loads(data)
        d["event_type"] = EventType(d["event_type"])
        return cls(**d)


# --- Typed event constructors ---

def case_created(case_code: str, case_name: str, year: int, **extra) -> DomainEvent:
    return DomainEvent(
        event_type=EventType.CASE_CREATED,
        payload={"case_code": case_code, "case_name": case_name, "year": year, **extra},
    )


def project_promoted(
    case_code: str, project_code: str, contract_project_id: int, **extra
) -> DomainEvent:
    return DomainEvent(
        event_type=EventType.PROJECT_PROMOTED,
        payload={
            "case_code": case_code,
            "project_code": project_code,
            "contract_project_id": contract_project_id,
            **extra,
        },
    )


def quotation_confirmed(
    case_code: str, erp_quotation_id: int, total_price: float, **extra
) -> DomainEvent:
    return DomainEvent(
        event_type=EventType.QUOTATION_CONFIRMED,
        payload={
            "case_code": case_code,
            "erp_quotation_id": erp_quotation_id,
            "total_price": total_price,
            **extra,
        },
    )


def billing_paid(
    billing_id: int, amount: float, case_code: str, **extra
) -> DomainEvent:
    return DomainEvent(
        event_type=EventType.BILLING_PAID,
        payload={
            "billing_id": billing_id,
            "amount": amount,
            "case_code": case_code,
            **extra,
        },
    )


def tender_awarded(
    unit_id: str, job_number: str, award_amount: float, **extra
) -> DomainEvent:
    return DomainEvent(
        event_type=EventType.TENDER_AWARDED,
        payload={
            "unit_id": unit_id,
            "job_number": job_number,
            "award_amount": award_amount,
            **extra,
        },
    )


def milestone_completed(
    milestone_id: int, case_code: str, milestone_name: str, **extra
) -> DomainEvent:
    return DomainEvent(
        event_type=EventType.MILESTONE_COMPLETED,
        payload={
            "milestone_id": milestone_id,
            "case_code": case_code,
            "milestone_name": milestone_name,
            **extra,
        },
    )


def expense_large_approved(
    expense_id: int, amount: float, case_code: str, **extra
) -> DomainEvent:
    return DomainEvent(
        event_type=EventType.EXPENSE_LARGE_APPROVED,
        payload={
            "expense_id": expense_id,
            "amount": amount,
            "case_code": case_code,
            "description": "大額費用核銷，建議評估是否列入資產",
            **extra,
        },
    )
