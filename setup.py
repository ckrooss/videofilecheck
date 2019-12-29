#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='videofilecheck',
    version="0.1.0",
    description='Check video files for decoding errors and keep a (pickle) database of results for incremental checking',
    packages=find_packages(),
    install_requires=[],
    python_requires='>=3.5',
    test_suite='tests',
    tests_require=['pytest', 'coverage', 'hypothesis', 'codeclimate-test-reporter'],
    setup_requires=['pytest', 'coverage', 'hypothesis', 'codeclimate-test-reporter'],
    author='Christopher Krooß',
    author_email='c.krooss@gmail.com',
    entry_points={
        'console_scripts':
            {
                "vcheck = videofilecheck.videofilecheck:cli",
            }
    }
)
