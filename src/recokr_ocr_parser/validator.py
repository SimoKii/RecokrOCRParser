from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import re

from .constants import ConfidenceWeights, ValidationThresholds, WARNING_CODE_MAP
from .schema import ParsedRecord, Warning, WarningSeverity


def _warning_key(warning: Warning) -> Tuple[str, Optional[Tuple[Tuple[str, Any], ...]]]:
    """경고 중복 제거를 위한 키 생성"""
    if warning.context is None:
        return (warning.code, None)
    return (warning.code, tuple(sorted(warning.context.items())))


def _default_warning_info(code: str, context: Dict[str, Any]) -> Tuple[WarningSeverity, str]:
    """경고 코드에 대한 기본 심각도/메시지 제공"""
    if code == "noise_lines_removed":
        count = context.get("count")
        if count is not None:
            return WarningSeverity.INFO, f"노이즈 라인 {count}개 제거"
        return WarningSeverity.INFO, "노이즈 라인 제거"
    if code == "input_json_fallback":
        return WarningSeverity.WARN, "입력 JSON 파싱 실패로 텍스트 기반 파싱 수행"
    if code == "missing_pages_and_text":
        return WarningSeverity.ERROR, "입력에 pages/text가 없어 라인 추출 실패"
    if code == "label_empty_value":
        label = context.get("label")
        if label:
            return WarningSeverity.WARN, f"라벨 값 누락: {label}"
        return WarningSeverity.WARN, "라벨 값 누락"
    if code == "gross_inferred_from_time_weight":
        return WarningSeverity.WARN, "총중량을 시간/무게 패턴으로 추정"
    if code == "tare_inferred_from_time_weight":
        return WarningSeverity.WARN, "공차중량을 시간/무게 패턴으로 추정"
    if code == "net_inferred_from_gross_tare":
        return WarningSeverity.WARN, "실중량을 총/공차 차이로 계산"
    if code == "net_mismatch":
        return WarningSeverity.ERROR, "총중량-공차중량과 실중량 불일치"
    if code == "time_order_reversed":
        time_in = context.get("time_in")
        time_out = context.get("time_out")
        if time_in and time_out:
            return WarningSeverity.WARN, f"입차 시간이 출차 시간보다 늦음: {time_in}>{time_out}"
        return WarningSeverity.WARN, "입차/출차 시간 순서 이상"
    if code == "negative_weight":
        field = context.get("field", "unknown")
        return WarningSeverity.ERROR, f"음수 무게 감지: {field}"
    if code == "weight_exceeds_limit":
        field = context.get("field", "unknown")
        return WarningSeverity.WARN, f"무게 범위 초과: {field}"
    return WarningSeverity.WARN, code


def _standardize_warning_code(code: str) -> str:
    """경고 코드를 문서 표준 형태로 변환"""
    if re.match(r"^[A-Z]{3}-[A-Z]{3}-\d{3}$", code):
        return code
    return WARNING_CODE_MAP.get(code, code)


def add_warning(
    warnings: List[Warning],
    code: str,
    context: Optional[Dict[str, Any]] = None,
    severity: Optional[WarningSeverity] = None,
    message: Optional[str] = None,
) -> None:
    """경고를 생성하고 중복을 제거하여 추가"""
    context = context or {}
    if severity is None or message is None:
        default_severity, default_message = _default_warning_info(code, context)
        severity = severity or default_severity
        message = message or default_message
    standardized = _standardize_warning_code(code)
    if standardized != code:
        context = dict(context)
        context.setdefault("legacy_code", code)
    warning = Warning(code=standardized, severity=severity, message=message, context=context or None)
    candidate_key = _warning_key(warning)
    if all(_warning_key(existing) != candidate_key for existing in warnings):
        warnings.append(warning)


def has_warning(warnings: Iterable[Warning], code: str) -> bool:
    """특정 코드의 경고 존재 여부 판단"""
    standardized = _standardize_warning_code(code)
    for warning in warnings:
        if warning.code == standardized:
            return True
        if warning.context and warning.context.get("legacy_code") == code:
            return True
    return False


def finalize_record(record: ParsedRecord, warnings: List[Warning]) -> ParsedRecord:
    """검증/보정/신뢰도 산정을 마무리"""
    validate_weights(record, warnings)
    validate_time_order(record, warnings)

    if record.net_weight_kg is None and record.gross_weight_kg and record.tare_weight_kg:
        record.net_weight_kg = record.gross_weight_kg - record.tare_weight_kg
        add_warning(warnings, "net_inferred_from_gross_tare")

    if (
        record.net_weight_kg is not None
        and record.gross_weight_kg is not None
        and record.tare_weight_kg is not None
    ):
        if (
            abs(record.gross_weight_kg - record.tare_weight_kg - record.net_weight_kg)
            > ValidationThresholds.NET_WEIGHT_TOLERANCE_KG
        ):
            add_warning(warnings, "net_mismatch")

    record.warnings = warnings

    confidence = 1.0

    if has_warning(warnings, "gross_inferred_from_time_weight"):
        confidence -= ConfidenceWeights.LABEL_INFERENCE
    if has_warning(warnings, "tare_inferred_from_time_weight"):
        confidence -= ConfidenceWeights.LABEL_INFERENCE
    if has_warning(warnings, "net_inferred_from_gross_tare"):
        confidence -= ConfidenceWeights.NET_CALC_INFERENCE

    if has_warning(warnings, "net_mismatch"):
        confidence -= ConfidenceWeights.LOGIC_MISMATCH

    if record.partner_name is None:
        confidence -= ConfidenceWeights.FIELD_MISSING
    if record.item_name is None:
        confidence -= ConfidenceWeights.FIELD_MISSING
    if record.timestamp is None:
        confidence -= ConfidenceWeights.FIELD_MISSING

    record.parse_confidence = max(0.0, min(1.0, confidence))
    return record

def validate_weights(record: ParsedRecord, warnings: List[Warning]) -> None:
    """무게 값 유효성 검사"""
    weight_fields = [
        ("gross_weight_kg", record.gross_weight_kg),
        ("tare_weight_kg", record.tare_weight_kg),
        ("net_weight_kg", record.net_weight_kg),
        ("deduction_weight_kg", record.deduction_weight_kg),
    ]
    
    for field_name, value in weight_fields:
        if value is None:
            continue
            
        if value < ValidationThresholds.MIN_WEIGHT_KG:
            add_warning(
                warnings,
                "negative_weight",
                {"field": field_name, "value": value},
                severity=WarningSeverity.ERROR,
            )
        
        if value > ValidationThresholds.MAX_WEIGHT_KG:
            add_warning(
                warnings,
                "weight_exceeds_limit",
                {"field": field_name, "value": value},
                severity=WarningSeverity.WARN,
            )


def validate_time_order(record: ParsedRecord, warnings: List[Warning]) -> None:
    """입차/출차 시간 순서 검증"""
    if record.weigh_time_in and record.weigh_time_out:
        if record.weigh_time_in > record.weigh_time_out:
            add_warning(
                warnings,
                "time_order_reversed",
                {"time_in": record.weigh_time_in, "time_out": record.weigh_time_out},
            )

def test_label_removal(tmp_path):
    """라벨 완전 제거 시 처리"""
    payload = {
        "pages": [{"lines": [
            {"text": "1,500 kg"}, 
            {"text": "1,200 kg"},  
        ]}]
    }
