import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0005_rentabilidad_presupuesto')]

    operations = [
        migrations.CreateModel(
            name='MovimientoMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('entrada', 'Entrada'), ('consumo', 'Consumo')], max_length=7)),
                ('cantidad', models.DecimalField(decimal_places=3, max_digits=12)),
                ('motivo', models.CharField(max_length=255)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('asignacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimientos', to='api.obramaterial')),
                ('registrado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-fecha', '-pk'],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='mov_material_cantidad_positiva'),
                    models.CheckConstraint(condition=models.Q(tipo__in=['entrada', 'consumo']), name='mov_material_tipo_valido'),
                ],
            },
        ),
    ]
