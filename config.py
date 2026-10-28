# Lista de control de acceso (Solo las personas con este Chat ID recibirán alertas)
TELEGRAM_TOKEN = "9270334261:AAEkwgtQsG0cc034mcMx8L_1IGtfFhy4dZk"

# LISTA BLANCA PRIVADA (WHITELIST)
# Si alguien más encuentra el bot e intenta usarlo, el bot lo ignora por completo.
TELEGRAM_CHAT_IDS = [
    "1028358282",  # Rafael Guzmán (Administrador)
    "7797844191"   # Eduardo Rivera (Operador)
]

# Gestión de Capital Estricta
DEFAULT_STAKE = 1.00  # $1.00 USD estricto por operación
TIMEFRAME = "1m"      # Opciones Fixed Time a 1 Minuto

# Filtro de Rentabilidad Mínima del Broker
MIN_PAYOUT_PERCENTAGE = 85  # Únicamente operar si el pago es >= 85%

# Tolerancia milimétrica para confluencia Fibo / EMA
FIBO_TOLERANCE = 0.05

# 22 MERCADOS OFICIALES
WATCHLIST_MARKETS = [
    "Metal Composite Index",
    "Oil Composite Index",
    "BNB OTC",
    "Bitcoin OTC",
    "Gold OTC",
    "Asia Composite Index",
    "BrasIndex",
    "Cafeina Index",
    "Compound Index",
    "Crypto Composite Index",
    "Dogecoin OTC",
    "Ethereum OTC",
    "Europe Composite Index",
    "Global Overview of Athletic Leagues Index",
    "Latam Index",
    "Pepe OTC",
    "Ripple OTC",
    "Shiba OTC",
    "Silver OTC",
    "Stable Tick Index",
    "Solana OTC",
    "Litecoin OTC"
]
