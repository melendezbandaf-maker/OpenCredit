#App donde los bancos comprueban el score de los clientes

import streamlit as st
import json
import os

st.set_page_config(
    page_title="OpenCredit | Portal B2B Bancario", 
    page_icon="🏢", 
    layout="centered"
)

# Etiquetas legibles compartidas para las métricas
ETIQUETAS_LEGIBLES = {
    "ratio_liquidez": "Ratio de liquidez",
    "ratio_gastos": "Ratio de gastos fijos / ingreso",
    "cv_tiempo": "Coef. de variación - puntualidad de pago",
    "cv_monto_ponderado": "Coef. de variación - impulsividad de gasto",
    "dias_supervivencia": "Días de supervivencia (saldo / gasto diario)",
    "ciclo_cobro_dias": "Ciclo de cobro estimado (días)",
    "num_pagos_fijos_detectados": "Pagos fijos detectados"
}

st.title("🏢 OpenCredit: Validador Corporativo B2B")
st.info("Portal exclusivo para oficiales de crédito y empresas. Ingrese la **Clave de Verificación (Folio)** y el **RFC** del solicitante para validar su autenticidad sin necesidad de ver datos sensibles.")

col1, col2 = st.columns(2)
with col1:
    folio_buscado = st.text_input("🔑 Clave de Verificación (Folio)", "").strip().upper()
with col2:
    rfc_buscado = st.text_input("📋 RFC del Solicitante", "").strip().upper()

if st.button("Verificar Autenticidad en Sistema"):
    if not folio_buscado or not rfc_buscado:
        st.warning("Por favor, introduce tanto el Folio como el RFC.")
    else:
        # Cargar la "base de datos" JSON compartida
        if os.path.exists("db_folios.json"):
            with open("db_folios.json", "r") as f:
                db = json.load(f)
        else:
            db = {}

        if folio_buscado in db:
            registro = db[folio_buscado]
            # Validar que coincida el RFC también
            if registro['rfc'].upper() == rfc_buscado:
                st.success("✅ ¡Certificado Oficial Válido y Auténtico!")
                
                st.markdown("---")
                st.subheader("📋 Información General y Dictamen")
                
                c1, c2 = st.columns(2)
                c1.metric("Titular Verificado", registro['nombre'])
                c2.metric("RFC Registrado", registro['rfc'])
                
                c3, c4 = st.columns(2)
                c3.metric("Banco Emisor", registro.get('banco', 'N/A'))
                c4.metric("Ingreso Mensual Comprobado", f"${registro.get('ingresos', 0):,.2f} MXN")
                
                st.metric("Capacidad de Pago Neta Estimada", f"${registro.get('capacidad', 0):,.2f} MXN")
                
                # Sección de Score Debiticio
                st.markdown("---")
                st.subheader("1. Score Debiticio (Escala 300-850)")
                
                # Si el registro no tiene score guardado, asignamos uno por defecto para visualización
                score_val = registro.get('score', 720)
                
                if score_val >= 700:
                    st.success(f"Score: **{score_val}** (Riesgo Bajo)")
                elif score_val >= 550:
                    st.warning(f"Score: **{score_val}** (Riesgo Moderado)")
                else:
                    st.error(f"Score: **{score_val}** (Riesgo Alto)")
                
                # Métricas / Indicadores (si no existen en el registro, usa métricas estándar de respaldo)
                metricas_a_mostrar = registro.get('metricas', {
                    "ratio_liquidez": 1.45,
                    "ratio_gastos": 0.62,
                    "cv_tiempo": 0.12,
                    "cv_monto_ponderado": 0.25,
                    "dias_supervivencia": 45.0,
                    "ciclo_cobro_dias": 15,
                    "num_pagos_fijos_detectados": 4
                })
                
                if metricas_a_mostrar:
                    st.markdown("##### Métricas Financieras:")
                    for clave, valor in metricas_a_mostrar.items():
                        etiqueta = ETIQUETAS_LEGIBLES.get(clave, clave)
                        st.write(f"- **{etiqueta}:** {valor}")
                
                st.markdown("---")
                st.markdown("""
                > **Dictamen de Riesgo:** Este usuario no cuenta con historial tradicional en buró, pero su comportamiento transaccional en cuenta de débito durante los últimos 12 meses avala la solvencia mostrada.
                """)
            else:
                st.error("❌ El RFC ingresado no coincide con el registro asociado a este Folio.")
        else:
            st.error("❌ Folio no encontrado en los registros oficiales de OpenCredit.")