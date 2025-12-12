"""
Unit tests for favicon availability and proper serving.

Tests verify that both favicon.ico and favicon.svg are:
- Accessible via HTTP
- Served with correct content type
- Return valid SVG content
- Available at root path (/)
"""

import pytest
import requests
from pathlib import Path


# Base URL for the frontend (Vite dev server)
FRONTEND_URL = "http://localhost:3001"


class TestFavicon:
    """Test suite for favicon serving."""

    def test_favicon_ico_exists(self):
        """Test that favicon.ico is accessible."""
        response = requests.get(f"{FRONTEND_URL}/favicon.ico")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_favicon_svg_exists(self):
        """Test that favicon.svg is accessible."""
        response = requests.get(f"{FRONTEND_URL}/favicon.svg")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_favicon_ico_content_type(self):
        """Test that favicon.ico has correct content type."""
        response = requests.get(f"{FRONTEND_URL}/favicon.ico")
        # Vite serves .ico files with image/x-icon content type (standard)
        content_type = response.headers.get("content-type", "").lower()
        assert "icon" in content_type or "svg" in content_type, \
            f"Expected icon or SVG content type, got {response.headers.get('content-type')}"

    def test_favicon_svg_content_type(self):
        """Test that favicon.svg has correct content type."""
        response = requests.get(f"{FRONTEND_URL}/favicon.svg")
        assert "svg" in response.headers.get("content-type", "").lower(), \
            f"Expected SVG content type, got {response.headers.get('content-type')}"

    def test_favicon_ico_is_valid_svg(self):
        """Test that favicon.ico contains valid SVG content."""
        response = requests.get(f"{FRONTEND_URL}/favicon.ico")
        content = response.text
        assert content.startswith("<svg"), "favicon.ico should start with <svg tag"
        assert "xmlns" in content, "favicon.ico should have xmlns attribute"
        assert "</svg>" in content, "favicon.ico should have closing </svg> tag"

    def test_favicon_svg_is_valid_svg(self):
        """Test that favicon.svg contains valid SVG content."""
        response = requests.get(f"{FRONTEND_URL}/favicon.svg")
        content = response.text
        assert content.startswith("<svg"), "favicon.svg should start with <svg tag"
        assert "xmlns" in content, "favicon.svg should have xmlns attribute"
        assert "</svg>" in content, "favicon.svg should have closing </svg> tag"

    def test_favicon_contains_graph_elements(self):
        """Test that favicon contains expected graph structure elements."""
        response = requests.get(f"{FRONTEND_URL}/favicon.svg")
        content = response.text
        # Check for graph structure elements (circles for nodes, lines for edges)
        assert "<circle" in content, "Favicon should contain circle elements (nodes)"
        assert "<line" in content, "Favicon should contain line elements (edges)"

    def test_favicon_files_exist_in_public_dir(self):
        """Test that favicon files exist in the public directory."""
        public_dir = Path(__file__).parent.parent / "frontend" / "public"
        
        favicon_ico = public_dir / "favicon.ico"
        assert favicon_ico.exists(), f"favicon.ico should exist at {favicon_ico}"
        
        favicon_svg = public_dir / "favicon.svg"
        assert favicon_svg.exists(), f"favicon.svg should exist at {favicon_svg}"

    def test_index_html_references_favicon(self):
        """Test that index.html correctly references the favicon."""
        index_html = Path(__file__).parent.parent / "frontend" / "index.html"
        assert index_html.exists(), "index.html should exist"
        
        content = index_html.read_text()
        assert 'href="/favicon.svg"' in content, \
            "index.html should reference /favicon.svg"
        assert 'type="image/svg+xml"' in content, \
            "index.html should specify SVG content type"


class TestFaviconIntegration:
    """Integration tests for favicon in application context."""

    def test_root_page_loads_with_favicon(self):
        """Test that the root page loads and includes favicon link."""
        response = requests.get(FRONTEND_URL)
        assert response.status_code == 200, "Root page should load successfully"
        
        content = response.text
        assert 'href="/favicon.svg"' in content, \
            "Root page HTML should include favicon link"

    def test_no_404_errors_for_favicon(self):
        """Test that requesting favicon doesn't cause 404 errors."""
        # Test both .ico and .svg
        ico_response = requests.get(f"{FRONTEND_URL}/favicon.ico")
        svg_response = requests.get(f"{FRONTEND_URL}/favicon.svg")
        
        assert ico_response.status_code != 404, "favicon.ico should not return 404"
        assert svg_response.status_code != 404, "favicon.svg should not return 404"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
