# Recursos de hardware do MicroPython.
from machine import Pin, SoftI2C, unique_id
 
# Bibliotecas do MicroPython.
import dht
import json
import network
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
 
# Configurações do PythonAnywhere
URL_PYTHONANYWHERE = "http://iotsaofranciscopi.pythonanywhere.com/api/dados"
PYTHONANYWHERE_INTERVAL_MS = 3_000
 
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
ultimo_envio_pythonanywhere_ms = time.ticks_ms() - PYTHONANYWHERE_INTERVAL_MS
 
# Horário da última tentativa de leitura.
ultima_leitura_ms = time.ticks_ms() - READ_INTERVAL_MS

# Conexão MQTT atual (None = desconectado).
cliente_mqtt = None
ultimo_envio_mqtt_ms = time.ticks_ms() - MQTT_INTERVALO_MS
 
 
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
 
 
def enviar_pythonanywhere():
    global ultimo_envio_pythonanywhere_ms
 
    agora = time.ticks_ms()
 
    if time.ticks_diff(
        agora,
        ultimo_envio_pythonanywhere_ms,
    ) < PYTHONANYWHERE_INTERVAL_MS:
        return
 
    if ultima_temperatura is None or ultima_umidade is None:
        print("[PythonAnywhere] Aguardando leitura do sensor...")
        return
 
    ultimo_envio_pythonanywhere_ms = agora
 
    payload = {
        "temperatura": str(ultima_temperatura),
        "umidade": str(ultima_umidade)
    }
 
    print("[PythonAnywhere] Enviando requisição POST...")
    resposta = None
 
    try:
        resposta = requests.post(
            URL_PYTHONANYWHERE,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        print("[PythonAnywhere] Resposta -> Status:", resposta.status_code)
 
    except Exception as erro:
        print("[PythonAnywhere] Erro no envio:", erro)
 
    finally:
        if resposta is not None:
            resposta.close()
 
 
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

    if not wifi.isconnected():
        print("[MQTT] Sem Wi-Fi, aguardando...")
        return

    if ultima_temperatura is None or ultima_umidade is None:
        print("[MQTT] Aguardando leitura do sensor...")
        return

    ultimo_envio_mqtt_ms = agora

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
 
# Faz a primeira tentativa de leitura.
atualizar_sensor()
 
# Cria o servidor local.
servidor = criar_servidor()
 
ip = wifi.ifconfig()[0]
 
print("Página:", f"http://{ip}/")
print("API:", f"http://{ip}/api/dados")
 
# Mantém sensor, display, envios na nuvem e servidor funcionando continuamente.
while True:
    atualizar_sensor()
    enviar_thingspeak()
    enviar_pythonanywhere()
    enviar_mqtt(wifi)
    atualizar_leds_status(wifi)
 
    try:
        cliente, endereco_cliente = servidor.accept()
 
        print("Cliente conectado:", endereco_cliente)
 
        atender_cliente(cliente)
 
    except OSError:
        pass