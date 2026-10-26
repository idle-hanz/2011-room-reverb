def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: longer than about 5 s. Default pytest skips these. "
        "Before a push: pytest -m slow",
    )
