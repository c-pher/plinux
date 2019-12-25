# read the contents of your README file
from os import path

from setuptools import setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='plinux',
    version='1.0.2',
    packages=['plinux'],
    url='https://github.com/agegemon/plinux',
    license='GNU General Public License v3.0',
    author='Andrey Komissarov',
    author_email='a.komisssarov@gmail.com',
    description='The cross-platform tool to execute bash commands remotely.',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'pynacl>=1.3.0',
        'bcrypt>=3.1.3',
        'cryptography>=2.5',
        'paramiko>=2.6.0',
    ],
    python_requires='>=3.6',
    long_description=long_description,
    long_description_content_type='text/markdown'
)