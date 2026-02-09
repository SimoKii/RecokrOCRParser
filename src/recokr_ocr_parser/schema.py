from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WarningSeverity(str, Enum):
    """경고 심각도 구분"""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Warning:
    """경고 정보 구조체"""
    code: str
    severity: WarningSeverity
    message: str
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """직렬화 가능한 dict 반환"""
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context,
        }


@dataclass
class ParsedRecord:
    """파싱 결과 레코드"""
    doc_type: str = "unknown"
    weigh_date: Optional[str] = None
    weigh_time_in: Optional[str] = None
    weigh_time_out: Optional[str] = None
    serial_no: Optional[str] = None
    vehicle_no: Optional[str] = None
    partner_name: Optional[str] = None
    item_name: Optional[str] = None
    direction: Optional[str] = None
    gross_weight_kg: Optional[float] = None
    tare_weight_kg: Optional[float] = None
    net_weight_kg: Optional[float] = None
    deduction_weight_kg: Optional[float] = None
    issuer: Optional[str] = None
    timestamp: Optional[str] = None
    gps: Optional[Dict[str, float]] = None
    raw_text: str = ""
    parse_confidence: float = 0.0
    warnings: List[Warning] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """직렬화 가능한 dict 반환"""
        return {
            "doc_type": self.doc_type,
            "weigh_date": self.weigh_date,
            "weigh_time_in": self.weigh_time_in,
            "weigh_time_out": self.weigh_time_out,
            "serial_no": self.serial_no,
            "vehicle_no": self.vehicle_no,
            "partner_name": self.partner_name,
            "item_name": self.item_name,
            "direction": self.direction,
            "gross_weight_kg": self.gross_weight_kg,
            "tare_weight_kg": self.tare_weight_kg,
            "net_weight_kg": self.net_weight_kg,
            "deduction_weight_kg": self.deduction_weight_kg,
            "issuer": self.issuer,
            "timestamp": self.timestamp,
            "gps": self.gps,
            "raw_text": self.raw_text,
            "parse_confidence": self.parse_confidence,
            "warnings": [warning.to_dict() for warning in self.warnings],
        }
