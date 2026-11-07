# Configuracoes do envio para a API do backend (piADS04). Vai para a placa junto
# com o main.py. A CHAVE da placa NAO fica aqui: fica no wifi_config.py (fora do Git),
# na variavel DEVICE_KEY.

# Endereco base da API (com https:// e sem barra no final).
API_URL = "https://projeto-integrador-time1.onrender.com/api/v1"

# Identificador desta placa no backend (o mesmo cadastrado em /devices).
DEVICE_UID = "VSF-001"

# De quanto em quanto tempo uma leitura entra na fila (ms). O plano sugere 5 min;
# para acompanhar em tempo real na apresentacao, 30 s funciona bem.
REGISTRO_INTERVALO_MS = 30_000

# De quanto em quanto tempo a placa tenta enviar o que esta na fila (ms).
ENVIO_INTERVALO_MS = 30_000

# De quanto em quanto tempo a placa pergunta qual e a viagem ativa (ms).
CONFIG_INTERVALO_MS = 60_000

# Maximo de leituras por lote (a API aceita ate 200).
LOTE_MAXIMO = 50

# Maximo de leituras guardadas na fila. Passou disso (muito tempo sem rede),
# as mais antigas sao descartadas para nao lotar a flash.
FILA_MAXIMA = 3000

# Tempo maximo de espera por uma resposta da API (s). O Render gratuito pode
# levar ~1 min para "acordar"; se estourar, a placa tenta de novo depois.
TIMEOUT_HTTP_S = 30

# Tempo maximo sem Wi-Fi antes de procurar as redes de novo (ms).
RECONEXAO_INTERVALO_MS = 60_000
