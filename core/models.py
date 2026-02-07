from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    createdDateTime = models.DateTimeField(blank=True, null=True, default=timezone.now)
    modifiedDateTime = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        abstract = True


class Tag(models.Model):
    name = models.CharField(max_length=2048, unique=True)

    def __str__(self):
        return self.name


class CatPurchases(models.Model):
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

    retailer = models.CharField(max_length=32, choices=Retailer.choices, default=Retailer.OTHER)
    date = models.DateField()
    brand = models.CharField(max_length=32, choices=Brand.choices, default=Brand.OTHER)
    item = models.CharField(max_length=32, choices=Item.choices, default=Item.OTHER)
    pouchPerBox = models.PositiveSmallIntegerField()
    unitWeight = models.PositiveSmallIntegerField()
    quantity = models.PositiveSmallIntegerField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    tags = models.ManyToManyField(Tag, blank=True, related_name='catPurchasesTags')


class JournalEntry(BaseModel):
    title = models.CharField(max_length=2048, blank=True, null=True)
    content = models.TextField()
    tags = models.ManyToManyField(Tag, blank=True, related_name='journalEntryTags')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'
        ordering = ['-modifiedDateTime']


class InventoryItem(models.Model):
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

    title = models.CharField(max_length=2048, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    identifier = models.CharField(max_length=16, choices=Identifier.choices, default=Identifier.OTHER)
    box = models.CharField(max_length=16, choices=BoxIdentifier.choices, default=BoxIdentifier.FLX4)
    isWorking = models.BooleanField(default=True)
    quantity = models.PositiveIntegerField(default=1)
    location = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='inventoryItemTags')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'


class MeterPoint(models.Model):
    class UtilityMarket(models.TextChoices):
        ELECTRICITY = 'ELECTRICITY', _('Electricity')
        GAS = 'GAS', _('Gas')

    class Tariff(models.TextChoices):
        STANDARD = 'STANDARD', _('Standard')
        SAFEGUARD_PAYG = 'SAFEGUARD_PAYG', _('Safeguard PAYG')

    smartCardNumber = models.CharField(max_length=64, blank=True, null=True)
    identifier = models.CharField(max_length=64, blank=True, null=True, unique=True)
    utilityMarket = models.CharField(max_length=64, blank=True, null=True, choices=UtilityMarket.choices)
    tariff = models.CharField(max_length=64, blank=True, null=True, choices=Tariff.choices)

    class Meta:
        verbose_name = 'Meter Point'
        verbose_name_plural = 'Meter Points'

    def __str__(self):
        return f'{self.utilityMarket} - {self.identifier}'


class EnergyPayment(models.Model):
    class Channel(models.TextChoices):
        APP = 'APP', _('App')
        ONLINE = 'ONLINE', _('Online')
        OTHER = 'OTHER', _('Other')
        PEAK_SAVE = 'PEAK_SAVE', _('PeakSave')
        PORTAL = 'PORTAL', _('Portal')
        WARM_HOME_DISCOUNT = 'WARM_HOME_DISCOUNT', _('Warm Home Discount')
        WEB = 'WEB', _('Web')

    date = models.DateField()
    time = models.TimeField()
    channel = models.CharField(max_length=32, blank=True, null=True, choices=Channel.choices)
    topUpCode = models.CharField(max_length=32, blank=True, null=True)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    meterPoint = models.ForeignKey(MeterPoint, blank=True, null=True, on_delete=models.SET_NULL,
                                   related_name='energyPaymentMeterPoint')

    class Meta:
        ordering = ['-date', '-time']
        verbose_name = 'Energy Payment'
        verbose_name_plural = 'Energy Payments'
        unique_together = ('date', 'time', 'channel', 'topUpCode', 'amount', 'meterPoint')


class Cat(BaseModel):
    name = models.CharField(max_length=1024, blank=True, null=True)
    breed = models.CharField(max_length=1024, blank=True, null=True)
    colour = models.CharField(max_length=1024, blank=True, null=True)
    microchip = models.CharField(max_length=1024, blank=True, null=True)
    additionalData = models.TextField(blank=True, null=True)
    dateOfBirth = models.DateField()
    tags = models.ManyToManyField(Tag, blank=True, related_name='catTags')

    class Meta:
        verbose_name = 'Cat'
        verbose_name_plural = 'Cats'


class EventReminder(BaseModel):
    class IntervalUnit(models.TextChoices):
        MINUTES = 'minutes', 'Minutes'
        HOURS = 'hours', 'Hours'
        DAYS = 'days', 'Days'

    title = models.CharField(max_length=1024)
    message = models.TextField(blank=True, null=True)
    emails = models.TextField(help_text='Comma separated email addresses')
    eventDateTime = models.DateTimeField()
    startBeforeDays = models.PositiveIntegerField(null=True, blank=True,
                                                  help_text='Days before event to start reminders (default = 2)')
    intervalValue = models.PositiveIntegerField(help_text='Send reminder every X units')
    intervalUnit = models.CharField(max_length=10, choices=IntervalUnit.choices)
    nextReminderDateTime = models.DateTimeField(null=True, blank=True, help_text='Next scheduled reminder time')
    lastSentDate = models.DateField(null=True, blank=True)
    sentCountToday = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    retryCount = models.PositiveIntegerField(default=0)
    lastFailureDateTime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Event Reminder'
        verbose_name_plural = 'Event Reminders'
        ordering = ['eventDateTime']

    def getStartDateTime(self):
        days = self.startBeforeDays if self.startBeforeDays is not None else 2
        return self.eventDateTime - timedelta(days=days)

    def getIntervalDelta(self):
        if self.intervalUnit == self.IntervalUnit.MINUTES:
            return timedelta(minutes=self.intervalValue)
        if self.intervalUnit == self.IntervalUnit.HOURS:
            return timedelta(hours=self.intervalValue)
        return timedelta(days=self.intervalValue)

    def getEmailList(self):
        return [e.strip() for e in self.emails.split(',') if e.strip()]


class Goal(BaseModel):
    name = models.CharField(max_length=2048)

    def __str__(self):
        return self.name


class Task(models.Model):
    goal = models.ForeignKey(Goal, related_name='tasks', on_delete=models.CASCADE)
    name = models.CharField(max_length=2048)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.name
