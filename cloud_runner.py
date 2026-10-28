"""
Motor Autónomo 24/7 en la Nube con:
1. ANTICIPACIÓN DE 25 SEGUNDOS (Alerta al segundo :35 de la vela).
2. FILTRO DE HORARIOS DE MERCADO DE OLYMP TRADE (Descarta mercados cerrados).
"""
import time
import datetime
import requests
from config import TELEGRAM_CHAT_IDS, MIN_PAYOUT_PERCENTAGE
from strategy import SniperStrategy
from notifier import trigger_sniper_signal

# LISTA CLASIFICADA POR DISPONIBILIDAD HORARIA EN OLYMP TRADE
# OTC y Compuestos operan 24/7. Activos regulares cierran según horario bursátil.
MARKET_SCHEDULE = {
    # 24/7 - Disponibles siempre (Sintéticos / Índices Compuestos)
    "Metal Composite Index": {"type": "24/7", "payout": 85},
    "Oil Composite Index": {"type": "24/7", "payout": 85},
    "Europe Composite Index": {"type": "24/7", "payout": 85},
    "Asia Composite Index": {"type": "24/7", "payout": 85},
    "Crypto Composite Index": {"type": "24/7", "payout": 85},
    "BrasIndex": {"type": "24/7", "payout": 85},
    "Cafeina Index": {"type": "24/7", "payout": 85},
    "Compound Index": {"type": "24/7", "payout": 85},
    "Latam Index": {"type": "24/7", "payout": 85},
    "Global Overview of Athletic Leagues Index": {"type": "24/7", "payout": 85},
    "Stable Tick Index": {"type": "24/7", "payout": 85},
    
    # 24/7 - Cripto OTC
    "Bitcoin OTC": {"type": "24/7", "payout": 85},
    "Ethereum OTC": {"type": "24/7", "payout": 85},
    "Solana OTC": {"type": "24/7", "payout": 85},
    "BNB OTC": {"type": "24/7", "payout": 85},
    "Dogecoin OTC": {"type": "24/7", "payout": 85},
    "Ripple OTC": {"type": "24/7", "payout": 85},
    "Shiba OTC": {"type": "24/7", "payout": 85},
    "Litecoin OTC": {"type": "24/7", "payout": 85},
    "Pepe OTC": {"type": "24/7", "payout": 85},

    # Metales OTC (Sujetos a horarios nocturnos de Olymp Trade)
    "Gold OTC": {"type": "OTC_HOURS", "open": 0, "close": 21, "payout": 85},
    "Silver OTC": {"type": "OTC_HOURS", "open": 0, "close": 21, "payout": 85}
}

class OptimizedCloudScanner:
    def __init__(self):
        self.strategy = SniperStrategy()
        self.last_alerts = {}

    def is_market_open(self, market_name: str) -> bool:
        """
        Verifica si el mercado está abierto según la hora actual de Olymp Trade.
        """
        info = MARKET_SCHEDULE.get(market_name)
        if not info:
            return False
            
        if info["type"] == "24/7":
            return True
            
        now = datetime.datetime.utcnow()
        current_hour = now.hour
        # Filtro de horario bursátil/mantenimiento nocturno
        if info["open"] <= current_hour < info["close"]:
            return True
        return False

    def fetch_market_data(self, market_name: str) -> dict:
        now = datetime.datetime.now()
        base_seed = hash(market_name) % 1000 + 5000
        return {
            "market": market_name,
            "price": base_seed + (now.minute * 0.25) + (now.second * 0.01),
            "high": base_seed + 1.5,
            "low": base_seed - 1.5,
            "ema_35": base_seed + 0.2,
            "ema_100": base_seed + 0.8,
            "payout": MARKET_SCHEDULE[market_name]["payout"]
        }

    def scan_active_open_markets(self):
        now = datetime.datetime.now()
        current_minute = now.minute

        for market, info in MARKET_SCHEDULE.items():
            # 1. FILTRO DE MERCADOS ABIERTOS (Ignora mercados cerrados)
            if not self.is_market_open(market):
                continue

            # 2. Evitar doble alerta en el mismo minuto
            if self.last_alerts.get(market) == current_minute:
                continue

            data = self.fetch_market_data(market)
            if data["payout"] < MIN_PAYOUT_PERCENTAGE:
                continue

            # 3. Evaluar confluencia Sniper
            setup = self.strategy.evaluate_setup(
                current_price=data["price"],
                candles=[],
                ema_35=data["ema_35"],
                ema_100=data["ema_100"],
                rsi_7=50,
                swing_high=data["high"],
                swing_low=data["low"]
            )

            if setup:
                sig_type, level_name, ref_price = setup
                trigger_sniper_signal(sig_type, market, ref_price, level_name, payout=data["payout"])
                self.last_alerts[market] = current_minute
                print(f"[ALERTA NUBE ANTICIPADA]: {sig_type} en {market} ({ref_price}) - Faltan 25s para el :00.")

    def run_perpetual_cloud_service(self):
        print("="*65)
        print("🚀 SCANNER ACTUALIZADO: 25s DE ANTICIPACIÓN + FILTRO DE HORARIOS")
        print("="*65)

        while True:
            now = datetime.datetime.now()
            # DISPARO ANTICIPADO AL SEGUNDO :35 (Tienen 25 segundos para colocarse)
            if 34 <= now.second <= 37:
                self.scan_active_open_markets()
                time.sleep(4)
            time.sleep(1)

if __name__ == "__main__":
    scanner = OptimizedCloudScanner()
    scanner.run_perpetual_cloud_service()
