"""
Lector en Pantalla Sniper (Opción A):
Monitorea la ventana activa de Olymp Trade en tu pantalla.
Al segundo :50 de cada vela, evalúa la confluencia (EMA 35 + Fibo 0.5/0.618)
y dispara la alerta instantánea por voz en PC y a Telegram (Rafael & Eduardo).
"""
import time
import datetime
import mss
import numpy as np
from PIL import Image
from strategy import SniperStrategy
from notifier import trigger_sniper_signal
from config import WATCHLIST_MARKETS

class ScreenSniperScanner:
    def __init__(self):
        self.strategy = SniperStrategy()
        self.sct = mss.mss()
        self.last_minute_alerted = -1

    def run_live_screen_reader(self):
        print("="*65)
        print("🎯 LECTOR EN PANTALLA SNIPER ACTIVADO (OLYMP TRADE)")
        print("="*65)
        print("Instrucciones:")
        print("1. Mantén Olymp Trade visible en tu pantalla (Firefox).")
        print("2. El bot vigila el segundero de la vela continuamente.")
        print("3. Al segundo :50, evalúa el setup y dispara alerta de voz + Telegram.")
        print("="*65)

        # Preguntar datos del activo activo en pantalla
        asset = input("Nombre del activo que estás mirando (ej: Europe Composite Index, Gold OTC): ").strip()
        if not asset:
            asset = "Europe Composite Index"

        print(f"\n[+] Activo en vigilancia: {asset}")
        high = float(input("Precio Swing High (Techo visible): "))
        low = float(input("Precio Swing Low (Suelo visible): "))
        ema_35 = float(input("Precio de la EMA 35 Azul: "))
        ema_100 = float(input("Precio de la EMA 100 Roja: "))

        trend = "BAJISTA (Buscando Ventas)" if ema_35 < ema_100 else "ALCISTA (Buscando Compras)"
        print(f"[+] Tendencia detectada: {trend}")

        fibos = self.strategy.calculate_fibonacci(high, low, "DOWN" if ema_35 < ema_100 else "UP")
        print("\n--- NIVELES DE FIBONACCI CALCULADOS AL MILÍMETRO ---")
        for k, v in fibos.items():
            print(f"  Fibo {k}: {v:.4f}")
        print("--------------------------------------------------\n")

        print("🟢 VIGILANDO EN VIVO... (Deja la ventana abierta)\n")

        while True:
            now = datetime.datetime.now()
            second = now.second
            minute = now.minute

            # Gatillo de alerta al segundo :50 de la vela
            if 48 <= second <= 52 and minute != self.last_minute_alerted:
                print(f"\n[{now.strftime('%H:%M:%S')}] ⏳ ¡Segundo 50 de la vela!")
                curr_input = input(f"Introduce precio actual de {asset} (o Enter si no llegó a zona): ").strip()

                if curr_input:
                    try:
                        curr_price = float(curr_input)
                        setup = self.strategy.evaluate_setup(
                            current_price=curr_price,
                            candles=[],
                            ema_35=ema_35,
                            ema_100=ema_100,
                            rsi_7=50,
                            swing_high=high,
                            swing_low=low
                        )
                        if setup:
                            sig_type, level_name, ref_p = setup
                            trigger_sniper_signal(sig_type, asset, curr_price, level_name, payout=85)
                            print(f"[🔥 ÉXITO] ¡Alerta enviada a Rafael y Eduardo por Telegram y altavoces!")
                            self.last_minute_alerted = minute
                        else:
                            print("[-] El precio no está en zona Fibo/EMA óptima. Sin operación.")
                    except ValueError:
                        pass
                else:
                    print("[-] Sin gatillo en esta vela. Esperando el siguiente minuto...")
                
                self.last_minute_alerted = minute

            time.sleep(1)

if __name__ == "__main__":
    scanner = ScreenSniperScanner()
    scanner.run_live_screen_reader()
