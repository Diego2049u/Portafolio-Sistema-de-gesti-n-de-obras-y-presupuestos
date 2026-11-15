from django.core.management.base import BaseCommand

from api.models import CategoriaServicio


class Command(BaseCommand):
    help = 'Crea o reactiva las categorías de servicio iniciales del MVP.'

    CATEGORIAS = [
        'Proyecto',
        'Mantención',
        'Climatización',
        'Proyecto eléctrico',
        'Emergencia',
        'Garantía',
        'Mejoras',
    ]

    def handle(self, *args, **options):
        for orden, nombre in enumerate(self.CATEGORIAS, start=1):
            categoria, creada = CategoriaServicio.all_objects.update_or_create(
                nombre=nombre,
                defaults={'orden': orden, 'deleted_at': None},
            )
            accion = 'Creada' if creada else 'Disponible'
            self.stdout.write(f'{accion}: {categoria.nombre}')
