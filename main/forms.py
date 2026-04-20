from django import forms
from .models import Participant


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['level', 'phone']
        labels = {
            'level': 'Your Level',
            'phone': 'Phone Number (optional)',
        }
        widgets = {
            'level': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '08012345678'
            }),
        }


class GuestNameForm(forms.Form):
    display_name = forms.CharField(
        max_length=60,
        label='Your Name',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your name to join...',
            'autofocus': True,
        })
    )