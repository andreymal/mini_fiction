#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import OrderedDict

from setuptools import setup, find_packages


def read_requirements(f):
    with open(f, 'r', encoding='utf-8-sig') as fp:
        reqs = fp.read().splitlines()
    result = []
    for line in reqs:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        result.append(line)
    return result


requirements = read_requirements('requirements.txt')
optional_requirements = read_requirements('optional-requirements.txt')
test_requirements = read_requirements('test-requirements.txt')


with open('README.rst', 'r', encoding='utf-8-sig') as rfp:
    desc = rfp.read()


import mini_fiction


setup(
    name='mini_fiction',
    version=mini_fiction.__version__,
    description='CMS for fanfics',
    long_description=desc,
    long_description_content_type='text/x-rst',
    author='andreymal',
    author_email='andriyano-31@mail.ru',
    license='GPLv3',
    url='https://github.com/andreymal/mini_fiction',
    platforms='any',
    python_requires='>=3.4',
    packages=find_packages(),
    install_requires=requirements,
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'mini_fiction=mini_fiction.management.main:run'
        ],
    },
    extras_require={
        'full': optional_requirements,
    },
    setup_requires=['pytest-runner'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Flask',
        'License :: OSI Approved',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    test_suite="tests",
    tests_require=test_requirements,
    project_urls=OrderedDict((
        ('Bug Reports', 'https://github.com/andreymal/mini_fiction/issues'),
    )),
)
