from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import datetime, timedelta
from django.utils.timezone import now
from decimal import Decimal
from django.conf import settings



class Cliente(models.Model):
    GENERO_CHOICES = [
        ('male', 'Masculino'),
        ('female', 'Femenino'),
        ('other', 'Otro'),
    ]
    
    PROVINCIA_CHOICES = [
        ('DN', 'Distrito Nacional'),
        ('SD', 'Santo Domingo'),
        ('SDE', 'Santo Domingo Este'),
        ('SA', 'Santiago'),
        ('PU', 'Puerto Plata'),
        ('LA', 'La Altagracia'),
        ('VE', 'La Vega'),
        ('SP', 'San Pedro de Macorís'),
        ('SC', 'San Cristóbal'),
        ('HR', 'Hermanas Mirabal'),
        ('MC', 'Montecristi'),
    ]
    
    TIPO_CUENTA_CHOICES = [
        ('corriente', 'Corriente'),
        ('ahorro', 'Ahorro'),
    ]

    # Información Personal
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    numero_identificacion = models.CharField(max_length=20, unique=True)
    genero = models.CharField(max_length=10, choices=GENERO_CHOICES)
    nacionalidad = models.CharField(max_length=50, default='Dominicana')
    
    # Información de Contacto
    telefono_principal = models.CharField(max_length=15)
    telefono_secundario = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.TextField()
    ciudad = models.CharField(max_length=50)
    provincia = models.CharField(max_length=3, choices=PROVINCIA_CHOICES)
    
    # Información Financiera
    tipo_cuenta = models.CharField(max_length=10, choices=TIPO_CUENTA_CHOICES)
    ingresos_mensuales = models.DecimalField(max_digits=10, decimal_places=2)
    empleador = models.CharField(max_length=100, blank=True, null=True)
    telefono_laboral = models.CharField(max_length=15, blank=True, null=True)
    banco_principal = models.CharField(max_length=50, blank=True, null=True)
    numero_cuenta = models.CharField(max_length=20, blank=True, null=True)
    
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
    
class Prestamo(models.Model):
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia Bancaria'),
        ('cheque', 'Cheque'),
    ]
    
    DEPARTAMENTO_CHOICES = [
        ('ayuntamiento', 'Ayuntamiento'),
        ('ferquido', 'Ferquido'),
        ('choga', 'Choga'),
        ('financiamiento', 'Financiamiento'),
        ('personal', 'Personal'),
    ]
    
    cliente = models.ForeignKey('Cliente', on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(1)])
    fecha_despacho = models.DateField()
    fecha_vencimiento = models.DateField()  # Nuevo campo agregado
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    departamento = models.CharField(max_length=20, choices=DEPARTAMENTO_CHOICES)
    observaciones = models.TextField(blank=True, null=True)
    numero_factura = models.CharField(max_length=50, unique=True, blank=True, null=True)
    estado = models.CharField(max_length=20, default='ACTIVO')
    fecha_vencimiento = models.DateField(default=now() + timedelta(days=30))
    fecha_registro = models.DateTimeField(auto_now_add=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return f"Préstamo {self.numero_factura or self.id} - {self.cliente.nombres}"
    
    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"
        ordering = ['-fecha_registro']




class Ingreso(models.Model):
    # Opciones para los campos de selección
    METODO_PAGO_OPCIONES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('CHEQUE', 'Cheque'),
        ('OTRO', 'Otro método'),
    ]
    
    TIPO_PAGO_OPCIONES = [
        ('COMPLETO', 'Pago Completo'),
        ('ABONO', 'Abono'),
    ]
    
    MOTIVO_ANULACION_OPCIONES = [
        ('ERROR_MONTO', 'Error en el monto'),
        ('RECIBO_DUPLICADO', 'Recibo duplicado'),
        ('SOLICITUD_CLIENTE', 'Solicitud del cliente'),
        ('ERROR_SISTEMA', 'Error del sistema'),
        ('OTRO', 'Otro'),
    ]

    # Campos del modelo
    no_recibo = models.CharField(
        'Número de Recibo', 
        max_length=50, 
        unique=True,
        help_text="Número único que identifica el recibo"
    )
    
    prestamo = models.ForeignKey(
        'Prestamo', 
        on_delete=models.CASCADE,
        related_name='pagos',
        null=True,
        blank=True
    )
    
    monto_pago = models.DecimalField(
        'Monto del Pago', 
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Monto del pago recibido"
    )
    
    fecha_pago = models.DateField(
        'Fecha de Pago', 
        default=timezone.now,
        help_text="Fecha en que se realizó el pago"
    )
    
    metodo_pago = models.CharField(
        'Método de Pago', 
        max_length=20, 
        choices=METODO_PAGO_OPCIONES,
        default='EFECTIVO',
        help_text="Método utilizado para el pago"
    )
    
    tipo_pago = models.CharField(
        'Tipo de Pago', 
        max_length=20, 
        choices=TIPO_PAGO_OPCIONES,
        default='COMPLETO',
        help_text="Tipo de pago: Pago Completo o Abono"
    )
    
    notas = models.TextField(
        'Notas', 
        blank=True, 
        null=True,
        help_text="Observaciones o detalles adicionales sobre el pago"
    )
    
    fecha_registro = models.DateTimeField(
        'Fecha de Registro', 
        auto_now_add=True,
        help_text="Fecha y hora en que se registró el ingreso en el sistema"
    )
    
    # Campos para anulación
    anulado = models.BooleanField(
        'Anulado',
        default=False,
        help_text="Indica si el recibo ha sido anulado"
    )
    
    fecha_anulacion = models.DateField(
        'Fecha de Anulación',
        null=True,
        blank=True,
        help_text="Fecha en que se anuló el recibo"
    )
    
    motivo_anulacion = models.CharField(
        'Motivo de Anulación',
        max_length=20,
        choices=MOTIVO_ANULACION_OPCIONES,
        null=True,
        blank=True,
        help_text="Motivo por el cual se anuló el recibo"
    )
    
    notas_anulacion = models.TextField(
        'Notas de Anulación',
        blank=True,
        null=True,
        help_text="Observaciones adicionales sobre la anulación"
    )
    
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anulaciones_realizadas',
        help_text="Usuario que realizó la anulación"
    )

    class Meta:
        verbose_name = 'Ingreso'
        verbose_name_plural = 'Ingresos'
        ordering = ['-fecha_pago', '-no_recibo']
        db_table = 'ingreso'

    def __str__(self):
        status = "ANULADO" if self.anulado else "ACTIVO"
        return f"Recibo {self.no_recibo} - {self.monto_pago} ({self.fecha_pago}) - {status}"

    def cancelar(self, motivo, notas, fecha_anulacion=None, usuario=None):
        """
        Cancela el recibo
        """
        try:
            if self.anulado:
                return False, "Este recibo ya está anulado"
            
            self.anulado = True
            self.motivo_anulacion = motivo
            self.notas_anulacion = notas
            
            if fecha_anulacion:
                if isinstance(fecha_anulacion, str):
                    from datetime import datetime
                    self.fecha_anulacion = datetime.strptime(fecha_anulacion, '%Y-%m-%d')
                else:
                    self.fecha_anulacion = fecha_anulacion
            else:
                self.fecha_anulacion = timezone.now()
            
            self.save()
            
            return True, f"Recibo {self.no_recibo} anulado exitosamente"
            
        except Exception as e:
            return False, f"Error al anular el recibo: {str(e)}"
    
    def __str__(self):
        return f"Recibo {self.no_recibo} - {self.monto_pago}"
    





# models.py
class RecibosAnulados(models.Model):
    # Copia todos los campos del modelo Ingreso
    no_recibo = models.CharField('Número de Recibo', max_length=50)
    prestamo = models.ForeignKey('Prestamo', on_delete=models.SET_NULL, null=True, blank=True)
    monto_pago = models.DecimalField('Monto del Pago', max_digits=10, decimal_places=2)
    fecha_pago = models.DateField('Fecha de Pago')
    metodo_pago = models.CharField('Método de Pago', max_length=20)
    tipo_pago = models.CharField('Tipo de Pago', max_length=20)
    notas = models.TextField('Notas', blank=True, null=True)
    fecha_registro = models.DateTimeField('Fecha de Registro')
    
    # Campos específicos de anulación
    motivo_anulacion = models.CharField('Motivo de Anulación', max_length=20)
    notas_anulacion = models.TextField('Notas de Anulación')
    fecha_anulacion = models.DateField('Fecha de Anulación')
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recibos_anulados'
    )
    
    class Meta:
        verbose_name = 'Recibo Anulado'
        verbose_name_plural = 'Recibos Anulados'
        ordering = ['-fecha_anulacion']
        
    def __str__(self):
        return f"Recibo Anulado {self.no_recibo} - {self.monto_pago}"