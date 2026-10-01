from django import forms
from .models import SMMERegistration


class SMMERegistrationForm(forms.ModelForm):
    # Honeypot: real users never see or fill this in
    website = forms.CharField(required=False)

    class Meta:
        model = SMMERegistration
        fields = ['name', 'surname', 'company', 'position', 'email',
                  'tel_number', 'mobile_number', 'sector', 'region', 'category']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['region'].choices = [('', 'Select region')] + list(SMMERegistration.REGION_CHOICES)
        self.fields['category'].choices = [('', 'Select category')] + list(SMMERegistration.CATEGORY_CHOICES)
        self.fields['tel_number'].required = False

    def validate_unique(self):
        # Duplicate (event, email) is handled in the view by updating the record
        pass

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Invalid submission.')
        return ''
