# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.utils.encoding import python_2_unicode_compatible

from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from unidecode import unidecode

import autoslug

from .settings import INDEX_SEARCH_NAMES, CITIES_LIGHT_APP_NAME


__all__ = ['AbstractCountry', 'AbstractRegion', 'AbstractCity',
           'CONTINENT_CHOICES']


CONTINENT_CHOICES = (
    ('OC', _('Oceania')),
    ('EU', _('Europe')),
    ('AF', _('Africa')),
    ('NA', _('North America')),
    ('AN', _('Antarctica')),
    ('SA', _('South America')),
    ('AS', _('Asia')),
)

ALPHA_REGEXP = re.compile('[\W_]+', re.UNICODE)


def to_ascii(value):
    """
    Convert a unicode value to ASCII-only unicode string.

    For example, 'République Françaisen' would become 'Republique Francaisen'
    """
    return force_text(unidecode(value))


def to_search(value):
    """
    Convert a string value into a string that is usable against
    City.search_names.

    For example, 'Paris Texas' would become 'paristexas'.
    """

    return ALPHA_REGEXP.sub('', to_ascii(value)).lower()


@python_2_unicode_compatible
class Base(models.Model):
    """
    Base model with boilerplate for all models.
    """

    name = models.CharField(max_length=200, db_index=True)
    name_ascii = models.CharField(max_length=200, blank=True, db_index=True)
    slug = autoslug.AutoSlugField(populate_from='name_ascii')
    geoname_id = models.IntegerField(null=True, blank=True, unique=True)
    alternate_names = models.TextField(null=True, blank=True, default='')

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        display_name = getattr(self, 'display_name', None)
        if display_name:
            return display_name
        return self.name


class AbstractCountry(Base):
    """
    Base Country model.
    """

    code2 = models.CharField(max_length=2, null=True, blank=True, unique=True)
    code3 = models.CharField(max_length=3, null=True, blank=True, unique=True)
    continent = models.CharField(max_length=2, db_index=True,
                                 choices=CONTINENT_CHOICES)
    tld = models.CharField(max_length=5, blank=True, db_index=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    class Meta(Base.Meta):
        verbose_name_plural = _('countries')
        abstract = True


class AbstractRegion(Base):
    """
    Base Region/State model.
    """

    display_name = models.CharField(max_length=200)
    geoname_code = models.CharField(max_length=50, null=True, blank=True,
                                    db_index=True)

    country = models.ForeignKey(CITIES_LIGHT_APP_NAME + '.Country',
                                on_delete=models.CASCADE)

    class Meta(Base.Meta):
        unique_together = (('country', 'name'), ('country', 'slug'))
        verbose_name = _('region/state')
        verbose_name_plural = _('regions/states')
        abstract = True

    def get_display_name(self):
        return '%s, %s' % (self.name, self.country.name)


class ToSearchTextField(models.TextField):
    """
    Trivial TextField subclass that passes values through to_search
    automatically.
    """
    def get_prep_lookup(self, lookup_type, value):
        """
        Return the value passed through to_search().
        """
        value = super(ToSearchTextField, self).get_prep_lookup(
            lookup_type,
            value)
        return to_search(value)


class AbstractCity(Base):
    """
    Base City model.
    """

    display_name = models.CharField(max_length=200)

    search_names = ToSearchTextField(
        max_length=4000,
        db_index=INDEX_SEARCH_NAMES,
        blank=True,
        default='')

    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        null=True,
        blank=True)

    longitude = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        null=True,
        blank=True)

    region = models.ForeignKey(CITIES_LIGHT_APP_NAME + '.Region', blank=True,
                               null=True, on_delete=models.CASCADE)
    country = models.ForeignKey(CITIES_LIGHT_APP_NAME + '.Country',
                                on_delete=models.CASCADE)
    population = models.BigIntegerField(null=True, blank=True, db_index=True)
    feature_code = models.CharField(max_length=10, null=True, blank=True,
                                    db_index=True)
    timezone = models.CharField(max_length=40, blank=True, null=True,
                                db_index=True)

    class Meta(Base.Meta):
        unique_together = (('region', 'name'), ('region', 'slug'))
        verbose_name_plural = _('cities')
        abstract = True

    def get_display_name(self):
        if self.region_id:
            return '%s, %s, %s' % (self.name, self.region.name,
                                   self.country.name)
        else:
            return '%s, %s' % (self.name, self.country.name)
