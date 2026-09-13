# Ejemplos de cuentas bancarias

import requests
from datetime import datetime, timedelta
import random
import json

print("--- CONFIGURACIÓN DE CUENTAS NESSIE (NIVELES DE SALUD FINANCIERA) ---")
API_KEY = input("Ingresa tu API Key de Nessie: ").strip()
BASE_URL = "https://api.nessieisreal.com"

if not API_KEY:
    print("❌ Error: La API Key no puede estar vacía.")
    exit()

print("\n1. Verificando o creando comercio base...")
merchant_id = None
try:
    res_get_m = requests.get(f"{BASE_URL}/merchants?key={API_KEY}")
    if res_get_m.status_code == 200:
        m_list = res_get_m.json()
        if isinstance(m_list, list) and len(m_list) > 0:
            merchant_id = m_list[0].get("_id")
            print(f"✔️ Comercio encontrado: {merchant_id}")
except Exception:
    pass

if not merchant_id:
    try:
        res_m = requests.post(f"{BASE_URL}/merchants?key={API_KEY}", json={
            "name": "Comercio Local", 
            "category": "retail",
            "address": {"street_number": "12", "street_name": "Av. Principal", "city": "CDMX", "state": "CDMX", "zip": "03100"},
            "geocode": {"lat": 19.35, "lng": -99.16}
        })
        if res_m.status_code not in (200, 201):
            print(f"⚠️ Error creando comercio ({res_m.status_code}): {res_m.text}")
        m_data = res_m.json()
        if isinstance(m_data, dict):
            merchant_id = m_data.get("objectCreated", {}).get("_id") or m_data.get("_id")
    except Exception as e:
        print(f"Error creando comercio: {e}")

if not merchant_id:
    print("❌ Error crítico: No se pudo obtener ni crear un merchant_id válido.")
    exit()

print("\n2. Creando cliente...")
try:
    res_c = requests.post(f"{BASE_URL}/customers?key={API_KEY}", json={
        "first_name": "Usuario", 
        "last_name": "SaludFinanciera",
        "address": {"street_number": "500", "street_name": "Reforma", "city": "CDMX", "state": "CDMX", "zip": "06500"}
    })
    if res_c.status_code not in (200, 201):
        print(f"⚠️ Error creando cliente ({res_c.status_code}): {res_c.text}")
    c_data = res_c.json()
    if isinstance(c_data, dict):
        customer_id = c_data.get("objectCreated", {}).get("_id") or c_data.get("_id")
    else:
        raise ValueError("Respuesta de cliente inválida")
except Exception as e:
    print(f"❌ Error creando cliente: {e}")
    exit()

print(f"Customer ID asignado: {customer_id}")

# Perfiles definidos por su salud financiera real
perfiles_config = [
    {
        "banco": "BBVA", 
        "nickname": "Cuenta Bien (Sólida)", 
        "balance": 45000,
        "ingreso_base": 30000, 
        "salud": "bien" # Ingresos altos, gastos bajos controlados, mucho ahorro
    },
    {
        "banco": "Santander", 
        "nickname": "Cuenta Masomenos (Estable)", 
        "balance": 18000,
        "ingreso_base": 18000, 
        "salud": "masomenos" # Ingresos cubren justo los gastos, sin grandes ahorros
    },
    {
        "banco": "Nu México", 
        "nickname": "Cuenta Mal (Descontrolada)", 
        "balance": 4200,
        "ingreso_base": 12000, 
        "salud": "mal" # Gastos superan o empatan los ingresos mes a mes, saldo bajo
    },
    {
        "banco": "Mercado Pago", 
        "nickname": "Cuenta Muy Mal (Crítica)", 
        "balance": 800,
        "ingreso_base": 8000, 
        "salud": "muymal" # Gastos masivos y constantes, servicios altos, al borde de cero
    }
]

cuentas_generadas = {}
hoy = datetime.now()

for perfil in perfiles_config:
    print(f"\nInyectando perfil '{perfil['salud'].upper()}' para: {perfil['banco']}...")
    
    res_acc = requests.post(f"{BASE_URL}/customers/{customer_id}/accounts?key={API_KEY}", json={
        "type": "Checking",
        "nickname": perfil["nickname"],
        "rewards": 50,
        "balance": perfil["balance"]
    })

    if res_acc.status_code not in (200, 201):
        print(f"⚠️ Error creando cuenta {perfil['banco']} ({res_acc.status_code}): {res_acc.text}")

    acc_data = res_acc.json()
    if isinstance(acc_data, dict):
        acc_id = acc_data.get("objectCreated", {}).get("_id") or acc_data.get("_id")
    else:
        print(f"Error al crear cuenta {perfil['banco']}")
        continue
        
    cuentas_generadas[perfil["banco"]] = acc_id
    
    salud = perfil["salud"]
    base_ingreso = perfil["ingreso_base"]
    
    # Inyectar historial de 12 meses
    for i in range(12):
        mes_base = hoy - timedelta(days=30 * i)
        fecha_str = mes_base.strftime("%Y-%m-%d")
        
        if salud == "bien":
            # BIEN: Ingreso sólido quincenal, gasto mínimo (solo 20% del ingreso), servicios bajos
            for q_offset in [0, 15]:
                f_q = (mes_base - timedelta(days=q_offset)).strftime("%Y-%m-%d")
                requests.post(f"{BASE_URL}/accounts/{acc_id}/deposits?key={API_KEY}", json={
                    "medium": "balance", "transaction_date": f_q, "status": "completed",
                    "amount": int(base_ingreso / 2), "description": "Nómina Principal"
                })
            requests.post(f"{BASE_URL}/accounts/{acc_id}/purchases?key={API_KEY}", json={
                "medium": "balance", "purchase_date": fecha_str, "status": "completed",
                "amount": int(base_ingreso * 0.20), "description": "Supermercado Esencial", "merchant_id": merchant_id
            })
            pago_servicio = 600

        elif salud == "masomenos":
            # MASOMENOS: Ingreso mensual único, gasto moderado (50% del ingreso), comportamiento neutral
            requests.post(f"{BASE_URL}/accounts/{acc_id}/deposits?key={API_KEY}", json={
                "medium": "balance", "transaction_date": fecha_str, "status": "completed",
                "amount": base_ingreso, "description": "Ingreso Mensual Fijo"
            })
            requests.post(f"{BASE_URL}/accounts/{acc_id}/purchases?key={API_KEY}", json={
                "medium": "balance", "purchase_date": fecha_str, "status": "completed",
                "amount": int(base_ingreso * 0.50), "description": "Consumo General y Compras", "merchant_id": merchant_id
            })
            pago_servicio = 1200

        elif salud == "mal":
            # MAL: Ingreso normal pero gastos hormiga y compras múltiples que se comen el 85% del ingreso
            requests.post(f"{BASE_URL}/accounts/{acc_id}/deposits?key={API_KEY}", json={
                "medium": "balance", "transaction_date": fecha_str, "status": "completed",
                "amount": base_ingreso, "description": "Ingreso Mensual Regular"
            })
            for c_idx in range(4):
                f_compra = (mes_base - timedelta(days=c_idx * 6)).strftime("%Y-%m-%d")
                requests.post(f"{BASE_URL}/accounts/{acc_id}/purchases?key={API_KEY}", json={
                    "medium": "balance", "purchase_date": f_compra, "status": "completed",
                    "amount": random.randint(1500, 3000), "description": "Compras impulsivas / E-commerce", "merchant_id": merchant_id
                })
            pago_servicio = 2200

        elif salud == "muymal":
            # MUY MAL: Ingresos bajos e irregulares, múltiples compras altas y retiros que dejan la cuenta en números críticos
            requests.post(f"{BASE_URL}/accounts/{acc_id}/deposits?key={API_KEY}", json={
                "medium": "balance", "transaction_date": fecha_str, "status": "completed",
                "amount": base_ingreso, "description": "Depósito Parcial / Préstamo"
            })
            for c_idx in range(5):
                f_compra = (mes_base - timedelta(days=c_idx * 5)).strftime("%Y-%m-%d")
                requests.post(f"{BASE_URL}/accounts/{acc_id}/purchases?key={API_KEY}", json={
                    "medium": "balance", "purchase_date": f_compra, "status": "completed",
                    "amount": random.randint(1800, 3500), "description": "Gastos excesivos / Deudas", "merchant_id": merchant_id
                })
            requests.post(f"{BASE_URL}/accounts/{acc_id}/withdrawals?key={API_KEY}", json={
                "medium": "balance", "transaction_date": fecha_str, "status": "completed",
                "amount": 2500, "description": "Retiro emergencia cajero"
            })
            pago_servicio = 3500

        # Registrar el pago de servicios correspondiente al nivel de salud
        requests.post(f"{BASE_URL}/accounts/{acc_id}/bills?key={API_KEY}", json={
            "status": "completed", 
            "payee": "Compañía de Servicios", 
            "nickname": "Pago de Servicios Básicos",
            "payment_amount": float(pago_servicio), 
            "payment_date": fecha_str, 
            "recurring_date": 10
        })

    print(f"-> Historial de {perfil['banco']} inyectado correctamente.")

# --- GUARDAR CONFIGURACIÓN ---
datos_configuracion = {
    "api_key": API_KEY,
    "cuentas": cuentas_generadas
}

with open("bancos_config.json", "w", encoding="utf-8") as f:
    json.dump(datos_configuracion, f, indent=4)

print("\n" + "="*80)
print("¡PROCESO CONCLUIDO CON ÉXITO!")
print("Los 4 niveles de salud financiera han sido guardados en 'bancos_config.json'.")
print("="*80)