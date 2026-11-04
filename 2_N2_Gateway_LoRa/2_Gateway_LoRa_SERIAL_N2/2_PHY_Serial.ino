/*
//  MoT LoRa | WissTek IoT
//  Versão Serial: comunicação Python N2_N3 ↔ Gateway PKLoRa
//
//  Camada PHY do Gateway LoRa Serial
//
//  Última Modificação: Branquinho / Felipe / Luís Felipe / Anderson - 27/06/2026
*/

// Camada Física PHY to Framework
//
// RECEBE PACOTE DOWNLINK
void Phy_serial_receive_DL() {

  if (Serial.available() >= Tamanho_pacote) {  // Testa se tem 52 bytes na serial

    for (byte i = 0; i < Tamanho_pacote; i++)  // PacoteUL[#] é preenchido com zero e PacoteDL[#] recebe os bytes do buffer
    {
      PacoteDL[i] = Serial.read();  // Recebe os bytes do buffer para o pacote de transmissão
    }
    ID_gateway = PacoteDL[10]; // Identifica que gateway que está enviando o pacote de DL

    Conta_Pacote_DL = (PacoteDL[12] << 8) | PacoteDL[13];

    // Chama camada física para transmitir pelo rádio RFM95
    Phy_radio_send_DL();
  }
}

// ==================== ENVIA PACOTE DL PELO RÁDIO RFM95 ==============
// (sem alterações em relação à versão serial)
void Phy_radio_send_DL() {

  // Pisca LED Vermelho → TX para nó sensor
  digitalWrite(LED_VERMELHO_PIN, HIGH);

  LoRa.beginPacket();
  for (int i = 0; i < Tamanho_pacote; i++) {
    LoRa.write(PacoteDL[i]);
  }
  LoRa.endPacket();
  LoRa.idle();  // Retorna ao modo standby/recepção
  
  digitalWrite(LED_VERMELHO_PIN, LOW);
}

// ==================== RECEBE PACOTE UL DO RÁDIO RFM95 ==============
// (sem alterações em relação à versão serial)
void Phy_radio_receive_UL() {

  uint8_t packetSize = LoRa.parsePacket();
  if (packetSize > 0) {
    if (packetSize >= Tamanho_pacote) {
      
      // Pisca LED Verde → RX confirmado
      digitalWrite(LED_VERDE_PIN, HIGH);
      
      for (int i = 0; i < Tamanho_pacote; i++) {
        PacoteUL[i] = LoRa.read();
      }

      RSSI_dBm_UL = LoRa.packetRssi();
      SNR_UL_bruto = LoRa.packetSnr();
      
      LoRa.idle(); // Retorna ao modo standby-recepção

      digitalWrite(LED_VERDE_PIN, LOW);

      // Chama função de envio UL agora via MQTT
      Phy_serial_send_UL();
    }
  }
}

// ==================== PUBLICA PACOTE UL NO BROKER MQTT ==============
// Substitui Phy_serial_send_UL(): envia o pacote UL ao Python via MQTT
void Phy_serial_send_UL() {

  // Calcula RSSI linear e aloca em 1 Byte conforme Documentação RFM95 de -10,5 dBm a -138dBm

  // Determina o offset baseado na frequência usada
  // (Ajuste para 164 se estiver usando 433MHz)
  int offset = 157; // Offset 157 para Frequência de 915MHz

  // Recupera o valor bruto (PacketRssi) para aplicar a nova fórmula
  int Rssi_UL_bruto = RSSI_dBm_UL + offset;

  if (SNR_UL_bruto >= 0) {
    // Sua fórmula com correção de linearidade (16/15)
    RSSI_dBm_UL = ((1.0666 * Rssi_UL_bruto) - offset); // 16/15 * RSSI - 157
  } else {
    // Fórmula para sinal abaixo do ruído (SNR < 0)
    RSSI_dBm_UL = ((Rssi_UL_bruto - offset) + (SNR_UL_bruto));
  }  

  //--- Bloco que faz adequação da leitura de RSSI para um byte ---
  if (RSSI_dBm_UL > -10.5)   // Caso a RSSI medida esteja acima do valor superior -10,5 dBm
  {
    RSSI_UL = 127;  // equivalente a -10,5 dBm
  }

  if (RSSI_dBm_UL <= -10.5 && RSSI_dBm_UL >= -74)  // Caso a RSSI medida esteja no intervalo [-10,5 dBm e -74 dBm]
  {
    RSSI_UL = ((RSSI_dBm_UL + 74) * 2);
  }

  if (RSSI_dBm_UL < -74)  // Caso a RSSI medida esteja no intervalo ]-74 dBm e -138 dBm]
  {
    RSSI_UL = (((RSSI_dBm_UL + 74) * 2) + 256);
  }

  // 1. Trava o valor entre -30 e +30 para evitar que o byte estoure
  if (SNR_UL_bruto < -30.0) SNR_UL_bruto = -30.0;
  if (SNR_UL_bruto > 30.0) SNR_UL_bruto = 30.0;

  // Usamos uint8_t (byte) para ocupar apenas 1 byte na memória.
  // Usamos a função round() para garantir que o número float seja 
  // arredondado corretamente antes de virar inteiro.
  SNR_UL_inteiro = (uint8_t)round((SNR_UL_bruto + 30.0) * 4.0); // Offset de 30.0dB e passo de 0.25dB (* 4.0)

  // --- Armazena informações de gerência no pacote UL ---
  PacoteUL[2] = RSSI_UL;
  //SNR_UL      = SNR_UL * 100;
  //SNR_UL_inteiro = (int)SNR_UL;
  PacoteUL[3] = (byte)SNR_UL_inteiro;

  // --- Envia pela serial os 20 bytes no Pacote UL ---
  // Transmissão do pacote pela serial do ESP32 para o script em Python
  for (int i = 0; i < Tamanho_pacote; i++) {
    Serial.write(PacoteUL[i]);
  }

}

