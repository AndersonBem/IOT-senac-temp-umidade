"""Assinante MQTT para rodar no PC: mostra o que a placa publica.

Instalar (uma vez):   python -m pip install paho-mqtt
Executar (na pasta pc): python assinante_pc.py
Parar:                Ctrl+C

Usa o MESMO broker e TOPICO_BASE de src/mqtt_config.py.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import paho.mqtt.client as mqtt
from mqtt_config import MQTT_BROKER, MQTT_PORT, TOPICO_BASE


def ao_conectar(cliente, userdata, flags, reason_code, properties=None):
    print("Conectado ao broker:", MQTT_BROKER, "| codigo:", reason_code)
    cliente.subscribe(TOPICO_BASE + "/#")
    print("Assinando:", TOPICO_BASE + "/#")


def ao_receber(cliente, userdata, msg):
    texto = msg.payload.decode("utf-8", "replace")
    print(f"[{msg.topic}] {texto}")

    if msg.topic.endswith("/dados"):
        try:
            dados = json.loads(texto)
            print(f"   => Temperatura {dados['temperatura']} C | Umidade {dados['umidade']} %")
        except (ValueError, KeyError):
            pass


cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
cliente.on_connect = ao_conectar
cliente.on_message = ao_receber
cliente.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
cliente.loop_forever()
