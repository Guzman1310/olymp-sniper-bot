"""
Scanner Multiactivo 24/7 para el Equipo (Rafael & Eduardo).
Monitorea continuamente la lista completa de mercados:
- Metal Composite Index
- Oil Composite Index
- Europe, Asia, Crypto, BrasIndex, Gold OTC, Silver OTC, BNB OTC, etc.
"""
import time
import datetime
import threading
from typing import Dict, Any
from config import WATCHLIST_MARKETS, TELEGRAM_CHAT_IDS
from strategy import SniperStrategy
from notifier import trigger_sniper_signal, send_telegram_alert

class MarketScanner:
    def __init__(self):
        self.strategy = SniperStrategy()
        self.markets_data: Dict[str, Dict[str, Any]] = {}
        self.last_alerts: Dict[str, int] = {}  # {market: last_alerted_minute}
        
        # Inicializar estructura para cada mercado
        for m in WATCHLIST_MARKETS:
            self.markets_data[m] = {
                "swing_high": 0.0,
                "swing_low": 0.0,
                "ema_35": 0.0,
                "ema_100": 0.0,
                "current_price": 0.0,
                "active": True
            }

    def update_market_levels(self, market: str, high: float, low: float, ema_35: float, ema_100: float, current_price: float):
        """
        Actualiza los parámetros analíticos de un mercado específico.
        """
        if market in self.markets_data:
            self.markets_data[market] = {
                "swing_high": high,
                "swing_low": low,
                "ema_35": ema_35,
                "ema_100": ema_100,
                "current_price": current_price,
                "active": True
            }
            print(f"[SCANNER] Actualizado: {market} | High={high} | Low={low} | EMA35={ema_35} | Precio={current_price}")

    def evaluate_all_markets(self):
        """
        Escanea todos los mercados activos y dispara alertas si se cumplen las reglas.
        """
        now = datetime.datetime.now()
        current_minute = now.minute

        for market, data in self.markets_data.items():
            if not data["active"] or data["current_price"] == 0:
                continue

            # Evitar alertar dos veces en la misma vela de 1m para el mismo activo
            if self.last_alerts.get(market) == current_minute:
                continue

            setup = self.strategy.evaluate_setup(
                current_price=data["current_price"],
                candles=[],
                ema_35=data["ema_35"],
                ema_100=data["ema_100"],
                rsi_7=50,
                swing_high=data["swing_high"],
                swing_low=data["swing_low"]
            )

            if setup:
                sig_type, level_name, ref_price = setup
                trigger_sniper_signal(sig_type, market, ref_price, level_name)
                self.last_alerts[market] = current_minute

    def start_loop(self):
        print("="*65)
        print("🚀 SCANNER MULTIACTIVO INICIADO (RAFAEL & EDUARDO)")
        print(f"📊 Mercados en vigilancia: {len(WATCHLIST_MARKETS)} activos")
        for idx, m in enumerate(WATCHLIST_MARKETS, 1):
            print(f"  {idx}. {m}")
        print("="*65)
        
        while True:
            now = datetime.datetime.now()
            # Escanear al segundo :50 de cada minuto
            if 48 <= now.second <= 52:
                self.evaluate_all_markets()
                time.sleep(4)
            time.sleep(1)

if __name__ == "__main__":
    scanner = MarketScanner()
    
    # Prueba rápida con Metal y Oil Composite Index
    scanner.update_market_levels("Metal Composite Index", high=5914.0, low=5909.2, ema_35=5911.5, ema_100=5912.8, current_price=5911.45)
    scanner.update_market_levels("Oil Composite Index", high=6421.0, low=6417.8, ema_35=6419.5, ema_100=6420.2, current_price=6419.48)
    
    # Evaluar disparo de prueba
    scanner.evaluate_all_markets()
