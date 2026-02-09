from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .constants import NOISE_COMPACT_TOKENS
from .normalizer import compact_text, normalize_spaces
from .schema import Warning
from .validator import add_warning


@dataclass(frozen=True)
class LineInfo:
    """라인 단위 원문/정규화/압축 텍스트 묶음"""
    raw: str
    cleaned: str
    compact: str


@dataclass
class PreprocessResult:
    """전처리 결과 묶음"""
    raw_text: str
    line_infos: List[LineInfo]
    warnings: List[Warning]


class ValidationError(Exception):
    """입력 검증 실패"""
    pass

def load_ocr_json(path: str) -> Tuple[Dict[str, Any], List[Warning]]:
    """입력 JSON 로드 및 예외를 도메인 에러로 변환"""
    warnings: List[Warning] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), warnings
    except FileNotFoundError:
        raise ValidationError(f"파일을 찾을 수 없습니다: {path}")
    except json.JSONDecodeError as e:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except Exception as fallback_error:
            raise ValidationError(f"파일 로드 실패: {fallback_error}")
        add_warning(warnings, "input_json_fallback", {"error": str(e)})
        return {"text": raw_text}, warnings
    except Exception as e:
        raise ValidationError(f"파일 로드 실패: {e}")


def extract_lines(payload: Dict[str, Any]) -> List[str]:
    """OCR payload에서 라인 후보를 추출"""
    pages = payload.get("pages", [])
    if pages:
        lines: List[str] = []
        for page in pages:
            for line in page.get("lines", []) or []:
                text = line.get("text")
                if text:
                    lines.append(text)
        if lines:
            return lines
        page_texts = [page.get("text") for page in pages if page.get("text")]
        if page_texts:
            return page_texts
    top_text = payload.get("text")
    return [top_text] if top_text else []


def is_noise_line(text: str) -> bool:
    """의미 없는 라인 여부 판별"""
    if not text.strip():
        return True
    compact = compact_text(text)
    if compact in NOISE_COMPACT_TOKENS:
        return True
    return False


def build_line_infos(lines: Iterable[str]) -> List[LineInfo]:
    """라인 리스트를 정규화/압축 형태로 변환"""
    infos: List[LineInfo] = []
    for line in lines:
        cleaned = normalize_spaces(line)
        infos.append(LineInfo(raw=line, cleaned=cleaned, compact=compact_text(cleaned)))
    return infos


def preprocess_payload(
    payload: Dict[str, Any], initial_warnings: Optional[List[Warning]] = None
) -> PreprocessResult:
    """라인 추출 + 노이즈 제거 + 경고 수집"""
    warnings: List[Warning] = list(initial_warnings or [])
    lines = extract_lines(payload)
    raw_text = "\n".join(lines)

    all_infos = build_line_infos(lines)
    line_infos = [info for info in all_infos if not is_noise_line(info.cleaned)]

    noise_count = len(all_infos) - len(line_infos)
    if not lines:
        add_warning(warnings, "missing_pages_and_text")

    if noise_count > 0:
        add_warning(warnings, "noise_lines_removed", {"count": noise_count})

    return PreprocessResult(raw_text=raw_text, line_infos=line_infos, warnings=warnings)
