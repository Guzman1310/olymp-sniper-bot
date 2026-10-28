"""
Panel de Control y Asistente en Vivo del Sniper Bot.
Permite ingresar los parámetros actuales del gráfico (o conectarse al feed) 
y emite las alertas en el segundo exacto.
"""
import time
import datetime
from strategy import SniperStrategy
from notifier import trigger_sniper_signal

def run_interactive_assistant():
    strategy = SniperStrategy()
    print("="*60)
    print("   SISTEMA DE ASISTENCIA SNIPER EN VIVO (OLYMP TRADE)")
    print("="*60)
    print("El bot monitorea el reloj de la vela en tu PC.")
    print("Alertas configuradas a Telegram (ID: 1028358282) y por voz.")
    print("="*60)

    asset = input("Nombre del activo (ej: Europe Composite Index, Gold OTC): ").strip()
    if not asset:
        asset = "Europe Composite Index"

    print(f"\n[+] Activo seleccionado: {asset}")
    swing_high = float(input("Precio Swing High (Techo mas alto): "))
    swing_low = float(input("Precio Swing Low (Suelo mas bajo): "))
    ema_35 = float(input("Precio actual de EMA 35 (Azul): "))
    ema_100 = float(input("Precio actual de EMA 100 (Roja): "))
    
    trend = "BAJISTA (Ventas)" if ema_35 < ema_100 else "ALCISTA (Compras)"
    print(f"\n[+] Tendencia detectada: {trend}")
    
    fibos = strategy.calculate_fibonacci(swing_high, swing_low, "DOWN" if ema_35 < ema_100 else "UP")
    print("\n--- NIVELES DE FIBONACCI CALCULADOS AL MILIMETRO ---")
    for lvl, val in fibos.items():
        print(f"  Nivel {lvl}: {val:.4f}")
    print("--------------------------------------------------\n")

    print("[*] Monitoreando el reloj para avisarte al segundo :50 de la vela...")
    print("Presiona Ctrl + C en cualquier momento para detener.\n")

    last_alerted_minute = -1

    while True:
        now = datetime.datetime.now()
        second = now.second
        minute = now.minute

        # Evaluamos al segundo 50 para darte 10 segundos de reacción antes del :00
        if 48 <= second <= 52 and minute != last_alerted_minute:
            # Preguntar o verificar el precio del segundo 50
            print(f"\n[TIEMPO: {now.strftime('%H:%M:%S')}] - ¡Segundo 50 de la vela!")
            curr_str = input(f"Introduce el precio actual de {asset} (o Enter si no llego a zona): ").strip()
            
            if curr_str:
                try:
                    curr_price = float(curr_str)
                    # Evaluamos setup
                    setup = strategy.evaluate_setup(
                        current_price=curr_price,
                        candles=[],
                        ema_35=ema_35,
                        ema_100=ema_100,
                        rsi_7=50,
                        swing_high=swing_high,
                        swing_low=swing_low
                    )
                    
                    if setup:
                        sig_type, level_name, ref_p = setup
                        trigger_sniper_signal(sig_type, asset, curr_price, level_name)
                        last_alerted_minute = minute
                        print(f"-> ALERTA ENVIADA EXITOSAMENTE A TU CELULAR Y VOZ.")
                    else:
                        print("-> Precio fuera de zona Fibo/EMA óptima. Sin operación.")
                except ValueError:
                    pass
            else:
                print("-> Sin entrada esta vela. Esperando la siguiente...")
            
            last_alerted_minute = minute

        time.sleep(1)

if __name__ == "__main__":
    run_interactive_assistant()
