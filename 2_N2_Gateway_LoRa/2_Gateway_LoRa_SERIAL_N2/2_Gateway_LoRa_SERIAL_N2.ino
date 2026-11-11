/*
//  MoT LoRa | WissTek IoT
//
//  Implementa o Gateway LoRa MQTT
//
//  Versão Gateway LoRa MQTT com QoS1: Gateway PKLoRa via broker MQTT ↔ comunicação Borda IoT Python N2_N3
//  - Mantém toda a camada de rádio LoRa (RFM95) do Framework Basic Local
//  - Substitui USB/Serial por Wi-Fi + MQTT [PHY]
//  - Usa a biblioteca MQTT by Joel Gaehwiler Vs. 2.5.3 (MQTT.h) para suportar QoS1 (MQTT com ACK)
//
//  Tópicos Publicados no Broker MQTT
//
//  - DL: assina "mot_lora_SEU_RA/gateway/downlink"  
//    Gateway LoRa ← realiza leitura via Broker MQTT da publicação do Tópico de Downlink do Python
//
//  - UL: publica em "mot_lora_SEU_RA/gateway/uplink"
//    Gateway → publica Tópico de Uplink ao Broker MQTT - Python N2_N3 realiza a leitura
//
//  Última Modificação: Branquinho / Guilherme / Luís Felipe / Anderson - 17/10/2026
//
*/

//=======================================================================
// 0 - Escolha do Módulo - ESP32 ou NodeMCU
//=======================================================================

// Remova o comentário da linha referente ao módulo que você está utilizando e comente a outro

//#define PKLORA_ESP32 // #define PKLORA_ESP32
#define PKLORA_NODEMCU // #define PKLORA_NODEMCU

// =====================================================================
//                     1 - Bibliotecas
// =====================================================================
#include <SPI.h>
#include <LoRa.h>


#if defined(PKLORA_ESP32)
  // ---- DECLARAÇÃO DIAGRAMA DE PINOS DO PROJETO ----
  // Pinos utilizados para comunicação SPI entre ESP32 e RFM95 - Módulo LoRa

  // ============= Pinagem na placa da PK-LoRa da ligação do RFM95 com o ESP32
  #define SCK_PIN   5
  #define MISO_PIN  19
  #define MOSI_PIN  27
  #define NSS_PIN   18
  #define RST_PIN   14
  #define DIO0_PIN  26
  #define DIO1_PIN  35
  #define DIO2_PIN  34

  // Pinos dos LEDs
  #define LED_VERMELHO_PIN  15    // PINO 15
  #define LED_VERDE_PIN     4    // PINO 4
  

#elif defined(PKLORA_NODEMCU)
  // ============= Pinagem na placa da PK-LoRa da ligação do RFM95 com o Node-MCU
  #define SCK_PIN   14    // PIN D5
  #define MISO_PIN  12    // PIN D6
  #define MOSI_PIN  13    // PIN D7
  #define NSS_PIN   15    // PIN D8
  #define RST_PIN   0     // PIN D3
  #define DIO0_PIN  5     // PIN D1

  // Pinos dos LEDs
  #define LED_VERMELHO_PIN  4    // PINO D4
  #define LED_VERDE_PIN     2    // PINO D2

#else
  #error "Por favor, definir a placa de hardware  (PKLORA_ESP32 ou PKLORA_NODEMCU) no topo deste código!"
#endif

// =====================================================================
//                     6 - Parâmetros LoRa
// =====================================================================
#define FREQUENCY_IN_HZ       915E6     // Frequência de operação
#define txPower               14        // Potência de transmissão 17 dBm
#define spreadingFactor       7        // Configuração SRC = 7     |  LRC=12
#define signalBandwidth       500E3    // Configuração SRC = 500E3  |  LRC=125E3
#define codingRateDenominator 5         // Configuração SRC = 5     |  LRC=8 
/*
// =====================================================================
//                     7 - Pinos de LED
// =====================================================================
#define LED_VERMELHO_PIN 15
#define LED_VERDE_PIN     4
*/
// =====================================================================
//                     8 - Variáveis do Gateway
// =====================================================================
#define Tamanho_pacote 20

byte  PacoteDL[Tamanho_pacote];
byte  PacoteUL[Tamanho_pacote];
uint8_t   ID_gateway;

float RSSI_dBm_UL;    // Variável com a potência rádio recebida (RSSI) em dBm
int RSSI_UL;          // Variável de mapeamento da RSSI em um valor de 0 a 255 para colocar no pacote

float SNR_UL_bruto;   // Variável com a relação sinal ruído
uint8_t SNR_UL_inteiro;           // Variável inteira para enviar a SNR, que será convertida para a SNR original no Python

int       Conta_Pacote_DL = 0;


// =====================================================================
//                    10 - Setup
// =====================================================================
void setup() {
  Serial.begin(115200);
  // Aguarda para estabilização da Serial
  delay(20);

  // Declara os pinos dos LEDs como saídas digitais
  pinMode(LED_VERMELHO_PIN, OUTPUT);
  pinMode(LED_VERDE_PIN,    OUTPUT);

  // Inicia os LEDs apagados
  digitalWrite(LED_VERMELHO_PIN, LOW);
  digitalWrite(LED_VERDE_PIN,    LOW);

#if defined(PKLORA_ESP32)
  // ---------- Inicia módulo LoRa RFM95 ----------
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
#endif
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    Serial.println("[LoRa] Erro ao iniciar modulo!");
    while (true) { delay(1000); }
  }

  // configura os parâmetros de rádio LoRa no RFM95
  LoRa.setTxPower(txPower);
  LoRa.setSpreadingFactor(spreadingFactor);
  LoRa.setSignalBandwidth(signalBandwidth);
  LoRa.setCodingRate4(codingRateDenominator);

  // Pisca verde - tudo OK
  digitalWrite(LED_VERDE_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_VERDE_PIN, LOW);
}

// =====================================================================
//                    10 - Loop principal
// =====================================================================
void loop() {

  // Verifica se chegou pacote DL via Serial e o envia pelo rádio LoRa
  Phy_serial_receive_DL();

  // Verifica se chegou pacote UL via rádio LoRa e o publica no broker
  Phy_radio_receive_UL();
}
