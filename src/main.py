# Recursos de hardware do MicroPython.
from machine import Pin, SoftI2C

# Bibliotecas do MicroPython.
import dht
import json
import network
import socket
import ssd1306
import time
import requests

# Credenciais mantidas fora do código principal.
from wifi_config import (
    WIFI_SSID,
    WIFI_PASSWORD,
    THINGSPEAK_WRITE_API_KEY,
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

# Tempo máximo para conectar ao Wi-Fi.
WIFI_TIMEOUT_SECONDS = 30

# Porta HTTP usada pela API.
HTTP_PORT = 80


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

def conectar_wifi():
    """Conecta a ESP32 a uma rede Wi-Fi e devolve a interface."""

    wifi = network.WLAN(network.STA_IF)

    # Reinicializa a interface para limpar estados anteriores.
    wifi.active(False)
    time.sleep(1)
    wifi.active(True)

    # Mantém a potência que funcionou nos testes desta placa.
    wifi.config(reconnects=3, txpower=8.5)

    mostrar_mensagem("Wi-Fi", "Conectando...")
    print("Conectando ao Wi-Fi:", WIFI_SSID)

    wifi.connect(WIFI_SSID, WIFI_PASSWORD)

    inicio = time.time()
    estado_led_azul = False

    while not wifi.isconnected():
        estado_led_azul = not estado_led_azul
        led_azul.value(estado_led_azul)

        status = wifi.status()
        tempo_decorrido = time.time() - inicio

        print(
            "Wi-Fi status:",
            status,
            "| tempo:",
            tempo_decorrido,
            "s",
        )

        if tempo_decorrido >= WIFI_TIMEOUT_SECONDS:
            raise RuntimeError(
                f"Timeout ao conectar no Wi-Fi. Status: {status}"
            )

        time.sleep_ms(500)

    ip = wifi.ifconfig()[0]

    print("Wi-Fi conectado!")
    print("IP:", ip)
    print("RSSI:", wifi.status("rssi"), "dBm")

    mostrar_mensagem("Wi-Fi OK", ip)
    led_azul.value(1)
    return wifi



def atualizar_leds_status(wifi):
    agora = time.ticks_ms()

    # Pisca continuamente: 500 ms aceso e 500 ms apagado.
    pisca_alerta = 1 if agora % 1_000 < 500 else 0

    # Condição normal: aceso, com breve apagada a cada 5 segundos.
    pulso_normal = 0 if agora % 5_000 < 250 else 1

    # Azul: Wi-Fi.
    if wifi.isconnected():
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
# LEITURA DO DHT11
# ============================================================

def atualizar_sensor():
    """
    Tenta obter uma nova medição.

    Se o DHT11 falhar, os últimos valores válidos são mantidos.
    """

    global ultima_temperatura
    global ultima_umidade
    global ultima_leitura_ms

    agora = time.ticks_ms()

    # Evita consultar o DHT11 antes do intervalo mínimo.
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
        # Timeouts ocasionais são comuns no DHT11.
        print("Falha ao ler DHT11:", erro)

        # Só mostra erro no OLED se nunca houve leitura válida.
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
# RESPOSTAS HTTP
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
    """Cria o JSON devolvido pelo endpoint /api/dados."""

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

    # Permite reutilizar a porta após reinicializações.
    servidor.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    servidor.bind(endereco)
    servidor.listen(2)

    # O timeout curto permite continuar lendo o DHT11
    # mesmo quando nenhum navegador está acessando a API.
    servidor.settimeout(0.2)

    print(f"Servidor HTTP ativo na porta {HTTP_PORT}")

    return servidor


def atender_cliente(cliente):
    """Lê uma requisição HTTP e envia a resposta adequada."""

    try:
        requisicao = cliente.recv(1024)

        if not requisicao:
            return

        # A primeira linha contém método, caminho e versão HTTP.
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

# Cria o servidor.
servidor = criar_servidor()

ip = wifi.ifconfig()[0]

print("Página:", f"http://{ip}/")
print("API:", f"http://{ip}/api/dados")

# Mantém sensor, display e servidor funcionando continuamente.
while True:
    atualizar_sensor()
    enviar_thingspeak()
    atualizar_leds_status(wifi)

    try:
        cliente, endereco_cliente = servidor.accept()

        print("Cliente conectado:", endereco_cliente)

        atender_cliente(cliente)

    except OSError:
        # O timeout é esperado quando ninguém acessa a API.
        pass