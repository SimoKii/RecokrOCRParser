from __future__ import annotations

from pathlib import Path

from setuptools import find_packages, setup


def read_readme() -> str:
    readme_path = Path(__file__).parent / "README.md"
    if not readme_path.exists():
        return ""
    return readme_path.read_text(encoding="utf-8")


setup(
    name="recokr-ocr-parser",
    version="0.1.0",
    description="OCR parsing utilities for recokr assignment",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    python_requires=">=3.10",
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    install_requires=[],
)
