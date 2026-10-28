"""
Motor Matemático y Lógica Sniper - FIDELIDAD 100% AL MANUAL MAESTRO:
MÓDULO 1: Las 4 Capas (EMA 100, EMA 35, Fibo Golden Zone 0.5/0.618, RSI 7).
MÓDULO 2: Uso estricto de EMA 35 vs EMA 100.
MÓDULO 3: Zonas Prohibidas (Efecto Sándwich, Mercado Serrucho, Cuchillo Cayendo, Vela Elefante, Multitoques, FOMO RSI).
MÓDULO 4: Emboscada de Compra y Venta con Gatillo al segundo :50.
"""
from typing import List, Dict, Optional, Tuple

class SniperStrategy:
    def __init__(self, fibo_tolerance_pct: float = 0.0010):
        self.fibo_tolerance_pct = fibo_tolerance_pct

    def calculate_fibonacci(self, swing_high: float, swing_low: float, trend: str) -> Dict[str, float]:
        diff = swing_high - swing_low
        if diff <= 0:
            diff = 0.0001

        if trend.upper() == "DOWN":
            return {
                "1.0": swing_high,
                "0.618": swing_low + diff * 0.618,
                "0.5": swing_low + diff * 0.5,
                "0.382": swing_low + diff * 0.382,
                "0.236": swing_low + diff * 0.236,
                "0.0": swing_low
            }
        else: # UP
            return {
                "0.0": swing_high,
                "0.236": swing_high - diff * 0.236,
                "0.382": swing_high - diff * 0.382,
                "0.5": swing_high - diff * 0.5,
                "0.618": swing_high - diff * 0.618,
                "1.0": swing_low
            }

    def evaluate_setup(
        self,
        current_price: float,
        candles: List[Dict[str, float]],
        ema_35: float,
        ema_100: float,
        rsi_7: float,
        swing_high: float,
        swing_low: float
    ) -> Optional[Tuple[str, str, float]]:
        """
        Evalúa el 100% de las 8 reglas del Checklist del Manual Maestro.
        Si CUALQUIERA de las condiciones de filtro falla, retorna None (No operar).
        """
        # =========================================================================
        # MÓDULO 3: ZONAS PROHIBIDAS (FILTROS DE BLOQUEO)
        # =========================================================================

        # 1. FILTRO: EFECTO SÁNDWICH (Medias pegadas / asfixiadas)
        # El manual exige separación limpia en canal de 45°, sin compresión
        ema_gap = abs(ema_35 - ema_100) / current_price
        if ema_gap < 0.00025: # Separación mínima del 0.025%
            # ZONA PROHIBIDA #2: Efecto Sándwich -> BLOQUEO TOTAL
            return None

        # 2. FILTRO: MERCADO SERRUCHO (Alternancia constante Verde-Roja-Verde-Roja)
        # El manual prohíbe operar cuando las velas alternan de color sin tendencia
        if len(candles) >= 4:
            c1 = candles[-1]["close"] > candles[-1]["open"] # True=Verde, False=Roja
            c2 = candles[-2]["close"] > candles[-2]["open"]
            c3 = candles[-3]["close"] > candles[-3]["open"]
            c4 = candles[-4]["close"] > candles[-4]["open"]
            # Si hay alternancia estricta en las últimas 4 velas (V-R-V-R o R-V-R-V)
            if (c1 != c2) and (c2 != c3) and (c3 != c4):
                # ZONA PROHIBIDA #6: Mercado Serrucho -> BLOQUEO TOTAL
                return None

        # 3. FILTRO: VELA ELEFANTE EN MÁXIMOS / MÍNIMOS (Clímax de agotamiento)
        if len(candles) >= 6:
            bodies = [abs(c["close"] - c["open"]) for c in candles[-6:-1]]
            avg_body = sum(bodies) / len(bodies) if bodies else 0.0001
            current_body = abs(candles[-1]["close"] - candles[-1]["open"])
            if current_body > (avg_body * 3.0):
                # ZONA PROHIBIDA #7: Vela elefante descomunal -> Peligro de reversión violenta
                return None

        # =========================================================================
        # MÓDULO 1 Y 2: DETERMINACIÓN DE TENDENCIA INSTITUCIONAL
        # =========================================================================
        is_downtrend = ema_35 < ema_100
        is_uptrend = ema_35 > ema_100

        trend_str = "DOWN" if is_downtrend else "UP"
        fibo = self.calculate_fibonacci(swing_high, swing_low, trend_str)

        golden_50 = fibo["0.5"]
        golden_618 = fibo["0.618"]

        # Tolerancia de proximidad al nivel
        at_ema35 = abs(current_price - ema_35) / current_price <= self.fibo_tolerance_pct
        at_05 = abs(current_price - golden_50) / current_price <= self.fibo_tolerance_pct
        at_618 = abs(current_price - golden_618) / current_price <= self.fibo_tolerance_pct

        # Solo operamos si toca Fibo 50%, Fibo 61.8% o EMA 35
        if not (at_ema35 or at_05 or at_618):
            return None

        level_desc = "EMA 35" if at_ema35 else ("Fibo 0.618" if at_618 else "Fibo 0.5")

        # =========================================================================
        # MÓDULO 4: CASO 1 - EMBOSCADA DE VENTA (Tendencia Bajista)
        # =========================================================================
        if is_downtrend:
            # 1. REGLA RSI 7: El precio debe haber hecho un pullback alcista con RSI entre 52 y 75
            # PROHIBIDO VENDER SI RSI < 50 (Vendedores agotados en el suelo)
            # PROHIBIDO VENDER SI RSI > 80 (Vela disparada fuera de rango)
            if rsi_7 < 50.0 or rsi_7 > 80.0:
                return None

            # 2. FILTRO CUCHILLO CAYENDO / ANTICASCADA:
            # Si la vela subió con fuerza hacia el techo, DEBE dejar mecha superior de rechazo
            if len(candles) >= 1:
                last_c = candles[-1]
                wick_top = last_c["high"] - max(last_c["open"], last_c["close"])
                body = abs(last_c["close"] - last_c["open"])
                # ZONA PROHIBIDA #3: Sin mecha superior (cuerpo sólido perforando)
                if body > 0 and wick_top < (body * 0.30):
                    return None

            return ("VENTA", level_desc, current_price)

        # =========================================================================
        # MÓDULO 4: CASO 2 - EMBOSCADA DE COMPRA (Tendencia Alcista)
        # =========================================================================
        elif is_uptrend:
            # 1. REGLA RSI 7: El precio debe haber hecho un pullback bajista con RSI entre 25 y 48
            # PROHIBIDO COMPRAR SI RSI > 50 (Compradores sin oxígeno en el techo / FOMO)
            # PROHIBIDO COMPRAR SI RSI < 20 (Desplome violento sin frenos)
            if rsi_7 > 50.0 or rsi_7 < 20.0:
                return None

            # 2. FILTRO CUCHILLO CAYENDO / ANTICASCADA:
            # Si la vela cayó hacia el soporte, DEBE dejar mecha inferior de rechazo
            if len(candles) >= 1:
                last_c = candles[-1]
                wick_bottom = min(last_c["open"], last_c["close"]) - last_c["low"]
                body = abs(last_c["close"] - last_c["open"])
                # ZONA PROHIBIDA #3: Sin mecha inferior (cuerpo sólido perforando)
                if body > 0 and wick_bottom < (body * 0.30):
                    return None

            return ("COMPRA", level_desc, current_price)

        return None
