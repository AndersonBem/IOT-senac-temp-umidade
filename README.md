<div align="center">

# 🌿 Caminho do Vale

### Monitoramento IoT para a cadeia de frio agrícola

<p>
  <img src="https://img.shields.io/badge/ESP32--C3-IoT-2D8B57?style=for-the-badge&logo=espressif&logoColor=white" alt="ESP32-C3">
  <img src="https://img.shields.io/badge/MicroPython-3B7EA1?style=for-the-badge&logo=python&logoColor=white" alt="MicroPython">
  <img src="https://img.shields.io/badge/Status-Prot%C3%B3tipo%20funcional-6FAF45?style=for-the-badge" alt="Status">
</p>

<p><i>Do vale ao destino: dados que ajudam a preservar qualidade.</i></p>

</div>

> Protótipo educacional para monitorar temperatura e umidade em ambientes de
> armazenamento e transporte de produtos agrícolas. O nó utiliza ESP32-C3,
> DHT11, OLED, telemetria remota e portal Wi-Fi configurável pelo celular.

## 👥 Equipe

| Integrante | Participação |
|---|---|
| Anderson Bem | Desenvolvimento do projeto |
| Laís Nayara | Desenvolvimento do projeto |
| Lucas Mendes | Desenvolvimento do projeto |
| Wendell Barboza | Desenvolvimento do projeto |
| Wendel Brasiliano | Desenvolvimento do projeto |

## ✨ Visão do projeto

O Caminho do Vale conecta a leitura do ambiente físico à operação logística.
Quando a placa não consegue acessar uma rede conhecida, ela cria uma rede
Wi-Fi própria e oferece uma página de configuração para o celular. Assim, a
instalação não depende de alterar credenciais diretamente no código.

## ✨ Recursos

- Leitura de temperatura e umidade pelo DHT11;
- exibição no OLED e LEDs de estado;
- envio para ThingSpeak, MQTT e API do projeto;
- fila local de leituras para envio posterior;
- API HTTP local;
- redes Wi-Fi de reserva;
- portal Wi-Fi com captive portal.

## 📶 Portal Wi-Fi

Após duas buscas sem encontrar uma rede conhecida, a ESP32 cria uma rede local.
Conecte o celular a ela e cadastre uma rede destino de 2,4 GHz. O portal tenta
abrir a página automaticamente; se não abrir, use:

    http://192.168.4.1

No arquivo local src\wifi_config.py:

    PORTAL_WIFI_NOME = "NOME-DA-REDE"
    PORTAL_WIFI_SENHA = "senha-com-no-minimo-8-caracteres"

wifi_config.py é ignorado pelo Git. O portal grava a rede cadastrada em
redes.json na flash; essa rede tem prioridade sobre as redes de reserva.

## 🗂️ Estrutura

    src\main.py          programa principal
    src\wifi_config.py   redes de reserva, chaves e credenciais locais
    src\wifi_portal.py   ponto de acesso e página de configuração
    src\mqtt_config.py
    src\api_config.py
    pc\assinante_pc.py   assinante MQTT para computador
    GUIA_COMANDOS.txt     comandos, diagnóstico e recuperação

O arquivo esp32-c3-temperatura-umidade.ino é uma versão anterior em Arduino.

## 🔌 Hardware e pinagem

| Componente | Conexão |
|---|---|
| DHT11 VCC/DATA/GND | 3,3 V / GPIO 1 / GND |
| OLED SDA/SCL | GPIO 5 / GPIO 6 |
| OLED I²C | 0x3C |
| LED azul, verde, vermelho | GPIO 3, 4, 7 |

## 🚀 Preparação

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install esptool==5.4.0 mpremote==1.29.0

Instale o driver OLED uma única vez:

    python -m mpremote connect COMx mip install ssd1306

## 📤 Envio para a ESP32

Substitua COMx pela porta da placa:

    python -m mpremote connect COMx fs cp .\src\wifi_portal.py :wifi_portal.py
    python -m mpremote connect COMx fs cp .\src\main.py :main.py
    python -m mpremote connect COMx fs cp .\src\wifi_config.py :wifi_config.py
    python -m mpremote connect COMx reset
    python -m mpremote connect COMx

Para testar somente o portal, sem substituir /main.py:

    python -m mpremote connect COMx run .\src\wifi_portal.py

Esse teste não substitui main.py, mas pode gravar redes.json se o formulário
for salvo.

## 🌐 API local

Depois de conectar ao Wi-Fi:

    http://IP_DA_ESP32/
    http://IP_DA_ESP32/api/dados

## ⚠️ Cuidados

- ESP32-C3 aceita somente Wi-Fi de 2,4 GHz.
- SSID e senha diferenciam maiúsculas, espaços e acentos.
- Prefira WPA2-Personal; WPA3-only pode falhar.
- Não publique wifi_config.py, redes.json, senhas ou backup da flash.
- Para apagar somente a rede cadastrada pelo portal:

      python -m mpremote connect COMx fs rm :redes.json
      python -m mpremote connect COMx reset

- Não execute erase-flash ou write-flash na rotina normal.

## 📚 Documentação

Consulte GUIA_COMANDOS.txt para upload, diagnóstico do portal, testes de OLED e
DHT11 e recuperação de conexão.

## 📄 Licença

Projeto educacional desenvolvido no SENAC.
