# Generated by Django 2.1.5 on 2019-09-12 20:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tom_dataproducts', '0005_auto_20190704_1010'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reduceddatum',
            name='data_type',
            field=models.CharField(choices=[('spectroscopy', 'Spectroscopy'), ('photometry', 'Photometry')], default='', max_length=100),
        ),
    ]