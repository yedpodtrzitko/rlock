from os.path import join, dirname
from setuptools import setup, find_packages

with open(join(dirname(__file__), "requirements.txt")) as f:
    requirements = [x.strip() for x in f.readlines()]

setup(
    name="releaselock",
    version="0.6.0",
    description="Slack App for managing release mutex",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
)
