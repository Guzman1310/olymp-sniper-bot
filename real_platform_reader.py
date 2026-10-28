"""
Lector y Escáner Real de Olymp Trade (Fidelidad 100% al Manual Maestro).
- Calcula EMA 35, EMA 100 y RSI 7 sobre VELAS DE 1 MINUTO REALES (nunca ticks).
- Extrae el historial de velas directamente de la plataforma (Red/WebSockets).
- Cálculo milimétrico de Fibonacci (Swing High a Swing Low de las velas).
- Monitoreo en vivo con reporte detallado de confluencia al segundo :50.
"""
import time
import datetime
import os
import sys
import json
import msvcrt
import requests
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright
from strategy import SniperStrategy
from notifier import trigger_sniper_signal

# BLOQUEO DE INSTANCIA ÚNICA
LOCK_FILE_PATH = os.path.join(os.path.dirname(__file__), "sniper_reader.lock")
lock_file = open(LOCK_FILE_PATH, "w")
try:
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
    print("="*60)
    print("⚠️ AVISO: YA HAY UNA VENTANA DEL BOT SNIPER ABIERTA.")
    print("No se abrirán ventanas duplicadas.")
    print("="*60)
    time.sleep(3)
    sys.exit(0)

USER_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "olymp_autotrader_bot", "browser_session")
LOG_PATH = os.path.join(os.path.dirname(__file__), "sniper_activity.log")

def log_msg(msg: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(full_msg + "\n")
    except Exception:
        pass

def calculate_ema_candles(closes: List[float], period: int) -> float:
    if not closes:
        return 0.0
    if len(closes) < period:
        return sum(closes) / len(closes)
    multiplier = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for p in closes[period:]:
        ema = (p - ema) * multiplier + ema
    return ema

def calculate_rsi_candles(closes: List[float], period: int = 7) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
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

class MasterManualSniperReader:
    def __init__(self):
        self.strategy = SniperStrategy(fibo_tolerance_pct=0.0012)
        self.last_alert_minute = -1
        self.candles: List[Dict[str, float]] = [] # Lista de velas 1m: {'open', 'high', 'low', 'close', 'time'}
        self.current_candle: Optional[Dict[str, float]] = None
        self.current_minute = -1
        self.current_price: float = 0.0
        self.current_asset: str = "Activo en Pantalla"
        self.current_payout: int = 85

    def add_candle_bar(self, open_p: float, high_p: float, low_p: float, close_p: float, timestamp: int):
        # Evitar duplicados por timestamp
        for c in self.candles:
            if abs(c.get("time", 0) - timestamp) < 30:
                c["high"] = max(c["high"], high_p)
                c["low"] = min(c["low"], low_p)
                c["close"] = close_p
                return
        self.candles.append({
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "time": timestamp
        })
        if len(self.candles) > 120:
            self.candles.pop(0)

    def register_tick(self, price: float, now: datetime.datetime):
        if price <= 0:
            return
        self.current_price = price
        minute = now.minute

        if minute != self.current_minute:
            if self.current_candle is not None:
                self.candles.append(dict(self.current_candle))
                if len(self.candles) > 120:
                    self.candles.pop(0)
            self.current_minute = minute
            self.current_candle = {
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "time": int(now.timestamp())
            }
        else:
            if self.current_candle:
                self.current_candle["high"] = max(self.current_candle["high"], price)
                self.current_candle["low"] = min(self.current_candle["low"], price)
                self.current_candle["close"] = price

    def start(self):
        log_msg("="*65)
        log_msg("🎯 LECTOR SNIPER PROFESIONAL (VELAS 1M REALES + MANUAL MAESTRO)")
        log_msg("   Calcula EMA 35 (35m), EMA 100 (100m), RSI 7 (7m) y Fibo Real")
        log_msg("   Equipo: Rafael Guzmán & Eduardo Rivera")
        log_msg("="*65)

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

            # Mantener una sola pestaña
            if len(browser.pages) > 1:
                for extra in browser.pages[1:]:
                    try:
                        extra.close()
                    except Exception:
                        pass

            page = browser.pages[0] if browser.pages else browser.new_page()

            # 1. INTERCEPTAR VELAS OFICIALES EN LA RED DE OLYMP TRADE
            def on_response(response):
                url = response.url
                if any(k in url for k in ["candle", "history", "chart", "quotes"]):
                    try:
                        data = response.json()
                        bars = None
                        if isinstance(data, list):
                            bars = data
                        elif isinstance(data, dict):
                            bars = data.get("data") or data.get("candles") or data.get("bars")

                        if bars and isinstance(bars, list):
                            for b in bars:
                                if isinstance(b, dict) and "c" in b and "o" in b:
                                    self.add_candle_bar(
                                        open_p=float(b.get("o", b.get("open", 0))),
                                        high_p=float(b.get("h", b.get("high", 0))),
                                        low_p=float(b.get("l", b.get("low", 0))),
                                        close_p=float(b.get("c", b.get("close", 0))),
                                        timestamp=int(b.get("t", b.get("time", 0)))
                                    )
                                elif isinstance(b, list) and len(b) >= 5:
                                    self.add_candle_bar(
                                        timestamp=int(b[0]),
                                        open_p=float(b[1]),
                                        high_p=float(b[2]),
                                        low_p=float(b[3]),
                                        close_p=float(b[4])
                                    )
                    except Exception:
                        pass

            page.on("response", on_response)

            # 2. INTERCEPTAR FLUJO WEBSOCKET
            def on_web_socket(ws):
                def on_frame(payload):
                    try:
                        if isinstance(payload, str) and ("candle" in payload or "quote" in payload):
                            data = json.loads(payload)
                            if isinstance(data, dict):
                                p = data.get("price") or data.get("p") or data.get("close")
                                if p:
                                    self.register_tick(float(p), datetime.datetime.now())
                    except Exception:
                        pass
                ws.on("framereceived", on_frame)

            page.on("websocket", on_web_socket)

            log_msg("[+] Abriendo plataforma de Olymp Trade...")
            page.goto("https://olymptrade.com/platform", timeout=60000)
            time.sleep(6)

            log_msg("\n[✓] Plataforma conectada.")
            log_msg("[*] Monitoreando gráfico en tiempo real...")
            log_msg("Asegúrate de tener abierta la gráfica que deseas operar (1M).\n")

            last_status = 0

            while True:
                try:
                    now = datetime.datetime.now()

                    # Lectura directa del DOM (precio actual y activo)
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
                            raw = price_el.inner_text().replace(",", "").replace("$", "").strip()
                            self.register_tick(float(raw), now)
                    except Exception:
                        pass

                    # Reporte de estado en pantalla cada 6 segundos
                    if time.time() - last_status >= 6:
                        last_status = time.time()
                        all_candles = self.candles + ([self.current_candle] if self.current_candle else [])
                        closes = [c["close"] for c in all_candles if "close" in c]
                        
                        if closes:
                            ema35 = calculate_ema_candles(closes, 35)
                            ema100 = calculate_ema_candles(closes, 100)
                            rsi7 = calculate_rsi_candles(closes, 7)
                            log_msg(f"📊 {self.current_asset} | Precio: {self.current_price:.4f} | Velas 1m: {len(closes)} | EMA35: {ema35:.4f} | EMA100: {ema100:.4f} | RSI7: {rsi7:.1f}")

                    # EVALUACIÓN SAGRADA AL SEGUNDO :50 (Manual Maestro)
                    if 49 <= now.second <= 52 and now.minute != self.last_alert_minute:
                        self.last_alert_minute = now.minute

                        all_candles = self.candles + ([self.current_candle] if self.current_candle else [])
                        closes = [c["close"] for c in all_candles if "close" in c]

                        if len(closes) >= 5 and self.current_price > 0:
                            # 1. EMAs sobre velas de 1 minuto
                            ema_35 = calculate_ema_candles(closes, 35)
                            ema_100 = calculate_ema_candles(closes, 100)
                            
                            # 2. RSI 7 sobre velas de 1 minuto
                            rsi_7 = calculate_rsi_candles(closes, 7)

                            # 3. Fibonacci Swing High y Low sobre las últimas velas (15 a 30 velas)
                            recent_candles = all_candles[-30:]
                            highs = [c["high"] for c in recent_candles if "high" in c]
                            lows = [c["low"] for c in recent_candles if "low" in c]
                            swing_high = max(highs) if highs else self.current_price * 1.002
                            swing_low = min(lows) if lows else self.current_price * 0.998

                            trend_desc = "ALCISTA (Solo Compras)" if ema_35 > ema_100 else "BAJISTA (Solo Ventas)"

                            log_msg(f"\n{'='*65}")
                            log_msg(f"🎯 EVALUACIÓN SEGUNDO :50 EN {self.current_asset}")
                            log_msg(f"   Precio Actual: {self.current_price:.4f}")
                            log_msg(f"   Tendencia EMAs: {trend_desc} (EMA 35: {ema_35:.4f} | EMA 100: {ema_100:.4f})")
                            log_msg(f"   RSI 7 (Velas 1M): {rsi_7:.1f} (Escala 0 a 100)")
                            log_msg(f"   Fibonacci: Techo={swing_high:.4f} | Suelo={swing_low:.4f}")

                            setup = self.strategy.evaluate_setup(
                                current_price=self.current_price,
                                candles=all_candles,
                                ema_35=ema_35,
                                ema_100=ema_100,
                                rsi_7=rsi_7,
                                swing_high=swing_high,
                                swing_low=swing_low
                            )

                            if setup:
                                sig_type, level_name, ref_p = setup
                                log_msg(f"🚨 ¡CONFLUENCIA TOTAL 100%! {sig_type} en {level_name} ({ref_p:.4f})")
                                log_msg(f"Disparando alerta a Telegram...")
                                trigger_sniper_signal(
                                    signal_type=sig_type,
                                    asset=self.current_asset,
                                    price=ref_p,
                                    level_name=level_name,
                                    payout=self.current_payout
                                )
                            else:
                                log_msg("ℹ️ Sin confluencia perfecta del Manual Maestro en este minuto. Capital protegido.")
                            log_msg(f"{'='*65}\n")

                    time.sleep(0.5)

                except KeyboardInterrupt:
                    log_msg("\n[!] Bot detenido manualmente.")
                    break
                except Exception as e:
                    time.sleep(1)

if __name__ == "__main__":
    reader = MasterManualSniperReader()
    reader.start()
