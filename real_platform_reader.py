"""
Lector y Escáner Real de Olymp Trade (Single Window - Real Time).
- Garantía de VENTANA ÚNICA (bloqueo por candado para evitar múltiples ventanas).
- Captura de datos en tiempo real directo de Olymp Trade (WebSocket + DOM).
- Cálculo en vivo de Velas, Swing High/Low, EMA 35, EMA 100, RSI 7 y Fibo 0.5/0.618.
- Alerta precisa al segundo :50 de la vela.
"""
import time
import datetime
import os
import sys
import json
import msvcrt
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright
from strategy import SniperStrategy
from notifier import trigger_sniper_signal

# 1. BLOQUEO DE INSTANCIA ÚNICA (Imposible abrir múltiples ventanas)
LOCK_FILE_PATH = os.path.join(os.path.dirname(__file__), "sniper_reader.lock")
lock_file = open(LOCK_FILE_PATH, "w")
try:
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
    print("="*60)
    print("⚠️ AVISO: YA HAY UNA VENTANA DEL BOT SNIPER ABIERTA.")
    print("No se abrirán ventanas duplicadas.")
    print("Por favor utiliza la ventana que ya tienes en pantalla.")
    print("="*60)
    time.sleep(5)
    sys.exit(0)

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

class RealTimeOlympSniper:
    def __init__(self):
        self.strategy = SniperStrategy(fibo_tolerance_pct=0.0010)
        self.last_alert_minute = -1
        self.price_history: List[float] = []
        self.candles: List[Dict[str, float]] = []
        self.current_minute = -1
        self.current_candle: Optional[Dict[str, float]] = None
        self.current_price: float = 0.0
        self.current_asset: str = "Activo en Pantalla"
        self.current_payout: int = 85

    def register_tick(self, price: float, now: datetime.datetime):
        if price <= 0:
            return
        self.current_price = price
        self.price_history.append(price)
        if len(self.price_history) > 600:
            self.price_history.pop(0)

        minute = now.minute
        if minute != self.current_minute:
            if self.current_candle is not None:
                self.candles.append(dict(self.current_candle))
                if len(self.candles) > 60:
                    self.candles.pop(0)
            self.current_minute = minute
            self.current_candle = {
                "open": price,
                "high": price,
                "low": price,
                "close": price
            }
        else:
            if self.current_candle:
                self.current_candle["high"] = max(self.current_candle["high"], price)
                self.current_candle["low"] = min(self.current_candle["low"], price)
                self.current_candle["close"] = price

    def start(self):
        print("="*65)
        print("🎯 INICIANDO BOT SNIPER EN VIVO (VENTANA ÚNICA)")
        print("   Equipo: Rafael Guzmán & Eduardo Rivera")
        print("="*65)
        print("[*] Abriendo una única ventana limpia...")

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized"
                ],
                viewport=None
            )

            # Cerrar pestañas extra si existieran
            if len(browser.pages) > 1:
                for extra in browser.pages[1:]:
                    try:
                        extra.close()
                    except Exception:
                        pass

            page = browser.pages[0] if browser.pages else browser.new_page()

            # Escuchar WebSockets para capturar datos oficiales de Olymp Trade
            def on_web_socket(ws):
                def on_frame(payload):
                    try:
                        if isinstance(payload, str) and ("quote" in payload or "price" in payload):
                            data = json.loads(payload)
                            # Extraer cotización en tiempo real si viene en JSON
                            if isinstance(data, dict):
                                p = data.get("price") or data.get("p") or data.get("close")
                                if p:
                                    self.register_tick(float(p), datetime.datetime.now())
                    except Exception:
                        pass
                ws.on("framereceived", on_frame)

            page.on("websocket", on_web_socket)

            print("[+] Conectando a la plataforma...")
            page.goto("https://olymptrade.com/platform", timeout=60000)
            time.sleep(6)

            print("\n" + "="*65)
            print("✅ CONEXIÓN ESTABLECIDA")
            print("1. En la ventana abierta, configura en el gráfico:")
            print("   - EMA 35 (Azul)")
            print("   - EMA 100 (Roja)")
            print("   - RSI 7 (Niveles 70 y 30)")
            print("2. El bot leerá los precios de esa gráfica y calculará Fibo y EMAs en vivo.")
            print("3. Al segundo :50 de cada minuto, si hay confluencia, sonará en Telegram.")
            print("="*65 + "\n")

            last_status_print = 0

            while True:
                try:
                    now = datetime.datetime.now()

                    # Lectura complementaria directa del DOM
                    try:
                        price_el = page.query_selector('.price-value, [data-test="current-price"], [class*="deal-button_price"], [class*="asset-quote"]')
                        asset_el = page.query_selector('.asset-name, [data-test="asset-name"], [class*="asset-select"]')
                        payout_el = page.query_selector('[data-test="deal-payout"], [class*="payout-value"]')

                        if asset_el:
                            self.current_asset = asset_el.inner_text().strip()

                        if payout_el:
                            try:
                                self.current_payout = int(payout_el.inner_text().replace("%", "").strip())
                            except Exception:
                                pass

                        if price_el:
                            raw_p = price_el.inner_text().replace(",", "").replace("$", "").strip()
                            val = float(raw_p)
                            self.register_tick(val, now)
                    except Exception:
                        pass

                    # Mostrar status en consola cada 5 segundos
                    if time.time() - last_status_print >= 5:
                        last_status_print = time.time()
                        if self.current_price > 0:
                            ema35_val = calculate_ema(self.price_history, 35)
                            ema100_val = calculate_ema(self.price_history, 100)
                            rsi7_val = calculate_rsi(self.price_history, 7)
                            print(f"[{now.strftime('%H:%M:%S')}] 📊 {self.current_asset} | Precio: {self.current_price:.4f} | EMA35: {ema35_val:.4f} | EMA100: {ema100_val:.4f} | RSI7: {rsi7_val:.1f}")

                    # EVALUACIÓN SNIPER AL SEGUNDO :50 (entre segundo 49 y 52)
                    if 49 <= now.second <= 52 and now.minute != self.last_alert_minute:
                        self.last_alert_minute = now.minute

                        if len(self.price_history) >= 15 and self.current_price > 0:
                            # Calcular extremos reales
                            recent_prices = self.price_history[-120:]
                            swing_high = max(recent_prices)
                            swing_low = min(recent_prices)
                            ema_35 = calculate_ema(self.price_history, 35)
                            ema_100 = calculate_ema(self.price_history, 100)
                            rsi_7 = calculate_rsi(self.price_history, 7)

                            print(f"\n[{now.strftime('%H:%M:%S')}] 🎯 ¡SEGUNDO :50! Evaluando confluencia en {self.current_asset}...")
                            print(f"   Techo High: {swing_high:.4f} | Suelo Low: {swing_low:.4f}")
                            print(f"   EMA 35: {ema_35:.4f} | EMA 100: {ema_100:.4f} | RSI 7: {rsi_7:.1f}")

                            setup = self.strategy.evaluate_setup(
                                current_price=self.current_price,
                                candles=self.candles,
                                ema_35=ema_35,
                                ema_100=ema_100,
                                rsi_7=rsi_7,
                                swing_high=swing_high,
                                swing_low=swing_low
                            )

                            if setup:
                                sig_type, level_name, ref_price = setup
                                print(f"🚨 ¡CONFLUENCIA SNIPER CONFIRMADA! {sig_type} en {level_name} ({ref_price:.4f})")
                                trigger_sniper_signal(
                                    signal_type=sig_type,
                                    asset=self.current_asset,
                                    price=ref_price,
                                    level_name=level_name,
                                    payout=self.current_payout
                                )
                            else:
                                print("ℹ️ Sin confluencia Fibo/EMA/RSI en este minuto. Esperando siguiente oportunidad.\n")

                    time.sleep(0.5)

                except KeyboardInterrupt:
                    print("\n[!] Bot detenido manualmente.")
                    break
                except Exception as e:
                    time.sleep(1)

if __name__ == "__main__":
    bot = RealTimeOlympSniper()
    bot.start()
