from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="options-simulator",
    version="0.1.0",
    author="Options Simulator",
    description="CLI tool for simulating tail risk hedging with options",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scipy>=1.11.0",
        "py-vollib>=1.0.0",
        "mibian>=0.1.0",
        "yfinance>=0.2.0",
        "alpha-vantage>=2.3.0",
        "requests>=2.31.0",
        "click>=8.1.0",
        "rich>=13.5.0",
        "tabulate>=0.9.0",
        "pydantic>=2.3.0",
        "pydantic-settings>=2.0.0",
        "python-dotenv>=1.0.0",
        "matplotlib>=3.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "options-sim=options_simulator.cli.main:cli",
        ],
    },
)