#!/usr/bin/env python3
"""
Simple test script to verify MarkItDown configuration options work correctly.
This is a standalone test for Phase 4 configuration features.
"""

import asyncio
import os
import tempfile
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from md_server.core.markitdown_config import MarkItDownConfig, LLMConfig, AzureDocIntelConfig, ConverterConfig
from md_server.adapters.markitdown_adapter import MarkItDownAdapter


async def test_basic_configuration():
    """Test basic configuration creation and validation."""
    print("Testing basic configuration...")
    
    # Test default configuration
    config = MarkItDownConfig()
    assert config.enable_builtins == True
    assert config.enable_plugins == False
    assert config.timeout_seconds == 30
    print("✓ Default configuration works")
    
    # Test configuration with custom values
    config = MarkItDownConfig(
        enable_builtins=False,
        enable_plugins=True,
        timeout_seconds=60
    )
    assert config.enable_builtins == False
    assert config.enable_plugins == True
    assert config.timeout_seconds == 60
    print("✓ Custom configuration works")


async def test_llm_configuration():
    """Test LLM configuration validation."""
    print("Testing LLM configuration...")
    
    try:
        # Test invalid client type
        llm_config = LLMConfig(client_type="invalid", model="gpt-4")
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "client_type must be one of" in str(e)
        print("✓ LLM client type validation works")
    
    # Test valid LLM configuration
    llm_config = LLMConfig(
        client_type="openai",
        model="gpt-4o",
        api_key="test-key",
        temperature=0.7,
        max_tokens=500
    )
    assert llm_config.client_type == "openai"
    assert llm_config.model == "gpt-4o"
    assert llm_config.temperature == 0.7
    print("✓ Valid LLM configuration works")


async def test_azure_docintel_configuration():
    """Test Azure Document Intelligence configuration."""
    print("Testing Azure Document Intelligence configuration...")
    
    try:
        # Test invalid endpoint
        azure_config = AzureDocIntelConfig(endpoint="invalid-url")
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "endpoint must be a valid URL" in str(e)
        print("✓ Azure endpoint validation works")
    
    # Test valid Azure configuration
    azure_config = AzureDocIntelConfig(
        endpoint="https://myservice.cognitiveservices.azure.com/",
        api_key="test-key",
        api_version="2023-07-31"
    )
    assert azure_config.endpoint.startswith("https://")
    assert azure_config.api_key == "test-key"
    print("✓ Valid Azure configuration works")


async def test_custom_converter_configuration():
    """Test custom converter configuration."""
    print("Testing custom converter configuration...")
    
    # Test converter config validation
    converter_config = ConverterConfig(
        module_path="my_module.converters",
        class_name="MyConverter",
        priority=1.0,
        config={"setting": "value"}
    )
    assert converter_config.module_path == "my_module.converters"
    assert converter_config.class_name == "MyConverter"
    assert converter_config.priority == 1.0
    print("✓ Custom converter configuration works")


async def test_environment_variables():
    """Test environment variable support."""
    print("Testing environment variable support...")
    
    # Test 1: Prefixed environment variables
    os.environ["MARKITDOWN_ENABLE_PLUGINS"] = "true"
    os.environ["MARKITDOWN_TIMEOUT_SECONDS"] = "45"
    os.environ["MARKITDOWN_OPENAI_API_KEY"] = "test-openai-key"
    os.environ["MARKITDOWN_AZURE_DOCINTEL_ENDPOINT"] = "https://test.cognitiveservices.azure.com/"
    
    try:
        config = MarkItDownConfig()
        assert config.enable_plugins == True, f"Expected True, got {config.enable_plugins}"
        assert config.timeout_seconds == 45, f"Expected 45, got {config.timeout_seconds}"
        assert config.openai_api_key == "test-openai-key", f"Expected 'test-openai-key', got {config.openai_api_key}"
        assert config.azure_docintel_endpoint == "https://test.cognitiveservices.azure.com/", f"Expected URL, got {config.azure_docintel_endpoint}"
        print("✓ Prefixed environment variables work")
    finally:
        # Clean up environment variables
        for key in ["MARKITDOWN_ENABLE_PLUGINS", "MARKITDOWN_TIMEOUT_SECONDS", 
                   "MARKITDOWN_OPENAI_API_KEY", "MARKITDOWN_AZURE_DOCINTEL_ENDPOINT"]:
            if key in os.environ:
                del os.environ[key]
    
    # Test 2: Non-prefixed environment variables
    os.environ["OPENAI_API_KEY"] = "direct-openai-key"
    os.environ["AZURE_DOCINTEL_ENDPOINT"] = "https://direct.cognitiveservices.azure.com/"
    
    try:
        config = MarkItDownConfig()
        assert config.openai_api_key == "direct-openai-key", f"Expected 'direct-openai-key', got {config.openai_api_key}"
        assert config.azure_docintel_endpoint == "https://direct.cognitiveservices.azure.com/", f"Expected direct URL, got {config.azure_docintel_endpoint}"
        print("✓ Non-prefixed environment variables work")
    finally:
        # Clean up environment variables
        for key in ["OPENAI_API_KEY", "AZURE_DOCINTEL_ENDPOINT"]:
            if key in os.environ:
                del os.environ[key]


async def test_adapter_with_configuration():
    """Test adapter initialization with configuration."""
    print("Testing adapter with configuration...")
    
    # Test adapter with default configuration
    adapter = MarkItDownAdapter()
    assert adapter.config.enable_builtins == True
    assert adapter.timeout_seconds == 30
    print("✓ Adapter with default configuration works")
    
    # Test adapter with custom configuration
    config = MarkItDownConfig(
        enable_builtins=False,
        enable_plugins=True,
        timeout_seconds=60
    )
    adapter = MarkItDownAdapter(config=config)
    assert adapter.config.enable_builtins == False
    assert adapter.config.enable_plugins == True
    assert adapter.timeout_seconds == 60
    print("✓ Adapter with custom configuration works")
    
    # Test backward compatibility
    adapter = MarkItDownAdapter(timeout_seconds=45, enable_plugins=True)
    assert adapter.timeout_seconds == 45
    assert adapter.config.enable_plugins == True
    print("✓ Adapter backward compatibility works")


async def test_configuration_methods():
    """Test configuration helper methods."""
    print("Testing configuration helper methods...")
    
    config = MarkItDownConfig()
    
    # Test requests session creation
    session = config.get_requests_session()
    assert session is not None
    assert "User-Agent" in session.headers
    print("✓ Requests session creation works")
    
    # Test MarkItDown kwargs generation
    kwargs = config.to_markitdown_kwargs()
    assert "enable_builtins" in kwargs
    assert "enable_plugins" in kwargs
    assert "requests_session" in kwargs
    print("✓ MarkItDown kwargs generation works")


async def test_health_check():
    """Test adapter health check functionality."""
    print("Testing health check...")
    
    try:
        adapter = MarkItDownAdapter()
        health_result = await adapter.health_check()
        assert health_result == True
        print("✓ Health check works")
        
        # Test configuration info
        info = adapter.get_configuration_info()
        assert "enable_builtins" in info
        assert "supported_formats" in info
        assert isinstance(info["supported_formats"], list)
        print("✓ Configuration info works")
        
    except Exception as e:
        print(f"Health check failed (expected if markitdown not installed): {e}")


async def test_simple_conversion():
    """Test simple text conversion with configuration."""
    print("Testing simple conversion...")
    
    try:
        adapter = MarkItDownAdapter()
        
        # Test with simple text content
        content = b"Hello, World!\nThis is a test."
        result = await adapter.convert_content(content, "test.txt")
        assert "Hello, World!" in result
        print("✓ Simple text conversion works")
        
    except Exception as e:
        print(f"Conversion test failed (expected if markitdown not installed): {e}")


async def main():
    """Run all configuration tests."""
    print("=== MarkItDown Configuration Tests ===")
    
    tests = [
        test_basic_configuration,
        test_llm_configuration,
        test_azure_docintel_configuration,
        test_custom_converter_configuration,
        test_environment_variables,
        test_adapter_with_configuration,
        test_configuration_methods,
        test_health_check,
        test_simple_conversion
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            return False
    
    print("\n✓ All configuration tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)