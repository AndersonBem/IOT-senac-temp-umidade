# 🌡️ ESP32-C3 DHT11 Environment Monitor

Projeto de monitoramento de **temperatura e umidade** utilizando uma placa **ESP32-C3 com display OLED integrado** e um sensor **DHT11**.

As informações coletadas pelo sensor são exibidas simultaneamente:

- No display OLED integrado à ESP32-C3
- No Serial Monitor da Arduino IDE

## 📋 Funcionalidades

- Leitura de temperatura em °C
- Leitura da umidade relativa do ar em %
- Exibição dos dados no OLED
- Exibição dos dados no Serial Monitor
- Atualização automática a cada 2 segundos
- Detecção de falhas na leitura do DHT11

## 🛠️ Hardware utilizado

- ESP32-C3 com display OLED integrado
- Sensor DHT11
- Jumpers
- Cabo USB-C

## 🔌 Conexões

O sensor DHT11 utilizado possui três pinos: **VCC, DATA e GND**.

| DHT11 | ESP32-C3 |
|------|----------|
| VCC | 3.3V |
| DATA | GPIO 4 |
| GND | GND |

> A pinagem pode variar dependendo do módulo DHT11 utilizado. Verifique as marcações presentes no seu sensor antes de realizar as conexões.

## 🖥️ Display OLED

O projeto utiliza o display OLED integrado à placa ESP32-C3.

Configuração utilizada:

```cpp
#define OLED_SDA 5
#define OLED_SCL 6
```

O display é controlado através da biblioteca **U8g2** utilizando comunicação I²C.

## 📚 Bibliotecas

Para compilar o projeto na Arduino IDE, instale as seguintes bibliotecas:

### DHT sensor library

Biblioteca da Adafruit utilizada para comunicação com o DHT11.

Na Arduino IDE:

`Library Manager → DHT sensor library by Adafruit`

### U8g2

Utilizada para controlar o display OLED.

Na Arduino IDE:

`Library Manager → U8g2`

Também pode ser necessário instalar a dependência:

`Adafruit Unified Sensor`

## ⚙️ Configuração da Arduino IDE

A placa utilizada neste projeto é baseada no **ESP32-C3**.

Configuração utilizada:

```text
Board: ESP32C3 Dev Module
Serial Monitor: 115200 baud
```

É necessário instalar o pacote:

`esp32 by Espressif Systems`

através do Boards Manager da Arduino IDE.

## 📊 Exemplo de saída

No Serial Monitor:

```text
=== DHT11 + OLED ===

Temperatura: 27.4 °C
Umidade: 63.0 %
--------------------

Temperatura: 27.5 °C
Umidade: 62.0 %
--------------------
```

No OLED:

```text
 AMBIENTE

T: 27.4 C
U: 63.0 %
```

## 🚀 Como executar

1. Monte o circuito conectando o DHT11 à ESP32-C3.
2. Abra o arquivo `.ino` na Arduino IDE.
3. Instale as bibliotecas necessárias.
4. Selecione `ESP32C3 Dev Module`.
5. Selecione a porta COM correspondente à placa.
6. Compile e envie o código.
7. Abra o Serial Monitor em `115200 baud`.

As leituras também serão apresentadas automaticamente no display OLED.

## 📁 Estrutura do projeto

```text
esp32-c3-dht11-monitor/
│
├── esp32-c3-dht11-monitor.ino
└── README.md
```

## 🔧 Tecnologias

- ESP32-C3
- Arduino Framework
- C++
- DHT11
- I²C
- OLED / SSD1306
- U8g2

## 📝 Observações

O DHT11 é um sensor simples e de baixo custo, adequado para projetos educacionais e prototipagem. Ele possui precisão e frequência de atualização limitadas quando comparado a sensores mais avançados.

Este projeto foi desenvolvido como uma implementação prática de leitura de sensores, comunicação I²C e exibição de dados utilizando o ESP32-C3.

## 📄 Licença

Este projeto pode ser utilizado para fins educacionais e de estudo.
