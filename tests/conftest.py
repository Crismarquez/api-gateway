"""
Pytest configuration and fixtures
"""

import pytest
import sys
from pathlib import Path

# Add backend/app to Python path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF content for testing (minimal valid PDF)"""
    # This is a minimal valid PDF file
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
190
%%EOF"""


@pytest.fixture
def sample_image_bytes():
    """Sample image bytes for testing"""
    # Minimal 1x1 JPEG image
    return bytes.fromhex(
        'ffd8ffe000104a46494600010101004800480000ffdb004300080606070605080707070909'
        '080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30'
        '313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d0d1832211c21323232'
        '32323232323232323232323232323232323232323232323232323232323232323232323232'
        '32323232323232323232323232ffc00011080001000103012200021101031101ffc4001500'
        '0101000000000000000000000000000000ffc400140100010000000000000000000000000000'
        '00ffda000c03010002110311003f00bf800ffd9'
    )


@pytest.fixture
def mock_azure_di_service():
    """Mock Azure Document Intelligence service"""
    from unittest.mock import AsyncMock, MagicMock
    from app.index.dto import DocumentIntelligenceResult

    mock_service = AsyncMock()
    mock_service.analyze_document = AsyncMock(return_value=DocumentIntelligenceResult(
        document_id="test_doc",
        extracted_text="# Test Document\n\nThis is test content.",
        tables=[],
        key_value_pairs=[],
        confidence_scores={"overall": 0.95},
        processing_time=1.5,
        page_count=1,
        language="en"
    ))

    return mock_service


@pytest.fixture
def mock_storage_service():
    """Mock storage service"""
    from unittest.mock import AsyncMock

    mock_storage = AsyncMock()
    mock_storage.download_blob = AsyncMock(return_value=b"fake_document_content")
    mock_storage.upload_or_replace_blob = AsyncMock()
    mock_storage.blob_exists = AsyncMock(return_value=True)

    return mock_storage


@pytest.fixture
def mock_database_service():
    """Mock database service"""
    from unittest.mock import AsyncMock

    mock_db = AsyncMock()
    mock_db.get_document = AsyncMock(return_value={
        "document_id": "test_doc_123",
        "document_name": "test.pdf",
        "domain_id": "test_domain",
        "stage": "raw",
        "metadata": {}
    })
    mock_db.update_document_stage = AsyncMock(return_value=True)

    return mock_db
