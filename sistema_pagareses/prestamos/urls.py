from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from . import views
from django.contrib import admin
from django_prometheus import exports

urlpatterns = [
    path("", views.index, name="index"),
    path("anulacion", views.anulacion, name="anulacion"),
    path("reporte", views.reporte, name="reporte"),
    path("anulacionderesivo", views.anulacionderesivo, name="anulacionderesivo"),
    path("clientes", views.clientes, name="clientes"),
    path("despacho", views.despacho, name="despacho"),
    path("facturas", views.facturas, name="facturas"),
    path("formulario", views.formulario, name="formulario"),
    # path("login", views.login, name="login"),
    path("prestamospagados", views.prestamospagados, name="prestamospagados"),
    path("registrodepago", views.registrodepago, name="registrodepago"),
    path("reimprimir", views.reimprimir, name="reimprimir"),
    path('buscar-clientes/', views.buscar_clientes, name='buscar_clientes'),
    path('registrar-despacho/', views.registrar_despacho, name='registrar_despacho'),
    path('factura/<int:prestamo_id>/', views.factura_prestamo, name='factura_prestamo'),

    path('clientes/', views.clientes, name='clientes'),
    path('clientes/<int:cliente_id>/', views.cliente_detalle, name='cliente_detalle'),
    path('clientes/registrar_pago/', views.registrar_pago, name='registrar_pago'),
    path('clientes/<int:cliente_id>/prestamos/', views.obtener_prestamos_cliente, name='obtener_prestamos_cliente'),
    path('buscar-facturas/', views.buscar_facturas, name='buscar_facturas'),
    path('imprimir-pagare/<str:numero_factura>/', views.imprimir_pagare, name='imprimir_pagare'),
    path('prestamos/toggle-status/<int:loan_id>/', views.toggle_loan_status, name='toggle_loan_status'),
    path('prestamos/delete/<int:loan_id>/', views.delete_loan, name='delete_loan'),

    path('search_receipts/', views.search_receipts, name='search_receipts'),
    # path('cancel_receipt/', views.cancel_receipt, name='cancel_receipt'),
    path('debug_receipts/', views.debug_receipts, name='debug_receipts'),
    path('anular_recibo/', views.anular_recibo, name='anular_recibo'),
    path('vistadecliente', views.vistadecliente, name='vistadecliente'),
    path('clientes/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),
    path('clientes/total-prestamos/', views.obtener_total_prestamos, name='total_prestamos'),

    path("estadosdecuentas", views.estadosdecuentas, name="estadosdecuentas"),
    
]


# urlpatterns += [
#     path('metrics/', exports.ExportToDjangoView, name="metrics")
# ]