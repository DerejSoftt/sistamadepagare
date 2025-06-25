from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
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
    





#prestamos 

class OtroPrestamo(models.Model):
    TIPO_PRESTAMO_CHOICES = [
        ('personal', 'Préstamo Personal'),
        ('vehiculo', 'Préstamo para Vehículo'),
        ('vivienda', 'Préstamo para Vivienda'),
        ('negocio', 'Préstamo para Negocio'),
        ('emergencia', 'Préstamo de Emergencia'),
        ('educacion', 'Préstamo Educativo'),
    ]
    
    FRECUENCIA_PAGO_CHOICES = [
        (1, 'Mensual'),
        (2, 'Quincenal'),
        (4, 'Semanal'),
    ]
    
    # Relación con el cliente
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='otros_prestamos')
    
    tipo_prestamo = models.CharField(
        max_length=20,
        choices=TIPO_PRESTAMO_CHOICES,
        verbose_name='Tipo de préstamo'
    )
    
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Monto del préstamo',
        validators=[MinValueValidator(0)]
    )
    
    tasa_interes = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Tasa de interés mensual (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    plazo_meses = models.PositiveSmallIntegerField(
        verbose_name='Plazo (meses)',
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    
    frecuencia_pagos = models.PositiveSmallIntegerField(
        choices=FRECUENCIA_PAGO_CHOICES,
        verbose_name='Frecuencia de pagos'
    )
    
    tasa_mora = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Tasa de mora por retraso (%)',
        default=2.00,
        validators=[MinValueValidator(0)]
    )
    
    fecha_calculo = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de cálculo'
    )
    
    # Campos calculados
    total_intereses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Intereses totales',
        validators=[MinValueValidator(0)]
    )
    
    total_pagar = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Total a pagar',
        validators=[MinValueValidator(0)]
    )
    
    pago_periodico = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Pago por período',
        validators=[MinValueValidator(0)]
    )

    observacion = models.TextField(
        verbose_name='Observación',
        blank=True,
        null=True,
        max_length=500
    )

    class Meta:
        db_table = 'otros_prestamos'
        verbose_name = 'Otro Préstamo'
        verbose_name_plural = 'Otros Préstamos'
        ordering = ['-fecha_calculo']
    
    def __str__(self):
        return f"Préstamo {self.get_tipo_prestamo_display()} - {self.cliente} - RD${self.monto}"
    
    def save(self, *args, **kwargs):
        # Calcular los valores antes de guardar
        if not self.pk:  # Solo para nuevos préstamos
            total_pagos = self.plazo_meses * self.frecuencia_pagos
            interes_total = self.monto * (self.tasa_interes / 100) * self.plazo_meses
            self.total_intereses = interes_total
            self.total_pagar = self.monto + interes_total
            self.pago_periodico = self.total_pagar / total_pagos
        super().save(*args, **kwargs)
    
    def generar_tabla_amortizacion(self):
        """
        Método para generar la tabla de amortización similar a la del HTML
        Devuelve una lista de diccionarios con los datos de cada pago
        """
        tabla = []
        saldo = self.monto
        total_pagos = self.plazo_meses * self.frecuencia_pagos
        pago_capital = self.monto / total_pagos
        interes_por_periodo = (self.monto * (self.tasa_interes / 100)) / self.frecuencia_pagos
        
        for i in range(1, total_pagos + 1):
            total_pago = pago_capital + interes_por_periodo
            saldo -= pago_capital
            
            tabla.append({
                'numero': i,
                'capital': round(pago_capital, 2),
                'interes': round(interes_por_periodo, 2),
                'total_pago': round(total_pago, 2),
                'balance': round(saldo if saldo > 0 else 0, 2)
            })
        
        return tabla




# class Amortizacion(models.Model):
#     prestamo = models.ForeignKey(
#         'OtroPrestamo',
#         on_delete=models.CASCADE,
#         related_name='amortizaciones'
#     )
#     numero_pago = models.PositiveSmallIntegerField(verbose_name='Número de pago')
#     capital = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         verbose_name='Capital',
#         validators=[MinValueValidator(0)]
#     )
#     interes = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         verbose_name='Interés',
#         validators=[MinValueValidator(0)]
#     )
#     total_pago = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         verbose_name='Total pago',
#         validators=[MinValueValidator(0)]
#     )
#     balance = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         verbose_name='Balance pendiente',
#         validators=[MinValueValidator(0)]
#     )
#     fecha_pago = models.DateField(
#         blank=True,
#         null=True,
#         verbose_name='Fecha de pago real'
#     )
#     pagado = models.BooleanField(default=False, verbose_name='¿Pagado?')

#     class Meta:
#         db_table = 'amortizaciones_prestamos'
#         verbose_name = 'Amortización'
#         verbose_name_plural = 'Amortizaciones'
#         ordering = ['prestamo', 'numero_pago']

#     def __str__(self):
#         return f"Pago {self.numero_pago} - {self.prestamo}"