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

#define PKLORA_ESP32 // #define PKLORA_ESP32
//#define PKLORA_NODEMCU // #define PKLORA_NODEMCU

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
  #define LED_VERMELHO_PIN  2    // PINO D4
  #define LED_VERDE_PIN     4    // PINO D2

#else
  #error "Por favor, definir a placa de hardware  (PKLORA_ESP32 ou PKLORA_NODEMCU) no topo deste código!"
#endif

#include <WiFi.h>

#include <WiFiMulti.h>
#include <MQTT.h>   // 256dpi/arduino-mqtt -- instalar via Library Manager: "MQTT" by 256dpi
                    // MQTT by Joel Gaehwiler Vs. 2.5.3 (MQTT.h)

// =====================================================================
//                     2 - Configurações Wi-Fi
// =====================================================================
// Instancia o objeto WiFiMulti
WiFiMulti wifiMulti;
// --- Objeto Wi-Fi Client ---
WiFiClient wifiClient;

// =====================================================================
//                     3 - Configurações MQTT
// =====================================================================

// Configurações do Broker Mosquitto (Usando o broker público oficial)
//const char* MQTT_BROKER = "test.mosquitto.org";

// Configurações do Broker HiveMQ (Usando o broker público oficial)
//const char* MQTT_BROKER   = "broker.hivemq.com";

// Configurações do Broker HiveMQ (Usando o broker público oficial)
const char* MQTT_BROKER   = "www.tpm.dev.br";

const int   MQTT_PORT     = 1883;
const char* TOPIC_DL      = "mot_mqtt_194104/gateway/downlink";  // Python → ESP32
const char* TOPIC_UL      = "mot_mqtt_194104/gateway/uplink";    // ESP32  → Python
String CLIENT_ID ;         // ID único no broker através do Endereço MAC do ESP32

// QoS usado nos dois sentidos (DL e UL). QoS1 = "at least once": o broker
// confirma o recebimento (PUBACK) e a biblioteca retransmite se necessário.
// Importante para o dado do cliente (luminosidade).
const int MQTT_QOS = 1;

// --- Objeto MQTT ---
MQTTClient mqttClient(256);   // buffer de 256 bytes (read/write)

// =====================================================================
//                     4 - Configurações Wi-Fi
// =====================================================================

void wifi_mqtt(){
  // Cadastre quantas redes você quiser (SSID, Senha)
  wifiMulti.addAP("MJCA_FUNDOS", "21092429MJC@");
  wifiMulti.addAP("COLETTI_ADV_CRIS", "45384609");

  //wifiMulti.addAP("SSID_1", "Password_1");
  //wifiMulti.addAP("SSID_2", "Password_2");
  //wifiMulti.addAP("SSID_3", "Senha_3");
  //wifiMulti.addAP("SSID_4", "Senha_4");

}
/*
// =====================================================================
//                     5 - Pinagem ESP32 <-> RFM95 (Kit PKLORa Vs3.1)
// =====================================================================
#define SCK_PIN    5
#define MISO_PIN  19
#define MOSI_PIN  27
#define NSS_PIN   18
#define RST_PIN   14
#define DIO0_PIN  26
*/
// =====================================================================
//                     6 - Parâmetros LoRa
// =====================================================================
#define FREQUENCY_IN_HZ       903E6     // Frequência de operação
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

int       RSSI_dBm_UL;
int       RSSI_UL;
float     SNR_UL;
uint8_t   SNR_UL_inteiro;
int       Conta_Pacote_DL = 0;

// =====================================================================
//                     9 - Variáveis MQTT
// =====================================================================

// --- Buffer e flag para o pacote DL recebido via MQTT ---
volatile bool mqtt_dl_disponivel = false;
byte          mqtt_dl_payload[Tamanho_pacote];

// =====================================================================
//                    10 - Setup
// =====================================================================
void setup() {
  Serial.begin(115200);
  // Aguarda para estabilização da Serial
  delay(20);

  // Chama a função das redes WiFi para conexão
  wifi_mqtt();

  // O wifiMulti.run() tenta conectar a uma das redes cadastradas
  // Ele retorna WL_CONNECTED quando consegue se conectar com sucesso
  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi conectado com sucesso!");
  Serial.print("Conectado na rede: ");
  Serial.println(WiFi.SSID());
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());

  // Declara os pinos dos LEDs como saídas digitais
  pinMode(LED_VERMELHO_PIN, OUTPUT);
  pinMode(LED_VERDE_PIN,    OUTPUT);

  // Inicia os LEDs apagados
  digitalWrite(LED_VERMELHO_PIN, LOW);
  digitalWrite(LED_VERDE_PIN,    LOW);

  CLIENT_ID = "esp32_gateway+lora_" + String(WiFi.macAddress());
  CLIENT_ID.replace(":", "");

  // ---------- Inicia conexão com broker MQTT ----------
  mqttClient.begin(MQTT_BROKER, MQTT_PORT, wifiClient);
  mqttClient.onMessageAdvanced(mqtt_callback);
  conectar_mqtt();

  // ---------- Inicia módulo LoRa RFM95 ----------
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
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

  Serial.println("[LoRa] Gateway inicializado com sucesso!");
  Serial.println("[INFO] Aguardando pacotes DL via MQTT (QoS1)...");

  // Pisca verde - tudo OK
  digitalWrite(LED_VERDE_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_VERDE_PIN, LOW);
}

// =====================================================================
//                    10 - Loop principal
// =====================================================================
void loop() {

  // Mantém conexões ativas
  // No loop, você pode monitorar a conexão.
  // Se a rede cair, o wifiMulti.run() tenta reconectar automaticamente à melhor rede disponível.
  if (wifiMulti.run() != WL_CONNECTED) {
    Serial.println("Conexão perdida! Tentando reconectar...");
    delay(1000);
  }

  if (!mqttClient.connected()) {
    conectar_mqtt();
  }
  mqttClient.loop();   // processa envio/recebimento e handshakes de QoS1/2

  // Verifica se chegou pacote DL via MQTT e o envia pelo rádio LoRa
  Phy_mqtt_receive_DL();

  // Verifica se chegou pacote UL via rádio LoRa e o publica no broker
  Phy_radio_receive_UL();
}
