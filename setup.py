#!/usr/bin/env python3
"""Setup script for L5X-ST compiler."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="l5x-st-compiler",
    version="2.0.0",
    author="Original Author + Modernization",
    description="Modern L5X to Structured Text compiler with ST to L5X capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Compilers",
        "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "l5x2st=l5x_st_compiler.cli:l5x2st_main",
            "st2l5x=l5x_st_compiler.cli:st2l5x_main",
            "l5k-overlay-validate=examples.validate_l5k_overlay_diff:main",
            "l5x-st-compiler=l5x_st_compiler.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 