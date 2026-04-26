from django.db import models
from django.utils.translation import gettext_lazy as _


class Retailer(models.TextChoices):
    AMAZON = 'AMAZON', _('Amazon')
    EBAY = 'EBAY', _('eBay')
    BITIBA = 'BITIBA', _('Bitiba')
    ZOOPLUS = 'ZOOPLUS', _('Zooplus')
    PETSHOP = 'PETSHOP', _('PetShop')
    TIKTOK = 'TIKTOK', _('TikTok')
    VETSHOP = 'VETSHOP', _('VetShop')
    OTHER = 'OTHER', _('Other')


class Brand(models.TextChoices):
    PURINA_ONE = 'PURINA_ONE', _('PurinaOne')
    FELIX = 'FELIX', _('Felix')
    WHISKAS = 'WHISKAS', _('Whiskas')
    FRONTLINE = 'FRONTLINE', _('Frontline')
    DRONTAL = 'DRONTAL', _('Drontal')
    OTHER = 'OTHER', _('Other')


class Item(models.TextChoices):
    FOOD = 'FOOD', _('Food')
    FLEA = 'FLEA', _('Flea')
    WORMER = 'WORMER', _('Wormer')
    OTHER = 'OTHER', _('Other')


class Meta:
    verbose_name = 'Cat Purchases'
    verbose_name_plural = 'Cat Purchases'
    ordering = ('-date',)


class Identifier(models.TextChoices):
    OFFICE = 'OFFICE', _('Office')
    MISCELLANEOUS = 'MISCELLANEOUS', _('Miscellaneous')
    WIRE = 'WIRE', _('Wire')
    CABLE = 'CABLE', _('Cable')
    UNKNOWN = 'UNKNOWN', _('Unknown')
    COMPUTER = 'COMPUTER', _('Computer')
    OTHER = 'OTHER', _('Other')
    TOOLS = 'TOOLS', _('Tools')


class BoxIdentifier(models.TextChoices):
    NONE = 'NONE', _('None')
    A3 = 'A3', _('A3')
    MB1 = 'MB1', _('MB1')
    FLX1 = 'FLX1', _('FLX1')
    FLX2 = 'FLX2', _('FLX2')
    FLX3 = 'FLX3', _('FLX3')
    FLX4 = 'FLX4', _('FLX4')
    NLA1 = 'NLA1', _('NLA1')
    NLA2 = 'NLA2', _('NLA2')
    NLA3 = 'NLA3', _('NLA3')
    NLA4 = 'NLA4', _('NLA4')
    NLA6 = 'NLA6', _('NLA6')
    NLA7 = 'NLA7', _('NLA7')
    WORK = 'WORK', _('Work')
    TODO = 'TODO', _('Todo')


class UtilityMarket(models.TextChoices):
    ELECTRICITY = 'ELECTRICITY', _('Electricity')
    GAS = 'GAS', _('Gas')
    WATER = 'WATER', _('Water')


class Tariff(models.TextChoices):
    STANDARD = 'STANDARD', _('Standard')
    SAFEGUARD_PAYG = 'SAFEGUARD_PAYG', _('Safeguard PAYG')
    OTHER = 'OTHER', _('Other')


class Channel(models.TextChoices):
    APP = 'APP', _('App')
    BANK = 'BANK', _('Bank')
    CHEQUE = 'CHEQUE', _('Cheque')
    ONLINE = 'ONLINE', _('Online')
    OTHER = 'OTHER', _('Other')
    PEAK_SAVE = 'PEAK_SAVE', _('PeakSave')
    PORTAL = 'PORTAL', _('Portal')
    WARM_HOME_DISCOUNT = 'WARM_HOME_DISCOUNT', _('Warm Home Discount')
    WEB = 'WEB', _('Web')


class IntervalUnit(models.TextChoices):
    MINUTES = 'minutes', 'Minutes'
    HOURS = 'hours', 'Hours'
    DAYS = 'days', 'Days'
