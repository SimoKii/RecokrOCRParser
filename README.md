# Recokr OCR Parser

OCR JSON 입력을 받아 계근지(계량표) 필드를 파싱/정규화하는 파이썬 프로젝트입니다.

## 실행 방법

### 빠른 실행 (Makefile 사용)
```
make setup
make run INPUT=inputs/sample_01.json OUTPUT=outputs/sample_01.parsed.json
make run INPUT=inputs/sample_02.json OUTPUT=outputs/sample_02.parsed.json
make run INPUT=inputs/sample_03.json OUTPUT=outputs/sample_03.parsed.json
make run INPUT=inputs/sample_04.json OUTPUT=outputs/sample_04.parsed.json

```

### 수동 실행 (Makefile 없이)
```
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
python -m recokr_ocr_parser --input inputs/sample_01.json --output outputs/sample_01.parsed.json
python -m recokr_ocr_parser --input inputs/sample_02.json --output outputs/sample_02.parsed.json
python -m recokr_ocr_parser --input inputs/sample_03.json --output outputs/sample_03.parsed.json
python -m recokr_ocr_parser --input inputs/sample_04.json --output outputs/sample_04.parsed.json

```

### 테스트 실행
```
pip install pytest
make test
```

## 의존성 / 환경

- Python: 3.10+ (권장 3.11 이상)
- 빌드: `setuptools>=68.0` (pyproject.toml 기준)
- 런타임: 표준 라이브러리만 사용
- 테스트: `pytest` (테스트 실행 시에만 필요)

## 주요 가정 및 설계

### 개발 문서
- [Recokr OCR Parser 개발 문서](https://namu00.notion.site/A-2feeaffb9b0e8090b7a8f8769d21b5a0)
- 설계/개발 과정에서 정리한 문서로, 입력 스키마 분석, 파싱 규칙 상세, 경고/신뢰도 기준, 테스트 전략 등의 내용을 포함하고 있습니다.

### 핵심 설계 원칙
- **입력 유연성**: `pages[].lines[].text` → `pages[].text` → 최상위 `text` 순서로 폴백
- **견고한 복구**: JSON 파싱 실패 시 텍스트 기반 파싱으로 자동 전환
- **노이즈 제거**: 빈 문자열, `N`, `없다` 등 무의미한 라인 자동 필터링
- **유사도 매칭**: 라벨 오탈자 자동 보정 (임계값: 긴 라벨 0.85, 짧은 라벨 0.66)
- **다중 포맷 지원**: `HH:MM(:SS)`, `HH시 MM분`, 쉼표/공백 구분 숫자
- **자동 계산**: 총중량 - 공차중량 = 실중량 (허용 오차 1kg)
- **표준화된 경고**: `STAGE-CATEGORY-NNN` 형식의 구조화된 에러 코드

## 한계 및 개선 아이디어

- 라벨/키워드 사전 의존도가 높아 신규 양식 추가 시 수동 업데이트가 필요
  - 개선: 라벨 사전 외부화, 문서 타입별 템플릿 분리
- 테이블/복수 페이지 문서에서 라인 순서가 어긋나는 경우 오인식 가능
  - 개선: 레이아웃/박스 좌표 활용, 페이지/표 단위 정렬 보정
- 단위가 없는 무게, `톤`/`t` 같은 단위는 현재 미지원
  - 개선: 단위 추론 규칙 추가, `kg`/`t` 단위 변환 지원
- 차량번호/거래처/품명 정규화 규칙이 제한적이며 OCR 오탈자에 취약
  - 개선: 정규화 규칙 확장, 사전 기반 보정, 학습 기반 분류 도입

## 프로젝트 구조
```
recokr-ocr-parser/
├── src/recokr_ocr_parser/
│   ├── __init__.py       # 패키지 초기화
│   ├── __main__.py       # python -m 진입점
│   ├── cli.py            # CLI 인터페이스
│   ├── constants.py      # 라벨/키워드/임계값
│   ├── normalizer.py     # 텍스트 정규화
│   ├── preprocessor.py   # 입력 전처리
│   ├── parser.py         # 라벨/패턴 파싱
│   ├── validator.py      # 검증/경고/신뢰도
│   ├── schema.py         # 출력 스키마
│   └── pipeline.py       # 오케스트레이션
├── tests/
│   └── test_pipeline.py  # 통합 테스트
├── inputs/               # 샘플 입력 파일
├── outputs/              # 파싱 결과 출력
```
