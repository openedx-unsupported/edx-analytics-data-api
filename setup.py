from setuptools import setup

setup(
    name="edx-analytics-data",
    version="0.1.0",
    packages=[
        'analyticsdata',
        'analyticsdataclient'
    ],
    install_requires=[
        "Django==1.4.12",
        "djangorestframework==2.3.5",
        "requests==2.3.0",
    ],
)
