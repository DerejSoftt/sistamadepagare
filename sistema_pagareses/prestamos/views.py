from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from .models import Cliente,  Prestamo, Ingreso, RecibosAnulados
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from decimal import Decimal,  InvalidOperation
import json

from django.db.models import Sum, Q, F, DecimalField, ExpressionWrapper, OuterRef
from django.db.models.functions import Coalesce
from django.db.models.expressions import ExpressionWrapper


from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from num2words import num2words
from datetime import datetime

import pandas as pd
import numpy as np
from django.db import transaction
from django.db import IntegrityError
import time
import uuid
from django.contrib import messages
from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa


from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator

from django.db.models import DurationField

from django.contrib.auth import authenticate, login as auth_login

from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required

def formulario(request):
    if request.method == 'POST':
        data = request.POST
        response_data = {'success': False, 'errors': {}}
        
        try:
            # Validación de campos requeridos
            required_fields = {
                'nombres': 'Nombre(s)',
                'apellidos': 'Apellido(s)',
                'numero_identificacion': 'Número de Identificación',
                'genero': 'Género',
                'telefono_principal': 'Teléfono Principal',
                'direccion': 'Dirección Residencial',
                'ciudad': 'Ciudad',
                'provincia': 'Provincia',
                'tipo_cuenta': 'Tipo de Cuenta',
                'ingresos_mensuales': 'Ingresos Mensuales'
            }
            
            for field, name in required_fields.items():
                if not data.get(field):
                    response_data['errors'][field] = [f'El campo {name} es requerido']

            # Validación de número de identificación único
            if not response_data['errors'].get('numero_identificacion'):
                if Cliente.objects.filter(numero_identificacion=data['numero_identificacion']).exists():
                    response_data['errors']['numero_identificacion'] = ['Este número de identificación ya existe']

            # Validación de ingresos mensuales
            try:
                ingresos = Decimal(data.get('ingresos_mensuales', '0'))
                if ingresos <= 0:
                    response_data['errors']['ingresos_mensuales'] = ['Los ingresos deben ser mayores a 0']
            except (InvalidOperation, ValueError):
                response_data['errors']['ingresos_mensuales'] = ['Ingrese un valor numérico válido']

            if response_data['errors']:
                raise ValidationError('Error de validación en los datos')

            # Crear el cliente
            cliente = Cliente(
                nombres=data['nombres'],
                apellidos=data['apellidos'],
                numero_identificacion=data['numero_identificacion'],
                genero=data['genero'],
                nacionalidad=data.get('nacionalidad', 'Dominicana'),
                telefono_principal=data['telefono_principal'],
                telefono_secundario=data.get('telefono_secundario') or None,
                direccion=data['direccion'],
                ciudad=data['ciudad'],
                provincia=data['provincia'],
                tipo_cuenta=data['tipo_cuenta'],
                ingresos_mensuales=ingresos,
                empleador=data.get('empleador') or None,
                telefono_laboral=data.get('telefono_laboral') or None,
                banco_principal=data.get('banco_principal') or None,
                numero_cuenta=data.get('numero_cuenta') or None
            )
            
            cliente.full_clean()
            cliente.save()
            
            response_data['success'] = True
            response_data['message'] = 'Cliente registrado exitosamente'
            
        except ValidationError as e:
            if not response_data['errors']:
                response_data['error_message'] = str(e)
        except Exception as e:
            response_data['error_message'] = 'Error al procesar el formulario'
            import logging
            logging.error(f'Error al guardar cliente: {str(e)}')
        
        return JsonResponse(response_data)
    
    # Método GET
    return render(request, "prestamos/formulario.html")


def reporte(request):
    return render(request, "prestamos/reporte.html")




def clientes(request):
    # Obtener parámetros de búsqueda
    search_query = request.GET.get('search', '')
    
    # Filtrar clientes
    if search_query:
        clientes = Cliente.objects.filter(
            Q(nombres__icontains=search_query) | 
            Q(apellidos__icontains=search_query) | 
            Q(numero_identificacion__icontains=search_query) |
            Q(telefono_principal__icontains=search_query)
        ).order_by('nombres')
    else:
        clientes = Cliente.objects.all().order_by('nombres')
    
    context = {
        'clientes': clientes,
        'search_query': search_query
    }
    
    return render(request, "prestamos/clientes.html", context)



def cliente_detalle(request, cliente_id):
    try:
        cliente = Cliente.objects.get(pk=cliente_id)
    except Cliente.DoesNotExist:
        return redirect('clientes')
    
    # Obtener préstamos del cliente
    prestamos = Prestamo.objects.filter(cliente=cliente, estado='ACTIVO')
    
    # Calcular totales para cada préstamo
    prestamos_con_saldo = []
    total_prestado = 0
    total_pagado = 0
    total_adeudado = 0
    
    for prestamo in prestamos:
        # Calcular pagos para este préstamo específico
        pagos_prestamo = Ingreso.objects.filter(
            prestamo=prestamo
        ).aggregate(total=Sum('monto_pago'))['total'] or 0
        
        saldo = prestamo.monto - pagos_prestamo
        
        # Crear objeto temporal con saldo calculado
        prestamo.total_pagado = pagos_prestamo
        prestamo.saldo = saldo
        
        prestamos_con_saldo.append(prestamo)
        total_prestado += prestamo.monto
        total_pagado += pagos_prestamo
        total_adeudado += saldo
    
    # Obtener historial de pagos del cliente
    pagos = Ingreso.objects.filter(
        prestamo__cliente=cliente
    ).order_by('-fecha_pago')
    
    context = {
        'cliente': cliente,
        'prestamos': prestamos_con_saldo,
        'total_prestado': total_prestado,
        'total_pagado': total_pagado,
        'total_adeudado': total_adeudado,
        'pagos': pagos,
        'prestamos_pagados': Prestamo.objects.filter(
            cliente=cliente, 
            estado='PAGADO'
        ).count(),
        'hoy': timezone.now().date()
    }
    
    return render(request, "prestamos/cliente_detalle.html", context)

def registrar_pago(request):
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            cliente_id = request.POST.get('cliente_id')
            prestamo_id = request.POST.get('prestamo_id')
            monto = Decimal(request.POST.get('monto'))
            fecha_pago = request.POST.get('fecha_pago')
            metodo_pago = request.POST.get('metodo_pago')
            tipo_pago = request.POST.get('tipo_pago')
            notas = request.POST.get('notas', '')
            
            
            # Validar datos
            if not all([cliente_id, prestamo_id, monto, fecha_pago, metodo_pago, tipo_pago]):
                return JsonResponse({'success': False, 'error': 'Faltan campos requeridos'})
            
            # Validar que el préstamo existe y pertenece al cliente
            try:
                prestamo = Prestamo.objects.get(pk=prestamo_id, cliente_id=cliente_id)
            except Prestamo.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Préstamo no encontrado'})
            
            # Calcular saldo actual del préstamo
            pagos_anteriores = Ingreso.objects.filter(
                prestamo=prestamo
            ).aggregate(total=Sum('monto_pago'))['total'] or 0
            
            saldo_actual = prestamo.monto - pagos_anteriores
            
            # Validar que el monto no exceda el saldo
            if monto > saldo_actual:
                return JsonResponse({
                    'success': False, 
                    'error': f'El monto excede el saldo pendiente (RD$ {saldo_actual:.2f})'
                })
            
            # Generar número de recibo único
            intentos = 0
            max_intentos = 5
            ingreso = None
            
            while intentos < max_intentos:
                try:
                    # Obtener el último recibo para este préstamo
                    ultimo_recibo = Ingreso.objects.filter(
                        prestamo=prestamo
                    ).order_by('-no_recibo').first()
                    
                    if ultimo_recibo:
                        try:
                            # Extraer el número secuencial del último recibo
                            ultimo_numero = int(ultimo_recibo.no_recibo.split('-')[-1])
                            nuevo_numero = f"{ultimo_numero + 1:04d}"
                        except (ValueError, IndexError):
                            # Si hay algún problema con el formato, empezamos desde 1
                            nuevo_numero = "0001"
                    else:
                        nuevo_numero = "0001"
                    
                    no_recibo = f"PR-{prestamo_id}-{nuevo_numero}"
                    
                    # Crear registro de ingreso
                    ingreso = Ingreso(
                        no_recibo=no_recibo,
                        prestamo=prestamo,
                        monto_pago=monto,
                        fecha_pago=fecha_pago,
                        metodo_pago=metodo_pago,
                        tipo_pago=tipo_pago,
                        notas=notas
                    )
                    ingreso.save()
                    break
                    
                except IntegrityError:
                    intentos += 1
                    if intentos >= max_intentos:
                        return JsonResponse({
                            'success': False, 
                            'error': 'No se pudo generar un número de recibo único después de varios intentos'
                        })
                    time.sleep(0.1)  # Pequeña pausa antes de reintentar
            
            # Verificar si el préstamo queda completamente pagado
            total_pagado_despues = pagos_anteriores + monto
            if total_pagado_despues >= prestamo.monto:
                prestamo.estado = 'PAGADO'
                prestamo.save()
            
            return JsonResponse({
                'success': True,
                'recibo': no_recibo,
                'fecha': fecha_pago,
                'monto': float(monto),
                'metodo': ingreso.get_metodo_pago_display(),
                'tipo': ingreso.get_tipo_pago_display(),
                'saldo_restante': float(prestamo.monto - total_pagado_despues)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})



def obtener_prestamos_cliente(request, cliente_id):
    try:
        prestamos = Prestamo.objects.filter(cliente_id=cliente_id, estado='ACTIVO')
        
        data = []
        for prestamo in prestamos:
            # Calcular pagos específicos para este préstamo
            pagos_prestamo = Ingreso.objects.filter(
                no_recibo__startswith=f'PR-{prestamo.id}-'
            ).aggregate(total=Sum('monto_pago'))['total'] or 0
            
            saldo = prestamo.monto - pagos_prestamo
            
            data.append({
                'id': prestamo.id,
                'numero_factura': prestamo.numero_factura or f"PR-{prestamo.id}",
                'monto': float(prestamo.monto),
                'pagado': float(pagos_prestamo),
                'saldo': float(saldo),
                'fecha': prestamo.fecha_despacho.strftime('%Y-%m-%d')
            })
        
        return JsonResponse({'success': True, 'prestamos': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})












def reimprimir(request):
    # Obtener el último préstamo registrado
    ultimo_prestamo = Prestamo.objects.order_by('-fecha_registro').first()
    
    # Obtener todos los préstamos para la búsqueda
    prestamos = Prestamo.objects.all().order_by('-fecha_registro')
    
    # Datos de la empresa (deberías configurarlos en settings.py o en un modelo)
    empresa = {
        'nombre': getattr(settings, 'EMPRESA_NOMBRE', 'Mi Empresa'),
        'direccion': getattr(settings, 'EMPRESA_DIRECCION', 'Calle Principal #123'),
        'rnc': getattr(settings, 'EMPRESA_RNC', '123456789'),
        'telefono': getattr(settings, 'EMPRESA_TELEFONO', '809-555-5555'),
    }
    
    context = {
        'ultimo_prestamo': ultimo_prestamo,
        'prestamos': prestamos,
        'empresa': empresa,
    }
    return render(request, "prestamos/reimprimir.html", context)



def imprimir_pagare(request, numero_factura):
    prestamo = get_object_or_404(Prestamo, numero_factura=numero_factura)
    
    # Datos de la empresa (configurar en settings.py)
    empresa = {
        'nombre': getattr(settings, 'EMPRESA_NOMBRE', 'AGRO-JIMENEZ CRUZ, SRL'),
        'direccion': getattr(settings, 'EMPRESA_DIRECCION', 'Calle Principal #123, CASTAÑUELAS, RD'),
        'rnc': getattr(settings, 'EMPRESA_RNC', '123-456789-11'),
        'telefono': getattr(settings, 'EMPRESA_TELEFONO', '808-555-5555'),
    }
    
    # Convertir monto a letras
    try:
        monto_letras = num2words(float(prestamo.monto), lang='es').upper() + " PESOS DOMINICANOS CON 00/100"
    except:
        monto_letras = ""

    context = {
        'empresa': empresa,
        'prestamo': {
            'numero_factura': prestamo.numero_factura,
            'fecha': prestamo.fecha_despacho.strftime('%d/%m/%Y'),
            'fecha_vencimiento': prestamo.fecha_vencimiento.strftime('%d/%m/%Y'),
            'monto': "{:,.2f}".format(float(prestamo.monto)),
            'monto_letras': monto_letras,
            'departamento': prestamo.get_departamento_display(),
            'observaciones': prestamo.observaciones or '',
        },
        'cliente': {
            'nombre_completo': f"{prestamo.cliente.nombres} {prestamo.cliente.apellidos or ''}",
            'documento': prestamo.cliente.numero_identificacion,
            'direccion': prestamo.cliente.direccion,
        }
    }

    return render(request, 'prestamos/facturas.html', context)



def registrodepago(request):
    # Obtener todos los préstamos con sus pagos relacionados
    prestamos = Prestamo.objects.select_related('cliente').prefetch_related('pagos').all()
    
    # Calcular campos adicionales para cada préstamo
    for prestamo in prestamos:
        # Calcular total pagado
        prestamo.total_pagado = sum(pago.monto_pago for pago in prestamo.pagos.all())
        
        # Calcular saldo pendiente
        prestamo.saldo_pendiente = prestamo.monto - prestamo.total_pagado
        
        # Calcular progreso de pago (porcentaje)
        prestamo.progreso_pago = (prestamo.total_pagado / prestamo.monto) * 100 if prestamo.monto > 0 else 0
        
        # Determinar estado basado en fechas y pagos
        hoy = timezone.now().date()
        if prestamo.progreso_pago >= 100:
            prestamo.estado = 'COMPLETADO'
        elif prestamo.fecha_vencimiento < hoy:
            prestamo.estado = 'ATRASADO'
        else:
            prestamo.estado = 'ACTIVO'
    
    context = {
        'prestamos': prestamos
    }
    return render(request, "prestamos/registrodepago.html", context)





def prestamospagados(request):
    # Obtener todos los préstamos con estado "PAGADO"
    prestamos = Prestamo.objects.filter(estado='PAGADO').select_related('cliente').prefetch_related('pagos').order_by('-fecha_registro')
    
    # Anotar cada préstamo con el total pagado (suma de todos sus recibos)
    prestamos = prestamos.annotate(
        total_pagado=Coalesce(Sum('pagos__monto_pago'), Decimal('0.00')),
        days=ExpressionWrapper(
            F('fecha_vencimiento') - F('fecha_despacho'),
            output_field=DurationField()
        )
    ).annotate(
        interest=F('total_pagado') - F('monto')
    )
    
    # Paginación
    paginator = Paginator(prestamos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'loans': page_obj,
    }
    return render(request, "prestamos/prestamospagados.html", context)

@require_http_methods(["POST"])
def toggle_loan_status(request, loan_id):
    prestamo = get_object_or_404(Prestamo, id=loan_id)
    if prestamo.estado == 'ACTIVO':
        prestamo.estado = 'INACTIVO'
    else:
        prestamo.estado = 'ACTIVO'
    prestamo.save()
    return JsonResponse({'success': True})

@require_http_methods(["DELETE"])
def delete_loan(request, loan_id):
    prestamo = get_object_or_404(Prestamo, id=loan_id)
    prestamo.delete()
    return JsonResponse({'success': True})


def despacho(request):
    return render(request, "prestamos/despacho.html")


@csrf_exempt
def buscar_clientes(request):
    if request.method == 'POST':
        try:
            # Parsear el cuerpo de la solicitud
            try:
                data = json.loads(request.body.decode('utf-8'))
                query = data.get('query', '').strip()
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'Formato JSON inválido'
                }, status=400)

            # Validar longitud mínima de búsqueda
            if len(query) < 3:
                return JsonResponse({
                    'success': False,
                    'error': 'La búsqueda requiere al menos 3 caracteres'
                }, status=400)

            # Realizar la búsqueda en la base de datos (CORREGIDO)
            clientes = Cliente.objects.filter(
                Q(nombres__icontains=query) | 
                Q(apellidos__icontains=query) |
                Q(numero_identificacion__icontains=query)
            ).order_by('nombres')[:10]  # Limitar a 10 resultados

            # Preparar los resultados
            resultados = [{
                'id': cliente.id,
                'nombre': f"{cliente.nombres} {cliente.apellidos}",
                'documento': cliente.numero_identificacion,
                'direccion': cliente.direccion or ''
            } for cliente in clientes]

            return JsonResponse({
                'success': True,
                'results': resultados
            })

        except Exception as e:
            print(f"Error en buscar_clientes: {str(e)}")  # Para debugging
            return JsonResponse({
                'success': False,
                'error': f'Error en el servidor: {str(e)}'
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)


# @csrf_exempt
# def registrar_despacho(request):
#     if request.method == 'POST':
#         try:
#             # Parsear los datos de la solicitud
#             try:
#                 data = json.loads(request.body.decode('utf-8'))
#             except json.JSONDecodeError:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'Formato JSON inválido'
#                 }, status=400)

#             # Validar campos obligatorios
#             required_fields = ['cliente_id', 'monto', 'fecha_despacho', 'metodo_pago', 'departamento']
#             for field in required_fields:
#                 if field not in data or not data[field]:
#                     return JsonResponse({
#                         'success': False,
#                         'error': f'El campo {field} es requerido'
#                     }, status=400)

#             # Obtener el cliente por documento (CORREGIDO - ya que envías el documento, no el ID)
#             try:
#                 cliente = Cliente.objects.get(numero_identificacion=data['cliente_id'])
#             except Cliente.DoesNotExist:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'Cliente no encontrado'
#                 }, status=404)

#             # Validar el monto
#             try:
#                 monto = float(data['monto'])
#                 if monto <= 0:
#                     raise ValueError("El monto debe ser positivo")
#             except (ValueError, TypeError):
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'Monto inválido'
#                 }, status=400)

#             # Crear el préstamo
#             try:
#                 prestamo = Prestamo(
#                     cliente=cliente,
#                     monto=monto,
#                     fecha_despacho=data['fecha_despacho'],
#                     metodo_pago=data['metodo_pago'],
#                     departamento=data['departamento'],
#                     observaciones=data.get('observaciones', '')
#                 )
                
#                 # Validar el modelo antes de guardar
#                 prestamo.full_clean()
#                 prestamo.save()

#                 return JsonResponse({
#                     'success': True,
#                     'prestamo_id': prestamo.id,
#                     'message': 'Préstamo registrado exitosamente'
#                 })

#             except ValidationError as e:
#                 return JsonResponse({
#                     'success': False,
#                     'error': 'Datos inválidos: ' + str(e)
#                 }, status=400)

#         except Exception as e:
#             print(f"Error en registrar_despacho: {str(e)}")  # Para debugging
#             return JsonResponse({
#                 'success': False,
#                 'error': f'Error en el servidor: {str(e)}'
#             }, status=500)

#     return JsonResponse({
#         'success': False,
#         'error': 'Método no permitido'
#     }, status=405)


def generar_numero_factura(departamento):
    """
    Genera un número de factura único con autoincremento
    Formato: DEPT-AAAA-NNNNNN
    """
    # Mapeo de departamentos a códigos
    dept_codes = {
        'ayuntamiento': 'AYU',
        'ferquido': 'FER'
    }
    
    dept_code = dept_codes.get(departamento, 'GEN')
    year = timezone.now().year
    
    # Obtener el último número para este departamento y año
    ultimo_prestamo = Prestamo.objects.filter(
        departamento=departamento,
        numero_factura__startswith=f"{dept_code}-{year}-"
    ).order_by('-id').first()
    
    if ultimo_prestamo and ultimo_prestamo.numero_factura:
        try:
            # Extraer el número secuencial
            ultimo_numero = int(ultimo_prestamo.numero_factura.split('-')[-1])
            nuevo_numero = ultimo_numero + 1
        except (ValueError, IndexError):
            nuevo_numero = 1
    else:
        nuevo_numero = 1
    
    # Generar número de factura
    numero_factura = f"{dept_code}-{year}-{nuevo_numero:06d}"
    
    # Verificar que no exista (por seguridad en caso de concurrencia)
    contador = 0
    numero_base = numero_factura
    while Prestamo.objects.filter(numero_factura=numero_factura).exists():
        contador += 1
        nuevo_numero += contador
        numero_factura = f"{dept_code}-{year}-{nuevo_numero:06d}"
        
        # Evitar bucle infinito
        if contador > 100:
            numero_factura = f"{dept_code}-{year}-{timezone.now().timestamp():.0f}"[-15:]
            break
    
    return numero_factura

@csrf_exempt
def registrar_despacho(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validar datos requeridos
            required_fields = ['cliente_id', 'monto', 'fecha_despacho', 'metodo_pago', 'departamento']
            if not all(key in data for key in required_fields):
                return JsonResponse({
                    'success': False, 
                    'error': 'Datos incompletos. Faltan campos requeridos.'
                }, status=400)
            
            # Validar que el monto sea positivo
            try:
                monto = float(data['monto'])
                if monto <= 0:
                    return JsonResponse({
                        'success': False, 
                        'error': 'El monto debe ser mayor a cero.'
                    }, status=400)
            except ValueError:
                return JsonResponse({
                    'success': False, 
                    'error': 'Monto inválido.'
                }, status=400)
            
            # Validar formato de fecha
            try:
                fecha_despacho = datetime.strptime(data['fecha_despacho'], '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False, 
                    'error': 'Formato de fecha inválido.'
                }, status=400)
            
            # Usar transacción para asegurar consistencia
            with transaction.atomic():
                # Obtener cliente
                try:
                    cliente = Cliente.objects.get(numero_identificacion=data['cliente_id'])
                except Cliente.DoesNotExist:
                    return JsonResponse({
                        'success': False, 
                        'error': 'Cliente no encontrado en el sistema.'
                    }, status=404)
                
                # Generar número de factura
                numero_factura = generar_numero_factura(data['departamento'])
                
                # Crear préstamo con número de factura ya asignado
                prestamo = Prestamo.objects.create(
                    cliente=cliente,
                    monto=monto,
                    fecha_despacho=fecha_despacho,
                    metodo_pago=data['metodo_pago'],
                    departamento=data['departamento'],
                    observaciones=data.get('observaciones', ''),
                    numero_factura=numero_factura,
                    estado='ACTIVO'
                )
                
                return JsonResponse({
                    'success': True,
                    'prestamo_id': prestamo.id,
                    'numero_factura': prestamo.numero_factura,
                    'message': f'Despacho registrado exitosamente. Número de factura: {prestamo.numero_factura}'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False, 
                'error': 'Datos JSON inválidos.'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': f'Error interno del servidor: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False, 
        'error': 'Método no permitido. Use POST.'
    }, status=405)

def despacho(request):
    return render(request, "prestamos/despacho.html")

def anulacion(request):
    # Obtener el último préstamo activo para mostrar por defecto
    ultimo_prestamo = Prestamo.objects.filter(estado='ACTIVO').order_by('-fecha_registro').first()
    
    if request.method == 'POST':
        prestamo_id = request.POST.get('invoiceId')
        motivo = request.POST.get('reason')
        observaciones = request.POST.get('cancellationNotes')
        
        try:
            prestamo = Prestamo.objects.get(numero_factura=prestamo_id, estado='ACTIVO')
            cliente = prestamo.cliente
            
            # Marcar el préstamo como anulado
            prestamo.estado = 'ANULADO'
            prestamo.observaciones = f"ANULADO - Motivo: {motivo}. Observaciones: {observaciones}"
            prestamo.fecha_anulacion = timezone.now()
            prestamo.save()
            
            messages.success(request, f'Factura {prestamo_id} anulada correctamente.')
            return redirect('anulacion')
            
        except Prestamo.DoesNotExist:
            messages.error(request, 'No se encontró la factura especificada o ya fue anulada.')
    
    context = {
        'ultimo_prestamo': ultimo_prestamo
    }
    return render(request, "prestamos/anulacion.html", context)

def buscar_facturas(request):
    if request.GET.get('q'):
        query = request.GET.get('q')
        facturas = Prestamo.objects.filter(
            estado='ACTIVO',
            numero_factura__icontains=query
        )[:10]  # Limitar a 10 resultados
        
        resultados = []
        for factura in facturas:
            resultados.append({
                'id': factura.numero_factura,
                'cliente': f"{factura.cliente.nombres} {factura.cliente.apellidos or ''}",
                'cedula': factura.cliente.numero_identificacion,
                'direccion': factura.cliente.direccion or '',
                'departamento': factura.get_departamento_display(),
                'monto': float(factura.monto)
            })
        
        return JsonResponse(resultados, safe=False)
    return JsonResponse([], safe=False)

def anulacionderesivo(request):
    return render(request, "prestamos/anulacionderesivo.html")

def facturas(request):
    return render(request, "prestamos/facturas.html")

def factura_prestamo(request, prestamo_id):
    try:
        prestamo = get_object_or_404(Prestamo.objects.select_related('cliente'), pk=prestamo_id)
        cliente = prestamo.cliente

        def monto_a_letras(monto):
            try:
                monto_float = float(monto)
                parte_entera = int(monto_float)
                parte_decimal = int(round((monto_float - parte_entera) * 100))
                
                letras_entera = num2words(parte_entera, lang='es').upper()
                
                return f"{letras_entera} PESOS DOMINICANOS CON {parte_decimal:02d}/100"
            except Exception as e:
                print(f"Error convirtiendo monto a letras: {str(e)}")
                return f"{monto:,.2f} PESOS DOMINICANOS"

        # Función para obtener el teléfono del cliente de forma segura
        def obtener_telefono_cliente(cliente):
            # Intenta diferentes nombres de campo comunes
            campos_telefono = ['telefono', 'celular', 'movil', 'numero_telefono', 'tel', 'phone']
            
            for campo in campos_telefono:
                if hasattr(cliente, campo):
                    valor = getattr(cliente, campo)
                    if valor:
                        return valor
            
            return 'No especificado'

        context = {
            'empresa': {
                'nombre': 'AGRO-JIMENEZ CRUZ, SRL',
                'direccion': 'Calle Principal #123, CASTAÑUELAS, RD',
                'rnc': '123-456789-1',
                'telefono': '809-555-5555'
            },
            'prestamo': {
                'numero_factura': prestamo.numero_factura or f"P-{prestamo.id}",
                'fecha': prestamo.fecha_despacho.strftime("%d/%m/%Y"),
                'monto': f"RD$ {float(prestamo.monto):,.2f}",
                'monto_letras': monto_a_letras(prestamo.monto),
                'fecha_vencimiento': (prestamo.fecha_despacho + timedelta(days=120)).strftime("%d/%m/%Y"),
                'departamento': prestamo.get_departamento_display(),
                'observaciones': prestamo.observaciones or 'Ninguna'
                
            },
            'cliente': {
                'nombre_completo': f"{cliente.nombres} {cliente.apellidos}",
                'documento': cliente.numero_identificacion,
                'direccion': cliente.direccion or 'No especificada',
                'telefono': obtener_telefono_cliente(cliente)  # Usar la función segura
            }
        }

        return render(request, 'prestamos/facturas.html', context)

    except Exception as e:
        error_msg = f"Error generando factura: {str(e)}"
        print(error_msg)
        return HttpResponse(error_msg, status=500)

@require_http_methods(["GET", "POST"])
def index(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            auth_login(request, user)
            return redirect('reporte')  # Redirige al dashboard después del login
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'Credenciales inválidas o no tiene permisos de superusuario'
            }, status=400)
        
        return render(request, "prestamos/index.html", {
            'form': {'errors': True}
        })
    
    return render(request, "prestamos/index.html")


@csrf_exempt
@require_http_methods(["GET"])
def search_receipts(request):
    try:
        query = request.GET.get('q', '').strip()
        
        if not query or len(query) < 3:
            return JsonResponse({
                'error': 'Ingrese al menos 3 caracteres para buscar'
            }, status=400)
        
        print(f"Buscando recibos con query: {query}")
        
        # Buscar recibos no anulados
        receipts = Ingreso.objects.filter(
            anulado=False,
            no_recibo__icontains=query
        ).select_related('prestamo__cliente')[:10]
        
        results = []
        for receipt in receipts:
            try:
                cliente = receipt.prestamo.cliente if receipt.prestamo else None
                
                # Debug: Imprimir el monto para verificar
                print(f"Recibo {receipt.no_recibo}: monto_pago = {receipt.monto_pago} (tipo: {type(receipt.monto_pago)})")
                
                # Convertir monto a float de forma segura
                if receipt.monto_pago is not None:
                    if isinstance(receipt.monto_pago, Decimal):
                        monto = float(receipt.monto_pago)
                    else:
                        monto = float(receipt.monto_pago)
                else:
                    monto = 0.00
                
                result_item = {
                    'id': receipt.id,
                    'no_recibo': receipt.no_recibo,
                    'monto_pago': round(monto, 2),  # Redondear a 2 decimales
                    'fecha_pago': receipt.fecha_pago.strftime('%Y-%m-%d'),
                    'client_name': f"{cliente.nombres} {cliente.apellidos}" if cliente else 'Cliente no disponible',
                    'client_id': cliente.numero_identificacion if cliente else 'N/A',
                    'client_address': cliente.direccion if cliente else 'Dirección no disponible',
                }
                
                # Debug: Imprimir el resultado
                print(f"Resultado procesado: {result_item}")
                
                results.append(result_item)
                
            except AttributeError as e:
                print(f"Error de atributo procesando recibo {receipt.id}: {str(e)}")
                # Intentar acceso directo a los campos
                try:
                    result_item = {
                        'id': receipt.id,
                        'no_recibo': receipt.no_recibo,
                        'monto_pago': float(receipt.monto_pago) if receipt.monto_pago else 0.00,
                        'fecha_pago': receipt.fecha_pago.strftime('%Y-%m-%d'),
                        'client_name': 'Cliente no disponible',
                        'client_id': 'N/A',
                        'client_address': 'Dirección no disponible',
                    }
                    results.append(result_item)
                except Exception as inner_e:
                    print(f"Error interno procesando recibo {receipt.id}: {str(inner_e)}")
                    continue
            except Exception as e:
                print(f"Error general procesando recibo {receipt.id}: {str(e)}")
                continue
        
        print(f"Total de resultados encontrados: {len(results)}")
        
        return JsonResponse({
            'results': results,
            'total': len(results)
        })
    
    except Exception as e:
        print(f"Error crítico en search_receipts: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}'
        }, status=500)


# Vista adicional para depuración - puedes usarla temporalmente
@csrf_exempt 
@require_http_methods(["GET"])
def debug_receipts(request):
    """Vista para depurar los datos de recibos"""
    try:
        # Obtener algunos recibos para verificar la estructura
        receipts = Ingreso.objects.all()[:5]
        
        debug_info = []
        for receipt in receipts:
            info = {
                'id': receipt.id,
                'no_recibo': receipt.no_recibo,
                'monto_pago': str(receipt.monto_pago),
                'monto_pago_type': str(type(receipt.monto_pago)),
                'fecha_pago': str(receipt.fecha_pago),
                'anulado': receipt.anulado,
                'has_prestamo': hasattr(receipt, 'prestamo') and receipt.prestamo is not None,
            }
            
            if hasattr(receipt, 'prestamo') and receipt.prestamo:
                info['has_cliente'] = hasattr(receipt.prestamo, 'cliente') and receipt.prestamo.cliente is not None
                if hasattr(receipt.prestamo, 'cliente') and receipt.prestamo.cliente:
                    cliente = receipt.prestamo.cliente
                    info['cliente_nombres'] = getattr(cliente, 'nombres', 'N/A')
                    info['cliente_apellidos'] = getattr(cliente, 'apellidos', 'N/A')
            
            debug_info.append(info)
        
        return JsonResponse({
            'debug_info': debug_info,
            'total_receipts': Ingreso.objects.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'traceback': str(traceback.format_exc())
        })




#ojo pendiente probar antes de borrar
@csrf_exempt
@require_http_methods(["POST"])
def cancel_receipt(request):
    try:
        data = request.POST
        receipt_id = data.get('receipt_id')
        reason = data.get('reason')
        notes = data.get('notes')
        cancellation_date = data.get('cancellation_date')
        
        if not all([receipt_id, reason, notes, cancellation_date]):
            return JsonResponse({'error': 'Faltan datos requeridos'}, status=400)
        
        receipt = Ingreso.objects.get(no_recibo=receipt_id, anulado=False)
        receipt.anulado = True
        receipt.motivo_anulacion = reason
        receipt.notas_anulacion = notes
        receipt.fecha_anulacion = cancellation_date
        receipt.save()
        
        return JsonResponse({'success': True, 'message': 'Recibo anulado exitosamente'})
            
    except Ingreso.DoesNotExist:
        return JsonResponse({'error': 'Recibo no encontrado o ya anulado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    





@csrf_exempt
@require_http_methods(["POST"])
@login_required
def anular_recibo(request):
    try:
        # Manejar diferentes tipos de contenido (FormData y JSON)
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        # Validar datos requeridos
        required_fields = ['no_recibo', 'motivo', 'notas', 'fecha_anulacion']
        if not all(field in data for field in required_fields):
            return JsonResponse({
                'success': False,
                'error': 'Faltan campos requeridos: no_recibo, motivo, notas, fecha_anulacion'
            }, status=400)

        no_recibo = data['no_recibo']
        motivo = data['motivo']
        notas = data['notas']
        fecha_anulacion = data['fecha_anulacion']

        # Validar formato de fecha
        try:
            fecha_anulacion = datetime.strptime(fecha_anulacion, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }, status=400)

        # Usar transacción atómica para asegurar integridad
        with transaction.atomic():
            # Buscar el recibo (solo no anulados)
            recibo = Ingreso.objects.select_for_update().get(
                no_recibo=no_recibo,
                anulado=False
            )

            # Crear copia en RecibosAnulados
            recibo_anulado = RecibosAnulados(
                no_recibo=recibo.no_recibo,
                prestamo=recibo.prestamo,
                monto_pago=recibo.monto_pago,
                fecha_pago=recibo.fecha_pago,
                metodo_pago=recibo.metodo_pago,
                tipo_pago=recibo.tipo_pago,
                notas=recibo.notas,
                fecha_registro=recibo.fecha_registro,
                motivo_anulacion=motivo,
                notas_anulacion=notas,
                fecha_anulacion=fecha_anulacion,
                anulado_por=request.user
            )
            recibo_anulado.save()

            # Eliminar el recibo original
            recibo.delete()

            # Respuesta exitosa con más detalles
            return JsonResponse({
                'success': True,
                'message': 'Recibo anulado exitosamente',
                'data': {
                    'id_anulado': recibo_anulado.id,
                    'numero_recibo': recibo_anulado.no_recibo,
                    'monto': float(recibo_anulado.monto_pago),
                    'fecha_anulacion': recibo_anulado.fecha_anulacion.strftime('%Y-%m-%d'),
                    'motivo': recibo_anulado.motivo_anulacion,
                    'anulado_por': request.user.username
                }
            })

    except Ingreso.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Recibo no encontrado o ya está anulado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la anulación: {str(e)}'
        }, status=500)