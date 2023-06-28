"""Set up the hypha_services package."""
import json
from pathlib import Path

from setuptools import find_packages, setup

DESCRIPTION = "A collection of hypha_services."

ROOT_DIR = Path(__file__).parent.resolve()
README_FILE = ROOT_DIR / "README.md"
LONG_DESCRIPTION = README_FILE.read_text(encoding="utf-8")
VERSION_FILE = ROOT_DIR / "hypha_services" / "VERSION"
VERSION = json.loads(VERSION_FILE.read_text())["version"]

REQUIRES = []

setup(
    name="hypha_services",
    version=VERSION,
    url="https://github.com/amun-ai/hypha_services",
    author="Amun AI AB",
    author_email="info@amun.ai",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    license="MIT",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    install_requires=REQUIRES,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Internet",
    ],
)
