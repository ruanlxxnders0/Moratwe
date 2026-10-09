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


class SMMERSVPForm(forms.ModelForm):
    class Meta:
        model = SMMERegistration
        fields = ['catering', 'catering_other']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['catering'].choices = [('', 'Select catering')] + list(SMMERegistration.CATERING_CHOICES)
        self.fields['catering'].required = True
        self.fields['catering_other'].required = False
        self.fields['catering_other'].label = 'Please specify'

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('catering') == 'other' and not (cleaned.get('catering_other') or '').strip():
            self.add_error('catering_other', 'Please specify your catering requirement.')
        if cleaned.get('catering') != 'other':
            cleaned['catering_other'] = ''
        return cleaned
