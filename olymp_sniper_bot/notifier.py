import requests
import pyttsx3
import threading
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_IDS, MIN_PAYOUT_PERCENTAGE

def send_telegram_alert(signal_type: str, asset: str, price: float, level_name: str, payout: int = 85):
    """
    Envía una alerta formateada con filtro de rentabilidad a Rafael y Eduardo.
    """
    # Filtro estricto de pago del broker (>= 85%)
    if payout < MIN_PAYOUT_PERCENTAGE:
        print(f"[FILTRADO]: {asset} tiene pago de {payout}%, menor al 85% requerido. Descartado.")
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

def speak_alert(text: str):
    """
    Reproduce la alerta por voz en español en la PC si está activa.
    """
    def _speak():
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            for v in voices:
                if "spanish" in v.name.lower() or "es" in v.id.lower() or "helena" in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break
            engine.setProperty('rate', 170)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            pass
            
    threading.Thread(target=_speak, daemon=True).start()

def trigger_sniper_signal(signal_type: str, asset: str, price: float, level_name: str, payout: int = 85):
    """
    Dispara la señal al equipo si cumple con el filtro de pago.
    """
    if payout < MIN_PAYOUT_PERCENTAGE:
        return
        
    print(f"\n==========================================")
    print(f"[DISPARO EQUIPO]: {signal_type} en {asset} ({payout}%) | Zona: {level_name} ({price})")
    print(f"==========================================\n")
    
    speech_text = f"Atento equipo. {signal_type} en {asset} al 85 por ciento. Entren al segundo cero."
    speak_alert(speech_text)
    send_telegram_alert(signal_type, asset, price, level_name, payout)
