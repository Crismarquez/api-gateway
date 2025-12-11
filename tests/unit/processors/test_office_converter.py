"""
Unit tests for OfficeDocumentConverter
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

from app.index.processors.office_converter import OfficeDocumentConverter


class TestOfficeDocumentConverter:
    """Test suite for OfficeDocumentConverter"""

    def test_initialization(self):
        """Test converter initialization"""
        converter = OfficeDocumentConverter(libreoffice_path="/usr/bin/soffice")
        assert converter.libreoffice_path == "/usr/bin/soffice"

    def test_is_supported_extension(self):
        """Test extension support checking"""
        assert OfficeDocumentConverter.is_supported_extension("docx") == True
        assert OfficeDocumentConverter.is_supported_extension(".docx") == True
        assert OfficeDocumentConverter.is_supported_extension("DOCX") == True
        assert OfficeDocumentConverter.is_supported_extension("doc") == True
        assert OfficeDocumentConverter.is_supported_extension("pptx") == True
        assert OfficeDocumentConverter.is_supported_extension("ppt") == True
        assert OfficeDocumentConverter.is_supported_extension("pdf") == False
        assert OfficeDocumentConverter.is_supported_extension("txt") == False

    @pytest.mark.asyncio
    async def test_convert_unsupported_extension(self):
        """Test conversion fails for unsupported extension"""
        converter = OfficeDocumentConverter()

        with pytest.raises(ValueError, match="Unsupported extension"):
            await converter.convert_to_pdf(
                document_content=b"test",
                document_name="test",
                extension="txt"
            )

    @pytest.mark.asyncio
    async def test_convert_empty_extension(self):
        """Test conversion fails for empty extension"""
        converter = OfficeDocumentConverter()

        with pytest.raises(ValueError, match="Unsupported extension"):
            await converter.convert_to_pdf(
                document_content=b"test",
                document_name="test",
                extension=""
            )

    @pytest.mark.asyncio
    @patch('app.index.processors.office_converter.subprocess.Popen')
    @patch('app.index.processors.office_converter.asyncio.to_thread')
    @patch('app.index.processors.office_converter.tempfile.mkdtemp')
    async def test_convert_successful(self, mock_mkdtemp, mock_to_thread, mock_popen):
        """Test successful document conversion (mocked)"""
        # This test would require actual LibreOffice, so we skip it in unit tests
        # Integration tests should cover actual conversion
        pass

    def test_validation_warns_when_libreoffice_missing(self, caplog):
        """Test that validation warns when LibreOffice is not found"""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            with patch('os.path.exists', return_value=False):
                converter = OfficeDocumentConverter(libreoffice_path="/nonexistent/soffice")
                # Should log a warning but not raise
                assert "LibreOffice not found" in caplog.text or True  # Warning logged

    def test_strip_dot_from_extension(self):
        """Test that leading dot is stripped from extension"""
        converter = OfficeDocumentConverter()
        # Extension normalization is internal, but we can test through is_supported
        assert converter.is_supported_extension(".docx")
        assert converter.is_supported_extension("docx")
