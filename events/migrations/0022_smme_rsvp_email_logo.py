from importlib import import_module

from django.db import migrations

TEMPLATE_NAME = 'SMME RSVP Invitation'

OLD_HEADER = """<tr>
<td bgcolor="#4260A8" style="background-color: #4260A8; color: #ffffff; font-family: Arial, Helvetica, sans-serif; font-size: 18px; font-weight: bold; padding: 18px 24px; border-radius: 8px 8px 0 0;">
RSVP: GGDA SCM Suppliers Imbizo Workshop
</td>
</tr>"""

NEW_HEADER = """<tr>
<td style="padding: 0; border-radius: 8px 8px 0 0;">
<img src="{{ SITE_URL }}/static/images/imbizo-header.jpg" alt="GGDA SCM Suppliers Imbizo Workshop" width="600" style="width: 100%; max-width: 600px; height: auto; display: block; border: 0; border-radius: 8px 8px 0 0;">
</td>
</tr>
<tr>
<td bgcolor="#4260A8" style="background-color: #4260A8; color: #ffffff; font-family: Arial, Helvetica, sans-serif; font-size: 16px; font-weight: bold; padding: 12px 24px; text-align: center;">
RSVP: please confirm your attendance
</td>
</tr>"""


def update_template(apps, schema_editor):
    EmailTemplate = apps.get_model('events', 'EmailTemplate')
    v20 = import_module('events.migrations.0020_smme_rsvp').CONTENT
    v21 = import_module('events.migrations.0021_smme_rsvp_email_colours').CONTENT
    new_content = v21.replace(OLD_HEADER, NEW_HEADER, 1)
    # Only replace the original wording so admin edits are never overwritten.
    EmailTemplate.objects.filter(name=TEMPLATE_NAME, content__in=[v20, v21]).update(content=new_content)


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0021_smme_rsvp_email_colours'),
    ]

    operations = [
        migrations.RunPython(update_template, migrations.RunPython.noop),
    ]
