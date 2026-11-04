// PWA Aplicativo de acesso

/*
  MoT LoRa Site Survey | WissTek IoT
  Última versão: Branquinho / Anderson 
  Hardware: PKLoRa ESP32
*/

//=======================================================================
// 1 - Escolha do Módulo - ESP32 ou NodeMCU
//=======================================================================

// Remova o comentário da linha referente ao módulo que você está utilizando e comente a outro

//#define PKLORA_ESP32 // #define PKLORA_ESP32
#define PKLORA_NODEMCU // #define PKLORA_NODEMCU

//=======================================================================
// 2 - Biblioteca - chama o arquivo Biblioteca.h
//=======================================================================

#include "Bibliotecas.h"  // Arquivo contendo declaração de bibliotecas e variáveis

//=======================================================================
// 4 - Configuração de Setup de Rádio LoRa
//=======================================================================

// ============= CAMADA FÍSICA
// Parâmetros do LoRa
#define FREQUENCY_IN_HZ            903E6    // LoRa Frequency
#define txPower                    14       // TX power in dBm, defaults to 17
#define spreadingFactorSetup       7       // ranges from 6-12,default 7
#define signalBandwidthSetup       500E3    // signal bandwidth in Hz
#define codingRateDenominatorSetup 5        // denominator of the coding rate

// Habilita ou disabilita o uso CRC, por padrão o CRC não é usado.
//#define loraCRC

bool lss_mode = 0;
bool uplink_mode = 0;

bool primeiro_setup = 1; // Indica o Startup do Módulo pela primeira vez

//=======================================================================
// 6 - Setup de inicialização 
//=======================================================================

// Inicializa as camadas
void setup() {
  //================= INICIALIZA SERIAL E MÓDULO RF95

  Serial.begin(115200);
  // Aguarda para estabilização da Serial
  delay(20);

  // declara Leds como saídas digital do ESP32
  pinMode(LED_VERMELHO_PIN, OUTPUT);
  pinMode(LED_VERDE_PIN, OUTPUT);
  digitalWrite(LED_VERMELHO_PIN, LOW);
  digitalWrite(LED_VERDE_PIN,    LOW);

  #if defined(PKLORA_ESP32)
    // --- Inicialização da Comunicação SPI entre o ESP32 e o Módulo LoRa RFM95 ---
    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
    delay(20);
    LoRa.setSPI(SPI);
    delay(20);
  #endif

  // --- Inicialização da Comunicação LoRa em 915Mhz---
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);
  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    //Serial.println("[Nó Sensor] Falha ao iniciar LoRa. Verifique conexões.");
    while (true); // Trava se o LoRa falhar
  }

  delay(1000);
  //  --- Atua Led vermelho  --- 
  digitalWrite(LED_VERMELHO_PIN, LOW); // LIGA LED VERMELHO - INDIFERENTE PARA O BOOT

  //  --- Atua Led verde  --- 
  digitalWrite(LED_VERDE_PIN, LOW);  // DESLIGA O LED VERDE - DEVE SER LOW DURANTE BOOT

  // Aguarda 1 segundo para estabilização
  delay(1000);

  //  --- Pisca Led verde  --- Sucesso ao Iniciar 
  digitalWrite(LED_VERMELHO_PIN, HIGH);  // DESLIGA O LED VERDE - DEVE SER LOW DURANTE BOOT
  digitalWrite(LED_VERDE_PIN, HIGH);  // 
  delay(2000);
  digitalWrite(LED_VERMELHO_PIN, LOW); 
  digitalWrite(LED_VERDE_PIN, LOW);  //

  #ifdef loraCRC   // Habilitação do CRC do chip lora  (Configurado em bibliotecas.h)
    LoRa.enableCrc();
  #endif

} // FIM DO SETUP


//=======================================================================
//                     4 - Loop de repetição
//=======================================================================
// A função loop irá executar repetidamente
void loop() {

  // Verifica se chegou pacote DL via Serial e o envia pelo rádio LoRa
  Phy_serial_receive_DL();

  // Verifica se chegou pacote UL via rádio LoRa e o publica no broker
  Phy_radio_receive_UL();
  

}
