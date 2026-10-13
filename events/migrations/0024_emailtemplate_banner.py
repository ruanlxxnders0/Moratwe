from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0023_restore_registration_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailtemplate',
            name='banner',
            field=models.ImageField(blank=True, help_text='Optional. Shown full width at the top of every email sent with this template.', null=True, upload_to='email_banners/', verbose_name='banner image'),
        ),
    ]
