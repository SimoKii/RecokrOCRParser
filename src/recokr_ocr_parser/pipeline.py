from __future__ import annotations

from typing import Any, Dict

from .parser import parse_preprocessed
from .preprocessor import load_ocr_json, preprocess_payload
from .schema import ParsedRecord
from .validator import finalize_record


def parse(payload: Dict[str, Any]) -> ParsedRecord:
    preprocessed = preprocess_payload(payload)
    record, warnings = parse_preprocessed(preprocessed)
    return finalize_record(record, warnings)


def run_pipeline(input_path: str) -> ParsedRecord:
    payload, warnings = load_ocr_json(input_path)
    preprocessed = preprocess_payload(payload, warnings)
    record, parse_warnings = parse_preprocessed(preprocessed)
    return finalize_record(record, parse_warnings)
