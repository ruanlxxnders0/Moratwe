from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0018_event_date_time_tbc'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='logo',
            field=models.ImageField(blank=True, help_text='Shown at the top of the registration form for this event.', null=True, upload_to='event_logos/', verbose_name='client logo'),
        ),
    ]
