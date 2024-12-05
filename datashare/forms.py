from django import forms

class frmPublish(forms.Form):
    PROJECTS = [
        ('1', '地域防災関連'),
        ('2', '都市計画関連'),
        ('3', '地域産業関連'),
    ]

    name = forms.CharField(label='Name', max_length=50)
    project = forms.ChoiceField(label='Project', choices=PROJECTS)
    contents = forms.CharField(label='Message', widget=forms.Textarea)