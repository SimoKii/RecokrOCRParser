from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .constants import (
    DOC_TYPES,
    DIRECTION_COMPACT_MAP,
    DIRECTION_KEYWORDS,
    DIRECTION_OUT,
    DOC_TYPE_PREFIX_MAP,
    ISSUER_CORP_MARKERS,
    ISSUER_EXCLUDE_CONTAINS,
    ISSUER_SKIP_CONTAINS,
    LABELS,
    SALUTATION_KEYWORDS,
)
from .normalizer import (
    clean_item_name,
    clean_vehicle_no,
    compact_text,
    find_label_span,
    find_label_span_fuzzy,
    strip_time_tokens,
    strip_value_prefix,
)
from .preprocessor import LineInfo, PreprocessResult
from .schema import ParsedRecord, Warning
from .validator import add_warning

_DATE_PATTERN = re.compile(r"(\d{4})[-./\s]*(\d{2})[-./\s]*(\d{2})")
_TIME_PATTERN = re.compile(r"(\d{1,2})\s*:\s*(\d{2})(?:\s*:\s*(\d{2}))?")
_TIME_PAREN_PATTERN = re.compile(r"\(?\s*(\d{1,2})\s*:\s*(\d{2})\s*\)?")
_TIME_KOREAN_PATTERN = re.compile(r"(\d{1,2})\s*시\s*(\d{1,2})\s*분")
_WEIGHT_PATTERN = re.compile(r"(\d[\d,\s]*)\s*kg", re.IGNORECASE)
_TIMESTAMP_PATTERN = re.compile(
    r"(\d{4})\s*-\s*(\d{2})\s*-\s*(\d{2})\s+(\d{2})\s*:\s*(\d{2})\s*:\s*(\d{2})"
)


def extract_date_serial(text: str) -> Tuple[Optional[str], Optional[str]]:
    """날짜와 일련번호를 같은 라인에서 추출"""
    date_match = _DATE_PATTERN.search(text)
    date_value = None
    serial_value = None
    if date_match:
        date_value = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        tail = text[date_match.end() :]
        serial_match = re.search(r"[-\s:]*([0-9]{1,6})", tail)
        if serial_match:
            serial_value = serial_match.group(1)
    return date_value, serial_value


def extract_time(text: str) -> Optional[str]:
    """시간 문자열을 표준 포맷으로 변환"""
    match = _TIME_PATTERN.search(text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        second = match.group(3)
        if second:
            return f"{hour:02d}:{minute:02d}:{int(second):02d}"
        return f"{hour:02d}:{minute:02d}"
    match = _TIME_PAREN_PATTERN.search(text)
    if match:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
    match = _TIME_KOREAN_PATTERN.search(text)
    if match:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
    return None


def extract_weight(text: str) -> Optional[float]:
    """무게(kg) 단일 값을 추출"""
    sanitized = strip_time_tokens(text)
    match = _WEIGHT_PATTERN.search(sanitized)
    if not match:
        return None
    value = re.sub(r"[,\s]", "", match.group(1))
    try:
        return float(value)
    except ValueError:
        return None


def extract_all_weights(text: str) -> List[float]:
    """라인 내 다중 무게 후보 추출"""
    sanitized = strip_time_tokens(text)
    matches = _WEIGHT_PATTERN.findall(sanitized)
    weights: List[float] = []
    for raw in matches:
        value = re.sub(r"[,\s]", "", raw)
        if value.isdigit():
            weights.append(float(value))
    return weights


def detect_doc_type(lines: List[LineInfo]) -> str:
    """문서 타입을 텍스트에서 추정"""
    for line in lines:
        compact = line.compact
        for doc_type, variants in DOC_TYPES.items():
            for variant in variants:
                if compact_text(variant) in compact:
                    return doc_type
    for line in lines:
        compact = line.compact
        for prefix, doc_type in DOC_TYPE_PREFIX_MAP.items():
            if compact.startswith(prefix):
                return doc_type
    return "unknown"


def detect_direction_from_text(text: str) -> Optional[str]:
    """입고/출고 텍스트 단서 판단"""
    for direction, keywords in DIRECTION_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return direction
    compact = compact_text(text)
    if compact in DIRECTION_COMPACT_MAP:
        return DIRECTION_COMPACT_MAP[compact]
    return None


def extract_gps(text: str) -> Optional[Dict[str, float]]:
    """GPS 좌표를 위도/경도로 파싱"""
    match = re.search(r"([-+]?\d+\.\d+)\s*,\s*([-+]?\d+\.\d+)", text)
    if not match:
        return None
    lat = float(match.group(1))
    lng = float(match.group(2))
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return {"lat": lat, "lng": lng}


def extract_timestamp(text: str) -> Optional[str]:
    """문서 하단 타임스탬프 파싱"""
    match = _TIMESTAMP_PATTERN.search(text)
    if not match:
        return None
    return (
        f"{match.group(1)}-{match.group(2)}-{match.group(3)} "
        f"{match.group(4)}:{match.group(5)}:{match.group(6)}"
    )


def split_item_direction(line: LineInfo) -> Tuple[Optional[str], Optional[str]]:
    """한 줄에 품명/구분이 함께 있는 경우 분리"""
    item_span = find_label_span(line.cleaned, LABELS["item"])
    direction_span = find_label_span(line.cleaned, LABELS["direction"])
    if not item_span or not direction_span:
        return None, None
    if item_span[1] >= direction_span[0]:
        return None, None
    item_value = strip_value_prefix(line.cleaned[item_span[1] : direction_span[0]]).strip()
    direction_value = strip_value_prefix(line.cleaned[direction_span[1] :]).strip()
    return item_value or None, direction_value or None


def is_label_line(line: LineInfo) -> bool:
    """라벨만 있는 라인인지 판별"""
    for labels in LABELS.values():
        if find_label_span(line.cleaned, labels):
            return True
    return False


def find_issuer(lines: List[LineInfo]) -> Optional[str]:
    """발행처 추정(상단 (주) 또는 하단 비라벨 라인)"""
    for line in lines:
        cleaned_compact = line.cleaned.replace(" ", "")
        if any(marker in cleaned_compact for marker in ISSUER_CORP_MARKERS) and not any(
            token in line.cleaned for token in ISSUER_EXCLUDE_CONTAINS
        ):
            return cleaned_compact
    for line in reversed(lines):
        if not line.cleaned.strip():
            continue
        if extract_timestamp(line.cleaned) or extract_gps(line.cleaned):
            continue
        if any(token in line.cleaned for token in ISSUER_SKIP_CONTAINS):
            continue
        if is_label_line(line):
            continue
        if len(line.cleaned) >= 2:
            return line.cleaned
    return None


def select_value_after_label(
    line: LineInfo, labels: List[str], warnings: List[Warning]
) -> Optional[str]:
    """라벨 뒤 값을 추출하고 누락 시 경고 기록"""
    best_span: Optional[Tuple[int, int]] = None
    best_label: Optional[str] = None
    for label in labels:
        regex = re.compile(r"\s*".join(map(re.escape, label.replace(" ", ""))))
        match = regex.search(line.cleaned)
        if match:
            if best_span is None or match.start() < best_span[0]:
                best_span = (match.start(), match.end())
                best_label = label
    if not best_span:
        for label in labels:
            span = find_label_span_fuzzy(line.cleaned, [label])
            if span:
                if best_span is None or span[0] < best_span[0]:
                    best_span = span
                    best_label = label
    if not best_span:
        return None

    value = strip_value_prefix(line.cleaned[best_span[1] :])

    if not value.strip():
        label_name = (best_label or labels[0]).replace(" ", "")
        add_warning(warnings, "label_empty_value", {"label": label_name})
        return None

    return value.strip()


def parse_preprocessed(preprocessed: PreprocessResult) -> Tuple[ParsedRecord, List[Warning]]:
    """전처리 결과를 ParsedRecord로 변환"""
    record = ParsedRecord()
    record.raw_text = preprocessed.raw_text

    warnings = preprocessed.warnings
    line_infos = preprocessed.line_infos

    record.doc_type = detect_doc_type(line_infos)

    candidate_time_weight: List[Tuple[str, float, int]] = []
    direction_source = "none"

    for idx, line in enumerate(line_infos):
        if not record.partner_name:
            for keyword in SALUTATION_KEYWORDS:
                if keyword in line.cleaned:
                    partner_value = line.cleaned.replace(keyword, "").strip()
                    if partner_value:
                        record.partner_name = partner_value.replace(" ", "")
                    break

        date_value = None
        serial_value = None
        if find_label_span(line.cleaned, LABELS["date"]):
            date_value, serial_value = extract_date_serial(line.cleaned)
        if date_value:
            record.weigh_date = record.weigh_date or date_value
        if serial_value:
            record.serial_no = record.serial_no or serial_value

        serial_text = select_value_after_label(line, LABELS["serial"], warnings)
        if serial_text and not record.serial_no:
            serial_match = re.search(r"\d{1,8}", serial_text.replace(" ", ""))
            if serial_match:
                record.serial_no = serial_match.group(0)

        vehicle_text = select_value_after_label(line, LABELS["vehicle"], warnings)
        if vehicle_text:
            direction = detect_direction_from_text(vehicle_text)
            if direction:
                record.direction = record.direction or direction
                direction_source = "weak"
                for keywords in DIRECTION_KEYWORDS.values():
                    for keyword in keywords:
                        vehicle_text = vehicle_text.replace(keyword, "")
                vehicle_text = vehicle_text.strip()
            vehicle_value = clean_vehicle_no(vehicle_text)
            if vehicle_value:
                record.vehicle_no = record.vehicle_no or vehicle_value

        partner_text = select_value_after_label(line, LABELS["partner"], warnings)
        if partner_text:
            record.partner_name = record.partner_name or partner_text.replace(" ", "")

        item_value, direction_value = split_item_direction(line)
        if item_value and not record.item_name:
            record.item_name = clean_item_name(item_value)
        if direction_value:
            detected = detect_direction_from_text(direction_value)
            if detected:
                record.direction = detected
                direction_source = "label"

        item_text = select_value_after_label(line, LABELS["item"], warnings)
        if item_text and not record.item_name:
            record.item_name = clean_item_name(item_text)

        direction_text = select_value_after_label(line, LABELS["direction"], warnings)
        if direction_text:
            detected = detect_direction_from_text(direction_text)
            if detected:
                record.direction = detected
                direction_source = "label"

        if direction_source != "label":
            detected = detect_direction_from_text(line.cleaned)
            if detected:
                if direction_source == "weak" and detected == DIRECTION_OUT:
                    record.direction = detected
                elif direction_source == "none":
                    record.direction = detected
                direction_source = "weak"

        gross_text = select_value_after_label(line, LABELS["gross"], warnings)
        if gross_text:
            gross_weight = extract_weight(gross_text)
            if gross_weight is not None and record.gross_weight_kg is None:
                record.gross_weight_kg = gross_weight
            gross_time = extract_time(gross_text)
            if gross_time is not None and record.weigh_time_in is None:
                record.weigh_time_in = gross_time

        tare_text = select_value_after_label(line, LABELS["tare"], warnings)
        if tare_text:
            tare_weight = extract_weight(tare_text)
            if tare_weight is not None and record.tare_weight_kg is None:
                record.tare_weight_kg = tare_weight
            tare_time = extract_time(tare_text)
            if tare_time is not None and record.weigh_time_out is None:
                record.weigh_time_out = tare_time

        net_text = select_value_after_label(line, LABELS["net"], warnings)
        if net_text:
            net_weight = extract_weight(net_text)
            if net_weight is not None and record.net_weight_kg is None:
                record.net_weight_kg = net_weight

        deduction_text = select_value_after_label(line, LABELS["deduction"], warnings)
        if deduction_text:
            deduction_weight = extract_weight(deduction_text)
            if deduction_weight is not None and record.deduction_weight_kg is None:
                record.deduction_weight_kg = deduction_weight

        if not any(
            find_label_span(line.cleaned, LABELS[key])
            for key in ("gross", "tare", "net", "deduction")
        ):
            weight = extract_weight(line.cleaned)
            time_value = extract_time(line.cleaned)
            if weight and time_value:
                candidate_time_weight.append((time_value, weight, idx))

        if not record.timestamp:
            record.timestamp = extract_timestamp(line.cleaned) or record.timestamp
        if not record.gps:
            record.gps = extract_gps(line.cleaned) or record.gps

    if candidate_time_weight:
        if not record.gross_weight_kg:
            time_value, weight_value, _ = candidate_time_weight[0]
            record.gross_weight_kg = weight_value
            record.weigh_time_in = record.weigh_time_in or time_value
            add_warning(warnings, "gross_inferred_from_time_weight")
        if len(candidate_time_weight) > 1 and not record.tare_weight_kg:
            time_value, weight_value, _ = candidate_time_weight[1]
            record.tare_weight_kg = weight_value
            record.weigh_time_out = record.weigh_time_out or time_value
            add_warning(warnings, "tare_inferred_from_time_weight")

    record.issuer = find_issuer(line_infos) or record.issuer

    return record, warnings
