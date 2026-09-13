# generador de reporte pdf de score debiticio

from fpdf import FPDF
import time
import uuid

from score_calculator import DESCRIPCION_PARAMETROS

class PDFReporte(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(0, 68, 129)
        self.cell(0, 10, 'OPENCREDIT - CERTIFICADO DE SCORE FINANCIERO', 0, 1, 'C')
        self.set_font('helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, 'Reporte Oficial de Open Banking para No-Bursatizados', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Página {self.page_no()} | Segmento: Sin Historial Crediticio Tradicional', 0, 0, 'C')


def _clasificacion_riesgo(score):
    """Devuelve (etiqueta, color RGB) según el rango del score."""
    if score >= 700:
        return "Riesgo Bajo", (0, 128, 0)
    elif score >= 550:
        return "Riesgo Moderado", (204, 140, 0)
    else:
        return "Riesgo Alto", (180, 0, 0)


# Etiquetas legibles compartidas entre la tabla de métricas y el glosario,
# para que ambos usen el mismo nombre por parámetro.
ETIQUETAS_LEGIBLES = {
    "ratio_liquidez": "Ratio de liquidez",
    "ratio_gastos": "Ratio de gastos fijos / ingreso",
    "cv_tiempo": "Coef. de variación - puntualidad de pago",
    "cv_monto_ponderado": "Coef. de variación - impulsividad de gasto",
    "dias_supervivencia": "Días de supervivencia (saldo / gasto diario)",
    "ciclo_cobro_dias": "Ciclo de cobro estimado (días)",
    "num_pagos_fijos_detectados": "Pagos fijos detectados"
}


def generar_pdf_score(banco, nombre_usuario, rfc, ingresos, gastos, capacidad, score=None, metricas=None):
    """
    Genera el certificado PDF de score financiero.

    Parámetros nuevos
    ------------------
    score : int, opcional
        Score final (300-850) calculado por scoremath.generar_score_debiticio.
        Si no se proporciona, la sección de score se omite (compatibilidad
        con llamadas antiguas que no lo mandaban).
    metricas : dict, opcional
        Diccionario de métricas devuelto junto al score (ratio_liquidez,
        ratio_gastos, cv_tiempo, cv_monto_ponderado, etc.). Si se proporciona,
        se agrega una tabla de detalle y, al final del documento, un anexo
        con la descripción de cada parámetro (glosario).
    """
    folio_unico = "OC-" + str(uuid.uuid4()).upper()[:8]

    pdf = PDFReporte()
    pdf.add_page()

    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f'Titular de la Cuenta: {nombre_usuario}', 0, 1)
    pdf.set_font('helvetica', '', 10)
    pdf.cell(0, 6, f'RFC: {rfc}', 0, 1)
    pdf.cell(0, 6, f'Institución Financiera Emisora: {banco}', 0, 1)
    pdf.cell(0, 6, f'Fecha de Emisión: {time.strftime("%d/%m/%Y")}', 0, 1)

    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 6, f'Clave de Verificación B2B (Folio): {folio_unico}', 0, 1)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    # =========================================================
    # SECCIÓN NUEVA: SCORE DEBITICIO
    # =========================================================
    if score is not None:
        pdf.set_font('helvetica', 'B', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, '1. Score Debiticio (Escala 300-850)', 0, 1)

        etiqueta, color_rgb = _clasificacion_riesgo(score)

        pdf.set_font('helvetica', 'B', 22)
        pdf.set_text_color(*color_rgb)
        pdf.cell(80, 14, f'{score}', 0, 0)

        pdf.set_font('helvetica', 'B', 11)
        pdf.cell(0, 14, etiqueta, 0, 1)

        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        if metricas:
            pdf.set_font('helvetica', '', 9)
            for clave, valor in metricas.items():
                etiqueta_legible = ETIQUETAS_LEGIBLES.get(clave, clave)
                pdf.cell(120, 6, f'  {etiqueta_legible}:', 0, 0)
                pdf.cell(0, 6, f'{valor}', 0, 1)

        pdf.ln(6)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(8)

        num_seccion_capacidad = "2"
        num_seccion_declaracion = "3"
    else:
        num_seccion_capacidad = "1"
        num_seccion_declaracion = "2"

    # =========================================================
    # SECCIÓN: RESUMEN DE CAPACIDAD DE PAGO (como ya existía)
    # =========================================================
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 8, f'{num_seccion_capacidad}. Resumen de Capacidad de Pago (Basado en Débito - 12 Meses)', 0, 1)

    pdf.set_font('helvetica', '', 10)
    pdf.cell(100, 8, 'Ingreso Promedio Mensual:', 0, 0)
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 8, f'${ingresos:,.2f} MXN', 0, 1)

    pdf.set_font('helvetica', '', 10)
    pdf.cell(100, 8, 'Gasto Promedio Mensual:', 0, 0)
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 8, f'${gastos:,.2f} MXN', 0, 1)

    pdf.set_font('helvetica', '', 10)
    pdf.cell(100, 8, 'Capacidad de Pago Neta Estimada:', 0, 0)
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(0, 128, 0)
    pdf.cell(0, 8, f'${capacidad:,.2f} MXN', 0, 1)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 8, f'{num_seccion_declaracion}. Declaración de Propósito y Validación', 0, 1)
    pdf.set_font('helvetica', '', 10)
    pdf.multi_cell(0, 6, f'Este certificado (Folio: {folio_unico}) emitido para {nombre_usuario} (RFC: {rfc}) está destinado exclusivamente para personas sin historial en buró tradicional.')

    # =========================================================
    # ANEXO: GLOSARIO DE PARÁMETROS DEL SCORE
    # =========================================================
    if metricas:
        pdf.add_page()

        pdf.set_font('helvetica', 'B', 14)
        pdf.set_text_color(0, 68, 129)
        pdf.cell(0, 10, 'Anexo: Glosario de Parámetros del Score Debiticio', 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        pdf.set_font('helvetica', '', 9)
        pdf.multi_cell(0, 5, 'A continuación se describe cada uno de los parámetros considerados en el cálculo del Score Debiticio, con el fin de dar transparencia a la metodología utilizada.')
        pdf.ln(4)

        # Solo describimos los parámetros que sí tienen una definición
        # conceptual en scoremath.DESCRIPCION_PARAMETROS (ratio_liquidez,
        # ratio_gastos, cv_tiempo, cv_monto_ponderado). Las demás llaves de
        # 'metricas' (dias_supervivencia, ciclo_cobro_dias,
        # num_pagos_fijos_detectados) son datos de apoyo, no parámetros con
        # peso propio en la fórmula, así que se omiten del glosario.
        for clave, descripcion in DESCRIPCION_PARAMETROS.items():
            if clave not in metricas:
                continue

            etiqueta_legible = ETIQUETAS_LEGIBLES.get(clave, clave)

            pdf.set_font('helvetica', 'B', 10)
            pdf.cell(0, 6, etiqueta_legible, 0, 1)

            pdf.set_font('helvetica', '', 9)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 5, descripcion)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)

    return bytes(pdf.output()), folio_unico