import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_IDS, MIN_PAYOUT_PERCENTAGE

def send_telegram_alert(signal_type: str, asset: str, price: float, level_name: str, payout: int = 85):
    """
    Envía una alerta con instrucción visual ULTRA-CLARA de la dirección exacta:
    - 🟢 COMPRA (BOTÓN VERDE / ARRIBA)
    - 🔴 VENTA (BOTÓN ROJO / ABAJO)
    """
    if payout < MIN_PAYOUT_PERCENTAGE:
        return

    is_buy = "COMPRA" in signal_type.upper()
    
    if is_buy:
        action_header = "🟢 ENTRADA: COMPRA (ARRIBA)"
        button_instruction = "🟩 PRESIONAR BOTÓN VERDE (ARRIBA)"
        direction_desc = "📈 Tendencia Alcista (Rebote sobre soporte / EMA 35)"
    else:
        action_header = "🔴 ENTRADA: VENTA (ABAJO)"
        button_instruction = "🟥 PRESIONAR BOTÓN ROJO (ABAJO)"
        direction_desc = "📉 Tendencia Bajista (Rechazo en resistencia / EMA 35)"

    text = (
        f"🎯 *¡ALERTA SNIPER EQUIPO!*\n\n"
        f"📊 *Activo:* `{asset}`\n"
        f"💰 *Retorno:* `{payout}%`\n\n"
        f"⚡ *DIRECCIÓN:* *{action_header}*\n"
        f"👉 *ACCIÓN:* *{button_instruction}*\n\n"
        f"💵 *Importe:* `$1.00 USD`\n"
        f"⏱ *Temporalidad:* `1m (60 seg)`\n"
        f"📍 *Zona Clave:* `{level_name}` ({price:.2f})\n"
        f"ℹ️ *Estructura:* _{direction_desc}_\n\n"
        f"⏳ *GATILLO:* Entrar al segundo exacto `:00` de la nueva vela."
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
    if payout < MIN_PAYOUT_PERCENTAGE:
        return
        
    print(f"\n==========================================")
    print(f"[DISPARO EQUIPO]: {signal_type} en {asset} ({payout}%) | Zona: {level_name} ({price:.2f})")
    print(f"==========================================\n")
    
    send_telegram_alert(signal_type, asset, price, level_name, payout)
