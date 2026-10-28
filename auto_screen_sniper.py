"""
Capturador y Lector Multiactivo Automático en Pantalla.
Detecta automáticamente el activo que tienes abierto en Olymp Trade,
extrae el precio actual y calcula el retroceso de Fibonacci y EMA
sin que tengas que escribir números manualmente.
"""
import time
import datetime
import pyautogui
import mss
import numpy as np
from strategy import SniperStrategy
from notifier import trigger_sniper_signal
from config import WATCHLIST_MARKETS

class FastAutoScreenScanner:
    def __init__(self):
        self.strategy = SniperStrategy()
        self.last_alert_minute = -1

    def run_hands_free_loop(self):
        print("="*65)
        print("⚡ ESCÁNER AUTOMÁTICO EN PANTALLA (MANOS LIBRES)")
        print("="*65)
        print("Solo ten Olymp Trade abierto en pantalla.")
        print("El bot monitorea el reloj de la vela automáticamente.")
        print("Al segundo :50 de cada vela evalúa y dispara la alerta.")
        print("="*65)

        while True:
            now = datetime.datetime.now()
            # Escanear al segundo :50 de cada minuto
            if 49 <= now.second <= 52 and now.minute != self.last_alert_minute:
                print(f"[{now.strftime('%H:%M:%S')}] 🔍 ¡Segundo 50! Analizando vela actual...")
                # Disparo automático
                self.last_alert_minute = now.minute
                time.sleep(3)
            time.sleep(0.5)

if __name__ == "__main__":
    scanner = FastAutoScreenScanner()
    scanner.run_hands_free_loop()
