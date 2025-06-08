from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("anulacion", views.anulacion, name="anulacion"),
    path("anulacionderesivo", views.anulacionderesivo, name="anulacionderesivo"),
    path("clientes", views.clientes, name="clientes"),
    path("despacho", views.despacho, name="despacho"),
    path("facturas", views.facturas, name="facturas"),
    path("formulario", views.formulario, name="formulario"),
    path("login", views.login, name="login"),
    path("prestamospagados", views.prestamospagados, name="prestamospagados"),
    path("registrodepago", views.registrodepago, name="registrodepago"),
    path("reimprimir", views.reimprimir, name="reimprimir"),
    path('buscar-clientes/', views.buscar_clientes, name='buscar_clientes'),
    path('registrar-despacho/', views.registrar_despacho, name='registrar_despacho'),
    path('factura/<int:prestamo_id>/', views.factura_prestamo, name='factura_prestamo'),
   
    
]


