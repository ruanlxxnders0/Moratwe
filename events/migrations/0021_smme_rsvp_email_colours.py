from importlib import import_module

from django.db import migrations

TEMPLATE_NAME = 'SMME RSVP Invitation'

CONTENT = """<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" bgcolor="#E8A820" style="background-color: #E8A820;">
<tr>
<td align="center" style="padding: 24px 12px;">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="width: 100%; max-width: 600px; background-color: #ffffff; border-radius: 8px;">
<tr>
<td bgcolor="#4260A8" style="background-color: #4260A8; color: #ffffff; font-family: Arial, Helvetica, sans-serif; font-size: 18px; font-weight: bold; padding: 18px 24px; border-radius: 8px 8px 0 0;">
RSVP: GGDA SCM Suppliers Imbizo Workshop
</td>
</tr>
<tr>
<td style="font-family: Arial, Helvetica, sans-serif; font-size: 15px; line-height: 1.6; color: #222222; padding: 24px;">

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

</td>
</tr>
</table>
</td>
</tr>
</table>"""


def update_template(apps, schema_editor):
    EmailTemplate = apps.get_model('events', 'EmailTemplate')
    old_content = import_module('events.migrations.0020_smme_rsvp').CONTENT
    # Only replace the original wording so admin edits are never overwritten.
    EmailTemplate.objects.filter(name=TEMPLATE_NAME, content=old_content).update(content=CONTENT)


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0020_smme_rsvp'),
    ]

    operations = [
        migrations.RunPython(update_template, migrations.RunPython.noop),
    ]
