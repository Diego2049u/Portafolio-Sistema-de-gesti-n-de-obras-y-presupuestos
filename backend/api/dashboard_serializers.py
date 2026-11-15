from django.utils import timezone
from rest_framework import serializers

from .models import Obra


class DashboardFiltroSerializer(serializers.Serializer):
    desde = serializers.DateField(required=False)
    hasta = serializers.DateField(required=False)
    cliente_id = serializers.IntegerField(required=False, min_value=1)
    tecnico_id = serializers.IntegerField(required=False, min_value=1)
    estado_obra = serializers.ChoiceField(choices=Obra.ESTADOS, required=False)

    def validate(self, attrs):
        hoy = timezone.localdate()
        hasta = attrs.get('hasta', hoy)
        desde_default = hasta.replace(day=1) if 'hasta' in attrs else hoy.replace(day=1)
        attrs.setdefault('desde', desde_default)
        attrs.setdefault('hasta', hasta)
        if attrs['desde'] > attrs['hasta']:
            raise serializers.ValidationError({'desde': 'La fecha inicial debe ser anterior o igual a la fecha final.'})
        if (attrs['hasta'] - attrs['desde']).days > 366:
            raise serializers.ValidationError({'hasta': 'El rango máximo de consulta es de 367 días.'})
        return attrs
