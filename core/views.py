import csv
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render

from core import service
from core.models import (
    EnergyPayment,
    MeterPoint
)

"""
CatPurchases:
    * Base table with additional columns to show totalWeight, totalPrice and pricePerKG.
    * Pie chart showing unique retailers and each pie showing how much money spent.
    * Pie chart showing unique brands and each pie showing how much money spent.
    * Card showing how much total amount spent on cat food.
    * Card showing average amount spend on cat food each month.
    * Table showing cat name, registered owner and primary/secondary.
    * Line graph showing amount spent on cat food each month.

EnergyPayment:
    * Bar graph showing total number of energy payments made for all utilities/electricity/gas for each month.
    * Bar graph showing cost for each month for all utilities/electricity/gas.
    * Card showing total amount spent on all utilities/electricity/gas.
    * Card showing average amount spent on all utilities/electricity/gas.
"""


@login_required
def energyPaymentUploadForMeterPoint(request):
    meterPoints = []
    meterPoint = None
    uploadPreview = []  # To store row info and errors

    if not request.GET.get('meter-point'):
        meterPoints = MeterPoint.objects.all()
    else:
        meterPoint = MeterPoint.objects.filter(identifier=request.GET.get('meter-point').strip()).first()

    createdCount = 0
    skippedCount = 0

    if request.method == 'POST' and request.FILES.get('payments') and meterPoint:
        paymentsFile = request.FILES.get('payments')
        if not paymentsFile.name.endswith('.csv'):
            messages.warning(request, 'The wrong file type was uploaded')
            return HttpResponseRedirect(request.path_info)

        decodedFile = paymentsFile.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decodedFile)

        for i, row in enumerate(reader, start=1):
            rowStatus = {'rowNumber': None, 'data': row, 'error': None, 'created': False}
            try:
                # Parse date and time
                dateObj = datetime.strptime(row['date'], '%d/%m/%y').date()
                timeObj = datetime.strptime(row['time'], '%I:%M %p').time()

                # Create or skip if exists
                payment, created = EnergyPayment.objects.get_or_create(
                    date=dateObj,
                    time=timeObj,
                    channel=service.mapChannelForEnergyPayment(row.get('channel')),
                    topUpCode=row.get('topUpCode') or None,
                    amount=row.get('amount'),
                    meterPoint=meterPoint
                )

                rowStatus['created'] = created
                rowStatus['rowNumber'] = payment.id
                if created:
                    createdCount += 1
                else:
                    skippedCount += 1

            except Exception as e:
                rowStatus['error'] = str(e)
                skippedCount += 1

            uploadPreview.append(rowStatus)

        messages.success(request, f'Upload finished. Created: {createdCount}, Skipped/Errors: {skippedCount}')

    context = {
        'meterPoints': meterPoints,
        'meterPoint': meterPoint,
        'uploadPreview': uploadPreview,
        'createdCount': createdCount,
        'skippedCount': skippedCount
    }
    return render(request, 'core/energy-payments--csv-upload.html', context)
