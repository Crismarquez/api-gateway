"""
Unit tests for EnhancedBronzeProcessor.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from app.index.dto import DocumentIntelligenceResult
from app.index.processors.enhanced_bronze_processor import EnhancedBronzeProcessor


class DummyDIService:
    """Simple stub for AzureDocumentIntelligenceService used in tests."""

    def __init__(self):
        self.analyze_document = AsyncMock()


@pytest.mark.asyncio
async def test_process_uses_standard_di_when_advanced_disabled():
    """When advanced OCR is disabled, processor should use standard DI path."""
    di_service = DummyDIService()

    # Return a minimal valid DocumentIntelligenceResult
    di_service.analyze_document.return_value = DocumentIntelligenceResult(
        document_id="doc-1",
        extracted_text="baseline text",
        tables=[],
        key_value_pairs=[],
        confidence_scores={"overall": 0.9},
        processing_time=0.1,
        page_count=1,
        language="en",
    )

    processor = EnhancedBronzeProcessor(
        doc_intelligence_service=di_service, enable_advanced_ocr=False, use_gpt_vision=False
    )

    result = await processor.process(b"%PDF-1.4", "file.pdf", "doc-1")

    di_service.analyze_document.assert_awaited_once()
    assert result.extracted_text == "baseline text"
    assert result.page_count == 1


@pytest.mark.asyncio
async def test_advanced_ocr_merges_di_and_vision_text():
    """
    Advanced OCR path should keep DI text and enrich it with Vision output
    instead of replacing it completely.
    """
    di_service = DummyDIService()

    # DI result for a single "page image"
    page_di_result = DocumentIntelligenceResult(
        document_id="doc-1_page_0",
        extracted_text="DI page text",
        tables=[{"markdown": "| a |"}],  # ensure tables so heuristics can trigger if needed
        key_value_pairs=[],
        confidence_scores={"overall": 0.6},
        processing_time=0.1,
        page_count=1,
        language="en",
    )

    # For the advanced flow, DI is called on each page image
    di_service.analyze_document.return_value = page_di_result

    processor = EnhancedBronzeProcessor(
        doc_intelligence_service=di_service, enable_advanced_ocr=True, use_gpt_vision=True
    )

    # Replace PDF/image and Vision processors with simple stubs
    processor.pdf_processor = Mock()
    processor.pdf_processor.convert_pdf_to_images = AsyncMock(
        return_value=[(0, b"image-bytes-page-0")]
    )

    processor.vision_processor = Mock()
    processor.use_gpt_vision = True

    async def fake_vision(image_bytes: bytes, page_num: int) -> str:
        assert image_bytes == b"image-bytes-page-0"
        assert page_num == 0
        return "VISION DETAILS"

    processor._process_with_vision = fake_vision  # type: ignore[assignment]

    # Force Vision usage without relying on internal heuristics
    processor._should_use_vision_for_page = lambda _: True  # type: ignore[assignment]

    result = await processor._process_with_advanced_ocr(b"%PDF-1.4", "doc-1")

    # DI is called once for the single page image
    di_service.analyze_document.assert_awaited_once()

    # The combined text should contain both DI and Vision content
    text = result.extracted_text
    assert "DI page text" in text
    assert "VISION DETAILS" in text
    assert result.page_count == 1


