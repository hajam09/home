from django import forms

from core.models import Event


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
