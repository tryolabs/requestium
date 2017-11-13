# Always prefer setuptools over distutils
from setuptools import setup

# Get the long description from the README file
try:
    import pypandoc
except ImportError:
    pypandoc = None

if pypandoc:
    long_description = pypandoc.convert('README.md', 'rst')
else:
    with open('README.md') as file:
        long_description = file.read()

setup(
    name='requestium',
    version='0.1.6',
    description=(
        "Adds a Selenium webdriver and parsel's parser to a request's Session "
        "object, and makes switching between them seamless. Handles cookie, "
        "proxy and header transfer."
    ),
    long_description=long_description,
    author='Joaquin Alori',
    author_email='joaquin.alori@gmail.com',
    url='https://github.com/tryolabs/requestium',
    packages=('requestium',),
    install_requires=(
        'requests>=2.18.1',
        'selenium>=3.4.3',
        'parsel>=1.2.0',
        'tldextract>=2.1.0'
    ),
    license='MIT',
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
    ]
)
