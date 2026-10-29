"""
Lector y Escáner Multiactivo Real de Olymp Trade (Opción 2: Rotador 22 Activos).
- Rota automáticamente entre los activos de la Watchlist (85%+ payout).
- Lee el precio real mediante Gancho de Canvas (fillText) y DOM en tiempo real.
- Calcula EMA 35, EMA 100, RSI 7 y Fibo de 1 Minuto según el Manual Maestro.
- Alerta precisa al segundo :50 para entrar al :00 de la nueva vela.
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
from config import MIN_PAYOUT_PERCENTAGE

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

ROTATION_MARKETS = [
    "Asia Composite Index",
    "Europe Composite Index",
    "Metal Composite Index",
    "Oil Composite Index",
    "Crypto Composite Index",
    "BrasIndex",
    "Cafeina Index",
    "Compound Index",
    "Latam Index",
    "Bitcoin OTC",
    "Ethereum OTC",
    "Solana OTC",
    "BNB OTC",
    "Dogecoin OTC",
    "Ripple OTC",
    "Shiba OTC",
    "Pepe OTC",
    "Litecoin OTC"
]

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

class MultiActiveOlympSniper:
    def __init__(self):
        self.strategy = SniperStrategy(fibo_tolerance_pct=0.0010)
        self.last_alert_minute = -1
        self.candles_by_asset: Dict[str, List[Dict[str, float]]] = {}
        self.current_minute = -1
        self.current_price: float = 0.0
        self.current_asset: str = "Asia Composite Index"
        self.current_payout: int = 85
        self.market_index = 0
        self.last_switch_time = 0

    def register_tick(self, asset: str, price: float, now: datetime.datetime):
        if price <= 100.0 or price == 622.0 or price == 22.50:
            return
        self.current_price = price
        minute = now.minute

        if asset not in self.candles_by_asset:
            self.candles_by_asset[asset] = []

        candles = self.candles_by_asset[asset]

        if not candles or candles[-1].get("minute") != minute:
            candles.append({
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "minute": minute,
                "time": int(now.timestamp())
            })
            if len(candles) > 120:
                candles.pop(0)
        else:
            curr = candles[-1]
            curr["high"] = max(curr["high"], price)
            curr["low"] = min(curr["low"], price)
            curr["close"] = price

    def switch_to_next_asset(self, page) -> str:
        self.market_index = (self.market_index + 1) % len(ROTATION_MARKETS)
        target_asset = ROTATION_MARKETS[self.market_index]
        log_msg(f"🔄 Rotando escáner hacia: {target_asset} ({self.market_index + 1}/{len(ROTATION_MARKETS)})...")

        try:
            # 1. Click en el selector de activos actual
            asset_btn = page.query_selector('[data-test*="asset"], [class*="asset-name"], [class*="asset-select"], [class*="pair-name"]')
            if asset_btn:
                asset_btn.click()
                time.sleep(0.8)

                # 2. Escribir nombre en el buscador
                search_input = page.query_selector('input[type="text"], input[placeholder*="Buscar"], input[placeholder*="Search"]')
                if search_input:
                    search_input.fill("")
                    search_input.fill(target_asset)
                    time.sleep(0.8)

                    # 3. Click en el resultado coincidente
                    match = page.query_selector(f'text="{target_asset}"')
                    if match:
                        match.click()
                        time.sleep(1.5)
                        self.current_asset = target_asset
                        self.last_switch_time = time.time()
                        log_msg(f"✅ Gráfico cambiado con éxito a: {target_asset}")
                        return target_asset

            # Si no encontró o quedó abierto el modal, cerrar con Escape
            page.keyboard.press("Escape")
        except Exception as e:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass

        return self.current_asset

    def start(self):
        log_msg("="*65)
        log_msg("🎯 ESCÁNER MULTIACTIVO EN VIVO (OPCIÓN 2: 18 MERCADOS 85%+)")
        log_msg("   Calcula EMA 35, EMA 100, RSI 7 y Fibo de 1 Minuto")
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

            # Gancho de Canvas para capturar precio dibujado en vivo
            canvas_hook_script = """
            (() => {
                window.__last_chart_price = 0;
                const hookText = function(text) {
                    if (text) {
                        let str = String(text).trim();
                        let m = str.match(/([0-9]{3,6}\\.[0-9]{2,5})/);
                        if (m) {
                            let val = parseFloat(m[1]);
                            if (val > 100.0 && val !== 622.0 && val !== 22.50) {
                                window.__last_chart_price = val;
                            }
                        }
                    }
                };

                const origFillText = CanvasRenderingContext2D.prototype.fillText;
                CanvasRenderingContext2D.prototype.fillText = function(text, x, y, maxW) {
                    hookText(text);
                    return origFillText.apply(this, arguments);
                };

                const origStrokeText = CanvasRenderingContext2D.prototype.strokeText;
                CanvasRenderingContext2D.prototype.strokeText = function(text, x, y, maxW) {
                    hookText(text);
                    return origStrokeText.apply(this, arguments);
                };
            })();
            """
            page.add_init_script(canvas_hook_script)

            log_msg("[+] Conectando a Olymp Trade...")
            page.goto("https://olymptrade.com/platform", timeout=60000)
            time.sleep(6)

            try:
                page.evaluate(canvas_hook_script)
            except Exception:
                pass

            log_msg("[✓] Conexión establecida con la ventana de Olymp Trade.")
            log_msg("[*] Iniciando ciclo multiactivo sobre los 18 mercados oficiales...\n")

            self.last_switch_time = time.time()
            last_status = 0

            while True:
                try:
                    now = datetime.datetime.now()

                    # 1. Leer precio en tiempo real del Canvas o DOM
                    info = page.evaluate("""() => {
                        let info = { price: window.__last_chart_price || 0, asset: '', payout: 85 };
                        
                        let assetEl = document.querySelector('[data-test*="asset"], [class*="asset-name"], [class*="asset-select"], [class*="pair-name"]');
                        if (assetEl) {
                            info.asset = assetEl.innerText.trim();
                        }

                        if (!info.price) {
                            let els = Array.from(document.querySelectorAll('*'));
                            for (let el of els) {
                                if (el.closest('header, nav, [class*="balance"]')) continue;
                                let m = (el.textContent || '').trim().match(/^([0-9]{3,6}\\.[0-9]{2,5})$/);
                                if (m) {
                                    let v = parseFloat(m[1]);
                                    if (v > 100.0 && v !== 622.0 && v !== 22.50) {
                                        info.price = v;
                                        break;
                                    }
                                }
                            }
                        }

                        let payEl = document.querySelector('[data-test="deal-payout"], [class*="payout-value"]');
                        if (payEl) {
                            let pm = payEl.innerText.match(/([0-9]{2})/);
                            if (pm) info.payout = parseInt(pm[1]);
                        }

                        return info;
                    }""")

                    if info.get("asset") and len(info["asset"]) > 2:
                        self.current_asset = info["asset"]
                    if info.get("payout"):
                        self.current_payout = info["payout"]

                    detected_price = info.get("price", 0)
                    if detected_price > 100.0:
                        self.register_tick(self.current_asset, detected_price, now)

                    # Reporte de estado en pantalla cada 6 segundos
                    if time.time() - last_status >= 6:
                        last_status = time.time()
                        candles = self.candles_by_asset.get(self.current_asset, [])
                        closes = [c["close"] for c in candles if "close" in c]

                        if closes and self.current_price > 0:
                            ema35 = calculate_ema_candles(closes, 35)
                            ema100 = calculate_ema_candles(closes, 100)
                            rsi7 = calculate_rsi_candles(closes, 7)
                            log_msg(f"📊 {self.current_asset} | Precio: {self.current_price:.4f} | Velas 1M: {len(closes)} | EMA35: {ema35:.4f} | EMA100: {ema100:.4f} | RSI7: {rsi7:.1f}")
                        else:
                            log_msg(f"🔍 Vigilando: {self.current_asset} (Precio en vivo: {detected_price}) | Payout: {self.current_payout}%")

                    # EVALUACIÓN SAGRADA AL SEGUNDO :50 (Manual Maestro)
                    if 49 <= now.second <= 52 and now.minute != self.last_alert_minute:
                        self.last_alert_minute = now.minute

                        candles = self.candles_by_asset.get(self.current_asset, [])
                        closes = [c["close"] for c in candles if "close" in c]

                        if self.current_price > 0 and len(closes) >= 3 and self.current_payout >= MIN_PAYOUT_PERCENTAGE:
                            ema_35 = calculate_ema_candles(closes, 35)
                            ema_100 = calculate_ema_candles(closes, 100)
                            rsi_7 = calculate_rsi_candles(closes, 7)

                            recent = candles[-30:]
                            highs = [c["high"] for c in recent if "high" in c]
                            lows = [c["low"] for c in recent if "low" in c]
                            swing_high = max(highs) if highs else self.current_price * 1.002
                            swing_low = min(lows) if lows else self.current_price * 0.998

                            trend_str = "ALCISTA (Solo Compras)" if ema_35 > ema_100 else "BAJISTA (Solo Ventas)"

                            log_msg(f"\n{'='*65}")
                            log_msg(f"🎯 EVALUACIÓN SEGUNDO :50 EN {self.current_asset}")
                            log_msg(f"   Precio Real: {self.current_price:.4f} | Payout: {self.current_payout}%")
                            log_msg(f"   Tendencia EMAs: {trend_str} (EMA35: {ema_35:.4f} | EMA100: {ema_100:.4f})")
                            log_msg(f"   RSI 7 (Velas 1M): {rsi_7:.1f} | Fibonacci: Techo={swing_high:.4f} Suelo={swing_low:.4f}")

                            setup = self.strategy.evaluate_setup(
                                current_price=self.current_price,
                                candles=candles,
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
                                log_msg("ℹ️ Sin confluencia en este minuto. Capital 100% protegido.")
                            log_msg(f"{'='*65}\n")

                    # ROTACIÓN AL SIGUIENTE ACTIVO: Tras el segundo :05 de cada minuto (da tiempo de evaluar al :50 y disparar al :00)
                    if 5 <= now.second <= 10 and (time.time() - self.last_switch_time) > 40:
                        self.switch_to_next_asset(page)

                    time.sleep(0.5)

                except KeyboardInterrupt:
                    log_msg("\n[!] Bot detenido manualmente.")
                    break
                except Exception as e:
                    time.sleep(1)

if __name__ == "__main__":
    scanner = MultiActiveOlympSniper()
    scanner.start()
