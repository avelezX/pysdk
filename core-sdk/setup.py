from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="xerenity",
    version="0.2.2",
    description="Python package for xerenity",
    url="https://xerenity.vercel.app/login",
    author="Andres Velez",
    author_email="svelez@xerenity.co",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "supabase>=2.4.4"
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
)
