from __future__ import annotations

LABELS = {
    "date": ["계량일자", "일자", "일시", "날짜", "계량 일자"],
    "serial": ["일련번호", "계량횟수", "전표번호", "ID-NO", "IDNO", "ID NO"],
    "vehicle": ["차량번호", "차번호", "차량No", "차량NO", "차량 No", "차량 NO"],
    "partner": ["거래처", "상호", "수신처", "회사명", "회 사 명"],
    "item": ["품명", "제품명", "품 명", "제 품 명"],
    "direction": ["구분", "구 분"],
    "gross": ["총중량", "총 중량"],
    "tare": ["공차중량", "차중량", "공 차 중 량", "차 중 량"],
    "net": ["실중량", "실 중 량"],
    "deduction": ["감량", "감 량"],
}

DOC_TYPES = {
    "계량증명서": ["계량증명서", "계량 증명서"],
    "계량증명표": ["계량증명표", "계량 증명 표", "계량 증명표"],
    "계량표": ["계량표", "계 량 표", "계그표"],
    "계량확인서": ["계량확인서", "계량 확인서", "계 량 확 인 서"],
}

DIRECTION_IN = "입고"
DIRECTION_OUT = "출고"

DIRECTION_KEYWORDS = {
    DIRECTION_IN: ["입고", "반입"],
    DIRECTION_OUT: ["출고", "반출"],
}

DIRECTION_COMPACT_MAP = {
    "출": DIRECTION_OUT,
}

SALUTATION_KEYWORDS = ["귀하"]

NOISE_COMPACT_TOKENS = {"", "N", "없다"}

LABEL_FUZZY_THRESHOLD = 0.85


class FuzzyMatchingThresholds:
    """유사도 매칭 임계값"""
    SHORT_LABEL_THRESHOLD = 0.66
    SHORT_LABEL_LENGTH = 3

DOC_TYPE_PREFIX_MAP = {
    "계그표": "계량표",
}

ISSUER_CORP_MARKERS = ["(주)"]
ISSUER_EXCLUDE_CONTAINS = ["경기도"]
ISSUER_SKIP_CONTAINS = ["계량하였음을", "증명"]

WARNING_CODE_MAP = {
    "input_json_fallback": "INP-FMT-001",
    "missing_pages_and_text": "INP-MISS-002",
    "noise_lines_removed": "PRE-CHK-001",
    "label_empty_value": "PRS-MISS-001",
    "gross_inferred_from_time_weight": "PRS-MAP-001",
    "tare_inferred_from_time_weight": "PRS-MAP-002",
    "net_inferred_from_gross_tare": "VAL-CHK-002",
    "net_mismatch": "VAL-CHK-001",
    "time_order_reversed": "VAL-CHK-003",
    "negative_weight": "VAL-CHK-004",
    "weight_exceeds_limit": "VAL-CHK-005",
}


class ValidationThresholds:
    """검증 임계값"""
    NET_WEIGHT_TOLERANCE_KG = 1.0
    MAX_WEIGHT_KG = 100000.0
    MIN_WEIGHT_KG = 0.0


class ConfidenceWeights:
    """신뢰도 가중치"""
    LABEL_INFERENCE = 0.05
    FIELD_MISSING = 0.05
    LOGIC_MISMATCH = 0.1
    NET_CALC_INFERENCE = 0.03
