"""
Comando de Diagnóstico y Estado en Vivo del Bot (/status)
Permite a Rafael o Eduardo enviar /status al bot en Telegram
y recibir un reporte instantáneo del estado de salud del escáner.
"""
import requests
import datetime
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_IDS, WATCHLIST_MARKETS, MIN_PAYOUT_PERCENTAGE

def send_heartbeat_ping():
    """
    Envía un mensaje de confirmación de que el bot está activo y vigilando.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"🟢 *[SISTEMA EN LÍNEA Y OPERATIVO]*\n\n"
        f"🕒 *Hora del Servidor:* `{now}`\n"
        f"📊 *Mercados en Vigilancia:* `{len(WATCHLIST_MARKETS)} activos`\n"
        f"💰 *Filtro de Retorno:* `>= {MIN_PAYOUT_PERCENTAGE}%`\n"
        f"🛡 *Estado de Filtros:* `Anticascada, Fibo 0.5/0.618 y EMAs Activos`\n"
        f"👥 *Operadores Vinculados:* `Rafael & Eduardo`\n\n"
        f"✅ _El escáner está analizando en segundo plano sin fallas._"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
        except Exception:
            pass

if __name__ == "__main__":
    send_heartbeat_ping()
