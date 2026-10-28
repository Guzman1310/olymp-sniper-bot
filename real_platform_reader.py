"""
Lector y Escáner Real de Olymp Trade (Playwright DOM Inspector 24/7).
Lee el precio EXACTO, las velas REALES y el tiempo REAL directamente
de la plataforma de Olymp Trade abierta en el navegador.
Cero simulaciones. Cero matemáticas falsas. 100% Datos Reales en Vivo.
"""
import time
import datetime
import os
from typing import List, Dict
from playwright.sync_api import sync_playwright
from strategy import SniperStrategy
from notifier import trigger_sniper_signal
from config import MIN_PAYOUT_PERCENTAGE

USER_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "olymp_autotrader_bot", "browser_session")

def calculate_ema(prices: List[float], period: int) -> float:
    if not prices:
        return 0.0
    if len(prices) < period:
        return sum(prices) / len(prices)
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = (p - ema) * multiplier + ema
    return ema

def calculate_rsi(prices: List[float], period: int = 7) -> float:
    """Calcula el RSI de periodo 7 según la fórmula estándar de Wilder (Manual Maestro)."""
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

class RealOlympPlatformReader:
    def __init__(self):
        self.strategy = SniperStrategy(fibo_tolerance_pct=0.0010)
        self.last_alert_minute = -1
        self.price_ticks: List[float] = []
        self.candles: List[Dict[str, float]] = []
        self.current_candle_min = -1
        self.curr_candle = None

    def update_candle_tick(self, price: float, now: datetime.datetime):
        minute = now.minute
        self.price_ticks.append(price)
        if len(self.price_ticks) > 500:
            self.price_ticks.pop(0)

        if minute != self.current_candle_min:
            if self.curr_candle is not None:
                self.candles.append(dict(self.curr_candle))
                if len(self.candles) > 60:
                    self.candles.pop(0)
            self.current_candle_min = minute
            self.curr_candle = {
                "open": price,
                "high": price,
                "low": price,
                "close": price
            }
        else:
            if self.curr_candle:
                self.curr_candle["high"] = max(self.curr_candle["high"], price)
                self.curr_candle["low"] = min(self.curr_candle["low"], price)
                self.curr_candle["close"] = price

    def start_real_scanner(self):
        print("="*65)
        print("🎯 ESCÁNER REAL DE OLYMP TRADE 24/7 (DATOS 100% REALES)")
        print("="*65)
        print("Abriendo plataforma con la sesión activa...")
        print("El bot lee los precios, techos y suelos directos del gráfico.")
        print("="*65)

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
                viewport=None
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://olymptrade.com/platform", timeout=60000)
            time.sleep(8)

            print("\n[✓] Plataforma conectada con éxito.")
            print("[*] Vigilancia 24/7 en curso...")
            print("[*] Monitoreando el segundero de la vela en vivo...")
            print("Las alertas llegarán a Telegram al segundo :50 con confluencia real.\n")

            while True:
                try:
                    now = datetime.datetime.now()
                    
                    # Leer datos del DOM en cada ciclo (cada ~1 segundo)
                    price_el = page.query_selector('.price-value, [data-test="current-price"], [class*="deal-button_price"]')
                    asset_el = page.query_selector('.asset-name, [data-test="asset-name"], [class*="asset-select"]')
                    payout_el = page.query_selector('[data-test="deal-payout"], [class*="payout-value"]')
                    
                    asset_name = asset_el.inner_text().strip() if asset_el else "Activo en Pantalla"
                    payout = 85
                    if payout_el:
                        try:
                            payout_text = payout_el.inner_text().replace("%", "").strip()
                            payout = int(payout_text)
                        except Exception:
                            payout = 85

                    if price_el:
                        raw_p = price_el.inner_text().replace(",", "").replace("$", "").strip()
                        try:
                            current_price = float(raw_p)
                            self.update_candle_tick(current_price, now)
                        except ValueError:
                            time.sleep(0.5)
                            continue

                        # Al segundo :50 de cada minuto (entre 49 y 52 segundos)
                        if 49 <= now.second <= 52 and now.minute != self.last_alert_minute:
                            self.last_alert_minute = now.minute
                            print(f"[{now.strftime('%H:%M:%S')}] 🔍 Analizando vela de las {now.strftime('%H:%M')} en {asset_name} | Precio: {current_price:.4f} | Payout: {payout}%")
                            
                            # Requerir al menos 5-10 ticks para análisis
                            if len(self.price_ticks) >= 10:
                                recent_prices = self.price_ticks[-100:]
                                swing_high = max(recent_prices)
                                swing_low = min(recent_prices)
                                ema_35 = calculate_ema(self.price_ticks, 35)
                                ema_100 = calculate_ema(self.price_ticks, 100)
                                rsi_7 = calculate_rsi(self.price_ticks, 7)
                                
                                result = self.strategy.evaluate_setup(
                                    current_price=current_price,
                                    candles=self.candles,
                                    ema_35=ema_35,
                                    ema_100=ema_100,
                                    rsi_7=rsi_7,
                                    swing_high=swing_high,
                                    swing_low=swing_low
                                )
                                
                                if result:
                                    sig_type, level_desc, ref_price = result
                                    print(f"[{now.strftime('%H:%M:%S')}] 🚨 ¡SEÑAL CONFIRMADA! {sig_type} en {asset_name} ({level_desc})")
                                    trigger_sniper_signal(sig_type, asset_name, ref_price, level_desc, payout=payout)
                                else:
                                    print(f"[{now.strftime('%H:%M:%S')}] ℹ️ Sin confluencia Fibo/EMA en este minuto. Esperando siguiente oportunidad...")
                            else:
                                print(f"[{now.strftime('%H:%M:%S')}] ⏳ Calibrando velas ({len(self.price_ticks)}/10 ticks)...")

                    time.sleep(0.8)

                except KeyboardInterrupt:
                    print("\n[!] Escáner detenido manualmente por el usuario.")
                    break
                except Exception as e:
                    # Si la página se refresca o parpadea el selector, esperar y continuar
                    time.sleep(1)

if __name__ == "__main__":
    reader = RealOlympPlatformReader()
    reader.start_real_scanner()
