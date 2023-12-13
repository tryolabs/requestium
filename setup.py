# Always prefer setuptools over distutils
from setuptools import setup

# Get the long description from the README file
with open('README.md') as file:
    long_description = file.read()

setup(
    name='requestium',
    version='0.3.0',
    description=(
        "Adds a Selenium webdriver and parsel's parser to a request's Session "
        "object, and makes switching between them seamless. Handles cookie, "
        "proxy and header transfer."
    ),
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Joaquin Alori',
    author_email='joaquin@tryolabs.com',
    url='https://github.com/tryolabs/requestium',
    packages=('requestium',),
    install_requires=(
        'parsel>=1.7.0',
        'requests>=2.28.1',
        'selenium>=4.6.0',
        'tldextract>=3.4.0',
    ),
    license='MIT',
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
)
