import hashlib
import re
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
        '%d/%m/%Y',  # dd/mm/yyyy
        '%d/%m/%y',  # dd/mm/yy
        '%d-%m-%Y',  # dd-mm-yyyy
        '%d-%m-%y',  # dd-mm-yy
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


def generateSmartCardAndIdentifier(doorNumber, postcode, utilityType, tariff):
    baseString = re.sub(r'\s+', '', f'{doorNumber}{postcode}{utilityType}{tariff}').lower()
    smartCardHash = hashlib.sha256(f'SMARTCARD:{baseString}'.encode('utf-8')).hexdigest()
    identifierHash = hashlib.sha256(f'IDENTIFIER:{baseString}'.encode('utf-8')).hexdigest()
    smartCardNumber = ''.join(filter(str.isdigit, smartCardHash))[:19].zfill(19)
    identifier = ''.join(filter(str.isdigit, identifierHash))[:13].zfill(13)
    return smartCardNumber, identifier


def generateTopUpCode(doorNumber, postcode, paymentDate, paymentTime, channel, amount, utilityType):
    inputString = re.sub(r'\s+', '', f'{doorNumber}{postcode}{paymentDate}{paymentTime}{channel}{amount}{utilityType}').lower()
    hashObject = hashlib.sha256(inputString.encode('utf-8'))
    hashHex = hashObject.hexdigest()
    numericCode = ''.join([c for c in hashHex if c.isdigit()])
    return numericCode[:20].zfill(20)
