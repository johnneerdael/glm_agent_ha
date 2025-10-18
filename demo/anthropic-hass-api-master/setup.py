"""Setup for Anthropic-hass-api integration."""
from setuptools import setup, find_packages

setup(
    name="anthropic-hass-api",
    version="1.0.0",
    description="Home Assistant integration for Anthropic Claude",
    url="https://github.com/slawa19/anthropic-hass-api",
    author="slawa19",
    author_email="",
    license="GPL-3.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "requests>=2.25.0",
    ],
    zip_safe=False,
)