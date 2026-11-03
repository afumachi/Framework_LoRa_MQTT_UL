    
//=======================================================================
// 1 - Bibliotecas
//=======================================================================

// Bibliotecas comuns para os Hardwares ESP32 e NodeMCU
#include <SPI.h>
#include <LoRa.h>


// ============================================================
// TABELA DE CONFIGURAÇÃO DE RÁDIO
// ============================================================
#include "Tabela_Radio_LUT.h"

//=======================================================================
// 2 - Mapeamento dos Pinos
//=======================================================================

//=======================================================================
// 3 - Variáveis
//=======================================================================
// Identificação do Nó Sensor e Tamanho de Pacote

#define MY_ID 0

#define TAMANHO_PACOTE_DL 20
#define TAMANHO_PACOTE_UL 20

byte PacoteDL[TAMANHO_PACOTE_DL];
byte PacoteUL[TAMANHO_PACOTE_UL];

// Taxa de comunicação Serial/USB para Debug
#define TAXA_SERIAL 115200

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

uint8_t ID_gateway = 0;

// Váriáveis utilizadas no código
uint16_t contadorUL = 0;
uint16_t contadorDL = 0;
uint16_t contador_medidas_total = 0; 
uint16_t contador_medidas = 0;
uint16_t    contadorSS = 0;
int LQI_UL;
int tipo, saltos, saltosTotal, dataInitAddress; // Variáveis utilizadas para o roteamento

float RSSI_dBm_UL;    // Variável com a potência rádio recebida (RSSI) em dBm
int RSSI_UL;          // Variável de mapeamento da RSSI em um valor de 0 a 255 para colocar no pacote

float SNR_UL_bruto;   // Variável com a relação sinal ruído
uint8_t SNR_UL;           // Variável inteira para enviar a SNR, que será convertida para a SNR original no Python

// # Configuração Atual Rádio LoRa
int valor_atual_spreadingfactor = 12; // # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
int valor_atual_bandwidth = 125E3; // # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
int valor_atual_codingrate = 8; // # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
int valor_atual_potencia_radio = 14; // # TX Power = 1 a 17???

// # Configuração Nova Rádio LoRa
int valor_novo_spreadingfactor = 12; // # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
int valor_novo_bandwidth = 125E3; // # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
int valor_novo_codingrate = 8; // # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
int valor_novo_potencia_radio = 14; // # TX Power = 1 a 17???

// # Configuração Anterior Rádio LoRa
int valor_anterior_spreadingfactor = 12; // # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
int valor_anterior_bandwidth = 125E3; // # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
int valor_anterior_codingrate = 8; // # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
int valor_anterior_potencia_radio = 14; // # TX Power = 1 a 17???
int recebe_comando_anterior_radio = 0; // # Comando de Downlink de mudança de configuração de rádio LoRa

uint8_t inicia_lora_site_survey = 0;
uint8_t confirma_novo_radio = 0;
uint8_t confirma_novo_radio_base = 0;
uint8_t confirma_novo_radio_sensor = 0;
//int recebe_comando_nova_radio = 0; // # Comando de Downlink de mudança de configuração de rádio LoRa

unsigned long lastPacketMillis = 0; 
unsigned long lastPacketTime = 0; // Timestamp local do último pacote recebido
int lostPacketCounter = 0;        // Contador de falhas
bool communicationLost = false;

// ============================================================
// VARIÁVEIS GLOBAIS - adicionar junto às demais declarações
// ============================================================

unsigned long millis_inicio_comando4 = 0;   // Marca o instante em que MAC4_COMANDO == 4 foi recebido
bool comando4_ativo = false;                 // Flag que indica se a contagem está em andamento
uint8_t tempo_radio = 0;                     // Tempo recebido em MAC3_TEMPO (em ms ou unidade definida pelo protocolo)
uint8_t recebe_comando_nova_radio = 0;       // Comando recebido em MAC4_COMANDO

// ============================================================
// VARIÁVEIS GLOBAIS - adicionar junto às demais declarações
// ============================================================

unsigned long millis_inicio_aguarda_UL = 0;  // Marca o instante em que o DL com COMANDO 4 foi enviado
bool aguardando_confirmacao_UL = false;       // Flag: gateway está aguardando UL de confirmação do sensor

// Tempo de controle de standby Pacote_UL
unsigned long millis_standby_controle = 0; // Marca o instante em que pacote foi recebido
unsigned long time_out_lora_ul = 60000UL;  // 1 min. time out Pacote_UL

unsigned long millis_mqtt_controle = 0;
unsigned long millis_radio_control = 0;
bool st_led_vermelho = 0;

  // adicionar um conjunto de variáveis PKT_UL e PKT_DL para deixar os pacotes independentes

  // --- Physical Layer ---
#define RSSI_DOWNLINK 0
#define LQI_DOWNLINK  1
#define RSSI_UPLINK   2
#define LQI_UPLINK    3

  // --- MAC Layer ---
#define MAC_COUNTER_MSB 4 
#define MAC_COUNTER_LSB 5
#define MAC3_TEMPO 6
#define MAC4_COMANDO 7

  // --- Network Layer ---
#define  RECEIVER_ID     8
#define  NET2            9
#define  TRANSMITTER_ID  10
#define  NET4            11

  // --- Transport Layer ---
#define DL_COUNTER_MSB 12
#define DL_COUNTER_LSB 13
#define UL_COUNTER_MSB 14
#define UL_COUNTER_LSB 15

