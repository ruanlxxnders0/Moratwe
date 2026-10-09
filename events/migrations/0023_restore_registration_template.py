from django.db import migrations

TEMPLATE_NAME = 'GGDA Group SMME Imbizo Workshop'

SUBJECT = 'You are invited: GGDA SCM Suppliers Imbizo Workshop'

CONTENT = """<div style="font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.6; color: #222222; max-width: 600px; margin: 0 auto;">
<img src="{{ SITE_URL }}/static/images/imbizo-header.jpg" alt="GGDA SCM Suppliers Imbizo Workshop" width="600" style="width: 100%; max-width: 600px; height: auto; display: block; border: 0;">

<p>Dear {{ first_name }},</p>

<p>The GGDA Group would like to invite you to participate in the upcoming GGDA SCM Suppliers Imbizo Workshop, organized by the Gauteng Growth and Development Agency, to be held in all 5 Gauteng Regions.</p>

<p><strong>When:</strong> {{ event_when }}<br>
<strong>Where:</strong> {{ event.location }}</p>

<p><strong>What you will gain:</strong></p>
<ul>
<li>GGDA Business Opportunities</li>
<li>Registration on the GGDA Database</li>
<li>RFQ &amp; Tender Documents Compliance</li>
<li>Procurement Processes</li>
<li>SCM Legislative Processes</li>
</ul>

<p><strong>You're invited if your business falls under one of these targeted SMME groups:</strong></p>
<ol>
<li>Women-owned Businesses</li>
<li>Youth-owned Businesses</li>
<li>Persons with Disabilities-owned Businesses</li>
<li>Military Veteran-owned Businesses</li>
</ol>

<p>The workshops will be conducted across all five Gauteng Regions.</p>

<p>Register your business now by clicking the button below:</p>

<p style="margin: 20px 0;">
<a href="{{ register_url }}" style="background-color: #4260A8; color: #ffffff; text-decoration: none; font-weight: bold; padding: 12px 24px; border-radius: 6px; display: inline-block;">Click here to Register</a>
</p>

<p style="font-size: 13px; color: #555555;">If the button does not work, copy and paste this link into your browser:<br>
{{ register_url }}</p>

<p>Kind regards,<br>GGDA Group</p>
</div>"""


def restore_template(apps, schema_editor):
    EmailTemplate = apps.get_model('events', 'EmailTemplate')
    EventInvitation = apps.get_model('events', 'EventInvitation')

    template = EmailTemplate.objects.filter(name__iexact=TEMPLATE_NAME).first()
    if template is None:
        template = EmailTemplate.objects.create(
            name=TEMPLATE_NAME,
            subject=SUBJECT,
            content=CONTENT,
            guest_category='all',
            is_default=False,
        )
    # Deleting a template blanks the link on its invitations; relink the Imbizo ones.
    EventInvitation.objects.filter(
        email_template__isnull=True,
        event__title__icontains='imbizo',
    ).update(email_template=template)


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0022_smme_rsvp_email_logo'),
    ]

    operations = [
        migrations.RunPython(restore_template, migrations.RunPython.noop),
    ]
