from django.db import migrations, models


def actualizar_superusuarios(apps, schema_editor):
    Usuario = apps.get_model('api', 'Usuario')
    Usuario._base_manager.using(schema_editor.connection.alias).filter(
        rol='GERENCIA', is_superuser=True,
    ).update(rol='ADMIN_GENERAL')


def restaurar_rol_anterior(apps, schema_editor):
    Usuario = apps.get_model('api', 'Usuario')
    Usuario._base_manager.using(schema_editor.connection.alias).filter(
        rol='ADMIN_GENERAL',
    ).update(rol='GERENCIA')


class Migration(migrations.Migration):
    dependencies = [('api', '0003_recursos')]

    operations = [
        migrations.AlterField(
            model_name='usuario',
            name='rol',
            field=models.CharField(
                choices=[
                    ('ADMIN_GENERAL', 'Administrador general'),
                    ('GERENCIA', 'Gerencia'),
                    ('FINANZAS', 'Finanzas'),
                    ('SUPERVISOR', 'Supervisor de Obras'),
                    ('TECNICO', 'Técnico'),
                ],
                default='TECNICO',
                max_length=20,
            ),
        ),
        migrations.RunPython(actualizar_superusuarios, restaurar_rol_anterior),
    ]
