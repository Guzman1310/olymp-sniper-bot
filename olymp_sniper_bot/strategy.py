"""
Motor Matemático y Lógica Sniper:
- Cálculo de Niveles de Fibonacci (0, 0.236, 0.382, 0.5, 0.618, 1.0)
- Cálculo de EMAs (35 y 100) y su pendiente
- Detección de zonas Golden Zone (0.5 y 0.618)
- Filtro Anticascada (mínimo de rechazo o no operar contra 3+ velas continuas)
"""
from typing import List, Dict, Optional, Tuple

class SniperStrategy:
    def __init__(self, fibo_tolerance_pct: float = 0.0008):
        self.fibo_tolerance_pct = fibo_tolerance_pct

    def calculate_fibonacci(self, swing_high: float, swing_low: float, trend: str) -> Dict[str, float]:
        """
        Calcula los niveles de Fibonacci exactos.
        trend: 'DOWN' (impulso bajista: 1 arriba en el High, 0 abajo en el Low)
        trend: 'UP' (impulso alcista: 1 abajo en el Low, 0 arriba en el High)
        """
        diff = swing_high - swing_low
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
        candles: List[Dict[str, float]], # Cada vela: {'open', 'high', 'low', 'close'}
        ema_35: float,
        ema_100: float,
        rsi_7: float,
        swing_high: float,
        swing_low: float
    ) -> Optional[Tuple[str, str, float]]:
        """
        Evalúa si se cumplen el 100% de las condiciones Sniper.
        Retorna: (Tipo_Senal, Nivel_Clave, Precio_Referencia) o None
        """
        # 1. Determinación de la Tendencia por EMAs
        is_downtrend = ema_35 < ema_100
        is_uptrend = ema_35 > ema_100
        
        # 2. Filtro de Pendiente (distancia mínima de separación entre EMAs)
        ema_gap = abs(ema_35 - ema_100) / current_price
        if ema_gap < 0.0001:
            # EMAs pegadas o planas -> Lateralización -> NO OPERAR
            return None

        # 3. Cálculo de Fibonacci
        trend_str = "DOWN" if is_downtrend else "UP"
        fibo = self.calculate_fibonacci(swing_high, swing_low, trend_str)
        
        # 4. Filtro Anticascada en las últimas 3 velas cerradas
        if len(candles) >= 3:
            last_3 = candles[-3:]
            greens = sum(1 for c in last_3 if c['close'] > c['open'])
            reds = sum(1 for c in last_3 if c['close'] < c['open'])
        else:
            greens, reds = 0, 0

        # CASO 1: VENTA (Tendencia Bajista)
        if is_downtrend:
            # El precio debe haber subido a retroceder (Pullback)
            # Zonas sniper: Fibo 0.5, Fibo 0.618 o toque directo a la EMA 35
            golden_50 = fibo["0.5"]
            golden_618 = fibo["0.618"]
            
            # Tolerancia de proximidad
            at_ema35 = abs(current_price - ema_35) / current_price <= self.fibo_tolerance_pct
            at_05 = abs(current_price - golden_50) / current_price <= self.fibo_tolerance_pct
            at_618 = abs(current_price - golden_618) / current_price <= self.fibo_tolerance_pct

            # Condición de gatillo: precio tocando la resistencia
            if at_ema35 or at_05 or at_618:
                # Si vienen 3 velas verdes con fuerza sin mecha, no entrar al choque
                if greens >= 3 and len(candles) > 0:
                    current_candle = candles[-1]
                    # Debe haber mecha superior de rechazo
                    wick_top = current_candle['high'] - max(current_candle['open'], current_candle['close'])
                    body = abs(current_candle['close'] - current_candle['open'])
                    if wick_top < (body * 0.3):
                        return None # Cascado alcista sin freno

                level_desc = "EMA 35" if at_ema35 else ("Fibo 0.618" if at_618 else "Fibo 0.5")
                return ("VENTA", level_desc, current_price)

        # CASO 2: COMPRA (Tendencia Alcista)
        elif is_uptrend:
            golden_50 = fibo["0.5"]
            golden_618 = fibo["0.618"]
            
            at_ema35 = abs(current_price - ema_35) / current_price <= self.fibo_tolerance_pct
            at_05 = abs(current_price - golden_50) / current_price <= self.fibo_tolerance_pct
            at_618 = abs(current_price - golden_618) / current_price <= self.fibo_tolerance_pct

            if at_ema35 or at_05 or at_618:
                if reds >= 3 and len(candles) > 0:
                    current_candle = candles[-1]
                    # Debe haber mecha inferior de rechazo
                    wick_bottom = min(current_candle['open'], current_candle['close']) - current_candle['low']
                    body = abs(current_candle['close'] - current_candle['open'])
                    if wick_bottom < (body * 0.3):
                        return None # Cascada bajista sin freno

                level_desc = "EMA 35" if at_ema35 else ("Fibo 0.618" if at_618 else "Fibo 0.5")
                return ("COMPRA", level_desc, current_price)

        return None
