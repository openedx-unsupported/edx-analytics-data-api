"""
This file holds constants and helper functions related to countries. All codes are assumed to be valid ISO 3166 country
codes.
"""
from collections import namedtuple
from django_countries import countries

Country = namedtuple('Country', 'name, alpha2, alpha3, numeric')

UNKNOWN_COUNTRY_CODE = u'UNKNOWN'
UNKNOWN_COUNTRY = Country(UNKNOWN_COUNTRY_CODE, None, None, None)


def _get_country_property(code, property_name):
    return unicode(getattr(countries, property_name)(code))


def get_country(code):
    if not code:
        return UNKNOWN_COUNTRY

    name = _get_country_property(code, 'name')
    if not name:
        return UNKNOWN_COUNTRY

    args = []
    properties = ['alpha2', 'alpha3', 'numeric']
    for property_name in properties:
        args.append(_get_country_property(code, property_name))

    return Country(name, *args)
