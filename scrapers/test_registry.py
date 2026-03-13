"""
Tests for the scraper registry.

Validates that registry.yaml is well-formed, all referenced modules exist,
and each module has a callable main() function.

Run with: cd scrapers && python -m pytest test_registry.py -v
"""

import importlib
import os
import sys
from unittest.mock import MagicMock

import pytest
import yaml

# Add scrapers directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Set dummy env vars so imports don't crash
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "fake-key")

# Mock playwright before importing scraper modules
sys.modules["playwright"] = MagicMock()
sys.modules["playwright.async_api"] = MagicMock()


REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "registry.yaml")


@pytest.fixture
def registry():
    """Load and return the registry data."""
    with open(REGISTRY_PATH) as f:
        data = yaml.safe_load(f)
    return data


class TestRegistryStructure:
    """Verify registry.yaml is valid and complete."""

    def test_registry_file_exists(self):
        assert os.path.exists(REGISTRY_PATH), "registry.yaml not found"

    def test_has_scrapers_key(self, registry):
        assert "scrapers" in registry, "registry.yaml must have a 'scrapers' key"

    def test_scrapers_is_dict(self, registry):
        assert isinstance(registry["scrapers"], dict), "'scrapers' must be a dict"

    def test_at_least_one_scraper(self, registry):
        assert len(registry["scrapers"]) > 0, "registry must have at least one scraper"

    def test_required_fields(self, registry):
        """Every scraper entry must have name, module, table, needs_browser, enabled."""
        required = {"name", "module", "table", "platform", "needs_browser", "enabled"}
        for key, config in registry["scrapers"].items():
            missing = required - set(config.keys())
            assert not missing, f"Scraper '{key}' missing fields: {missing}"

    def test_table_is_valid(self, registry):
        """Table must be one of the known Supabase tables."""
        valid_tables = {"meetings", "comment_periods", "agenda_summaries"}
        for key, config in registry["scrapers"].items():
            assert config["table"] in valid_tables, (
                f"Scraper '{key}' has invalid table '{config['table']}'. "
                f"Valid: {valid_tables}"
            )

    def test_enabled_is_bool(self, registry):
        for key, config in registry["scrapers"].items():
            assert isinstance(config["enabled"], bool), (
                f"Scraper '{key}' enabled must be bool, got {type(config['enabled'])}"
            )

    def test_needs_browser_is_bool(self, registry):
        for key, config in registry["scrapers"].items():
            assert isinstance(config["needs_browser"], bool), (
                f"Scraper '{key}' needs_browser must be bool"
            )

    def test_depends_on_references_valid_keys(self, registry):
        """If depends_on is set, all entries must be valid scraper keys."""
        all_keys = set(registry["scrapers"].keys())
        for key, config in registry["scrapers"].items():
            deps = config.get("depends_on", [])
            if deps:
                for dep in deps:
                    assert dep in all_keys, (
                        f"Scraper '{key}' depends on '{dep}' which is not in registry"
                    )


class TestRegistryModules:
    """Verify all referenced modules exist and have main()."""

    def test_module_files_exist(self, registry):
        """Each module referenced in registry must have a .py file."""
        scrapers_dir = os.path.dirname(__file__)
        for key, config in registry["scrapers"].items():
            module_file = os.path.join(scrapers_dir, f"{config['module']}.py")
            assert os.path.exists(module_file), (
                f"Scraper '{key}' references module '{config['module']}' "
                f"but {module_file} does not exist"
            )

    def test_modules_have_main(self, registry):
        """Each module must have a callable main() function."""
        for key, config in registry["scrapers"].items():
            mod = importlib.import_module(config["module"])
            assert hasattr(mod, "main"), (
                f"Module '{config['module']}' (scraper '{key}') has no main() function"
            )
            assert callable(mod.main), (
                f"Module '{config['module']}' main is not callable"
            )
