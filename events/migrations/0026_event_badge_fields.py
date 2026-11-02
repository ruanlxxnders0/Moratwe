from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0025_smmeregistration_attended'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='badge_bar_text',
            field=models.CharField(blank=True, default='SMME', help_text='Text on the black bar of the printed SMME badge, e.g. SMME or VISITOR.', max_length=40, verbose_name='badge bar text'),
        ),
        migrations.AddField(
            model_name='event',
            name='badge_logo',
            field=models.ImageField(blank=True, help_text='Optional logo printed on the SMME badge.', null=True, upload_to='event_badge_logos/', verbose_name='badge logo'),
        ),
    ]
