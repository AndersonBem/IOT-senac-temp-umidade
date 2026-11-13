#include <DHT.h>
#include <Wire.h>
#include <U8g2lib.h>

// ======================
// DHT11
// ======================
#define DHTPIN 3
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

// ======================
// OLED da ESP32-C3
// ======================
#define OLED_SDA 5
#define OLED_SCL 6

U8G2_SSD1306_72X40_ER_F_HW_I2C display(
  U8G2_R0,
  U8X8_PIN_NONE,
  OLED_SCL,
  OLED_SDA
);

void setup() {

  // Serial
  Serial.begin(115200);
  delay(2000);

  Serial.println();
  Serial.println("=== DHT11 + OLED ===");

  // DHT11
  dht.begin();

  // OLED
  Wire.begin(OLED_SDA, OLED_SCL);
  display.begin();

  // Mensagem inicial
  display.clearBuffer();
  display.setFont(u8g2_font_6x10_tf);
  display.drawStr(5, 15, "Iniciando");
  display.drawStr(10, 30, "DHT11...");
  display.sendBuffer();

  delay(1500);
}

void loop() {

  float umidade = dht.readHumidity();
  float temperatura = dht.readTemperature();

  // Verifica erro
  if (isnan(umidade) || isnan(temperatura)) {

    Serial.println("Erro ao ler DHT11!");

    display.clearBuffer();
    display.setFont(u8g2_font_6x10_tf);
    display.drawStr(5, 15, "ERRO");
    display.drawStr(2, 30, "DHT11");
    display.sendBuffer();

  } else {

    // ======================
    // SERIAL MONITOR
    // ======================

    Serial.print("Temperatura: ");
    Serial.print(temperatura, 1);
    Serial.println(" °C");

    Serial.print("Umidade: ");
    Serial.print(umidade, 1);
    Serial.println(" %");

    Serial.println("--------------------");

    // ======================
    // OLED
    // ======================

    display.clearBuffer();

    // Título
    display.setFont(u8g2_font_5x7_tf);
    display.drawStr(8, 7, "AMBIENTE");

    // Temperatura
    display.setFont(u8g2_font_6x10_tf);
    display.setCursor(0, 21);
    display.print("T: ");
    display.print(temperatura, 1);
    display.print(" C");

    // Umidade
    display.setCursor(0, 36);
    display.print("U: ");
    display.print(umidade, 1);
    display.print(" %");

    display.sendBuffer();
  }

  delay(2000);
}