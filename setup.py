#!/usr/bin/env python
import os
from setuptools import setup, find_packages

# Read requirements (ignore comments and empty lines)
def load_requirements(path='requirements.txt'):
    reqs = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                reqs.append(line)
    return reqs

setup(
    name='revsys',
    version='0.1.0',
    description='Automated systematic review toolkit',
    author='',
    author_email='',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=load_requirements(),
    entry_points={
        'console_scripts': [
            'revsys = revsys.cli:cli'
        ]
    },
    python_requires='>=3.7',
)