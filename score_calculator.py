# calculador de score debiticio

import pandas as pd
import numpy as np

# Categorías que la app considerará para el Ratio de Gastos Obligatorios y CV de Tiempo
CATEGORIAS_FIJAS = ['renta', 'servicios', 'educacion', 'colegiatura', 'transporte_basico', 'salud']

DESCRIPCION_PARAMETROS = {
    "ratio_liquidez": (
        "Mide cuántos ciclos de cobro puede cubrir la persona con su saldo "
        "actual, comparando sus días de colchón contra la frecuencia con la "
        "que recibe ingresos. Entre más alto, mayor margen antes de quedarse "
        "sin dinero."
    ),
    "ratio_gastos": (
        "Proporción del ingreso total que se destina a gastos fijos como "
        "renta, servicios, educación o salud. Un ratio bajo indica que la "
        "persona tiene más ingreso libre disponible para absorber un nuevo "
        "compromiso de pago."
    ),
    "cv_tiempo": (
        "Coeficiente de variación de los intervalos entre pagos fijos. "
        "Refleja qué tan puntual y constante es la persona pagando renta o "
        "servicios. Valores bajos indican pagos regulares; valores altos, "
        "comportamiento errático."
    ),
    "cv_monto_ponderado": (
        "Coeficiente de variación de los montos gastados en compras "
        "variables, ponderado por su peso relativo al saldo. Valores altos "
        "sugieren gasto impulsivo; valores bajos indican un patrón de "
        "consumo más controlado y predecible."
    ),
}


def _normalizar_compras(compras_json):
    """
    Convierte las compras que devuelve la API (purchase_date/amount/description)
    al formato interno que usa el resto del pipeline (transaction_date/amount/
    description/categoria), para que todo lo que sigue (df_fijos, cv_tiempo,
    df_todo_gasto, etc.) pueda seguir trabajando con 'transaction_date' sin
    importar cómo se llame la fecha en la respuesta cruda de la API.
    """
    if not compras_json:
        return pd.DataFrame(columns=['transaction_date', 'amount', 'description', 'categoria'])

    df = pd.DataFrame(compras_json)

    # La API puede devolver la fecha como 'purchase_date' (formato actual) o
    # como 'transaction_date' (formato legado/otros endpoints). Normalizamos
    # a 'transaction_date' sin importar cuál venga.
    if 'purchase_date' in df.columns and 'transaction_date' not in df.columns:
        df = df.rename(columns={'purchase_date': 'transaction_date'})

    if 'transaction_date' not in df.columns:
        raise KeyError(
            "Las compras no traen ni 'purchase_date' ni 'transaction_date'; "
            "revisa el formato que está devolviendo la API."
        )

    df['transaction_date'] = pd.to_datetime(df['transaction_date'])

    if 'description' not in df.columns:
        df['description'] = ''

    df['categoria'] = df['description'].apply(
        lambda x: x.split(']')[0].replace('[', '').strip().lower() if ']' in str(x) else 'otros'
    )

    return df[['transaction_date', 'amount', 'description', 'categoria']]


def _normalizar_bills(bills_json):
    """
    Convierte los bills de Nessie (payment_date/payment_amount/payee) al mismo
    formato que usan las compras (transaction_date/amount/description/categoria),
    para poder concatenarlos sin problema al resto del pipeline.
    """
    if not bills_json:
        return pd.DataFrame(columns=['transaction_date', 'amount', 'description', 'categoria'])

    df_bills = pd.DataFrame(bills_json)

    df_bills = df_bills.rename(columns={
        'payment_date': 'transaction_date',
        'payment_amount': 'amount'
    })

    # Si el bill ya trae una categoría explícita (ej. tú se la agregas al jalar de Nessie),
    # se respeta; si no, se cae a 'servicios' por default ya que la mayoría de bills
    # en Nessie representan pagos de suministros.
    if 'categoria' not in df_bills.columns:
        df_bills['categoria'] = 'servicios'

    if 'description' not in df_bills.columns:
        df_bills['description'] = df_bills.get('payee', 'Pago fijo').apply(
            lambda p: f"[servicios] {p}"
        )

    df_bills['transaction_date'] = pd.to_datetime(df_bills['transaction_date'])
    return df_bills[['transaction_date', 'amount', 'description', 'categoria']]


def generar_score_debiticio(compras_json, depositos_json, bills_json, saldo_actual, saldo_promedio):
    """
    Calcula los 4 parámetros del Score Debiticio a partir de los datos de la API.
    Devuelve un diccionario con las métricas y el puntaje final (300-850).

    Parámetros
    ----------
    compras_json : list[dict]
        Lista de compras/transacciones. Cada dict debe incluir al menos:
        'purchase_date' (o 'transaction_date'), 'amount', 'description'.
        Las compras de gasto fijo pueden venir con la categoría entre corchetes
        al inicio de la descripción, ej: "[renta] Pago mensual departamento".
    depositos_json : list[dict]
        Lista de depósitos/ingresos. Cada dict debe incluir 'transaction_date' y 'amount'.
    bills_json : list[dict]
        Lista de bills (pagos de servicios) obtenidos del endpoint /accounts/{id}/bills
        de Nessie. Cada dict trae 'payment_date', 'payment_amount', 'payee'.
        Se tratan como gastos fijos (categoría 'servicios' por default) y se combinan
        con las compras fijas para calcular ratio_gastos y cv_tiempo.
    saldo_actual : float
        Saldo actual de la cuenta.
    saldo_promedio : float
        Saldo promedio histórico de la cuenta (usado para ponderar impulsividad).

    Retorna
    -------
    dict con 'score' (int, 300-850) y 'metricas' (dict con detalle de cada parámetro).
    """
    df_purchases = _normalizar_compras(compras_json)
    df_deposits = pd.DataFrame(depositos_json)
    df_bills = _normalizar_bills(bills_json)

    # --- PREPARACIÓN DE DATOS ---
    if not df_purchases.empty:
        df_fijos_compras = df_purchases[df_purchases['categoria'].isin(CATEGORIAS_FIJAS)]
        df_variables = df_purchases[~df_purchases['categoria'].isin(CATEGORIAS_FIJAS)]
    else:
        df_fijos_compras = pd.DataFrame(columns=['transaction_date', 'amount', 'description', 'categoria'])
        df_variables = pd.DataFrame()

    # NUEVO: gastos fijos = compras marcadas como fijas + bills, todo junto y ordenado
    df_fijos = pd.concat([df_fijos_compras, df_bills], ignore_index=True)
    if not df_fijos.empty:
        df_fijos = df_fijos.sort_values('transaction_date')

    if not df_deposits.empty:
        df_deposits['transaction_date'] = pd.to_datetime(df_deposits['transaction_date'])
        ingreso_total = df_deposits['amount'].sum()
    else:
        ingreso_total = 1.0  # Evita división entre cero


    # =========================================================
    # PARÁMETRO 1: RATIO DE COBERTURA DE LIQUIDEZ (Peso: 35%)
    # Evolución del Ratio Inmediato para usuarios con cobro diario vs quincenal
    # =========================================================
    # NOTA: el gasto diario ahora considera compras + bills, ya que ambos
    # representan salida real de dinero de la cuenta.
    df_todo_gasto = pd.concat(
        [df_purchases[['transaction_date', 'amount']] if not df_purchases.empty else pd.DataFrame(columns=['transaction_date', 'amount']),
         df_bills[['transaction_date', 'amount']]],
        ignore_index=True
    )

    if not df_todo_gasto.empty:
        rango_dias_gasto = max((df_todo_gasto['transaction_date'].max() - df_todo_gasto['transaction_date'].min()).days, 1)
        gasto_diario = df_todo_gasto['amount'].sum() / rango_dias_gasto
    else:
        gasto_diario = 1.0

    dias_supervivencia = saldo_actual / gasto_diario if gasto_diario > 0 else 0

    if len(df_deposits) > 1:
        df_deposits = df_deposits.sort_values('transaction_date')
        ciclo_ingreso = max(df_deposits['transaction_date'].diff().dt.days.mean(), 1.0)
    else:
        ciclo_ingreso = 15.0  # Asume quincena por defecto si no hay historial suficiente

    cobertura_liquidez = dias_supervivencia / ciclo_ingreso


    # =========================================================
    # PARÁMETRO 2: RATIO DE GASTOS OBLIGATORIOS (Peso: 25%)
    # (Gastos Obligatorios / Ingreso Total)
    # =========================================================
    if not df_fijos.empty:
        gastos_fijos_total = df_fijos['amount'].sum()
    else:
        gastos_fijos_total = 0.0

    ratio_gastos = gastos_fijos_total / ingreso_total


    # =========================================================
    # PARÁMETRO 3: CV DE TIEMPO SIMPLE / NORMAL (Peso: 20%)
    # Variación de pagos fijos individuales (Puntualidad)
    # =========================================================
    # 1. Asegurar que las fechas estén ordenadas de más antigua a más reciente
    df_fijos = df_fijos.sort_values('transaction_date')

# 2. Necesitamos más de 2 transacciones para tener al menos 2 intervalos y calcular std()
    if len(df_fijos) > 2:
    # dt.days convierte el formato timedelta a un número entero
        intervalos = df_fijos['transaction_date'].diff().dt.days.dropna()
    
        media_t = intervalos.mean()
        std_t = intervalos.std()

    # Si por alguna razón la media es 0 (ej. pagos el mismo día), evitamos división entre cero
        cv_tiempo = (std_t / media_t) if media_t > 0 else 0.0
    
# Si tiene 1 o 2 pagos, no hay historial suficiente para evaluar regularidad
    else:
    # 0.5 es un buen valor de penalización por falta de datos
        cv_tiempo = 0.5


    # =========================================================
    # PARÁMETRO 4: CV DE MONTO PONDERADO (Peso: 20%)
    # Volatilidad ponderada por el saldo (Impulsividad)
    # =========================================================
    if len(df_variables) > 1 and saldo_promedio > 0:
        montos = df_variables['amount']
        pesos = montos / saldo_promedio

        media_ponderada = np.average(montos, weights=pesos)
        varianza_ponderada = np.average((montos - media_ponderada) ** 2, weights=pesos)
        std_ponderada = np.sqrt(varianza_ponderada)

        cv_monto = (std_ponderada / media_ponderada) if media_ponderada > 0 else 0.0
    else:
        cv_monto = 0.0


    # =========================================================
    # CÁLCULO FINAL: SCORING (300 a 850 pts)
    # =========================================================
    L = min(max(cobertura_liquidez, 0.0), 1.0)
    Go = min(max(ratio_gastos, 0.0), 1.0)
    CVt = min(max(cv_tiempo, 0.0), 1.0)
    CVm = min(max(cv_monto, 0.0), 1.0)

    puntos_L = 193 * L
    puntos_Go = 137 * (1.0 - Go)
    puntos_CVt = 110 * (1.0 - CVt)
    puntos_CVm = 110 * (1.0 - CVm)

    score_final = 300 + puntos_L + puntos_Go + puntos_CVt + puntos_CVm

    # ---> REGLA DE PROTECCIÓN BANCARIA (OVERRIDE POR DÉFICIT REAL) <---
    # Sumamos absolutamente todas las salidas de dinero (compras + bills)
    total_compras = df_purchases['amount'].sum() if not df_purchases.empty else 0.0
    total_bills = df_bills['amount'].sum() if not df_bills.empty else 0.0
    egreso_total_acumulado = total_compras + total_bills

    # Si los egresos totales superan a los ingresos totales, o la capacidad neta es negativa
    if egreso_total_acumulado > ingreso_total:
        score_final = min(score_final, 520)  # Lo fuerza directo a Riesgo Alto (< 550)

    return {
        "score": int(score_final),
        "metricas": {
            "dias_supervivencia": round(dias_supervivencia, 1),
            "ciclo_cobro_dias": round(ciclo_ingreso, 1),
            "ratio_liquidez": round(L, 2),
            "ratio_gastos": round(Go, 2),
            "cv_tiempo": round(CVt, 2),
            "cv_monto_ponderado": round(CVm, 2),
            "num_pagos_fijos_detectados": int(len(df_fijos))
        }
    }