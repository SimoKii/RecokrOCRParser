from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, List, Optional, Tuple

from .constants import FuzzyMatchingThresholds, LABEL_FUZZY_THRESHOLD


def normalize_spaces(text: str) -> str:
    """연속 공백을 단일 공백으로 정규화"""
    return re.sub(r"\s+", " ", text).strip()


def compact_text(text: str) -> str:
    """라벨 매칭을 위한 압축 문자열 생성"""
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def build_label_regex(label: str) -> re.Pattern[str]:
    """라벨 공백 변형을 허용하는 정규식 생성"""
    chars = [re.escape(ch) for ch in label.replace(" ", "")]
    pattern = r"\s*".join(chars)
    return re.compile(pattern)


def _compact_with_index_map(text: str) -> Tuple[str, List[int]]:
    """compact 문자열과 원문 인덱스 매핑 생성"""
    compact_chars: List[str] = []
    index_map: List[int] = []
    for idx, ch in enumerate(text):
        if re.match(r"[0-9A-Za-z가-힣]", ch):
            compact_chars.append(ch)
            index_map.append(idx)
    return "".join(compact_chars), index_map


def _fuzzy_label_span(text: str, label: str) -> Optional[Tuple[int, int]]:
    """유사도 매칭으로 라벨 위치 추정"""
    compacted_text, index_map = _compact_with_index_map(text)
    compact_label = compact_text(label)
    label_len = len(compact_label)
    if label_len == 0 or len(compacted_text) < label_len:
        return None
    best_score = 0.0
    best_start = None
    for start in range(0, len(compacted_text) - label_len + 1):
        window = compacted_text[start : start + label_len]
        if window and window[0] != compact_label[0]:
            continue
        score = SequenceMatcher(None, compact_label, window).ratio()
        if score > best_score:
            best_score = score
            best_start = start
    threshold = (
        FuzzyMatchingThresholds.SHORT_LABEL_THRESHOLD
        if label_len <= FuzzyMatchingThresholds.SHORT_LABEL_LENGTH
        else LABEL_FUZZY_THRESHOLD
    )
    if best_start is None or best_score < threshold:
        return None
    start_idx = index_map[best_start]
    end_idx = index_map[best_start + label_len - 1] + 1
    return (start_idx, end_idx)


def find_label_span(text: str, labels: Iterable[str]) -> Optional[Tuple[int, int]]:
    """라벨 후보 중 가장 앞선 매칭 구간 반환"""
    best: Optional[Tuple[int, int]] = None
    for label in labels:
        regex = build_label_regex(label)
        match = regex.search(text)
        if match:
            if best is None or match.start() < best[0]:
                best = (match.start(), match.end())
    return best


def find_label_span_fuzzy(text: str, labels: Iterable[str]) -> Optional[Tuple[int, int]]:
    """라벨 후보 유사도 매칭 구간 반환"""
    best: Optional[Tuple[int, int]] = None
    for label in labels:
        fuzzy_span = _fuzzy_label_span(text, label)
        if fuzzy_span:
            if best is None or fuzzy_span[0] < best[0]:
                best = fuzzy_span
    return best


def strip_value_prefix(text: str) -> str:
    """라벨 뒤 구분자 제거"""
    return text.lstrip(" :：|-")


def clean_vehicle_no(text: str) -> Optional[str]:
    """차량번호 후보에서 불필요 문자를 제거"""
    parts = re.findall(r"[0-9A-Za-z가-힣]+", text)
    if not parts:
        return None
    return "".join(parts)


def clean_item_name(text: str) -> Optional[str]:
    """품명 후보에서 구분 잔여 문구 제거"""
    compact = text.replace(" ", "")
    if compact.endswith("구분"):
        compact = compact[: -len("구분")]
    return compact or None


def strip_time_tokens(text: str) -> str:
    """무게 파싱 시 시간 토큰 제거"""
    text = re.sub(r"\(\s*\d{1,2}\s*:\s*\d{2}\s*\)", " ", text)
    text = re.sub(r"\d{1,2}\s*:\s*\d{2}(?:\s*:\s*\d{2})?", " ", text)
    text = re.sub(r"\d{1,2}\s*시\s*\d{1,2}\s*분", " ", text)
    return text
