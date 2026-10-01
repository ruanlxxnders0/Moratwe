from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0016_emailtemplate_guest_category_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SMMERegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('surname', models.CharField(max_length=100, verbose_name='surname')),
                ('company', models.CharField(max_length=200, verbose_name='company/organisation')),
                ('position', models.CharField(max_length=100, verbose_name='position')),
                ('email', models.EmailField(max_length=254, verbose_name='email')),
                ('tel_number', models.CharField(blank=True, max_length=30, verbose_name='tel number')),
                ('mobile_number', models.CharField(max_length=30, verbose_name='mobile no')),
                ('sector', models.CharField(max_length=150, verbose_name='sector/industry')),
                ('region', models.CharField(choices=[('johannesburg', 'City of Johannesburg'), ('tshwane', 'Tshwane'), ('ekurhuleni', 'Ekurhuleni'), ('west_rand', 'West-Rand'), ('sedibeng', 'Sedibeng')], max_length=20, verbose_name='Gauteng region')),
                ('category', models.CharField(choices=[('women_owned', 'Women Owned'), ('black_owned', 'Black Owned'), ('youth', 'Youth'), ('disabilities', 'People with Disabilities'), ('military_veterans', 'Military Veterans')], max_length=20, verbose_name='category')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='registered at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='smme_registrations', to='events.event')),
            ],
            options={
                'verbose_name': 'SMME registration',
                'verbose_name_plural': 'SMME registrations',
                'ordering': ['-created_at'],
                'unique_together': {('event', 'email')},
            },
        ),
    ]
