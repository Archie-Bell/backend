# Generated by Django 3.1.12 on 2025-03-14 18:15

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MissingPerson',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('age', models.IntegerField()),
                ('last_location_seen', models.CharField(max_length=255)),
                ('last_date_time_seen', models.DateTimeField()),
                ('additional_info', models.TextField(blank=True, null=True)),
                ('image_url', models.CharField(max_length=500)),
            ],
        ),
    ]
