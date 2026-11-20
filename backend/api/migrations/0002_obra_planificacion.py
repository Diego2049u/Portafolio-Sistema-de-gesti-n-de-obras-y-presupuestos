from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0001_initial')]
    operations = [
        migrations.AddField(model_name='obra', name='inicio_programado', field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name='obra', name='fin_estimado', field=models.DateTimeField(null=True, blank=True)),
    ]
