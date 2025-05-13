"""
Test configuration file for pytest
"""

import pytest


# Define pytest configuration to filter warnings
def pytest_addoption(parser):
    """Add options to pytest command line."""
    parser.addoption(
        "--no-warnings",
        action="store_true",
        default=True,
        help="Disable warning capture",
    )


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """Configure pytest."""
    # Disable warning capture
    config.option.showwarning = False
    config.option.filterwarnings = ["ignore::DeprecationWarning"]
