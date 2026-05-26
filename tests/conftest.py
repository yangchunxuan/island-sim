"""pytest 配置：注册自定义标记"""

import pytest


def pytest_configure(config):
    """注册自定义标记"""
    config.addinivalue_line("markers", "slow: 长期运行测试，默认跳过")
