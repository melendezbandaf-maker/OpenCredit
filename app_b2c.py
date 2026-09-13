# App donde los clientes checan su score

import streamlit as st
import pandas as pd
import requests
import time
from pdf_generator import generar_pdf_score
from score_calculator import generar_score_debiticio

st.set_page_config(
    page_title="OpenCredit | Portal de Usuario", 
    page_icon="💳", 
    layout="centered"
)

import json
import os

BASE_URL = "https://api.nessieisreal.com"

# --- CARGAR CONFIGURACIÓN AUTOMÁTICA DESDE EL ARCHIVO DE LA CONSOLA ---
if os.path.exists("bancos_config.json"):
    with open("bancos_config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)
        API_KEY = config_data.get("api_key")
        BANCOS_ACCOUNTS = config_data.get("cuentas")
else:
    st.error("⚠️ No se encontró el archivo `bancos_config.json`. Ejecuta primero el script de consola para generar las cuentas y la API Key.")
    st.stop()
    
# Inicializar estados de sesión
if 'step' not in st.session_state:
    st.session_state.step = 1

if 'banco_fijo' not in st.session_state:
    st.session_state.banco_fijo = "BBVA"

if 'solicitud_credito_enviada' not in st.session_state:
    st.session_state.solicitud_credito_enviada = False

# --- LÓGICA PARA CONgelar EL BANCO SI YA INICIÓ EL PROCESO ---
st.sidebar.header("⚙️ Configuración del Banco")
if st.session_state.step == 1:
    banco_seleccionado = st.sidebar.selectbox(
        "Simular vista dentro de la app de:",
        list(BANCOS_ACCOUNTS.keys())
    )
    st.session_state.banco_fijo = banco_seleccionado
else:
    banco_seleccionado = st.session_state.banco_fijo
    st.sidebar.info(f"🏦 Banco activo: **{banco_seleccionado}**\n\n*(El banco se fija durante el proceso. Reinicia para cambiar)*")

estilos_banco = {
    "BBVA": {"color": "#004481", "badge": "🔵 BBVA México - Banca en Línea"},
    "Santander": {"color": "#EC0000", "badge": "🔴 Santander - SuperNet"},
    "Nu México": {"color": "#820AD1", "badge": "🟣 Nu - Cuenta Nu"},
    "Mercado Pago": {"color": "#009EE3", "badge": "🟡 Mercado Pago - Wallet"}
}
info_banco = estilos_banco[banco_seleccionado]

st.markdown(f"""
<div style="background-color: {info_banco['color']}; padding: 10px 15px; border-radius: 8px; color: white; margin-bottom: 20px;">
    <strong>{info_banco['badge']}</strong> | Módulo de Portabilidad Financiera Alternativa
</div>
""", unsafe_allow_html=True)

st.title("💳 OpenCredit: Solicitud de Score sin Historial")

# PASO 1: Captura y Validación de Público
if st.session_state.step == 1:
    st.info("""
    🎯 **¿A quién va dirigido OpenCredit?**  
    Diseñado para personas sin historial crediticio tradicional que necesitan comprobar sus ingresos mediante su cuenta de débito.
    """)
    
    nombre_input = st.text_input("Nombre completo del Titular", "Alex Rivera")
    rfc_input = st.text_input("RFC con Homoclave (Inventado)", "RIRA010101XYZ")
    usuario_email = st.text_input("Correo electrónico", "usuario@ejemplo.com")
    
    tiene_historial = st.radio(
        "¿Actualmente cuentas con tarjetas de crédito o historial activo en Buró de Crédito?",
        ("Sí, tengo historial activo", "No tengo historial / Nunca he tenido tarjeta de crédito / Mi historial está en blanco")
    )

    if st.button("Continuar ➡️"):
        st.session_state.nombre_usuario = nombre_input
        st.session_state.rfc_usuario = rfc_input
        if "Sí" in tiene_historial:
            st.session_state.step = "rechazado_publico"
            st.rerun()
        else:
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == "rechazado_publico":
    st.warning("⚠️ **Perfil no compatible con OpenCredit**")
    st.write("Tu perfil ya cuenta con historial en el buró tradicional. OpenCredit es exclusivo para segmentos no bursatizados.")
    if st.button("🔄 Volver al inicio"):
        st.session_state.step = 1
        st.rerun()

elif st.session_state.step == 2:
    st.subheader("🔒 Autorización de Datos (Open Banking)")
    st.warning(f"**{banco_seleccionado}** requiere tu consentimiento para compartir el historial financiero de **{st.session_state.nombre_usuario}** (RFC: `{st.session_state.rfc_usuario}`).")

    if 'rechazado' not in st.session_state:
        st.session_state.rechazado = False

    if not st.session_state.rechazado:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ Rechazar"):
                st.session_state.rechazado = True
                st.rerun()
        with col2:
            if st.button("✅ Autorizar y Enviar al Banco"):
                st.session_state.step = 3
                st.rerun()
    else:
        st.error("Has cancelado la autorización.")
        if st.button("🔄 Reiniciar"):
            st.session_state.rechazado = False
            st.session_state.step = 1
            st.rerun()

elif st.session_state.step == 3:
    acc_id = BANCOS_ACCOUNTS[banco_seleccionado]
    
    with st.spinner(f"El banco ({banco_seleccionado}) está procesando los flujos de {st.session_state.nombre_usuario}..."):
        try:
            res_dep = requests.get(f"{BASE_URL}/accounts/{acc_id}/deposits?key={API_KEY}").json()
            res_pur = requests.get(f"{BASE_URL}/accounts/{acc_id}/purchases?key={API_KEY}").json()
            res_wit = requests.get(f"{BASE_URL}/accounts/{acc_id}/withdrawals?key={API_KEY}").json()
            res_bil = requests.get(f"{BASE_URL}/accounts/{acc_id}/bills?key={API_KEY}").json()
            res_acc = requests.get(f"{BASE_URL}/accounts/{acc_id}?key={API_KEY}").json()

            df_depositos = pd.DataFrame(res_dep) if isinstance(res_dep, list) else pd.DataFrame()
            df_compras = pd.DataFrame(res_pur) if isinstance(res_pur, list) else pd.DataFrame()
            df_retiros = pd.DataFrame(res_wit) if isinstance(res_wit, list) else pd.DataFrame()
            df_bills = pd.DataFrame(res_bil) if isinstance(res_bil, list) else pd.DataFrame()

            total_ingresos = df_depositos['amount'].sum() if not df_depositos.empty and 'amount' in df_depositos else 0
            total_compras = df_compras['amount'].sum() if not df_compras.empty and 'amount' in df_compras else 0
            total_retiros = df_retiros['amount'].sum() if not df_retiros.empty and 'amount' in df_retiros else 0
            total_bills = df_bills['payment_amount'].sum() if not df_bills.empty and 'payment_amount' in df_bills else 0

            gasto_total = total_compras + total_retiros + total_bills
            ingresos_mensuales = total_ingresos / 12 if total_ingresos > 0 else 15000
            gastos_mensuales = gasto_total / 12 if gasto_total > 0 else 10000

            # --- Saldo actual y saldo promedio para el score ---
            saldo_actual = res_acc.get("balance", 10000) if isinstance(res_acc, dict) else 10000
            # Nessie no expone historial de saldo diario; se aproxima el saldo
            # promedio como el saldo actual. Si más adelante se tiene un
            # histórico real de saldo, sustituir aquí.
            saldo_promedio = saldo_actual

            # --- CÁLCULO DEL SCORE REAL (scoremath.py) ---
            resultado_score = generar_score_debiticio(
                compras_json=res_pur if isinstance(res_pur, list) else [],
                depositos_json=res_dep if isinstance(res_dep, list) else [],
                bills_json=res_bil if isinstance(res_bil, list) else [],
                saldo_actual=saldo_actual,
                saldo_promedio=saldo_promedio
                )
            score_final = resultado_score["score"]
            metricas_score = resultado_score["metricas"]
            error_score = None

        except Exception as e:
            st.error(f"Error al conectar con la API: {e}")
            ingresos_mensuales, gastos_mensuales = 18500, 12000
            total_ingresos, total_compras, total_retiros, total_bills = 0, 0, 0, 0
            saldo_actual, saldo_promedio = 10000, 10000
            score_final = 300
            metricas_score = {}
            error_score = str(e)

        time.sleep(1)
        capacidad_pago = ingresos_mensuales - gastos_mensuales

        st.success(f"¡Análisis completado para **{st.session_state.nombre_usuario}**!")

        # Score destacado arriba de todo
        st.markdown("---")
        st.subheader("🏆 Score Debiticio")
        col_score1, col_score2 = st.columns([1, 2])
        with col_score1:
            st.metric("Score (300-850)", score_final)
        with col_score2:
            if score_final >= 700:
                st.success("Perfil de bajo riesgo")
            elif score_final >= 550:
                st.warning("Perfil de riesgo moderado")
            else:
                st.error("Perfil de riesgo alto")

        if metricas_score:
            with st.expander("📐 Detalle de las métricas del score"):
                m1, m2, m3 = st.columns(3)
                m1.metric("Ratio de liquidez", metricas_score.get("ratio_liquidez", "N/A"))
                m2.metric("Ratio de gastos fijos", metricas_score.get("ratio_gastos", "N/A"))
                m3.metric("CV de tiempo (puntualidad)", metricas_score.get("cv_tiempo", "N/A"))
                m4, m5, m6 = st.columns(3)
                m4.metric("CV de monto (impulsividad)", metricas_score.get("cv_monto_ponderado", "N/A"))
                m5.metric("Días de supervivencia", metricas_score.get("dias_supervivencia", "N/A"))
                m6.metric("Pagos fijos detectados", metricas_score.get("num_pagos_fijos_detectados", "N/A"))

        # Resumen visual de métricas de movimientos
        st.markdown("---")
        st.subheader(f"📊 Resumen de Movimientos: {st.session_state.nombre_usuario}")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Depósitos Totales", f"${total_ingresos:,.2f}")
        col_m2.metric("Compras Totales", f"${total_compras:,.2f}")
        col_m3.metric("Retiros ATM", f"${total_retiros:,.2f}")
        col_m4.metric("Servicios / Bills", f"${total_bills:,.2f}")

        # Pestañas detalladas de transacciones
        with st.expander("🔍 Inspeccionar transacciones detalladas (Entrada de datos)"):
            tab1, tab2, tab3, tab4 = st.tabs(["Depósitos", "Compras", "Retiros", "Servicios"])
            with tab1:
                if not df_depositos.empty: st.dataframe(df_depositos[['transaction_date', 'amount', 'description', 'status']])
            with tab2:
                if not df_compras.empty: st.dataframe(df_compras[['purchase_date', 'amount', 'description', 'status']])
            with tab3:
                if not df_retiros.empty: st.dataframe(df_retiros[['transaction_date', 'amount', 'description', 'status']])
            with tab4:
                if not df_bills.empty: st.dataframe(df_bills[['payment_date', 'payment_amount', 'payee', 'status']])

        st.markdown("---")
        st.subheader("📑 Métricas de Capacidad Financiera")

        c1, c2, c3 = st.columns(3)
        c1.metric("Ingreso Promedio Mensual", f"${ingresos_mensuales:,.2f}")
        c2.metric("Capacidad de Pago Neta", f"${capacidad_pago:,.2f}")
        c3.metric("RFC Validado", st.session_state.rfc_usuario)

        # Generar PDF con RFC, Folio y Score
        pdf_bytes, folio_generado = generar_pdf_score(
            banco_seleccionado, 
            st.session_state.nombre_usuario, 
            st.session_state.rfc_usuario,
            ingresos_mensuales, 
            gastos_mensuales, 
            capacidad_pago,
            score_final,
            metricas_score
        )

        # Guardar en archivo local JSON para el portal B2B
        import json
        try:
            with open("db_folios.json", "r") as f:
                db = json.load(f)
        except:
            db = {}
        
        db[folio_generado] = {
            "nombre": st.session_state.nombre_usuario,
            "rfc": st.session_state.rfc_usuario,
            "banco": banco_seleccionado,
            "ingresos": ingresos_mensuales,
            "capacidad": capacidad_pago,
            "score": score_final,
            "metricas_score": metricas_score
        }
        with open("db_folios.json", "w") as f:
            json.dump(db, f)

        st.info(f"🔑 **Guarda tu Clave de Verificación B2B:** `{folio_generado}` (Proporciónala al banco o empresa para validar tu certificado).")

        st.markdown("---")
        st.download_button(
            label="📄 Descargar Certificado de Score Financiero (PDF)",
            data=pdf_bytes,
            file_name=f"Certificado_{st.session_state.rfc_usuario}.pdf",
            mime="application/pdf"
        )

        # --- SOLICITAR CRÉDITO AL BANCO ---
        st.markdown("---")
        st.subheader("🏦 Solicitud de Crédito")

        if not st.session_state.solicitud_credito_enviada:
            if st.button("📨 Solicitar al banco crédito"):
                st.session_state.solicitud_credito_enviada = True
                st.rerun()
        else:
            with st.spinner("Enviando tu solicitud al banco..."):
                time.sleep(1.2)
            st.info(f"🕓 **El banco está revisando tu solicitud.** {banco_seleccionado} recibió tu Score Debiticio (`{score_final}`) y tu Clave de Verificación B2B (`{folio_generado}`). Te notificaremos por correo cuando haya una respuesta.")

        if st.button("🔄 Volver a iniciar"):
            st.session_state.step = 1
            st.session_state.rechazado = False
            st.session_state.solicitud_credito_enviada = False
            st.rerun()