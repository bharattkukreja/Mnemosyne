from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mnemosyne-cli",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A CLI tool for automatically capturing conversations with Claude/Cursor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mnemosyne",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "rich>=13.0.0",
        "watchdog>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mnemosyne=mnemosyne.cli:cli",
        ],
    },
)
