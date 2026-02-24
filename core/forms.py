from django import forms

from core.models import Event, MeterPoint, EnergyPayment


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'location', 'startDateTime', 'endDateTime', 'description']
        widgets = {
            'title': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Title', 'required': 'True'}
            ),
            'location': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Location'}
            ),
            'startDateTime': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local', 'required': 'True'}
            ),
            'endDateTime': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local', 'required': 'True'}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Description'}
            ),
        }

    def clean(self):
        data = super().clean()
        start = data.get('startDateTime')
        end = data.get('endDateTime')

        if start and end and end <= start:
            startClass = self.fields.get('startDateTime').widget.attrs.get('class', '')
            endClass = self.fields.get('endDateTime').widget.attrs.get('class', '')
            self.fields.get('startDateTime').widget.attrs['class'] = f'{startClass} is-invalid'
            self.fields.get('endDateTime').widget.attrs['class'] = f'{endClass} is-invalid'
            raise forms.ValidationError('End date must be after start date.')

        return data


class SmartCardForm(forms.Form):
    doorNumber = forms.CharField(max_length=64, label='Door Number')
    postcode = forms.CharField(max_length=10, label='Postcode')
    utilityType = forms.ChoiceField(choices=MeterPoint.UtilityMarket.choices, label='Utility Type')
    tariff = forms.ChoiceField(choices=MeterPoint.Tariff.choices, label='Tariff')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doorNumber'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['postcode'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['utilityType'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['tariff'].widget.attrs.update({'class': 'form-control form-control-sm'})


class TopUpForm(forms.Form):
    doorNumber = forms.CharField(max_length=64, label='Door Number')
    postcode = forms.CharField(max_length=10, label='Postcode')
    paymentDate = forms.DateField(label='Payment Date',widget=forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}))
    paymentTime = forms.TimeField(label='Payment Time',widget=forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}))
    channel = forms.ChoiceField(choices=EnergyPayment.Channel.choices, label='Payment Channel')
    amount = forms.DecimalField(max_digits=6, decimal_places=2, label='Amount')
    utilityType = forms.ChoiceField(choices=MeterPoint.UtilityMarket.choices, label='Utility Type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doorNumber'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['postcode'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['paymentDate'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['paymentTime'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['channel'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['amount'].widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['utilityType'].widget.attrs.update({'class': 'form-control form-control-sm'})
