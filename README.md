# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/tryolabs/requestium/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                               |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|----------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| requestium/\_\_init\_\_.py         |        4 |        0 |        0 |        0 |    100% |           |
| requestium/requestium.py           |        4 |        0 |        0 |        0 |    100% |           |
| requestium/requestium\_mixin.py    |      106 |       38 |       30 |        7 |     62% |28-31, 59, 64-65, 80, 97, 100, 103, 106, 109, 112, 115, 118, 159->162, 163, 165, 168-172, 177->179, 187, 190, 193, 196, 199, 221-237 |
| requestium/requestium\_response.py |       19 |        5 |        0 |        0 |     74% |21, 24, 27, 30, 33 |
| requestium/requestium\_session.py  |       88 |       22 |       42 |        8 |     68% |62, 72, 75, 79-80, 85-87, 90-91, 95-96, 116->122, 128-132, 140-142, 145-147 |
|                          **TOTAL** |  **221** |   **65** |   **72** |   **15** | **67%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/tryolabs/requestium/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/tryolabs/requestium/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/tryolabs/requestium/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/tryolabs/requestium/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Ftryolabs%2Frequestium%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/tryolabs/requestium/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.