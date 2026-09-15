# Nó Sensor IoT com ESP32-C3, DHT11 e ThingSpeak

Protótipo de um nó sensor edge para monitoramento de temperatura e umidade relativa do ar, desenvolvido com ESP32-C3 e DHT11.

O projeto foi pensado para aplicações no agronegócio do Vale do São Francisco, especialmente em packing houses, câmaras de resfriamento e ambientes de armazenamento e transporte de frutas.

As medições são apresentadas localmente em um display OLED, disponibilizadas por uma API HTTP na rede local e enviadas periodicamente para a plataforma ThingSpeak.

## Identificação da equipe

**Nome da equipe:** `[PREENCHER]`

**Integrantes:**

- `[NOME COMPLETO]`
- `[NOME COMPLETO]`
- `[NOME COMPLETO]`

## Canal de telemetria

**Canal público do ThingSpeak:** `[INSERIR LINK DO CANAL]`

Campos utilizados:

| Campo | Informação | Unidade |
|---|---|---|
| Field 1 | Temperatura ambiente | °C |
| Field 2 | Umidade relativa do ar | % |

> O canal deve estar configurado como público para permitir a visualização dos gráficos sem uma chave privada.

## Funcionalidades

- Leitura do sensor DHT11 a cada 2 segundos;
- medição de temperatura e umidade relativa;
- apresentação das medições no display OLED;
- envio ao ThingSpeak a cada 20 segundos;
- servidor HTTP disponível na rede local;
- endpoint JSON para consulta das medições;
- retenção da última leitura válida quando ocorre uma falha temporária no DHT11;
- indicação visual por LEDs para Wi-Fi, temperatura e umidade;
- tentativa limitada de reconexão automática do Wi-Fi;
- credenciais armazenadas fora do código principal.

## Aplicação no negócio

O nó sensor pode ser instalado em uma câmara fria pós-colheita ou em uma área controlada de um packing house de uvas e mangas.

Nesse cenário, ele realiza o acompanhamento inicial do microclima e permite identificar condições de temperatura ou umidade fora da faixa configurada. Os dados enviados ao ThingSpeak também podem ser utilizados como fonte inicial para análises históricas e futuras integrações em nuvem.

No protótipo, as faixas de referência configuradas são:

| Grandeza | Faixa configurada |
|---|---|
| Temperatura | 0 °C a 5 °C |
| Umidade relativa | 85% a 95% |

Esses valores são referências experimentais do protótipo e devem ser ajustados conforme o produto armazenado, a etapa logística e os requisitos fitossanitários aplicáveis.

## Arquitetura e fluxo de dados

```text
DHT11
  |
  | leitura digital
  v
ESP32-C3
  |----> Display OLED
  |----> LEDs de estado
  |----> API HTTP local
  |
  | Wi-Fi + HTTPS
  v
ThingSpeak
  |
  v
Gráficos e histórico de temperatura/umidade
```

O DHT11 faz internamente a medição e a conversão das grandezas. A ESP32-C3 recebe os valores digitais, atualiza a interface local e envia a telemetria para a API do ThingSpeak.

## Hardware utilizado

- ESP32-C3 com display OLED integrado;
- sensor DHT11;
- três LEDs de indicação;
- resistores adequados para os LEDs;
- jumpers;
- cabo USB-C para alimentação e programação;
- embalagem reaproveitada para o gabinete.

## Pinagem

### Sensor DHT11

| DHT11 | ESP32-C3 |
|---|---|
| VCC | 3,3 V |
| DATA | GPIO 1 |
| GND | GND |

### Display OLED integrado

| Sinal | ESP32-C3 |
|---|---|
| SDA | GPIO 5 |
| SCL | GPIO 6 |
| Endereço I²C | `0x3C` |
| Resolução | 72 × 40 pixels |

### LEDs de estado

| LED | GPIO | Indicação |
|---|---:|---|
| Azul | 3 | Estado da conexão Wi-Fi |
| Verde | 4 | Temperatura dentro ou fora da faixa |
| Vermelho | 7 | Umidade dentro ou fora da faixa |

Comportamento dos LEDs:

- pulso breve a cada cinco segundos: condição normal;
- piscando continuamente: desconexão ou variável fora da faixa;
- apagado: ainda não existe uma leitura válida.

> Confira a pinagem e utilize resistores limitadores nos LEDs. A disposição dos pinos pode variar entre modelos de ESP32-C3.

## Software e tecnologias

- MicroPython para ESP32-C3;
- módulo `dht` do MicroPython;
- comunicação I²C com `SoftI2C`;
- driver `ssd1306`;
- Wi-Fi em modo estação;
- requisições HTTPS com `requests`;
- servidor HTTP utilizando `socket`;
- ThingSpeak para armazenamento e visualização da telemetria.

O arquivo `.ino` mantido na raiz corresponde a uma implementação anterior em Arduino/C++ e pode ser usado como referência. A versão principal atual está em `src/main.py`.

## Estrutura do projeto

```text
.
├── src/
│   ├── main.py
│   └── wifi_config.py        # Arquivo local, não deve ser enviado ao Git
├── esp32-c3-temperatura-umidade.ino
├── GUIA_COMANDOS.txt
├── .gitignore
└── README.md
```

Os arquivos de firmware e backup com extensão `.bin` também devem permanecer fora do repositório, pois podem conter dados gravados anteriormente na memória da placa.

## Configuração das credenciais

Crie o arquivo `src/wifi_config.py` com o seguinte formato:

```python
WIFI_SSID = "NOME_DA_REDE"
WIFI_PASSWORD = "SENHA_DA_REDE"
THINGSPEAK_WRITE_API_KEY = "CHAVE_DE_ESCRITA"
```

Esse arquivo contém informações privadas e não deve ser enviado para um repositório público.

Confirme que o `.gitignore` contém:

```gitignore
src/wifi_config.py
*.bin
.venv/
__pycache__/
*.pyc
.vscode/
```

Nunca publique a senha do Wi-Fi nem a Write API Key do ThingSpeak. Se alguma chave já tiver sido publicada, ela deve ser substituída no painel do ThingSpeak.

## Preparação do ambiente

Instale Python e as ferramentas utilizadas para comunicação com a placa:

```powershell
python -m pip install --upgrade pip
python -m pip install esptool==5.4.0 mpremote==1.29.0
```

Verifique a instalação:

```powershell
python -m esptool version
python -m mpremote --version
```

A placa utilizada nos testes possui firmware MicroPython para `ESP32_GENERIC_C3`.

## Instalação na ESP32-C3

Substitua `COM3` pela porta correspondente à sua placa.

Instale o driver do OLED diretamente na placa:

```powershell
python -m mpremote connect COM3 mip install ssd1306
```

Envie as credenciais:

```powershell
python -m mpremote connect COM3 fs cp .\src\wifi_config.py :wifi_config.py
```

Envie o programa principal:

```powershell
python -m mpremote connect COM3 fs cp .\src\main.py :main.py
```

Reinicie a placa e abra o terminal:

```powershell
python -m mpremote connect COM3 reset
python -m mpremote connect COM3
```

Para sair do terminal do `mpremote`, utilize `Ctrl+]`.

## API HTTP local

Depois que a placa se conecta ao Wi-Fi, seu endereço IP é apresentado no terminal e no OLED.

Página inicial:

```text
http://IP_DA_ESP32/
```

Endpoint das medições:

```text
http://IP_DA_ESP32/api/dados
```

Exemplo de resposta:

```json
{
  "sensor": "DHT11",
  "temperatura": 4,
  "umidade": 90,
  "unidade_temperatura": "C"
}
```

A API local utiliza HTTP sem criptografia e deve ser acessada somente em uma rede confiável. O envio externo ao ThingSpeak utiliza HTTPS.

## Gabinete reaproveitado

O gabinete do protótipo deve ser construído com uma embalagem reaproveitada, aplicando princípios de upcycling e design circular.

A montagem deve prever:

- passagem segura para o cabo USB-C;
- fixação da placa e da fiação;
- proteção contra contato acidental;
- aberturas próximas ao DHT11 para troca de ar por convecção;
- distância adequada entre o sensor e componentes que gerem calor;
- acesso para manutenção.

A ventilação é necessária para evitar que o calor interno da ESP32-C3 altere as medições.

## Registro fotográfico

### Montagem eletrônica interna

`[ADICIONAR FOTO COM CIRCUITO E PINAGEM VISÍVEIS]`

### Protótipo final no gabinete reaproveitado

`[ADICIONAR FOTO DO PROTÓTIPO FECHADO E DAS ABERTURAS DE AERAÇÃO]`

Sugestão: armazene as imagens em uma pasta `docs/imagens/` e substitua os textos acima por:

```markdown
![Montagem eletrônica](docs/imagens/montagem-interna.jpg)
![Protótipo final](docs/imagens/prototipo-final.jpg)
```

## Limitações técnicas

### Sensor DHT11

O DHT11 é um sensor simples e de baixo custo, adequado para demonstrações e protótipos educacionais, mas possui limitações importantes:

- precisão e resolução inferiores às de sensores profissionais;
- baixa frequência de amostragem;
- tempo de resposta relativamente lento;
- faixa de operação limitada;
- possibilidade de leituras incorretas em caso de condensação;
- ausência de calibração rastreável para uso fitossanitário ou comercial.

Por isso, o protótipo não substitui instrumentos calibrados exigidos por normas agrícolas, de armazenamento ou de exportação.

### Comunicação Wi-Fi

- O alcance pode ser reduzido por paredes, estruturas metálicas, câmaras frias e equipamentos industriais;
- a conexão pode ficar indisponível durante o transporte;
- o código realiza tentativas limitadas de reconexão, mas ainda não possui uma estratégia permanente de recuperação após falhas prolongadas;
- o Wi-Fi apresenta consumo energético maior que alternativas voltadas a longas distâncias e baixo consumo;
- ainda não foram implementados Deep Sleep, LoRaWAN ou armazenamento local para períodos sem conexão.

### Gabinete reaproveitado

O gabinete artesanal não possui certificação de grau de proteção IP. Ele pode apresentar vulnerabilidade à poeira, respingos, condensação, impactos e variações extremas de temperatura.

O sensor precisa permanecer em contato com o ar, portanto as aberturas de ventilação também reduzem a proteção do conjunto contra água e partículas.

## Próximos passos

- Implementar reconexão contínua do Wi-Fi;
- armazenar temporariamente as medições durante quedas de conexão;
- adicionar RSSI ou contador de pacotes ao Field 3;
- implementar watchdog e tratamento de falhas prolongadas;
- avaliar sensores com melhor precisão e resistência à condensação;
- utilizar Deep Sleep para reduzir o consumo energético;
- avaliar LoRaWAN ou comunicação celular para transporte e áreas extensas;
- desenvolver um gabinete com proteção apropriada para o ambiente;
- integrar os dados do ThingSpeak com AWS ou Azure;
- armazenar as séries temporais em um banco de dados em nuvem;
- utilizar os dados em dashboards, alertas e modelos preditivos de conservação e qualidade da safra.

Uma integração futura poderá consultar a API do ThingSpeak ou utilizar um serviço intermediário para encaminhar as medições a componentes como AWS IoT Core, Amazon Timestream, Azure IoT Hub ou bancos de séries temporais.

## Situação da entrega

Implementado:

- leitura de temperatura e umidade;
- exibição local no OLED;
- indicação por LEDs;
- conexão Wi-Fi;
- API HTTP local;
- envio periódico ao ThingSpeak;
- separação das credenciais do código principal;
- documentação básica de instalação e arquitetura.

Pendente de preenchimento ou validação pela equipe:

- identificação completa dos integrantes;
- link público do canal ThingSpeak;
- fotografias da montagem e do gabinete;
- validação de campo no ambiente escolhido;
- confirmação e documentação final do material utilizado no gabinete;
- implementação de recuperação permanente após quedas prolongadas do Wi-Fi.

## Licença

Projeto desenvolvido para fins educacionais no curso do SENAC.