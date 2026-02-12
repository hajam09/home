from datetime import datetime

from core.models import EnergyPayment, MeterReading


def mapChannelForEnergyPayment(label):
    if label is None:
        return None
    for choice in EnergyPayment.Channel:

        if choice.label.lower() == label.lower():
            return choice.value

    raise ValueError('Invalid channel')


def parseDate(date):
    formats = [
        "%d/%m/%Y",  # dd/mm/yyyy
        "%d/%m/%y",  # dd/mm/yy
        "%d-%m-%Y",  # dd-mm-yyyy
        "%d-%m-%y",  # dd-mm-yy
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date, fmt).date()
        except ValueError:
            continue
    return None


def data(model, row):
    if model == EnergyPayment:
        return {
            'date': parseDate(row['date']),
            'time': datetime.strptime(row['time'], '%H:%M').time(),
            'channel': mapChannelForEnergyPayment(row['channel']),
            'topUpCode': row['topUpCode'],
            'amount': row['amount']
        }
    elif model == MeterReading:
        return {
            'date': parseDate(row['date']),
            'reading': row['reading']
        }


def parseCsvFile(reader, model, meterPoint):
    createdCount = 0
    skippedCount = 0
    uploadPreview = []

    for i, row in enumerate(reader, start=1):
        rowStatus = {'rowNumber': None, 'data': row, 'error': None, 'created': False}

        try:

            obj, created = model.objects.get_or_create(
                meterPoint=meterPoint,
                **data(model, row)
            )

            rowStatus['created'] = created
            rowStatus['rowNumber'] = obj.id

            if created:
                createdCount += 1
            else:
                skippedCount += 1

        except Exception as e:
            rowStatus['error'] = str(e)
            skippedCount += 1

        uploadPreview.append(rowStatus)

    return {
        'createdCount': createdCount,
        'skippedCount': skippedCount,
        'uploadPreview': uploadPreview,
    }
