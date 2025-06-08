from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from .models import Cliente,  Prestamo
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from decimal import Decimal,  InvalidOperation
import json
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from num2words import num2words
from datetime import datetime

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


def index(request):
    return render(request, "prestamos/index.html")


def clientes(request):
    return render(request, "prestamos/clientes.html")

def reimprimir(request):
    return render(request, "prestamos/reimprimir.html")

def registrodepago(request):
    return render(request, "prestamos/registrodepago.html")

def prestamospagados(request):
    return render(request, "prestamos/prestamospagados.html")

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


@csrf_exempt
def registrar_despacho(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validar datos
            if not all(key in data for key in ['cliente_id', 'monto', 'fecha_despacho', 'metodo_pago', 'departamento']):
                return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)
            
            # Obtener cliente
            cliente = Cliente.objects.get(numero_identificacion=data['cliente_id'])
            
            # Crear préstamo
            prestamo = Prestamo.objects.create(
                cliente=cliente,
                monto=data['monto'],
                fecha_despacho=datetime.strptime(data['fecha_despacho'], '%Y-%m-%d').date(),
                metodo_pago=data['metodo_pago'],
                departamento=data['departamento'],
                observaciones=data.get('observaciones', ''),
                estado='ACTIVO'
            )
            
            return JsonResponse({
                'success': True,
                'prestamo_id': prestamo.id
            })
            
        except Cliente.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cliente no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


def despacho(request):
    return render(request, "prestamos/despacho.html")

def anulacion(request):
    return render(request, "prestamos/anulacion.html")

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
                'metodo_pago': prestamo.get_metodo_pago_display(),
                'departamento': prestamo.get_departamento_display()
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


def login(request):
    return render(request, "prestamos/login.html")

