"""Pytest configuration and fixtures."""
import pytest
import os
import tempfile


@pytest.fixture(autouse=True)
def reset_db_env():
    """Reset database environment for each test."""
    # Store original value
    original = os.environ.get('DATABASE_URL')

    yield

    # Restore original value
    if original:
        os.environ['DATABASE_URL'] = original
    elif 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
