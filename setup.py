# Always prefer setuptools over distutils
from setuptools import setup

# Get the long description from the README file
with open("README.md") as file:
    long_description = file.read()

setup(
    name="requestium",
    version="0.4.0",
    description=(
        "Adds a Selenium webdriver and parsel's parser to a request's Session "
        "object, and makes switching between them seamless. Handles cookie, "
        "proxy and header transfer."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Joaquin Alori",
    author_email="joaquin@tryolabs.com",
    url="https://github.com/tryolabs/requestium",
    packages=["requestium"],
    install_requires=(
        "parsel>=1.8.1",
        "requests>=2.32.0",
        "selenium>=4.15.2",
        "tldextract>=5.1.1",
    ),
    license="MIT",
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
