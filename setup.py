from setuptools import setup

setup(
    name="edx-analytics-data-client",
    version="0.1.0",
    packages=[
        'analyticsdataclient'
    ],
    install_requires=[
        "requests==2.3.0",
    ],
)
