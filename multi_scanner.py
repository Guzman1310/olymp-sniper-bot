"""
Scanner Multiactivo 24/7 para el Equipo (Rafael & Eduardo).
Monitorea continuamente la lista completa de los 22 mercados con rotación equitativa:
- Metal Composite Index, Oil Composite Index, Europe, Asia, Crypto, BrasIndex,
  Cafeina, Compound, Latam, Stable Tick, Bitcoin OTC, Ethereum OTC, Solana OTC,
  BNB OTC, Dogecoin OTC, Ripple OTC, Shiba OTC, Litecoin OTC, Pepe OTC, Gold OTC, Silver OTC.
"""
import time
import datetime
from cloud_runner import OriginalTimingScanner

if __name__ == "__main__":
    print("="*65)
    print("🚀 SCANNER SNIPER MULTIACTIVO GITHUB ACTIONS (24/7 ACTIVO)")
    print("   Escaneando los 22 mercados completos con rotación equitativa")
    print("   Rafael Guzmán & Eduardo Rivera")
    print("="*65)
    scanner = OriginalTimingScanner()
    scanner.run_loop()
