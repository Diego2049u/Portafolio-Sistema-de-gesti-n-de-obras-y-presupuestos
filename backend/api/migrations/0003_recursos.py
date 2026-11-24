from django.db import migrations, models
import django.db.models.deletion


def cargar_catalogo(apps, schema_editor):
    Material = apps.get_model('api', 'Material')
    electrico = 'Proyecto eléctrico'
    clima = 'Climatización'
    mantenimiento = 'Mantención'
    proyecto = 'Proyecto'
    catalogo = [
        ('Cable de cobre THHN 2,5 mm²', 'm', [electrico]),
        ('Canalización EMT 20 mm', 'm', [electrico]),
        ('Interruptor termomagnético', 'un', [electrico]),
        ('Interruptor diferencial', 'un', [electrico]),
        ('Caja de derivación eléctrica', 'un', [electrico, clima]),
        ('Tubería de cobre frigorífica', 'm', [clima, proyecto, mantenimiento]),
        ('Aislación elastomérica para tubería', 'm', [clima, proyecto, mantenimiento]),
        ('Manguera de drenaje de condensados', 'm', [clima, mantenimiento]),
        ('Soporte para unidad condensadora', 'par', [clima, proyecto]),
        ('Panel aislante para cámara frigorífica', 'm²', [proyecto, 'Mejoras']),
        ('Sellador para juntas de cámara frigorífica', 'cartucho', [proyecto, mantenimiento]),
        ('Burlete para puerta de cámara frigorífica', 'm', [proyecto, mantenimiento, 'Venta de repuestos']),
        ('Filtro deshidratador', 'un', [proyecto, mantenimiento, 'Venta de repuestos']),
        ('Sonda de temperatura NTC', 'un', [clima, mantenimiento, 'Emergencia']),
        ('Contactor eléctrico', 'un', [electrico, mantenimiento, 'Emergencia']),
        ('Filtro de aire para climatización', 'un', [clima, mantenimiento, 'Garantía']),
    ]
    for nombre, unidad, servicios in catalogo:
        Material.objects.using(schema_editor.connection.alias).get_or_create(
            nombre=nombre, defaults={'unidad': unidad, 'servicios': servicios},
        )


class Migration(migrations.Migration):
    dependencies = [('api', '0002_obra_planificacion')]

    operations = [
        migrations.CreateModel(
            name='Material',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120, unique=True)),
                ('unidad', models.CharField(max_length=20)),
                ('servicios', models.JSONField(blank=True, default=list)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={'ordering': ['nombre', 'pk']},
        ),
        migrations.CreateModel(
            name='ObraMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('obra', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='materiales', to='api.obra')),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='api.material')),
                ('cantidad_planificada', models.DecimalField(decimal_places=3, max_digits=12)),
            ],
            options={'ordering': ['pk'], 'constraints': [
                models.UniqueConstraint(fields=('obra', 'material'), name='obra_material_unico'),
                models.CheckConstraint(condition=models.Q(cantidad_planificada__gt=0), name='obra_material_cantidad_positiva'),
            ]},
        ),
        migrations.CreateModel(
            name='MermaMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asignacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='mermas', to='api.obramaterial')),
                ('cantidad', models.DecimalField(decimal_places=3, max_digits=12)),
                ('motivo', models.CharField(max_length=255)),
                ('fecha', models.DateField(auto_now_add=True, db_index=True)),
                ('registrado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='api.usuario')),
            ],
            options={'ordering': ['-fecha', '-pk'], 'constraints': [
                models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='merma_material_cantidad_positiva'),
            ]},
        ),
        migrations.RunPython(cargar_catalogo, migrations.RunPython.noop),
    ]
