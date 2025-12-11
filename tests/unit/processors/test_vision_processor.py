"""
Unit tests for VisionProcessor
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import base64

from app.index.processors.vision_processor import VisionProcessor


class TestVisionProcessor:
    """Test suite for VisionProcessor"""

    def test_initialization(self):
        """Test vision processor initialization"""
        processor = VisionProcessor(
            azure_openai_endpoint="test-endpoint",
            AZURE_OPENAI_API_KEY="test-key",
            deployment_name="gpt-4o"
        )

        assert processor.azure_openai_endpoint == "test-endpoint"
        assert processor.AZURE_OPENAI_API_KEY == "test-key"
        assert processor.deployment_name == "gpt-4o"
        assert processor.retries == 5
        assert processor.timeout == 90.0

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters"""
        processor = VisionProcessor(
            azure_openai_endpoint="test",
            AZURE_OPENAI_API_KEY="key",
            deployment_name="custom-model",
            api_version="2024-12-01",
            retries=3,
            timeout=60.0
        )

        assert processor.deployment_name == "custom-model"
        assert processor.api_version == "2024-12-01"
        assert processor.retries == 3
        assert processor.timeout == 60.0

    def test_base_url_construction(self):
        """Test that base URL is correctly constructed"""
        processor = VisionProcessor(
            azure_openai_endpoint="my-service",
            AZURE_OPENAI_API_KEY="key",
            deployment_name="gpt-4o",
            api_version="2024-06-01"
        )

        expected_url = (
            "https://my-service.openai.azure.com/openai/"
            "deployments/gpt-4o/chat/completions"
            "?api-version=2024-06-01"
        )
        assert processor.base_url == expected_url

    @pytest.mark.asyncio
    async def test_analyze_image_url_success(self):
        """Test successful image analysis from URL"""
        processor = VisionProcessor(
            azure_openai_endpoint="test",
            AZURE_OPENAI_API_KEY="key"
        )

        # Mock the aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'message': {
                    'content': '# Test Markdown\n\nTest content'
                }
            }]
        })
        mock_response.raise_for_status = Mock()

        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await processor.analyze_image_url("https://example.com/image.jpg")

            assert result == '# Test Markdown\n\nTest content'
            mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_image_bytes_success(self):
        """Test successful image analysis from bytes"""
        processor = VisionProcessor(
            azure_openai_endpoint="test",
            AZURE_OPENAI_API_KEY="key"
        )

        # Mock the aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'choices': [{
                'message': {
                    'content': '# Image Analysis\n\nContent from bytes'
                }
            }]
        })
        mock_response.raise_for_status = Mock()

        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await processor.analyze_image_bytes(
                b"fake_image_data",
                image_format="jpeg"
            )

            assert result == '# Image Analysis\n\nContent from bytes'

            # Verify the request payload includes base64 encoded image
            call_args = mock_session.post.call_args
            payload = call_args.kwargs['json']
            image_url = payload['messages'][0]['content'][1]['image_url']['url']
            assert image_url.startswith('data:image/jpeg;base64,')

    @pytest.mark.asyncio
    async def test_analyze_with_custom_prompt(self):
        """Test analysis with custom prompt"""
        processor = VisionProcessor(
            azure_openai_endpoint="test",
            AZURE_OPENAI_API_KEY="key"
        )

        custom_prompt = "Custom analysis instructions"

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            'choices': [{'message': {'content': 'result'}}]
        })
        mock_response.raise_for_status = Mock()

        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch('aiohttp.ClientSession', return_value=mock_session):
            await processor.analyze_image_url(
                "https://example.com/image.jpg",
                custom_prompt=custom_prompt
            )

            # Verify custom prompt was used
            call_args = mock_session.post.call_args
            payload = call_args.kwargs['json']
            text_content = payload['messages'][0]['content'][0]['text']
            assert text_content == custom_prompt

    @pytest.mark.asyncio
    async def test_retry_on_http_error(self):
        """Test retry logic on HTTP errors"""
        processor = VisionProcessor(
            azure_openai_endpoint="test",
            AZURE_OPENAI_API_KEY="key",
            retries=3
        )

        # Mock response that fails twice then succeeds
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_resp = AsyncMock()
            if call_count < 3:
                # First 2 calls fail
                from aiohttp import ClientResponseError
                mock_resp.raise_for_status.side_effect = ClientResponseError(
                    request_info=Mock(),
                    history=(),
                    status=500,
                    message="Server Error"
                )
            else:
                # Third call succeeds
                mock_resp.json = AsyncMock(return_value={
                    'choices': [{'message': {'content': 'success'}}]
                })
                mock_resp.raise_for_status = Mock()

            return mock_resp

        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                result = await processor.analyze_image_url("https://example.com/image.jpg")

                assert result == 'success'
                assert call_count == 3  # Failed twice, succeeded on third

    @pytest.mark.asyncio
    async def test_analyze_multiple_images_sequential(self):
        """Test analyzing multiple images sequentially"""
        processor = VisionProcessor(
            azure_openai_endpoint="test",
            AZURE_OPENAI_API_KEY="key"
        )

        images = [
            (0, b"image1"),
            (1, b"image2"),
            (2, b"image3")
        ]

        call_count = 0

        async def mock_analyze(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return f"Result {call_count}"

        with patch.object(processor, 'analyze_image_bytes', mock_analyze):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                results = await processor.analyze_multiple_images(images)

                assert len(results) == 3
                assert results[0] == (0, "Result 1")
                assert results[1] == (1, "Result 2")
                assert results[2] == (2, "Result 3")

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries"""
        processor = VisionProcessor(
            azure_openai_endpoint="test",
            AZURE_OPENAI_API_KEY="key",
            retries=2
        )

        async def mock_post_fail(*args, **kwargs):
            from aiohttp import ClientResponseError
            mock_resp = AsyncMock()
            mock_resp.raise_for_status.side_effect = ClientResponseError(
                request_info=Mock(),
                history=(),
                status=500,
                message="Error"
            )
            return mock_resp

        mock_session = MagicMock()
        mock_session.post = mock_post_fail
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(Exception, match="Vision API request failed"):
                    await processor.analyze_image_url("https://example.com/image.jpg")
