import requests
import os
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_IDS, MIN_PAYOUT_PERCENTAGE

def send_telegram_alert(signal_type: str, asset: str, price: float, level_name: str, payout: int = 85):
    """
    Envía una alerta formateada con filtro de rentabilidad a Rafael y Eduardo.
    """
    if payout < MIN_PAYOUT_PERCENTAGE:
        return

    emoji = "🟢 COMPRA (ARRIBA)" if "COMPRA" in signal_type.upper() else "🔴 VENTA (ABAJO)"
    
    text = (
        f"🎯 *¡ALERTA SNIPER EQUIPO!*\n\n"
        f"📊 *Activo:* `{asset}`\n"
        f"💰 *Retorno:* `{payout}%` *(Filtro >= 85% Aprobado)*\n"
        f"⚡ *Acción:* *{emoji}*\n"
        f"💵 *Importe:* `$1.00 USD`\n"
        f"⏱ *Temporalidad:* `1m (60 seg)`\n"
        f"📍 *Zona Clave:* `{level_name}` ({price})\n"
        f"⏳ *Gatillo:* Entrar en el segundo `:00` de la nueva vela.\n\n"
        f"⚠️ _Filtro Anticascada verificado. No persigan si el precio ya se alejó._"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"[Error enviando a {chat_id}]: {e}")

def trigger_sniper_signal(signal_type: str, asset: str, price: float, level_name: str, payout: int = 85):
    """
    Dispara la señal al equipo si cumple con el filtro de pago.
    Compatible con entornos Cloud Linux (GitHub Actions / Render).
    """
    if payout < MIN_PAYOUT_PERCENTAGE:
        return
        
    print(f"\n==========================================")
    print(f"[DISPARO EQUIPO]: {signal_type} en {asset} ({payout}%) | Zona: {level_name} ({price})")
    print(f"==========================================\n")
    
    # En la nube envía directamente a Telegram (Linux no tiene altavoces de PC)
    send_telegram_alert(signal_type, asset, price, level_name, payout)
