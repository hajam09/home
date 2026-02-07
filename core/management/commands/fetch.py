import requests
from decouple import config
from django.core.management.base import BaseCommand

from core.models import (
    Tag,
    CatPurchases,
    JournalEntry,
    InventoryItem,
    MeterPoint,
    EnergyPayment,
    Cat,
    EventReminder,
    Goal,
    Task,
)


class Command(BaseCommand):
    BASE_URL = 'https://barkinghome.pythonanywhere.com/api/'

    def request(self, url):
        return requests.get(
            url=self.BASE_URL + url,
            auth=(config('ADMIN_USERNAME', cast=str), config('ADMIN_PASSWORD', cast=str))
        ).json()

    def log(self, value):
        self.stdout.write(f'\n{value}\n')

    def handle(self, *args, **kwargs):
        self.log('Start fetching objects...')
        self.log('Fetching Tag objects...')
        tags = Tag.objects.bulk_create(
            [
                Tag(
                    name=item.get('name')
                )
                for item in self.request('tags/')
            ],
            ignore_conflicts=True
        )
        self.log(f'Fetched {len(tags)} Tag objects.')

        self.log('Fetching CatPurchases objects...')
        tagMap = []
        cpBulk = []
        for item in self.request('cat-purchases/'):
            cp = CatPurchases(
                retailer=item.get('retailer'),
                date=item.get('date'),
                brand=item.get('brand'),
                item=item.get('item'),
                pouchPerBox=item.get('pouchPerBox'),
                unitWeight=item.get('unitWeight'),
                quantity=item.get('quantity'),
                price=item.get('price'),
            )
            cpBulk.append(cp)
            tagMap.append((cp, item.get('tags')))
        CatPurchases.objects.bulk_create(cpBulk)
        for item in tagMap:
            item[0].tags.add(*Tag.objects.filter(name__in=item[1]))
        self.log(f'Fetched {len(cpBulk)} CatPurchases objects.')

        self.log('Fetching JournalEntry objects...')
        tagMap = []
        jeBulk = []
        for item in self.request('journal-entries/'):
            je = JournalEntry(
                title=item.get('title'),
                content=item.get('content'),
                createdDateTime=item.get('createdDateTime'),
                modifiedDateTime=item.get('modifiedDateTime'),
            )
            jeBulk.append(je)
            tagMap.append((je, item.get('tags')))
        JournalEntry.objects.bulk_create(jeBulk)
        for item in tagMap:
            item[0].tags.add(*Tag.objects.filter(name__in=item[1]))
        self.log(f'Fetched {len(jeBulk)} JournalEntry objects.')

        self.log('Fetching InventoryItem objects...')
        tagMap = []
        iiBulk = []
        for item in self.request('inventory-items/'):
            ii = InventoryItem(
                title=item.get('title'),
                description=item.get('description'),
                identifier=item.get('identifier'),
                box=item.get('box'),
                isWorking=item.get('isWorking'),
                quantity=item.get('quantity'),
                location=item.get('location'),
            )
            iiBulk.append(ii)
            tagMap.append((ii, item.get('tags')))
        InventoryItem.objects.bulk_create(iiBulk)
        for item in tagMap:
            item[0].tags.add(*Tag.objects.filter(name__in=item[1]))
        self.log(f'Fetched {len(iiBulk)} InventoryItem objects.')

        self.log('Fetching MeterPoint objects...')
        meterPoints = MeterPoint.objects.bulk_create(
            [
                MeterPoint(
                    smartCardNumber=item.get('smartCardNumber'),
                    identifier=item.get('identifier'),
                    utilityMarket=item.get('utilityMarket'),
                    tariff=item.get('tariff'),
                )
                for item in self.request('meter-points/')
            ],
            ignore_conflicts=True
        )
        self.log(f'Fetched {len(meterPoints)} MeterPoint objects.')
        meterPoints = {
            mp.identifier: mp
            for mp in MeterPoint.objects.all()
        }

        self.log('Fetching EnergyPayment objects...')
        energyPayments = EnergyPayment.objects.bulk_create(
            [
                EnergyPayment(
                    date=item.get('date'),
                    time=item.get('time'),
                    channel=item.get('channel'),
                    topUpCode=item.get('topUpCode'),
                    amount=item.get('amount'),
                    meterPoint=meterPoints.get(item.get('meterPointIdentifier')),
                )
                for item in self.request('energy-payments/')
            ]
        )
        self.log(f'Fetched {len(energyPayments)} EnergyPayment objects.')

        self.log('Fetching Cat objects...')
        tagMap = []
        cBulk = []
        for item in self.request('cats/'):
            cat = Cat(
                name=item.get('name'),
                breed=item.get('breed'),
                colour=item.get('colour'),
                microchip=item.get('microchip'),
                additionalData=item.get('additionalData'),
                dateOfBirth=item.get('dateOfBirth'),
                createdDateTime=item.get('createdDateTime'),
                modifiedDateTime=item.get('modifiedDateTime'),
            )
            cBulk.append(cat)
            tagMap.append((cat, item.get('tags')))
        Cat.objects.bulk_create(cBulk)
        for item in tagMap:
            item[0].tags.add(*Tag.objects.filter(name__in=item[1]))
        self.log(f'Fetched {len(cBulk)} Cat objects.')

        self.log('Fetching EventReminder objects...')
        eventReminders = EventReminder.objects.bulk_create(
            [
                EventReminder(
                    createdDateTime=item.get('createdDateTime'),
                    modifiedDateTime=item.get('modifiedDateTime'),
                    title=item.get('title'),
                    message=item.get('message'),
                    emails=item.get('emails'),
                    eventDateTime=item.get('eventDateTime'),
                    startBeforeDays=item.get('startBeforeDays'),
                    intervalValue=item.get('intervalValue'),
                    intervalUnit=item.get('intervalUnit'),
                    nextReminderDateTime=item.get('nextReminderDateTime'),
                    lastSentDate=item.get('lastSentDate'),
                    sentCountToday=item.get('sentCountToday'),
                    completed=item.get('completed'),
                    retryCount=item.get('retryCount'),
                    lastFailureDateTime=item.get('lastFailureDateTime'),
                )
                for item in self.request('event-reminders/')
            ]
        )
        self.log(f'Fetched {len(eventReminders)} EventReminder objects.')

        self.log('Fetching Goal objects...')
        goals = Goal.objects.bulk_create(
            [
                Goal(
                    name=item.get('name'),
                    createdDateTime=item.get('createdDateTime'),
                    modifiedDateTime=item.get('modifiedDateTime'),
                )
                for item in self.request('goals/')
            ]
        )
        self.log(f'Fetched {len(goals)} Goal objects.')
        goals = {
            g.id: g
            for g in Goal.objects.all()
        }

        self.log('Fetching Task objects...')
        tasks = Task.objects.bulk_create(
            [
                Task(
                    name=item.get('name'),
                    completed=item.get('completed'),
                    goal=goals.get(item.get('goal')),
                )
                for item in self.request('tasks/')
            ]
        )
        self.log(f'Fetched {len(tasks)} Task objects.')
