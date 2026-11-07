# Recursos de hardware do MicroPython.
from machine import Pin, RTC, SoftI2C, unique_id
 
# Bibliotecas do MicroPython.
import dht
import json
import network
import ntptime
import os
import socket
import ssd1306
import time
import requests
import ubinascii
from umqtt.simple import MQTTClient   # instalar: mpremote mip install umqtt.simple
 
# Credenciais mantidas fora do código principal.
from wifi_config import (
    WIFI_SSID,
    WIFI_PASSWORD,
    THINGSPEAK_WRITE_API_KEY,
)

# Lista de redes conhecidas: [("nome", "senha"), ...]. Se o wifi_config.py
# nao tiver REDES, usa so a rede WIFI_SSID/WIFI_PASSWORD de antes.
try:
    from wifi_config import REDES
except ImportError:
    REDES = [(WIFI_SSID, WIFI_PASSWORD)]

# Configuracoes do MQTT (broker, porta, topicos).
from mqtt_config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_USUARIO,
    MQTT_SENHA,
    TOPICO_TEMPERATURA,
    TOPICO_UMIDADE,
    TOPICO_DADOS,
    TOPICO_STATUS,
    MQTT_INTERVALO_MS,
    MQTT_KEEPALIVE_S,
)

# Configuracoes do envio para a API do backend (endereco, intervalos, tamanho do lote).
from api_config import (
    API_URL,
    DEVICE_UID,
    REGISTRO_INTERVALO_MS,
    ENVIO_INTERVALO_MS,
    CONFIG_INTERVALO_MS,
    LOTE_MAXIMO,
    FILA_MAXIMA,
    TIMEOUT_HTTP_S,
    RECONEXAO_INTERVALO_MS,
)

# Chave da placa (X-Device-Key) gerada no backend. Fica no wifi_config.py, fora do Git.
try:
    from wifi_config import DEVICE_KEY
except ImportError:
    DEVICE_KEY = None
 
 
# ============================================================
# CONFIGURAÇÃO DOS PINOS E DISPOSITIVOS
# ============================================================
 
# GPIO conectado ao pino DATA do DHT11.
DHT_PIN = 1
 
# GPIOs internos usados pelo OLED.
OLED_SDA_PIN = 5
OLED_SCL_PIN = 6
 
LED_AZUL_PIN = 3
LED_VERDE_PIN = 4
LED_VERMELHO_PIN = 7
 
TEMPERATURA_MINIMA = 0
TEMPERATURA_MAXIMA = 5
 
UMIDADE_MINIMA = 85
UMIDADE_MAXIMA = 95
 
# Configuração confirmada do OLED.
OLED_ADDRESS = 0x3C
OLED_WIDTH = 72
OLED_HEIGHT = 40
 
# Intervalo mínimo entre leituras do DHT11.
READ_INTERVAL_MS = 2_000
 
THINGSPEAK_INTERVAL_MS = 20_000
 
# Tempo máximo para conectar ao Wi-Fi.
WIFI_TIMEOUT_SECONDS = 30
 
# Porta HTTP usada pela API.
HTTP_PORT = 80

# ID unico desta placa no broker (dois clientes com o mesmo ID se derrubam).
CLIENT_ID = b"esp32c3-" + ubinascii.hexlify(unique_id())
 
 
# ============================================================
# INICIALIZAÇÃO DO HARDWARE
# ============================================================
 
# Cria o barramento I2C utilizado pelo OLED.
i2c = SoftI2C(
    sda=Pin(OLED_SDA_PIN),
    scl=Pin(OLED_SCL_PIN),
    freq=400_000,
)
 
# Inicializa o OLED.
oled = ssd1306.SSD1306_I2C(
    OLED_WIDTH,
    OLED_HEIGHT,
    i2c,
    addr=OLED_ADDRESS,
)
 
# Inicializa o sensor DHT11.
sensor = dht.DHT11(Pin(DHT_PIN))
led_azul = Pin(LED_AZUL_PIN, Pin.OUT, value=0)
led_verde = Pin(LED_VERDE_PIN, Pin.OUT, value=0)
led_vermelho = Pin(LED_VERMELHO_PIN, Pin.OUT, value=0)
 
 
# Últimos valores válidos obtidos do sensor.
ultima_temperatura = None
ultima_umidade = None
ultimo_envio_thingspeak_ms = time.ticks_ms() - THINGSPEAK_INTERVAL_MS
 
# Horário da última tentativa de leitura.
ultima_leitura_ms = time.ticks_ms() - READ_INTERVAL_MS

# Conexão MQTT atual (None = desconectado).
cliente_mqtt = None
ultimo_envio_mqtt_ms = time.ticks_ms() - MQTT_INTERVALO_MS

# Envio para a API: fila local, viagem ativa e controle de tempo.
ARQUIVO_FILA = "fila.jsonl"       # uma leitura por linha, em JSON
ARQUIVO_SEQUENCE = "sequence.txt" # ultimo sequence usado (sobrevive a reinicio)
viagem_ativa = None               # shipment_id informado pela API (/iot/config)
relogio_ok = False                # True depois de acertar o relogio (NTP ou API)
ultimo_registro_ms = time.ticks_ms() - REGISTRO_INTERVALO_MS
ultimo_envio_api_ms = time.ticks_ms() - ENVIO_INTERVALO_MS
ultima_config_ms = time.ticks_ms() - CONFIG_INTERVALO_MS
ultima_reconexao_ms = time.ticks_ms()
 
 
# ============================================================
# FUNÇÕES DO OLED
# ============================================================
 
def mostrar_mensagem(linha_1, linha_2="", linha_3=""):
    """Limpa o OLED e mostra até três linhas."""
 
    oled.fill(0)
    oled.text(linha_1, 0, 0)
    oled.text(linha_2, 0, 14)
    oled.text(linha_3, 0, 28)
    oled.show()
 
 
def mostrar_dados(temperatura, umidade):
    """Mostra temperatura e umidade no OLED."""
 
    oled.fill(0)
    oled.text("DHT11", 16, 0)
    oled.text(f"T: {temperatura} C", 0, 14)
    oled.text(f"U: {umidade} %", 0, 28)
    oled.show()
 
 
# ============================================================
# CONEXÃO WI-FI
# ============================================================
 
def tentar_rede(wifi, ssid, senha):
    """Tenta conectar em UMA rede. Devolve True se conseguiu."""

    if wifi.isconnected():
        wifi.disconnect()

    mostrar_mensagem("Wi-Fi", ssid[:9], "Conectando")
    print("Conectando ao Wi-Fi:", ssid)

    wifi.connect(ssid, senha)

    inicio = time.time()
    estado_led_azul = False

    while not wifi.isconnected():
        estado_led_azul = not estado_led_azul
        led_azul.value(estado_led_azul)

        status = wifi.status()
        tempo_decorrido = time.time() - inicio

        print("Wi-Fi status:", status, "| tempo:", tempo_decorrido, "s")

        if tempo_decorrido >= WIFI_TIMEOUT_SECONDS:
            print("Timeout em", ssid, "| status:", status)
            try:
                wifi.disconnect()
            except OSError:
                pass
            return False

        time.sleep_ms(500)

    return True


def conectar_wifi():
    """Procura as redes conhecidas (REDES) e conecta na de sinal mais forte."""

    wifi = network.WLAN(network.STA_IF)

    # Reinicializa a interface para limpar estados anteriores.
    wifi.active(False)
    time.sleep(1)
    wifi.active(True)

    wifi.config(reconnects=3, txpower=8.5)

    while True:
        mostrar_mensagem("Wi-Fi", "Procurando...")

        try:
            encontradas = wifi.scan()
        except OSError as erro:
            print("Falha no scan:", erro)
            encontradas = []

        # nome da rede -> melhor sinal (RSSI, mais perto de 0 = mais forte)
        sinais = {}
        for item in encontradas:
            try:
                nome = item[0].decode()
            except UnicodeError:
                continue
            sinais[nome] = max(sinais.get(nome, -127), item[3])

        # So as redes conhecidas que estao ao alcance, a mais forte primeiro.
        candidatas = [r for r in REDES if r[0] in sinais]
        candidatas.sort(key=lambda r: -sinais[r[0]])

        if not candidatas:
            print("Nenhuma rede conhecida por perto. Tentando de novo...")
            mostrar_mensagem("Wi-Fi", "Sem rede", "conhecida")
            time.sleep(5)
            continue

        for ssid, senha in candidatas:
            if tentar_rede(wifi, ssid, senha):
                ip = wifi.ifconfig()[0]

                print("Wi-Fi conectado!")
                print("Rede:", ssid)
                print("IP:", ip)
                print("RSSI:", wifi.status("rssi"), "dBm")

                mostrar_mensagem("Wi-Fi OK", ip)
                led_azul.value(1)
                return wifi


def atualizar_leds_status(wifi):
    agora = time.ticks_ms()
 
    pisca_alerta = 1 if agora % 1_000 < 500 else 0
    pulso_normal = 0 if agora % 5_000 < 250 else 1
 
    # Azul: Wi-Fi + MQTT. Pisca rápido se o Wi-Fi OU o MQTT estiver fora.
    if wifi.isconnected() and cliente_mqtt is not None:
        led_azul.value(pulso_normal)
    else:
        led_azul.value(pisca_alerta)
 
    # Verde: temperatura.
    if ultima_temperatura is None:
        led_verde.value(0)
    elif TEMPERATURA_MINIMA <= ultima_temperatura <= TEMPERATURA_MAXIMA:
        led_verde.value(pulso_normal)
    else:
        led_verde.value(pisca_alerta)
 
    # Vermelho: umidade.
    if ultima_umidade is None:
        led_vermelho.value(0)
    elif UMIDADE_MINIMA <= ultima_umidade <= UMIDADE_MAXIMA:
        led_vermelho.value(pulso_normal)
    else:
        led_vermelho.value(pisca_alerta)
 
 
# ============================================================
# LEITURA DO DHT11 E ENVIOS REMOTOS
# ============================================================
 
def atualizar_sensor():
    """Tenta obter uma nova medição."""
 
    global ultima_temperatura
    global ultima_umidade
    global ultima_leitura_ms
 
    agora = time.ticks_ms()
 
    if time.ticks_diff(agora, ultima_leitura_ms) < READ_INTERVAL_MS:
        return
 
    ultima_leitura_ms = agora
 
    try:
        sensor.measure()
 
        ultima_temperatura = sensor.temperature()
        ultima_umidade = sensor.humidity()
 
        print(
            f"Temperatura: {ultima_temperatura} C | "
            f"Umidade: {ultima_umidade} %"
        )
 
        mostrar_dados(
            ultima_temperatura,
            ultima_umidade,
        )
 
    except OSError as erro:
        print("Falha ao ler DHT11:", erro)
 
        if ultima_temperatura is None:
            mostrar_mensagem("Erro DHT11")
 
 
def enviar_thingspeak():
    global ultimo_envio_thingspeak_ms
 
    agora = time.ticks_ms()
 
    if time.ticks_diff(
        agora,
        ultimo_envio_thingspeak_ms,
    ) < THINGSPEAK_INTERVAL_MS:
        return
 
    if ultima_temperatura is None or ultima_umidade is None:
        return
 
    ultimo_envio_thingspeak_ms = agora
 
    url = (
        "https://api.thingspeak.com/update"
        f"?api_key={THINGSPEAK_WRITE_API_KEY}"
        f"&field1={ultima_temperatura}"
        f"&field2={ultima_umidade}"
    )
 
    resposta = None
 
    try:
        resposta = requests.get(url)
        entry_id = resposta.text
 
        if entry_id == "0":
            print("ThingSpeak recusou a atualização")
        else:
            print("ThingSpeak atualizado. Entry ID:", entry_id)
 
    except Exception as erro:
        print("Falha ao enviar ao ThingSpeak:", erro)
 
    finally:
        if resposta is not None:
            resposta.close()
 
 
# ============================================================
# ENVIO PARA A API DO BACKEND (fila local + lote)
# ============================================================
#
# Regras que o backend exige (docs/API.md do backend):
#   1. Toda leitura entra primeiro na FILA (arquivo na flash). Sem rede, nada se perde.
#   2. Cada leitura tem um `sequence` que nunca se repete, nem depois de reiniciar a placa.
#   3. `recorded_at` vai em UTC. Sem relogio certo, a placa nao registra.
#   4. So sai da fila o que a API confirmar (accepted_reading_sequences).


def agora_iso():
    """Hora atual em UTC no formato ISO 8601 (ex.: 2026-11-05T13:00:00Z)."""
    t = time.gmtime()
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % t[:6]


def relogio_valido():
    """O relogio da placa comeca em 2000 quando liga; antes de acertar, o ano e < 2025."""
    return time.gmtime()[0] >= 2025


def acertar_relogio_ntp():
    """Acerta o relogio pela internet (NTP, em UTC). Devolve True se conseguiu."""
    global relogio_ok
    try:
        ntptime.settime()
        relogio_ok = relogio_valido()
        print("[Relogio] NTP OK:", agora_iso())
    except Exception as erro:
        print("[Relogio] Falha no NTP:", erro)
    return relogio_ok


def acertar_relogio_pela_api(server_time):
    """Plano B: usa a hora que a API devolve em /iot/config (ex.: 2026-11-05T13:00:00.123Z)."""
    global relogio_ok
    try:
        data, hora = server_time.split("T")
        ano, mes, dia = [int(x) for x in data.split("-")]
        h, m, seg = hora.replace("Z", "").split(":")
        RTC().datetime((ano, mes, dia, 0, int(h), int(m), int(float(seg)), 0))
        relogio_ok = relogio_valido()
        print("[Relogio] Acertado pela API:", agora_iso())
    except Exception as erro:
        print("[Relogio] Falha ao usar a hora da API:", erro)


def proximo_sequence():
    """Le o ultimo sequence da flash, soma 1, grava de volta e devolve."""
    try:
        with open(ARQUIVO_SEQUENCE) as arquivo:
            ultimo = int(arquivo.read().strip() or 0)
    except (OSError, ValueError):
        ultimo = 0
    atual = ultimo + 1
    with open(ARQUIVO_SEQUENCE, "w") as arquivo:
        arquivo.write(str(atual))
    return atual


def substituir_fila(temporario):
    """Troca a fila pelo arquivo novo. Em alguns sistemas de arquivos o rename nao
    sobrescreve: nesse caso apaga a antiga e renomeia."""
    try:
        os.rename(temporario, ARQUIVO_FILA)
    except OSError:
        os.remove(ARQUIVO_FILA)
        os.rename(temporario, ARQUIVO_FILA)


def http(metodo, url, **opcoes):
    """requests com tempo limite. Versoes antigas do MicroPython nao aceitam `timeout`:
    nesse caso repete sem ele."""
    try:
        return metodo(url, timeout=TIMEOUT_HTTP_S, **opcoes)
    except TypeError:
        return metodo(url, **opcoes)


def tamanho_fila():
    total = 0
    try:
        with open(ARQUIVO_FILA) as arquivo:
            for _ in arquivo:
                total += 1
    except OSError:
        pass
    return total


def descartar_mais_antigas(quantas):
    """Fila cheia (muito tempo sem rede): apaga as leituras mais antigas."""
    try:
        with open(ARQUIVO_FILA) as origem, open(ARQUIVO_FILA + ".tmp", "w") as destino:
            for numero, linha in enumerate(origem):
                if numero >= quantas:
                    destino.write(linha)
        substituir_fila(ARQUIVO_FILA + ".tmp")
        print("[Fila] Cheia: descartadas", quantas, "leituras antigas")
    except OSError as erro:
        print("[Fila] Erro ao descartar:", erro)


def ler_pico_impacto():
    """Pico de aceleracao dinamica (g) desde a ultima leitura. Sem ADXL345 ainda: None."""
    return None


def registrar_leitura():
    """A cada REGISTRO_INTERVALO_MS, coloca a ultima medicao na fila local."""
    global ultimo_registro_ms

    agora = time.ticks_ms()
    if time.ticks_diff(agora, ultimo_registro_ms) < REGISTRO_INTERVALO_MS:
        return
    if ultima_temperatura is None or ultima_umidade is None:
        return
    if not relogio_ok:
        print("[Fila] Relogio ainda nao acertado: leitura nao registrada")
        return
    if viagem_ativa is None:
        # Sem viagem ativa no backend, a leitura nao teria a quem pertencer.
        return

    ultimo_registro_ms = agora

    leitura = {
        "shipment_id": viagem_ativa,   # guardado junto: o dado offline continua na viagem certa
        "sequence": proximo_sequence(),
        "recorded_at": agora_iso(),
        "temperature_c": ultima_temperatura,
        "humidity_pct": ultima_umidade,
        "impact_peak_g": ler_pico_impacto(),
    }
    with open(ARQUIVO_FILA, "a") as arquivo:
        arquivo.write(json.dumps(leitura) + "\n")

    total = tamanho_fila()
    print("[Fila] Leitura #%d registrada (%d na fila)" % (leitura["sequence"], total))
    if total > FILA_MAXIMA:
        descartar_mais_antigas(total - FILA_MAXIMA)


def ler_lote():
    """Le ate LOTE_MAXIMO leituras do inicio da fila, todas da mesma viagem."""
    lote, viagem = [], None
    try:
        with open(ARQUIVO_FILA) as arquivo:
            for linha in arquivo:
                try:
                    item = json.loads(linha)
                except ValueError:
                    continue  # linha corrompida (ex.: energia caiu no meio da escrita)
                if viagem is None:
                    viagem = item["shipment_id"]
                if item["shipment_id"] != viagem:
                    break
                lote.append(item)
                if len(lote) >= LOTE_MAXIMO:
                    break
    except OSError:
        pass
    return viagem, lote


def remover_da_fila(sequences, viagem):
    """Reescreve a fila sem as leituras confirmadas (lendo linha a linha, para caber na RAM)."""
    confirmadas = set(sequences)
    try:
        with open(ARQUIVO_FILA) as origem, open(ARQUIVO_FILA + ".tmp", "w") as destino:
            for linha in origem:
                try:
                    item = json.loads(linha)
                except ValueError:
                    continue
                if item["shipment_id"] == viagem and item["sequence"] in confirmadas:
                    continue
                destino.write(linha)
        substituir_fila(ARQUIVO_FILA + ".tmp")
    except OSError as erro:
        print("[Fila] Erro ao remover confirmadas:", erro)


def cabecalhos_api():
    return {"Content-Type": "application/json", "X-Device-Key": DEVICE_KEY}


def atualizar_config(wifi):
    """Pergunta a API qual e a viagem ativa desta placa (e aproveita para acertar o relogio)."""
    global viagem_ativa, ultima_config_ms

    agora = time.ticks_ms()
    if time.ticks_diff(agora, ultima_config_ms) < CONFIG_INTERVALO_MS:
        return
    if not wifi.isconnected() or not DEVICE_KEY:
        return
    ultima_config_ms = agora

    resposta = None
    try:
        resposta = http(requests.get, API_URL + "/iot/config", headers=cabecalhos_api())
        if resposta.status_code == 200:
            dados = resposta.json()["data"]
            if dados["shipment_id"] != viagem_ativa:
                print("[API] Viagem ativa:", dados["shipment_id"])
            viagem_ativa = dados["shipment_id"]
            if not relogio_ok:
                acertar_relogio_pela_api(dados["server_time"])
        else:
            print("[API] /iot/config respondeu", resposta.status_code, resposta.text)
    except Exception as erro:
        print("[API] Falha em /iot/config:", erro)
    finally:
        if resposta is not None:
            resposta.close()


def enviar_api(wifi):
    """Envia um lote da fila e apaga dela so o que a API confirmou."""
    global ultimo_envio_api_ms

    agora = time.ticks_ms()
    if time.ticks_diff(agora, ultimo_envio_api_ms) < ENVIO_INTERVALO_MS:
        return
    if not wifi.isconnected() or not DEVICE_KEY:
        return
    ultimo_envio_api_ms = agora

    viagem, lote = ler_lote()
    if not lote:
        return

    corpo = {
        "device_uid": DEVICE_UID,
        "shipment_id": viagem,
        "network": "wifi",
        "readings": [
            {chave: item[chave] for chave in ("sequence", "recorded_at", "temperature_c",
                                             "humidity_pct", "impact_peak_g")}
            for item in lote
        ],
    }

    resposta = None
    try:
        resposta = http(requests.post, API_URL + "/iot/telemetry/batch", data=json.dumps(corpo),
                        headers=cabecalhos_api())
        if resposta.status_code == 200:
            aceitas = resposta.json()["data"]["accepted_reading_sequences"]
            remover_da_fila(aceitas, viagem)
            print("[API] Lote enviado: %d de %d confirmadas" % (len(aceitas), len(lote)))
        elif resposta.status_code == 400:
            # A API recusou o lote inteiro (ex.: viagem encerrada/cancelada ou dado invalido).
            # Reenviar nao adianta: tira da fila para nao travar as proximas leituras.
            print("[API] Lote recusado (400):", resposta.text)
            remover_da_fila([item["sequence"] for item in lote], viagem)
        else:
            # 401 (chave errada), 429 (limite), 5xx: mantem na fila e tenta depois.
            print("[API] Erro", resposta.status_code, "- lote mantido na fila")
    except Exception as erro:
        print("[API] Sem resposta (lote mantido na fila):", erro)
    finally:
        if resposta is not None:
            resposta.close()


def manter_wifi(wifi):
    """Se o Wi-Fi caiu, tenta reconectar de vez em quando SEM parar as medicoes."""
    global ultima_reconexao_ms

    if wifi.isconnected():
        return
    agora = time.ticks_ms()
    if time.ticks_diff(agora, ultima_reconexao_ms) < RECONEXAO_INTERVALO_MS:
        return
    ultima_reconexao_ms = agora

    print("[Wi-Fi] Desconectado. Tentando reconectar...")
    try:
        visiveis = {item[0].decode() for item in wifi.scan()}
    except Exception:
        visiveis = set()
    for ssid, senha in REDES:
        if ssid in visiveis:
            try:
                wifi.connect(ssid, senha)
            except OSError:
                pass
            return  # a conexao termina sozinha; o loop segue medindo


# ============================================================
# MQTT
# ============================================================

def conectar_mqtt():
    """Abre a conexão com o broker e avisa que a placa está online."""

    global cliente_mqtt

    cliente = MQTTClient(
        CLIENT_ID,
        MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USUARIO,
        password=MQTT_SENHA,
        keepalive=MQTT_KEEPALIVE_S,
    )

    # Last Will: mensagem que o BROKER publica sozinho se a placa sumir.
    cliente.set_last_will(TOPICO_STATUS, b"offline", retain=True)

    print("[MQTT] Conectando em", MQTT_BROKER, "...")
    cliente.connect()

    # Depois de conectado, evita que um envio trave o loop principal.
    cliente.sock.settimeout(5)

    cliente.publish(TOPICO_STATUS, b"online", retain=True)

    cliente_mqtt = cliente
    print("[MQTT] Conectado como", CLIENT_ID)


def enviar_mqtt(wifi):
    """Publica temperatura e umidade a cada MQTT_INTERVALO_MS."""

    global cliente_mqtt
    global ultimo_envio_mqtt_ms

    agora = time.ticks_ms()

    if time.ticks_diff(agora, ultimo_envio_mqtt_ms) < MQTT_INTERVALO_MS:
        return

    # Marca a tentativa antes de checar o Wi-Fi: sem rede, avisa uma vez por intervalo
    # (e nao a cada volta do loop).
    ultimo_envio_mqtt_ms = agora

    if not wifi.isconnected():
        print("[MQTT] Sem Wi-Fi, aguardando...")
        return

    if ultima_temperatura is None or ultima_umidade is None:
        print("[MQTT] Aguardando leitura do sensor...")
        return

    try:
        # Se caiu antes, reconecta (só a cada MQTT_INTERVALO_MS).
        if cliente_mqtt is None:
            conectar_mqtt()

        cliente_mqtt.publish(TOPICO_TEMPERATURA, str(ultima_temperatura))
        cliente_mqtt.publish(TOPICO_UMIDADE, str(ultima_umidade))
        cliente_mqtt.publish(
            TOPICO_DADOS,
            json.dumps({
                "temperatura": ultima_temperatura,
                "umidade": ultima_umidade,
            }),
        )

        print(
            "[MQTT] Publicado ->",
            ultima_temperatura, "C |", ultima_umidade, "%",
        )

    except Exception as erro:
        print("[MQTT] Erro:", erro)

        # Descarta a conexão; a próxima rodada reconecta.
        try:
            cliente_mqtt.sock.close()
        except Exception:
            pass
        cliente_mqtt = None


# ============================================================
# RESPOSTAS HTTP (SERVIDOR LOCAL)
# ============================================================
 
def criar_resposta(status, tipo, conteudo):
    """Monta uma resposta seguindo o formato básico do HTTP."""
 
    corpo = conteudo.encode("utf-8")
 
    cabecalhos = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {tipo}\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Connection: close\r\n"
        f"Content-Length: {len(corpo)}\r\n"
        "\r\n"
    ).encode("utf-8")
 
    return cabecalhos + corpo
 
 
def resposta_api():
    """Cria o JSON devolvido pelo endpoint /api/dados local."""
 
    dados = {
        "sensor": "DHT11",
        "temperatura": ultima_temperatura,
        "umidade": ultima_umidade,
        "unidade_temperatura": "C",
    }
 
    return criar_resposta(
        "200 OK",
        "application/json; charset=utf-8",
        json.dumps(dados),
    )
 
 
def resposta_inicial():
    """Cria uma página simples para abrir no navegador."""
 
    pagina = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>ESP32-C3</title>
</head>
<body>
<h1>ESP32-C3 + DHT11</h1>
<p>Use <a href="/api/dados">/api/dados</a> para consultar o sensor.</p>
</body>
</html>
"""
 
    return criar_resposta(
        "200 OK",
        "text/html; charset=utf-8",
        pagina,
    )
 
 
def resposta_nao_encontrada():
    """Resposta usada para endereços inexistentes."""
 
    return criar_resposta(
        "404 Not Found",
        "application/json; charset=utf-8",
        '{"erro":"rota nao encontrada"}',
    )
 
 
# ============================================================
# SERVIDOR HTTP
# ============================================================
 
def criar_servidor():
    """Abre o servidor HTTP na porta configurada."""
 
    endereco = socket.getaddrinfo(
        "0.0.0.0",
        HTTP_PORT,
    )[0][-1]
 
    servidor = socket.socket()
 
    servidor.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )
 
    servidor.bind(endereco)
    servidor.listen(2)
 
    servidor.settimeout(0.2)
 
    print(f"Servidor HTTP ativo na porta {HTTP_PORT}")
 
    return servidor
 
 
def atender_cliente(cliente):
    """Lê uma requisição HTTP e envia a resposta adequada."""
 
    try:
        requisicao = cliente.recv(1024)
 
        if not requisicao:
            return
 
        primeira_linha = requisicao.split(b"\r\n", 1)[0]
        partes = primeira_linha.split()
 
        if len(partes) < 2:
            cliente.sendall(
                resposta_nao_encontrada()
            )
            return
 
        metodo = partes[0]
        caminho = partes[1]
 
        print("HTTP:", metodo, caminho)
 
        if metodo != b"GET":
            resposta = criar_resposta(
                "405 Method Not Allowed",
                "application/json; charset=utf-8",
                '{"erro":"metodo nao permitido"}',
            )
 
        elif caminho == b"/":
            resposta = resposta_inicial()
 
        elif caminho == b"/api/dados":
            resposta = resposta_api()
 
        else:
            resposta = resposta_nao_encontrada()
 
        cliente.sendall(resposta)
 
    except Exception as erro:
        print("Erro ao atender cliente:", erro)
 
    finally:
        cliente.close()
 
 
# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
 
# Conecta ao Wi-Fi.
wifi = conectar_wifi()

# Acerta o relogio (UTC). Se o NTP falhar, a hora vem da API em /iot/config.
acertar_relogio_ntp()
if not DEVICE_KEY:
    print("[API] DEVICE_KEY ausente no wifi_config.py: envio para a API desligado")
 
# Faz a primeira tentativa de leitura.
atualizar_sensor()
 
# Cria o servidor local.
servidor = criar_servidor()
 
ip = wifi.ifconfig()[0]
 
print("Página:", f"http://{ip}/")
print("API:", f"http://{ip}/api/dados")
 
# Mantem sensor, display, envios (MQTT, ThingSpeak e API) e servidor local funcionando continuamente.
while True:
    atualizar_sensor()
    manter_wifi(wifi)
    enviar_thingspeak()
    enviar_mqtt(wifi)
    atualizar_config(wifi)
    registrar_leitura()
    enviar_api(wifi)
    atualizar_leds_status(wifi)
 
    try:
        cliente, endereco_cliente = servidor.accept()
 
        print("Cliente conectado:", endereco_cliente)
 
        atender_cliente(cliente)
 
    except OSError:
        pass