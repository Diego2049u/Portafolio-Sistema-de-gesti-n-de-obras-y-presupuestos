from rest_framework import serializers
from .models import Usuario, Cliente, Presupuesto, ItemPresupuesto, Obra, CostoMaterial, Factura, Pago, AuditoriaLog, Material, MovimientoBodega

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'rut_usuario', 'cargo', 'rol', 'estado']

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

class ItemPresupuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemPresupuesto
        fields = '__all__'

class PresupuestoSerializer(serializers.ModelSerializer):
    items = ItemPresupuestoSerializer(many=True, read_only=True)
    cliente_nombre = serializers.ReadOnlyField(source='cliente.razon_social')

    class Meta:
        model = Presupuesto
        fields = '__all__'

class ObraSerializer(serializers.ModelSerializer):
    tecnico_nombre = serializers.ReadOnlyField(source='tecnico_responsable.get_full_name')
    
    class Meta:
        model = Obra
        fields = '__all__'

class CostoMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostoMaterial
        fields = '__all__'

class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'

class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'

class MovimientoBodegaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoBodega
        fields = '__all__'