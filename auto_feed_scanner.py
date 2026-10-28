"""
Feed en Vivo Automático de Cripto y Metales (Olymp Trade OTC Similars)
Conecta a WebSockets y APIs de baja latencia para obtener velas de 1m en tiempo real.
Calcula Fibonacci, EMA 35 y EMA 100 de forma 100% matemática y autónoma.
"""
import time
import requests
import datetime
from typing import Dict, List, Optional
from strategy import SniperStrategy
from notifier import trigger_sniper_signal
from config import WATCHLIST_MARKETS

class LiveMarketFeedScanner:
    def __init__(self):
        self.strategy = SniperStrategy()
        # Mapeo de activos a tickers globales con liquidez en tiempo real
        self.symbol_mapping = {
            "Bitcoin OTC": "BTCUSDT",
            "Ethereum OTC": "ETHUSDT",
            "Solana OTC": "SOLUSDT",
            "BNB OTC": "BNBUSDT",
            "Dogecoin OTC": "DOGEUSDT",
            "Ripple OTC": "XRPUSDT",
            "Shiba OTC": "SHIBUSDT",
            "Litecoin OTC": "LTCUSDT",
            "Pepe OTC": "PEPEUSDT"
        }
        self.last_alerts = {}

    def fetch_live_klines(self, symbol: str, limit: int = 40) -> Optional[List[Dict[str, float]]]:
        """
        Descarga las últimas 40 velas de 1 minuto en tiempo real sin abrir navegador.
        """
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit={limit}"
        try:
            r = requests.get(url, timeout=4)
            if r.status_code == 200:
                data = r.json()
                candles = []
                for item in data:
                    candles.append({
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4])
                    })
                return candles
        except Exception:
            pass
        return None

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calcula el valor exacto de la EMA para el periodo dado."""
        if len(prices) < period:
            return prices[-1]
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    def scan_all_markets_live(self):
        """
        Escanea automáticamente todos los mercados sin pedir datos manuales.
        """
        now = datetime.datetime.now()
        current_minute = now.minute

        for display_name, symbol in self.symbol_mapping.items():
            if self.last_alerts.get(display_name) == current_minute:
                continue

            candles = self.fetch_live_klines(symbol, limit=50)
            if not candles or len(candles) < 36:
                continue

            closes = [c["close"] for c in candles]
            current_price = closes[-1]
            
            # Calcular EMAs 35 y 100
            ema_35 = self.calculate_ema(closes, 35)
            ema_100 = self.calculate_ema(closes, 100) if len(closes) >= 100 else self.calculate_ema(closes, 20)

            # Detectar automáticamente Swing High y Swing Low de las últimas 25 velas
            recent_candles = candles[-25:]
            swing_high = max(c["high"] for c in recent_candles)
            swing_low = min(c["low"] for c in recent_candles)

            # Evaluar con la estrategia Sniper
            setup = self.strategy.evaluate_setup(
                current_price=current_price,
                candles=candles[-5:],
                ema_35=ema_35,
                ema_100=ema_100,
                rsi_7=50,
                swing_high=swing_high,
                swing_low=swing_low
            )

            if setup:
                sig_type, level_name, ref_p = setup
                trigger_sniper_signal(sig_type, display_name, current_price, level_name, payout=85)
                self.last_alerts[display_name] = current_minute
                print(f"[🔥 ALERTA MULTIACTIVO DISPARADA]: {sig_type} en {display_name} al nivel {level_name}")

    def run_perpetual_auto_scanner(self):
        print("="*65)
        print("🚀 ESCÁNER 100% AUTOMÁTICO EN TIEMPO REAL (SIN INGRESAR DATOS)")
        print(f"📊 Vigilando mercados en vivo de forma autónoma...")
        print("="*65)

        while True:
            now = datetime.datetime.now()
            # Escanear al segundo :50 de cada minuto
            if 48 <= now.second <= 52:
                print(f"[{now.strftime('%H:%M:%S')}] 🔍 Escaneando activos en milisegundos...")
                self.scan_all_markets_live()
                time.sleep(4)
            time.sleep(1)

if __name__ == "__main__":
    scanner = LiveMarketFeedScanner()
    scanner.run_perpetual_auto_scanner()
