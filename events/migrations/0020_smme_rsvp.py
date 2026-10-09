from django.db import migrations, models

TEMPLATE_NAME = 'SMME RSVP Invitation'

SUBJECT = 'Please confirm your attendance: GGDA SCM Suppliers Imbizo Workshop, 2 - 6 November 2026'

CONTENT = """<div style="font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.6; color: #222222; max-width: 600px; margin: 0 auto;">
<p>Dear {{ first_name }},</p>

<p>Thank you for registering {{ company }} with the GGDA. The Gauteng Growth and Development Agency (GGDA) is pleased to formally invite you to the <strong>GGDA SCM Suppliers Imbizo Workshop</strong>.</p>

<p><strong>When:</strong> 2 - 6 November 2026<br>
<strong>RSVP by:</strong> 16 October 2026</p>

<p>Venue details for your region will be shared with confirmed attendees.</p>

<p><strong>What you will gain:</strong></p>
<ul>
<li>GGDA Business Opportunities</li>
<li>Registration on the GGDA Database</li>
<li>RFQ &amp; Tender Documents Compliance</li>
<li>Procurement Processes</li>
<li>SCM Legislative Processes</li>
</ul>

<p><strong>Please let us know if you will attend:</strong></p>

<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 16px 0;">
<tr>
<td style="padding-right: 12px;">
<a href="{{ rsvp_confirm_url }}" style="background-color: #1a7f37; color: #ffffff; text-decoration: none; font-weight: bold; padding: 12px 24px; border-radius: 6px; display: inline-block;">Confirm RSVP</a>
</td>
<td>
<a href="{{ rsvp_decline_url }}" style="background-color: #b42318; color: #ffffff; text-decoration: none; font-weight: bold; padding: 12px 24px; border-radius: 6px; display: inline-block;">Decline RSVP</a>
</td>
</tr>
</table>

<p>When you confirm, you will be asked for your catering requirements.</p>

<p style="font-size: 13px; color: #555555;">If the buttons do not work, copy and paste these links into your browser:<br>
Confirm: {{ rsvp_confirm_url }}<br>
Decline: {{ rsvp_decline_url }}</p>

<p>Kind regards,<br>GGDA Group</p>
</div>"""


def create_template(apps, schema_editor):
    EmailTemplate = apps.get_model('events', 'EmailTemplate')
    if not EmailTemplate.objects.filter(name=TEMPLATE_NAME).exists():
        EmailTemplate.objects.create(
            name=TEMPLATE_NAME,
            subject=SUBJECT,
            content=CONTENT,
            guest_category='all',
            is_default=False,
        )


def remove_template(apps, schema_editor):
    apps.get_model('events', 'EmailTemplate').objects.filter(name=TEMPLATE_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0019_event_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='smmeregistration',
            name='rsvp_token',
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='smmeregistration',
            name='rsvp_status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('declined', 'Declined')], default='pending', max_length=10, verbose_name='RSVP status'),
        ),
        migrations.AddField(
            model_name='smmeregistration',
            name='rsvp_email_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='RSVP email sent at'),
        ),
        migrations.AddField(
            model_name='smmeregistration',
            name='rsvp_responded_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='RSVP responded at'),
        ),
        migrations.AddField(
            model_name='smmeregistration',
            name='catering',
            field=models.CharField(blank=True, choices=[('standard', 'Standard'), ('halal', 'Halal'), ('vegetarian', 'Vegetarian'), ('other', 'Other (specify)')], max_length=10, verbose_name='catering'),
        ),
        migrations.AddField(
            model_name='smmeregistration',
            name='catering_other',
            field=models.CharField(blank=True, max_length=200, verbose_name='catering (other)'),
        ),
        migrations.RunPython(create_template, remove_template),
    ]
