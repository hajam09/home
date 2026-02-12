import csv
from datetime import datetime
from io import StringIO, TextIOWrapper

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import BooleanField, Case, Count, DateTimeField, F, Q, Value, When
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.timezone import now
from django.views import View
from django.views.generic import ListView

from core import service
from core.models import EnergyPayment, MeterPoint, Goal, Task, MeterReading


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


class MeterPointsView(LoginRequiredMixin, ListView):
    model = MeterPoint
    template_name = 'core/meter-points.html'
    context_object_name = 'meterPoints'


class MeterPointView(View):
    templateName = 'core/meter-point.html'

    tab = None
    meterPoint = None
    table = None
    columns = None

    def dispatch(self, request, *args, **kwargs):
        self.tab = request.GET.get('tab', 'payments')
        self.meterPoint = MeterPoint.objects.get(identifier=kwargs.get('identifier'))

        if self.tab == 'payments':
            self.table = EnergyPayment.objects.filter(meterPoint=self.meterPoint)
            self.columns = {'date', 'time', 'channel', 'topUpCode', 'amount'}
        else:
            self.table = MeterReading.objects.filter(meterPoint=self.meterPoint)
            self.columns = {'date', 'reading'}
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, identifier):
        context = {
            'meterPoint': self.meterPoint,
            'table': self.table,
        }
        return render(request, self.templateName, context)

    def data(self, request):
        if self.tab == 'payments':
            dt = datetime.fromisoformat(request.POST['datetime'])
            data = {
                'date': dt.date(),
                'time': dt.time(),
                'channel': request.POST['channel'],
                'topUpCode': request.POST['topUpCode'],
                'amount': request.POST['amount'],
            }
            return data
        elif self.tab == 'readings':
            data = {
                'date': datetime.strptime(request.POST['date'], '%Y-%m-%d').date(),
                'reading': request.POST['reading']
            }
            return data

    def post(self, request, identifier):
        context = {
            'meterPoint': self.meterPoint,
            'table': self.table,
        }

        if self.tab in ['payments', 'readings'] and 'file' in request.POST:
            file = request.FILES.get('file')
            if not file.name.endswith('.csv'):
                messages.warning(request, 'Only CSV files are accepted!')
                return HttpResponseRedirect(request.path_info)

            reader = csv.DictReader(TextIOWrapper(file.file, encoding='utf-8'))
            if not self.columns.issubset(set(reader.fieldnames)):
                messages.warning(request, f'Incorrect file is uploaded for {self.tab}!')
                return HttpResponseRedirect(request.path_info)

            model = EnergyPayment if self.tab == 'payments' else MeterReading
            response = service.parseCsvFile(reader, model, self.meterPoint)
            context.update(response)

        elif self.tab in ['payments', 'readings'] and 'text' in request.POST:
            reader = csv.DictReader(StringIO(request.POST.get('data')))
            if not self.columns.issubset(set(reader.fieldnames)):
                messages.warning(request, f'Incorrect date supplied for {self.tab}!')
                return HttpResponseRedirect(request.path_info)

            model = EnergyPayment if self.tab == 'payments' else MeterReading
            response = service.parseCsvFile(reader, model, self.meterPoint)
            context.update(response)

        elif self.tab in ['payments', 'readings'] and 'form' in request.POST:
            data = self.data(request)
            rowStatus = {'rowNumber': None, 'data': data, 'error': None, 'created': False}
            model = EnergyPayment if self.tab == 'payments' else MeterReading

            try:
                obj, created = model.objects.get_or_create(
                    meterPoint=self.meterPoint,
                    **data
                )
                rowStatus['created'] = created
                rowStatus['rowNumber'] = obj.id
            except Exception as e:
                rowStatus['error'] = str(e)

            context['uploadPreview'] = [rowStatus]
        return render(request, self.templateName, context)


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
