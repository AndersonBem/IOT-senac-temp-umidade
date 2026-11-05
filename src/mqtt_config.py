# Configuracoes do MQTT. Vai para a placa junto com o main.py.

# Broker publico e gratuito. Alternativa: "test.mosquitto.org".
# Qualquer pessoa consegue ler o que for publicado: nao envie dado sensivel.
MQTT_BROKER = "broker.hivemq.com"

# Porta padrao do MQTT sem criptografia (8883 = com TLS).
MQTT_PORT = 1883

# Broker publico: deixe None.
MQTT_USUARIO = None
MQTT_SENHA = None

# IMPORTANTE: o broker e publico, entao use um nome UNICO do seu grupo
# para nao misturar com dados de outras pessoas.
TOPICO_BASE = "senac/grupo-wendell/ambiente"

TOPICO_TEMPERATURA = TOPICO_BASE + "/temperatura"   # ex.: "28"
TOPICO_UMIDADE = TOPICO_BASE + "/umidade"           # ex.: "62"
TOPICO_DADOS = TOPICO_BASE + "/dados"               # ex.: {"temperatura":28,"umidade":62}
TOPICO_STATUS = TOPICO_BASE + "/status"             # "online" ou "offline"

# De quantos em quantos milissegundos publicar.
MQTT_INTERVALO_MS = 5_000

# Sem falar com o broker por esse tempo, ele publica "offline" (Last Will).
MQTT_KEEPALIVE_S = 60
