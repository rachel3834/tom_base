# Generated by Django 2.1.4 on 2019-05-03 23:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tom_observations', '0002_auto_20190306_2343'),
    ]

    operations = [
        migrations.AlterField(
            model_name='observationrecord',
            name='observation_id',
            field=models.CharField(max_length=255),
        ),
    ]
