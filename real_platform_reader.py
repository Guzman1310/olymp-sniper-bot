"""
Lector y Escáner Real de Olymp Trade con Diagnóstico Visual y DOM Dump.
- Toma captura de pantalla (debug_screen.png) para auditar la visual del gráfico.
- Extrae el texto completo de la plataforma (dom_dump.txt) para localizar el precio exacto.
- Calcula EMA 35, EMA 100, RSI 7 y Fibo de 1 Minuto según el Manual Maestro.
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
SCREENSHOT_PATH = os.path.join(os.path.dirname(__file__), "debug_screen.png")
DOM_DUMP_PATH = os.path.join(os.path.dirname(__file__), "dom_dump.txt")

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

class DiagnosedOlympReader:
    def __init__(self):
        self.strategy = SniperStrategy(fibo_tolerance_pct=0.0010)
        self.last_alert_minute = -1
        self.candles: List[Dict[str, float]] = []
        self.current_candle: Optional[Dict[str, float]] = None
        self.current_minute = -1
        self.current_price: float = 0.0
        self.current_asset: str = "Buscando activo..."
        self.current_payout: int = 85

    def register_tick(self, price: float, now: datetime.datetime):
        if price <= 0 or price == 622.0 or price == 1.0 or price == 100.0:
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
        log_msg("🎯 LECTOR SNIPER CON DIAGNÓSTICO VISUAL Y DOM ACTIVO")
        log_msg("   Calcula EMA 35, EMA 100, RSI 7 y Fibo sobre Velas 1M")
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

            if len(browser.pages) > 1:
                for extra in browser.pages[1:]:
                    try:
                        extra.close()
                    except Exception:
                        pass

            page = browser.pages[0] if browser.pages else browser.new_page()

            log_msg("[+] Abriendo plataforma de Olymp Trade...")
            page.goto("https://olymptrade.com/platform", timeout=60000)
            time.sleep(6)

            # 1. Guardar captura de pantalla de diagnóstico
            try:
                page.screenshot(path=SCREENSHOT_PATH)
                log_msg(f"[✓] Captura visual guardada en: {SCREENSHOT_PATH}")
            except Exception as e:
                log_msg(f"[!] Error guardando captura: {e}")

            # 2. Guardar dump de texto del DOM
            try:
                dom_text = page.evaluate("() => document.body.innerText")
                with open(DOM_DUMP_PATH, "w", encoding="utf-8") as f:
                    f.write(dom_text)
                log_msg(f"[✓] Dump del texto de la plataforma guardado en: {DOM_DUMP_PATH}")
            except Exception as e:
                log_msg(f"[!] Error guardando dump: {e}")

            log_msg("[✓] Conexión establecida con la ventana de Olymp Trade.")
            log_msg("[*] Iniciando escáner de cotizaciones en vivo...\n")

            last_status = 0
            last_screenshot = time.time()

            while True:
                try:
                    now = datetime.datetime.now()

                    # Tomar captura cada 60 segundos para auditoría visual continua
                    if time.time() - last_screenshot >= 60:
                        last_screenshot = time.time()
                        try:
                            page.screenshot(path=SCREENSHOT_PATH)
                        except Exception:
                            pass

                    # Extractor JS Completo
                    info = page.evaluate("""() => {
                        let info = { price: 0, asset: '', title: document.title, payout: 85, candidates: [] };
                        
                        // 1. Extraer nombre de activo
                        let assetEl = document.querySelector('[data-test*="asset"], [class*="asset-name"], [class*="asset-select"], [class*="pair-name"]');
                        if (assetEl) {
                            info.asset = assetEl.innerText.trim();
                        }
                        
                        // 2. Extraer todos los números candidatos que NO sean saldo ni cabecera
                        let allEls = Array.from(document.querySelectorAll('*'));
                        for (let el of allEls) {
                            if (el.children.length === 0 && el.innerText) {
                                let t = el.innerText.trim();
                                if (/^[0-9]{2,6}\\.[0-9]{2,5}$/.test(t.replace(/,/g, ''))) {
                                    let val = parseFloat(t.replace(/,/g, ''));
                                    // Ignorar saldo de cuenta conocido y porcentajes
                                    if (val > 1.0 && val !== 100.0 && val !== 622.0) {
                                        // Verificar si está en la zona de trading o gráfico
                                        let isHeader = el.closest('header, nav, [class*="balance"], [class*="user"], [class*="profile"]');
                                        if (!isHeader) {
                                            info.candidates.push({ val: val, tag: el.tagName, cls: el.className });
                                            if (!info.price) {
                                                info.price = val;
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // 3. Payout
                        let payEl = document.querySelector('[data-test="deal-payout"], [class*="payout-value"]');
                        if (payEl) {
                            let pm = payEl.innerText.match(/([0-9]{2})/);
                            if (pm) info.payout = parseInt(pm[1]);
                        }

                        return info;
                    }""")

                    if info.get("asset"):
                        self.current_asset = info["asset"]
                    if info.get("payout"):
                        self.current_payout = info["payout"]

                    detected_price = info.get("price", 0)
                    if detected_price > 0 and detected_price != 622.0:
                        self.register_tick(detected_price, now)

                    # Reporte cada 6 segundos en consola y log
                    if time.time() - last_status >= 6:
                        last_status = time.time()
                        all_candles = self.candles + ([self.current_candle] if self.current_candle else [])
                        closes = [c["close"] for c in all_candles if "close" in c]
                        
                        if closes:
                            ema35 = calculate_ema_candles(closes, 35)
                            ema100 = calculate_ema_candles(closes, 100)
                            rsi7 = calculate_rsi_candles(closes, 7)
                            log_msg(f"📊 {self.current_asset} | Precio Real: {self.current_price:.4f} | Velas 1M: {len(closes)} | EMA35: {ema35:.4f} | EMA100: {ema100:.4f} | RSI7: {rsi7:.1f}")
                        else:
                            log_msg(f"🔍 Conectando con gráfico: {self.current_asset} (Precio detectado: {detected_price}) | Candidatos: {len(info.get('candidates', []))}")

                    # EVALUACIÓN SAGRADA AL SEGUNDO :50 (Manual Maestro)
                    if 49 <= now.second <= 52 and now.minute != self.last_alert_minute:
                        self.last_alert_minute = now.minute

                        all_candles = self.candles + ([self.current_candle] if self.current_candle else [])
                        closes = [c["close"] for c in all_candles if "close" in c]

                        if self.current_price > 0 and len(closes) >= 3:
                            ema_35 = calculate_ema_candles(closes, 35)
                            ema_100 = calculate_ema_candles(closes, 100)
                            rsi_7 = calculate_rsi_candles(closes, 7)

                            recent = all_candles[-30:]
                            highs = [c["high"] for c in recent if "high" in c]
                            lows = [c["low"] for c in recent if "low" in c]
                            swing_high = max(highs) if highs else self.current_price * 1.002
                            swing_low = min(lows) if lows else self.current_price * 0.998

                            trend_str = "ALCISTA (Solo Compras)" if ema_35 > ema_100 else "BAJISTA (Solo Ventas)"

                            log_msg(f"\n{'='*65}")
                            log_msg(f"🎯 EVALUACIÓN SEGUNDO :50 EN {self.current_asset}")
                            log_msg(f"   Precio Real: {self.current_price:.4f}")
                            log_msg(f"   Tendencia EMAs: {trend_str} (EMA35: {ema_35:.4f} | EMA100: {ema_100:.4f})")
                            log_msg(f"   RSI 7 (Velas 1M): {rsi_7:.1f} | Fibonacci: Techo={swing_high:.4f} Suelo={swing_low:.4f}")

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
                                log_msg(f"🚨 ¡CONFLUENCIA SNIPER CONFIRMADA! {sig_type} en {level_name} ({ref_p:.4f})")
                                trigger_sniper_signal(
                                    signal_type=sig_type,
                                    asset=self.current_asset,
                                    price=ref_p,
                                    level_name=level_name,
                                    payout=self.current_payout
                                )
                            else:
                                log_msg("ℹ️ Sin confluencia perfecta en este minuto. Capital 100% protegido.")
                            log_msg(f"{'='*65}\n")

                    time.sleep(0.5)

                except KeyboardInterrupt:
                    log_msg("\n[!] Bot detenido manualmente.")
                    break
                except Exception as e:
                    time.sleep(1)

if __name__ == "__main__":
    reader = DiagnosedOlympReader()
    reader.start()
