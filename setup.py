#!/usr/bin/env python3

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
     name='interact',
     version='0.1',
     scripts=[] ,
     author="Justin Dubs",
     author_email="jtdubs@gmail.com",
     description="Tool for interacting with sockets & processes",
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="",
     packages=["interact"],
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: MIT License",
         "Operating System :: OS Independent",
     ],
)
