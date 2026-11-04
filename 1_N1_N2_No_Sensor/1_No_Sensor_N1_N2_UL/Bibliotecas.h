
//=======================================================================
// 1 - Bibliotecas
//=======================================================================

// Bibliotecas comuns para os Hardwares ESP32 e NodeMCU

#include <SPI.h>  // A SPI é usada para conectar o Módulo de Processamento ao RFM95
#include <LoRa.h> // Biblioteca do Módulo de Rádio LoRa RFM95W
// ============================================================
// TABELA DE CONFIGURAÇÃO DE RÁDIO
// ============================================================
#include "Tabela_Radio_LUT.h"
// ============================================================
// TABELA DE CONFIGURAÇÃO DE RÁDIO
// ============================================================
// #include "RadioConfigOptimized_FIXED.h"

#if defined(OLED_INTEGRADO)
    #include <Wire.h>              // Inclui a Biblioteca Wire para Oled
    #include <Adafruit_GFX.h>      // Inclui a Biblioteca GFX para Oled 
    #include <Adafruit_SSD1306.h>  // Inclui a Biblioteca OLED SSD1306
    //#include <DHT.h>             // Inclui a Biblioteca para Sensor DHT22 temperatura e humidade
#endif
#if defined(GPS_INTEGRADO)
    #include <TinyGPS++.h>         // Inclui a Biblioteca GPS
#endif

//=======================================================================
// 2 - Mapeamento dos Pinos
//=======================================================================

#if defined(PKLORA_ESP32)
  // ============= Pinagem na placa da PK-LoRa da ligação do RFM95 com o ESP32
  #define SCK_PIN   5
  #define MISO_PIN  19
  #define MOSI_PIN  27
  #define NSS_PIN   18
  #define RST_PIN   14
  #define DIO0_PIN  26
  #define DIO1_PIN  35
  #define DIO2_PIN  34

  // ============= CAMADA DE APLICAÇÃO
  // ESP32 I/Os - DIAGRAMA DE PINOS ENTRADAS E SAÍDAS
  // Pinos de Saída Digitais (Opcional, mas útil para debug no Gateway)
  #define LED_VERMELHO_PIN  15
  #define LED_VERDE_PIN     4
  #define LED_AMARELO_PIN   2
  #define BOTAO_PIN         39

  #define LDR_PIN 36   // ADC1_CH0 — sensor LDR - PIN VP

#elif defined(PKLORA_NODEMCU)
  // ============= Pinagem na placa da PK-LoRa da ligação do RFM95 com o Node-MCU
  #define SCK_PIN   14    // PIN D5
  #define MISO_PIN  12    // PIN D6
  #define MOSI_PIN  13    // PIN D7
  #define NSS_PIN   15    // PIN D8
  #define RST_PIN   0     // PIN D3
  #define DIO0_PIN  5     // PIN D1

  // ============= CAMADA DE APLICAÇÃO
  // Pinos dos LEDs
  #define LED_VERMELHO_PIN  2    // PINO D4
  #define LED_VERDE_PIN     4    // PINO D2
  #define LDR_PIN A0   // ADC1_CH0 — sensor LDR - PIN VP

#else
  #error "Por favor, definir a placa de hardware  (PKLORA_ESP32 ou PKLORA_NODEMCU) no topo deste código!"
#endif

#if defined(OLED_INTEGRADO)
  /*
  // Pinos sensor de temperatura e umidade DHT22 AM2302
  #define DHTPIN 13     // Define o pino de dados para o sensor DHT
  #define DHTTYPE DHT22   // Especifica o tipo do sensor como DHT22

  // Inicializa o sensor DHT
  DHT dht(DHTPIN, DHTTYPE);
  unsigned long millis_dht22_controle = 0;
  float temperatura, umidade;

  */

  // OLED configuration
  #define SCREEN_WIDTH 128 
  #define SCREEN_HEIGHT 64 
  #define OLED_RESET    -1 // Reset pin # (or -1 if sharing Arduino reset pin)
  Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
#endif

#if defined(GPS_INTEGRADO)
  // GPS Setup (UART2)
  TinyGPSPlus gps;
  HardwareSerial SerialGPS(2); // Use UART2

  // Controle de leitura do GPS no Void Loop
  unsigned long millis_gps_controle = 0;
  bool gps_satelite = false;

  int32_t lat = -22999394;

      // Longitude -46.818973
  int32_t lon = -46818973;

      // Altitude (metros sem casas decimais, convertida explicitamente para inteiro de 16 bits)
  int16_t alt = 785;
#endif

// ============================================================
// CONFIGURAÇÕES LoRa OTIMIZADAS COM LUT
// ============================================================
uint8_t radio_config_index = 63;        // Índice da configuração (0-71)
                                         // 63 = SF12, BW125kHz, CR4/8 (default)

// Variáveis mantidas para compatibilidade com MAC (podem ser removidas depois):
int valor_atual_spreadingfactor = 12;
int valor_atual_bandwidth = 125E3;
int valor_atual_codingrate = 8;
int valor_atual_potencia_radio = 20;

/*
// # Configuração Atual Rádio LoRa
int valor_atual_spreadingfactor = 12; // # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
int valor_atual_bandwidth = 125E3; // # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
int valor_atual_codingrate = 8; // # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
int valor_atual_potencia_radio = 20; // # TX Power = 1 a 17???
*/

// # Configuração Nova Rádio LoRa
int valor_novo_spreadingfactor = 12; // # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
int valor_novo_bandwidth = 125E3; // # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
int valor_novo_codingrate = 8; // # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
int valor_novo_potencia_radio = 20; // # TX Power = 1 a 17???



// # Configuração Anterior Rádio LoRa
int valor_anterior_spreadingfactor = 12; // # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
int valor_anterior_bandwidth = 125E3; // # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
int valor_anterior_codingrate = 8; // # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
int valor_anterior_potencia_radio = 20; // # TX Power = 1 a 17???
int recebe_comando_anterior_radio = 0; // # Comando de Downlink de mudança de configuração de rádio LoRa

uint8_t inicia_lora_site_survey = 0;
uint8_t confirma_novo_radio = 0;
uint8_t confirma_novo_radio_base = 10; // AAF 17-09 inicio do Estado_DL == 10
uint8_t confirma_novo_radio_sensor = 0;
//int recebe_comando_nova_radio = 0; // # Comando de Downlink de mudança de configuração de rádio LoRa

unsigned int primeiro_setup = 1; // Indica o Startup do Módulo pela primeira vez

unsigned long lastPacketMillis = 0; 
unsigned long lastPacketTime = 0; // Timestamp local do último pacote recebido
int lostPacketCounter = 0;        // Contador de falhas
bool communicationLost = false;

unsigned long time_out_lora_dl = 60000UL; // 1 min. time out Pacote_DL
unsigned long millis_mqtt_controle = 0;
// ============================================================
// VARIÁVEIS GLOBAIS - adicionar junto às demais declarações
// ============================================================

unsigned long millis_standby_controle = 0;   // Marca o instante em que pacote foi recebido
unsigned long millis_inicio_controle = 0;   // Marca o instante em que MAC4_COMANDO == foi recebido
unsigned long millis_radio_control = 0;
bool st_led_vermelho = false;
unsigned long millis_contador_DL = 0;   // Marca o instante em que pacote foi recebido
bool Perda_DL = 0;

bool controle_ativo = false;                 // Flag que indica se a contagem está em andamento
uint8_t recebe_comando_nova_radio = 0;       // Comando recebido em MAC4_COMANDO
uint8_t contador_perda_DL = 0;


