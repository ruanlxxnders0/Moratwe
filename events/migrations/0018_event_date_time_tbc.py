from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0017_smmeregistration'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='date_tbc',
            field=models.BooleanField(default=False, help_text='Tick if the date is not confirmed yet. The date field can then be left as is.', verbose_name='date to be confirmed'),
        ),
        migrations.AddField(
            model_name='event',
            name='time_tbc',
            field=models.BooleanField(default=False, help_text='Tick if the time is not confirmed yet.', verbose_name='time to be confirmed'),
        ),
        migrations.AlterField(
            model_name='event',
            name='date',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True, verbose_name='date'),
        ),
    ]
