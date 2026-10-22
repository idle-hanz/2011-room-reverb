def pytest_configure(config):
    config.addinivalue_line("markers", "slow: real renders (30-120 s each)")
