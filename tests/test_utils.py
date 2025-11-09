import pytest
import requests
from shared.utils import extract_domain, get_article_metadata

def test_extract_domain_simple():
    """Tests extraction from a standard URL."""
    url = "https://www.google.com/search?q=test"
    assert extract_domain(url) == "google.com"

def test_extract_domain_no_subdomain():
    """Tests extraction from a URL without 'www'."""
    url = "http://example.org"
    assert extract_domain(url) == "example.org"

def test_extract_domain_with_path():
    """Tests that the path is correctly ignored."""
    url = "https://github.com/user/repo"
    assert extract_domain(url) == "github.com"

def test_extract_domain_no_protocol():
    """Tests that the function handles URLs without a protocol."""
    # The `extract_domain` function expects a protocol, so the result
    # of urlparse might be unexpected. This test documents the behavior.
    url = "www.test.com"
    assert extract_domain(url) == "test.com"

def test_extract_domain_empty_string():
    """Tests that an empty string returns an empty string."""
    url = ""
    assert extract_domain(url) == ""

def test_extract_domain_invalid_url():
    """Tests that an invalid input does not cause an error and returns an empty string."""
    url = "non-un-url"
    assert extract_domain(url) == ""

# --- Tests for get_article_metadata ---

def test_get_article_metadata_success(mocker):
    """
    Tests successful metadata extraction by mocking the network request.
    """
    # 1. Prepare fake HTML content
    fake_html = """
    <html>
        <head>
            <title>Test Title</title>
            <meta property="og:title" content="OG Test Title">
            <meta name="description" content="Test Description">
            <meta property="og:image" content="https://example.com/image.jpg">
        </head>
        <body></body>
    </html>
    """
    
    # 2. Mock both requests.head and requests.get
    mock_head_response = mocker.Mock()
    mock_head_response.headers = {'Content-Type': 'text/html'}
    mocker.patch('requests.head', return_value=mock_head_response)

    mock_get_response = mocker.Mock()
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.content = fake_html.encode('utf-8')
    mocker.patch('requests.get', return_value=mock_get_response)

    # 3. Call the function
    metadata = get_article_metadata("https://example.com")

    # 4. Assert the results
    assert metadata['title'] == "OG Test Title" # Prefers 'og:title'
    assert metadata['description'] == "Test Description"
    assert metadata['image_url'] == "https://example.com/image.jpg"
    assert metadata['domain'] == "example.com"

def test_get_article_metadata_non_html(mocker):
    """
    Tests that the function correctly handles non-HTML content like a PDF.
    """
    # Mock the HEAD request to return a non-html content type
    mock_head_response = mocker.Mock()
    mock_head_response.headers = {'Content-Type': 'application/pdf'}
    mocker.patch('requests.head', return_value=mock_head_response)
    mock_get = mocker.patch('requests.get') # Also mock get to ensure it's not called

    metadata = get_article_metadata("https://example.com/document.pdf")

    assert "Link to file" in metadata['title']
    assert "application/pdf" in metadata['description']
    mock_get.assert_not_called() # Crucially, the GET request should be skipped

def test_get_article_metadata_network_error(mocker):
    """
    Tests that the function handles a network error gracefully.
    """
    # Mock requests.get to raise an exception
    mocker.patch('requests.head', side_effect=requests.exceptions.RequestException("Network Error"))
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Network Error"))

    metadata = get_article_metadata("https://example.com")

    assert "Error:" in metadata['title']
    assert "Network Error" in metadata['description']

def test_get_article_metadata_no_protocol(mocker):
    """Tests that the function adds 'https://' to a URL without a protocol."""
    mocker.patch('requests.head', side_effect=requests.exceptions.RequestException("Network Error"))
    mock_get = mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Network Error"))

    get_article_metadata("example.com")

    # Assert that requests.get was called with the corrected URL
    mock_get.assert_called_once_with('https://example.com', headers=mocker.ANY, timeout=10, allow_redirects=True)
