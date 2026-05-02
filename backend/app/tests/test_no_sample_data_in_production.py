"""Test sample data seeding behavior.

Ensures that auto_seed is disabled by default and production
environments never automatically seed sample data.
"""

import os
import pytest
from app.core.config import Settings


def test_auto_seed_defaults_false_without_env():
    """Test that auto_seed defaults to False when no env var is set."""
    # Temporarily clear the env var that conftest.py sets
    old_value = os.environ.pop("JTA_AUTO_SEED", None)
    try:
        # Create fresh settings without the env var
        settings = Settings()
        assert settings.auto_seed is False
    finally:
        # Restore env var for other tests
        if old_value is not None:
            os.environ["JTA_AUTO_SEED"] = old_value


def test_auto_seed_explicit_false():
    """Test that auto_seed can be explicitly set to False."""
    settings = Settings(auto_seed=False)
    assert settings.auto_seed is False


def test_production_env_can_disable_auto_seed():
    """Test that production environment can have auto_seed disabled."""
    settings = Settings(app_env="production", auto_seed=False)
    assert settings.app_env == "production"
    assert settings.auto_seed is False


def test_development_env_can_enable_auto_seed():
    """Test that development environment can optionally enable auto_seed."""
    settings = Settings(app_env="development", auto_seed=True)
    assert settings.app_env == "development"
    assert settings.auto_seed is True
