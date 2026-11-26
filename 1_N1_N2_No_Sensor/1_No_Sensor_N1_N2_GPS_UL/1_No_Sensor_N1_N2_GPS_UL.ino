/*
  MoT LoRa Site Survey Versão Configura Rádio | WissTek IoT
  Última versão: Branquinho / Anderson
  Hardware: PKLoRa ESP32 ou PKLoRa NodeMCU
  Nó Sensor - 
*/

//=======================================================================
// 1 - Escolha do Módulo - ESP32 ou NodeMCU
//=======================================================================

// Remova o comentário da linha referente ao módulo que você está utilizando e comente a outro

#define PKLORA_ESP32 // HARDWARE COM ESP32
//#define JVTECH_ESP32   // HARDWARE COM RFM96 + ESP32 da JVTECH
//#define PKLORA_NODEMCU // HARDWARE COM ESP12E - NODEMCU

// Caso tenha sensor GPS integrado ao Módulo
//#define SEM_GPS // MoT 20 Bytes
#define GPS_INTEGRADO // MoT 30 Bytes

// Caso tenha Display OLED integrado ao Módulo
//#define OLED_INTEGRADO

//=======================================================================
// 2 - Biblioteca - chama o arquivo Biblioteca.h
//=======================================================================

#include "Bibliotecas.h"  // Arquivo contendo declaração de bibliotecas e variáveis

//=======================================================================
// 3 - Configuração de Setup de Rádio LoRa
//=======================================================================

// ============= CAMADA FÍSICA
// Parâmetros do LoRa
#define FREQUENCY_IN_HZ            903E6    // LoRa Frequency
#define txPower                    20       // TX power in dBm, defaults to 17
#define spreadingFactorSetup       12       // ranges from 6-12,default 7
#define signalBandwidthSetup       125E3    // signal bandwidth in Hz
#define codingRateDenominatorSetup 8        // denominator of the coding rate

// Habilita ou disabilita o uso CRC, por padrão o CRC não é usado.
//#define loraCRC

// Váriáveis utilizadas no código
int RSSI_dBm_DL; // Variável com a potência rádio recebida (RSSI) em dBm
int RSSI_DL;     // Variável de mapeamento da RSSI em um valor de 0 a 255 para colocar no pacote

float SNR_DL_bruto;   // Variável com a relação sinal ruído
uint8_t SNR_DL;           // Variável inteira para enviar a SNR, que será convertida para a SNR original no Python

// ============== CAMADA MAC

#define TAMANHO_PACOTE_DL 20

#if defined(GPS_INTEGRADO)
  #define TAMANHO_PACOTE_UL 30
#elif defined(SEM_GPS)
  #define TAMANHO_PACOTE_UL 20
#endif

byte PacoteDL[TAMANHO_PACOTE_DL];
byte PacoteUL[TAMANHO_PACOTE_UL];

bool lss_mode = 0;
bool uplink_mode = 0;
unsigned long tempo_radio = 200UL;                     // Tempo recebido em DL[6] (em ms ou unidade definida pelo protocolo)

// Variável global para armazenar o tempo da última execução
unsigned long ultimoTempo = 0; 
// Intervalo de tempo desejado em milissegundos
const long intervalo = 100;

// ============= CAMADA DE REDE
// Identificação do sensor e tamanho de pacote
int ID_sensor = 1; // Variável de iIdentificação do sensor que está no pacote de DL byte 8
int ID_gateway = 0;    // Variável com o ID_gateway que estará no pacote de DL byte 10

// ============== CAMADA DE TRANSPORTE
int contador_pkt_DL = 0; // Variável para o contador de pacotes de DL
int contador_pkt_UL = 0; // Variável para o contador de pacotes de UL
uint16_t contadorUL = 0;
uint16_t contadorDL = 0;
uint16_t medidasLSS = 0;

int luminosidade; // Variável que vai receber o valor da luminosidade entre 0 e 4095 - ADC 12 bits
uint8_t feedback_led_amarelo = 0;

//=======================================================================
// 4 - Setup de inicialização
//=======================================================================
// Inicializa as camadas
void setup() {

  Serial.begin(115200);
  delay(20);
  Serial.println("--- Iniciando Nó Sensor LoRa ---");

  #if defined(PKLORA_ESP32) || defined(PKLORA_NODEMCU)
    // --- Inicialização de I/O ---
    pinMode(LED_VERMELHO_PIN, OUTPUT);
    pinMode(LED_VERDE_PIN, OUTPUT);
    pinMode(LDR_PIN, INPUT);

  #endif

  #if defined(PKLORA_ESP32)
    pinMode(BOTAO_PIN, INPUT); 
    pinMode(LED_AMARELO_PIN, OUTPUT);
    // Configuração ADC para o LDR
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);
  #endif

  #if defined(PKLORA_ESP32) || defined(PKLORA_NODEMCU)
    // Garante que os LEDs iniciem desligados
    digitalWrite(LED_VERMELHO_PIN, LOW);
    digitalWrite(LED_VERDE_PIN, LOW);
  #endif

  #if defined(PKLORA_ESP32)
    digitalWrite(LED_AMARELO_PIN, LOW);

  #endif

  #if defined(GPS_INTEGRADO)
    // GPS Serial: Baud 9600, Pins: RX=16, TX=17
    SerialGPS.begin(9600, SERIAL_8N1, 16, 17);
  #endif
  #if defined(OLED_INTEGRADO)
    // Initialize I2C with your specific pins (SDA = 21, SCL = 22)
    Wire.begin(21, 22);
    delay(100);

    // Initialize OLED display
    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // 0x3C is common I2C address
      Serial.println(F("SSD1306 allocation failed"));
      for(;;); 
    }
    
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    delay(100);

  #endif

    // --- Inicialização Módulo RF95 (LoRa) ---
  #if defined(PKLORA_ESP32) || defined(JVTECH_ESP32)
    // 1. Remapeia e inicializa o barramento SPI com os pinos do seu Kit
    SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
  #endif
  
  // 2. Informa à biblioteca LoRa os pinos de controle
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    Serial.println("Erro ao iniciar módulo RFM95");
  }
 
  Serial.println("LoRa Inicializado com Sucesso!");

  #if defined(OLED_INTEGRADO)
    // Limpa o Display
    display.clearDisplay();

    // Escreve o Título Display
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("PKLoRa Site Survey");
    display.drawLine(0, 12, 128, 12, SSD1306_WHITE);    

    // Escreve valor do LDR
    display.setTextSize(1);
    display.setCursor(0, 17);
    display.println("PKLoRa Inicializado");
    display.println("");  
    display.setTextSize(2);
    display.println("SUCESSO!"); 

    // Escreve o buffer na tela Oled
    display.display();
  #endif

  #ifdef loraCRC   // Habilitação do CRC do chip lora  (Configurado em bibliotecas.h)
    LoRa.enableCrc();
  #endif

  #if defined(PKLORA_ESP32) || defined(PKLORA_NODEMCU)
    // Pisca o LED Verde para indicar inicialização bem-sucedida
    digitalWrite(LED_VERDE_PIN, HIGH);
    delay(2000);
    digitalWrite(LED_VERDE_PIN, LOW);
  #endif

  #if defined(JVTECH_ESP32)
    // Acende em VERDE (Pino, Vermelho, Verde, Azul de 0 a 255)
    neopixelWrite(PIN_RGB, 0, 255, 0);
    delay(2000);
    neopixelWrite(PIN_RGB, 0, 0, 0);
  #endif  

} // FIM DO SETUP

//=======================================================================
//  5 - Loop de repetição
//=======================================================================
// A função loop irá executar repetidamente
void loop() {
    
  // --- Controle de timeout do Comando 4 ---
  // Executado a cada iteração do loop, independente de novo pacote chegar
  if (controle_ativo) {
    unsigned long tempo_limite_ms = (unsigned long)tempo_radio * 100UL * 1000UL; // 10x o valor recebido em MAC3_TEMPO

    if (millis() - millis_inicio_controle >= tempo_limite_ms) {
      //reset_para_setup_inicial(); // Timeout atingido → volta ao SETUP
    }
    millis_inicio_controle = millis();
  }

  unsigned long tempo_standby_ms = 10UL * time_out_lora_dl; // 10 min. sem Pacotes DL sobe para MAX  

  if ((millis() - millis_standby_controle >= tempo_standby_ms)) {
    Serial.println("TEMPO SEM RECEBER PACOTES - Time-Out");
    Serial.println("Voltando a Configuração LoRa MDC");
    millis_standby_controle = millis();
    //reset_para_setup_inicial(); // Timeout atingido → volta ao SETUP
  }     

  #if defined(GPS_INTEGRADO)
    // Lê os caracteres do GPS a cada 200 [ms]
    unsigned long tempo_sensores_ms = 200UL; // 200 ms

    if (millis() - millis_gps_controle >= tempo_sensores_ms) {        
      updateGPS(); // Atualiza / Lê GPS
      //Serial.println("FUNÇÃO UPDATE GPS");  
      // Zera contagem do tempo de controle GPS para tempo de ESP32 rodando
      millis_gps_controle = millis(); 
    }
  #endif

  //if (uplink_mode == 0){
    Phy_radio_receive_DL(); // Função que recebe os pacotes pelo rádio
  //}
  //else if(uplink_mode == 1){// era somente if aaf 09/11
    
    unsigned long tempoAtual = millis(); // estava fora, antes do if aaf 09/11

    // Verifica se a diferença entre o tempo atual e a última execução é de 500ms ou mais
    if (tempoAtual - ultimoTempo >= intervalo) {
      // Salva o tempo atual como o tempo da última execução
      ultimoTempo = tempoAtual;

      // Chama a sua função
      App_radio_send_UL();
    }
  //}

}

