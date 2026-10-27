import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('events', '0024_emailtemplate_banner'),
    ]

    operations = [
        migrations.AddField(
            model_name='smmeregistration',
            name='attended_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='attended at'),
        ),
        migrations.AddField(
            model_name='smmeregistration',
            name='attended_marked_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='marked attended by'),
        ),
    ]
