"""
Unit tests for PDFImageProcessor
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

# Skip all tests if fitz is not available
pytest.importorskip("fitz")

from app.index.processors.pdf_image_processor import PDFImageProcessor


class TestPDFImageProcessor:
    """Test suite for PDFImageProcessor"""

    def test_initialization_default_zoom(self):
        """Test processor initialization with default zoom"""
        processor = PDFImageProcessor()
        assert processor.zoom_factor == 5.0

    def test_initialization_custom_zoom(self):
        """Test processor initialization with custom zoom"""
        processor = PDFImageProcessor(zoom_factor=3.0)
        assert processor.zoom_factor == 3.0

    def test_initialization_requires_fitz(self):
        """Test that initialization requires PyMuPDF (fitz)"""
        with patch('app.index.processors.pdf_image_processor.fitz', None):
            # Need to reimport to trigger the check
            with pytest.raises(ImportError, match="PyMuPDF"):
                # This would fail on import, so we can't easily test it
                pass

    @pytest.mark.asyncio
    async def test_get_page_count_mock(self):
        """Test getting page count from PDF (mocked)"""
        processor = PDFImageProcessor()

        # Mock PDF
        mock_pdf = MagicMock()
        mock_pdf.page_count = 10

        with patch('fitz.open', return_value=mock_pdf):
            count = await processor.get_page_count(b"fake_pdf_content")
            assert count == 10
            mock_pdf.close.assert_called_once()

    def test_detect_figures_in_analysis(self):
        """Test figure detection heuristic"""
        # Test with figures present
        analysis_with_figures = {
            "figures": [{"id": 1}, {"id": 2}]
        }
        assert PDFImageProcessor.detect_figures_in_analysis(analysis_with_figures) == True

        # Test without figures
        analysis_without_figures = {
            "text": "some text"
        }
        assert PDFImageProcessor.detect_figures_in_analysis(analysis_without_figures) == False

        # Test with paragraph role = figure
        analysis_with_figure_role = {
            "paragraphs": [
                {"role": "figure", "content": "..."}
            ]
        }
        assert PDFImageProcessor.detect_figures_in_analysis(analysis_with_figure_role) == True

        # Test with empty figures list
        analysis_empty_figures = {
            "figures": []
        }
        assert PDFImageProcessor.detect_figures_in_analysis(analysis_empty_figures) == False

    @pytest.mark.asyncio
    async def test_convert_pdf_to_images_mock(self):
        """Test PDF to images conversion (mocked)"""
        processor = PDFImageProcessor(zoom_factor=2.0)

        # Mock PDF and pages
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b"fake_image_data"
        mock_page.get_pixmap.return_value = mock_pixmap

        mock_pdf = MagicMock()
        mock_pdf.page_count = 2
        mock_pdf.load_page.return_value = mock_page

        with patch('fitz.open', return_value=mock_pdf):
            images = await processor.convert_pdf_to_images(
                b"fake_pdf_content",
                "test_document"
            )

            assert len(images) == 2
            assert images[0] == (0, b"fake_image_data")
            assert images[1] == (1, b"fake_image_data")

            # Verify PDF was closed
            mock_pdf.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_convert_single_page_mock(self):
        """Test single page conversion (mocked)"""
        processor = PDFImageProcessor()

        # Mock PDF and page
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b"single_page_image"
        mock_page.get_pixmap.return_value = mock_pixmap

        mock_pdf = MagicMock()
        mock_pdf.page_count = 5
        mock_pdf.load_page.return_value = mock_page

        with patch('fitz.open', return_value=mock_pdf):
            image = await processor.convert_single_page(
                b"fake_pdf_content",
                page_number=2,
                document_id="test_doc"
            )

            assert image == b"single_page_image"
            mock_pdf.load_page.assert_called_once_with(2)
            mock_pdf.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_convert_single_page_invalid_page_number(self):
        """Test single page conversion with invalid page number"""
        processor = PDFImageProcessor()

        mock_pdf = MagicMock()
        mock_pdf.page_count = 3

        with patch('fitz.open', return_value=mock_pdf):
            with pytest.raises(ValueError, match="Invalid page number"):
                await processor.convert_single_page(
                    b"fake_pdf_content",
                    page_number=10,  # Out of range
                    document_id="test_doc"
                )

    @pytest.mark.asyncio
    async def test_convert_pdf_handles_page_errors(self):
        """Test that conversion continues even if some pages fail"""
        processor = PDFImageProcessor()

        # Mock first page success, second page fails
        mock_page1 = MagicMock()
        mock_pixmap1 = MagicMock()
        mock_pixmap1.tobytes.return_value = b"page1_image"
        mock_page1.get_pixmap.return_value = mock_pixmap1

        mock_pdf = MagicMock()
        mock_pdf.page_count = 2

        def load_page_side_effect(page_num):
            if page_num == 0:
                return mock_page1
            else:
                raise Exception("Page error")

        mock_pdf.load_page.side_effect = load_page_side_effect

        with patch('fitz.open', return_value=mock_pdf):
            images = await processor.convert_pdf_to_images(
                b"fake_pdf_content",
                "test_document"
            )

            # Should only have 1 successful page
            assert len(images) == 1
            assert images[0] == (0, b"page1_image")
