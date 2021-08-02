"""
The ``setup`` file simply serves as a means of setting up the application for
installation and execution. The author is still fairly new to the Python project
development process, so there may be errors in this file that may need
correcting in future.
"""

from setuptools import setup, find_packages
from pathlib import Path

setup(
    name="fandomassenger",
    version="0.0.1",
    description="A mass-messaging application for Wikia/Fandom wikis",
    long_description=(Path(__file__).parent.resolve() / "README.md").read_text(
        encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/andreweissen/Fandomassenger",
    author="Andrew Eissen",
    author_email="andrew@andreweissen.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="Fandom, Wikia, MediaWiki",
    package_dir={"": "fandomassenger"},
    packages=find_packages(where="fandomassenger"),
    python_requires=">=3, <4",
    install_requires=["requests"],
    entry_points={
        "console_scripts": [
            "main=fandomassenger:main",
        ],
    },
    project_urls={
        "Bug reports": "https://github.com/andreweissen/Fandomassenger/issues",
        "Source": "https://github.com/andreweissen/Fandomassenger/"
    }
)
