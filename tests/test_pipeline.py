import json

import pytest

from recokr_ocr_parser.pipeline import run_pipeline
from recokr_ocr_parser.preprocessor import ValidationError

def test_sample_01_fields():
    """sample_01 필수 필드 정확도"""
    result = run_pipeline("inputs/sample_01.json")
    
    assert result.doc_type == "계량증명서"
    assert result.weigh_date == "2026-02-02"
    assert result.vehicle_no == "8713"
    assert result.gross_weight_kg == 12480.0
    assert result.tare_weight_kg == 7470.0
    assert result.net_weight_kg == 5010.0

def test_sample_01_confidence():
    """sample_01 신뢰도 및 경고"""
    result = run_pipeline("inputs/sample_01.json")
    
    assert 0.84 <= result.parse_confidence <= 0.86
    warning_codes = [w.code for w in result.warnings]
    assert "PRS-MAP-001" in warning_codes
    assert "PRS-MAP-002" in warning_codes

def test_sample_02_perfect():
    """sample_02 완벽한 파싱"""
    result = run_pipeline("inputs/sample_02.json")
    
    assert result.parse_confidence == 1.0
    assert result.doc_type == "계량표"
    assert result.direction == "입고"

def test_sample_03_missing_fields():
    """sample_03 필드 누락 감지"""
    result = run_pipeline("inputs/sample_03.json")
    
    assert result.partner_name is None
    assert result.item_name is None
    assert 0.89 <= result.parse_confidence <= 0.91
    
    warning_codes = [w.code for w in result.warnings]
    assert "PRS-MISS-001" in warning_codes


def test_sample_04_fields():
    """sample_04 필드 추출"""
    result = run_pipeline("inputs/sample_04.json")

    assert result.doc_type == "계량증명표"
    assert result.weigh_date == "2025-12-01"
    assert result.vehicle_no == "0580"
    assert result.partner_name == "신성(푸디스트)"
    assert result.item_name == "국판"
    assert result.direction == "출고"
    assert result.gross_weight_kg == 14230.0
    assert result.tare_weight_kg == 12910.0
    assert result.net_weight_kg == 1320.0
    assert result.deduction_weight_kg == 0.0
    assert result.issuer == "(주)하은펄프"

    warning_codes = [w.code for w in result.warnings]
    assert "PRS-MISS-001" in warning_codes


def test_fuzzy_label_matching(tmp_path):
    """라벨 오탈자 유사도 매칭"""
    payload = {
        "pages": [
            {
                "lines": [
                    {"text": "총중량: 1,500 kg"},
                    {"text": "차중랑: 1,200 kg"},
                    {"text": "실중량: 300 kg"},
                ]
            }
        ]
    }
    input_path = tmp_path / "fuzzy.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = run_pipeline(str(input_path))
    assert result.gross_weight_kg == 1500.0
    assert result.tare_weight_kg == 1200.0
    assert result.net_weight_kg == 300.0


def test_multiple_time_weight_pairs(tmp_path):
    """3개 이상의 시간-무게 쌍이 있을 때 처리"""
    payload = {
        "pages": [
            {
                "lines": [
                    {"text": "01:00 1,000 kg"},
                    {"text": "01:10 800 kg"},
                    {"text": "01:20 900 kg"},
                ]
            }
        ]
    }
    input_path = tmp_path / "multi_pairs.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = run_pipeline(str(input_path))
    assert result.gross_weight_kg == 1000.0
    assert result.tare_weight_kg == 800.0
    assert result.net_weight_kg == 200.0

    warning_codes = [w.code for w in result.warnings]
    assert "PRS-MAP-001" in warning_codes
    assert "PRS-MAP-002" in warning_codes
    assert "VAL-CHK-002" in warning_codes


def test_extreme_weight_values(tmp_path):
    """음수, 0, 매우 큰 값 처리"""
    payload = {
        "pages": [
            {
                "lines": [
                    {"text": "총중량: 200,000 kg"},
                    {"text": "공차중량: 0 kg"},
                ]
            }
        ]
    }
    input_path = tmp_path / "extreme.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = run_pipeline(str(input_path))
    warning_codes = [w.code for w in result.warnings]
    assert "VAL-CHK-005" in warning_codes


def test_malformed_date_formats(tmp_path):
    """비정상적인 날짜 형식 처리"""
    payload = {
        "pages": [
            {
                "lines": [
                    {"text": "날짜: 2026-2-1"},
                    {"text": "총중량: 100 kg"},
                ]
            }
        ]
    }
    input_path = tmp_path / "malformed_date.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = run_pipeline(str(input_path))
    assert result.weigh_date is None


def test_mixed_encoding(tmp_path):
    """UTF-8 외 인코딩 혼재 시"""
    input_path = tmp_path / "mixed.json"
    input_path.write_bytes(b'{"text": "caf\xe9"}')

    with pytest.raises(ValidationError, match="파일 로드 실패"):
        run_pipeline(str(input_path))

def test_file_not_found():
    """존재하지 않는 파일 예외"""
    with pytest.raises(ValidationError, match="파일을 찾을 수 없습니다"):
        run_pipeline("nonexistent.json")

def test_invalid_json(tmp_path):
    """잘못된 JSON 형식 예외"""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{ invalid json", encoding="utf-8")
    
    result = run_pipeline(str(invalid_file))
    warning_codes = [w.code for w in result.warnings]
    assert "INP-FMT-001" in warning_codes
    assert "{ invalid json" in result.raw_text