from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse

# Imports de modelos
from .models import (
    Usuario, Cliente, Presupuesto, Obra, 
    CostoMaterial, Factura, Pago, Material, MovimientoBodega
)
# Imports de serializers
from .serializers import (
    UsuarioSerializer, ClienteSerializer, PresupuestoSerializer, 
    ObraSerializer, CostoMaterialSerializer, FacturaSerializer, PagoSerializer,
    MaterialSerializer, MovimientoBodegaSerializer
)
# Servicios de negocio y generador de PDF
from .services import validar_cierre_obra, registrar_egreso_bodega
from .pdf_generador import generar_pdf_presupuesto


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer


class PresupuestoViewSet(viewsets.ModelViewSet):
    queryset = Presupuesto.objects.all()
    serializer_class = PresupuestoSerializer

    # Endpoint para descargar el PDF: /api/presupuestos/{id}/exportar-pdf/
    @action(detail=True, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request, pk=None):
        presupuesto = self.get_object()
        pdf_buffer = generar_pdf_presupuesto(presupuesto)
        
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Presupuesto_{presupuesto.numero_presupuesto}.pdf"'
        return response


class ObraViewSet(viewsets.ModelViewSet):
    queryset = Obra.objects.all()
    serializer_class = ObraSerializer

    # Sobrescribimos el update para aplicar la validación RF-07
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        nuevo_estado = request.data.get('estado_operativo')

        # Si intentan pasar la obra a 'finalizada', valida las facturas/pagos pendientes
        if nuevo_estado == 'finalizada' and instance.estado_operativo != 'finalizada':
            validar_cierre_obra(instance)

        return super().update(request, *args, **kwargs, partial=partial)


class CostoMaterialViewSet(viewsets.ModelViewSet):
    queryset = CostoMaterial.objects.all()
    serializer_class = CostoMaterialSerializer


class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer


class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer


class MovimientoBodegaViewSet(viewsets.ModelViewSet):
    queryset = MovimientoBodega.objects.all()
    serializer_class = MovimientoBodegaSerializer

    def create(self, request, *args, **kwargs):
        tipo = request.data.get('tipo')
        if tipo == 'EGRESO':
            material_id = request.data.get('material')
            cantidad = int(request.data.get('cantidad', 0))
            obra_id = request.data.get('obra')
            
            movimiento, alerta = registrar_egreso_bodega(
                material_id=material_id,
                cantidad=cantidad,
                obra_id=obra_id,
                usuario=request.user if request.user.is_authenticated else None
            )
            serializer = self.get_serializer(movimiento)
            return Response({
                "movimiento": serializer.data,
                "alerta_stock_critico": alerta
            }, status=status.HTTP_201_CREATED)
        
        return super().create(request, *args, **kwargs)