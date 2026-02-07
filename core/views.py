import csv
from datetime import datetime

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import BooleanField, Case, Count, DateTimeField, F, Q, Value, When
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.timezone import now

from core import service
from core.models import EnergyPayment, MeterPoint, Goal, Task


def indexView(request):
    appData = []
    totalModels = 0

    for appConfig in apps.get_app_configs():
        if appConfig.label in {'admin', 'contenttypes', 'sessions', }:
            continue

        modelData = []
        appLatestActivity = None
        appTotalObjects = 0

        for model in appConfig.get_models():
            totalModels += 1
            qs = model.objects.all()
            objectCount = qs.count()

            appTotalObjects += objectCount

            dateTimeFields = [
                field.name for field in model._meta.fields
                if isinstance(field, DateTimeField)
            ]

            lastObject = None
            modelLastActivity = None

            if dateTimeFields:
                fieldName = dateTimeFields[0]
                lastObject = qs.order_by(f'-{fieldName}').first()

                if lastObject:
                    modelLastActivity = getattr(lastObject, fieldName, None)

            if modelLastActivity and (
                    not appLatestActivity or modelLastActivity > appLatestActivity
            ):
                appLatestActivity = modelLastActivity

            modelData.append({
                'modelName': model.__name__,
                'objectCount': objectCount,
                'lastObject': lastObject,
                'lastActivity': modelLastActivity,
            })

        if modelData:
            appData.append({
                'appName': appConfig.label,
                'modelCount': len(modelData),
                'models': modelData,
                'latestActivity': appLatestActivity,
                'totalObjects': appTotalObjects,
            })

    context = {
        'apps': appData,
        'totalApps': len(appData),
        'totalModels': totalModels,
        'generatedAt': now(),
    }
    return render(request, 'core/index.html', context)


@login_required
def meterPointsView(request):
    meterPoints = []
    meterPoint = None
    uploadPreview = []  # To store row info and errors
    energyPayments = []

    if not request.GET.get('meter-point'):
        meterPoints = MeterPoint.objects.all()
    else:
        meterPoint = MeterPoint.objects.filter(identifier=request.GET.get('meter-point').strip()).first()
        energyPayments = EnergyPayment.objects.filter(meterPoint=meterPoint)

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
                timeObj = datetime.strptime(row['time'], '%H:%M').time()

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
        'skippedCount': skippedCount,
        'energyPayments': energyPayments,
    }
    return render(request, 'core/meter-points-template.html', context)


@login_required
def goalAndTasks(request):
    goals = []
    goal = None

    if request.GET.get('goal'):
        if request.method == 'POST' and request.POST.get('name'):
            Task.objects.bulk_create(
                [
                    Task(goal_id=request.GET.get('goal'), name=name)
                    for name in [name.strip() for name in request.POST.get('name').split(',') if name.strip()]
                ]
            )
            return redirect(f'{request.path}?goal={request.GET.get("goal")}')

        goal = Goal.objects.get(id=request.GET.get('goal'))
    else:
        goals = Goal.objects.annotate(
            totalTasks=Count('tasks'),
            completedTasks=Count('tasks', filter=Q(tasks__completed=True)),
        ).annotate(
            isCompleted=Case(
                When(
                    totalTasks__gt=0,
                    totalTasks=F('completedTasks'),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )
        ).order_by('isCompleted', '-createdDateTime')

        if request.method == 'POST' and request.POST.get('name'):
            Goal.objects.create(name=request.POST.get('name'))
            return redirect(request.path)

    context = {
        'goals': goals,
        'goal': goal,
    }
    return render(request, 'core/goals-and-tasks.html', context)
