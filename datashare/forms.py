from django import forms
from .models import pub_message

class frmPublish(forms.Form):
    PROJECTS = [
        ('1', '地域防災関連'),
        ('2', '都市計画関連'),
        ('3', '地域産業関連'),
    ]

    name = forms.CharField(label='Name', max_length=50)
    project = forms.ChoiceField(label='Project', choices=PROJECTS)
    contents = forms.CharField(label='Message', widget=forms.Textarea)

class frmModelPublish(forms.ModelForm):
    class Meta:
        model = pub_message
        fields = ['sender', 'project', 'send_message', 'send_document']