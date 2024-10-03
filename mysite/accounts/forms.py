from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Sequence
from .models import AlignmentTask
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='邮箱')

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        
class SequenceForm(forms.ModelForm):
    class Meta:
        model = Sequence
        fields = ('name', 'file')

class AlignmentTaskForm(forms.ModelForm):
    class Meta:
        model = AlignmentTask
        fields = ('sequence',)
        widgets = {
            'sequence': forms.Select(attrs={'class': 'form-control'}),
        }
