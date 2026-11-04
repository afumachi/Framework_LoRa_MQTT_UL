
void Phy_radio_receive_DL() {

  // Parâmetros do LoRa caso primeira energização do módulo NodeMCU/ESP32
  if (primeiro_setup == 1){
    //Serial.println("Primeiro SETUP");
    LoRa.sleep();

    LoRa.setSpreadingFactor(spreadingFactorSetup);
    LoRa.setSignalBandwidth(signalBandwidthSetup);
    LoRa.setCodingRate4(codingRateDenominatorSetup);
    LoRa.setTxPower(txPower);

    LoRa.idle(); // Retorna ao modo standby-recepção

    primeiro_setup = 0;
    confirma_novo_radio_sensor = 0;
    confirma_novo_radio_base = 10; // stand-by
    confirma_novo_radio = 0;
    recebe_comando_nova_radio = 0;
    contador_perda_DL = 0;
    uplink_mode = 0;
    lss_mode = 0;
    contadorUL = 0;
    medidasLSS = 0;
    Serial.println("SETUP INICIAL - Sensor LoRa");

  }

  // Neste ponto zeramos o pacote de DL para garantir que ele não está carregando nenhuma informação de comunicação anterior.
  for (int i = 0; i < TAMANHO_PACOTE_DL; i++) {
    PacoteDL[i] = 0;    
  }
  
  // Escuta o Rádio LoRa se identificou algum preâmbulo de Pacote
  uint8_t packetSize = LoRa.parsePacket();

  // Caso positivo, identifica o tamanho do Payload do Pacote
  if (packetSize) {
    
    digitalWrite(LED_VERDE_PIN, HIGH); // Liga Led Verde Indicando Inicio da leitura do Pacote
    
    //Serial.println("Pacote DL IDENTIFICADO");
    // Realiza a leitura caso Payload do Pacote seja compatível com o Pacote de 6 Bytes
    if (packetSize >= TAMANHO_PACOTE_DL) {

      millis_standby_controle = millis();

      for (int i = 0; i < TAMANHO_PACOTE_DL; i++) {
        PacoteDL[i] = LoRa.read();  // Aloca no Pacote de DL os 6 bytes que vieram do RFM95
      }

      RSSI_dBm_DL = LoRa.packetRssi();
      SNR_DL_bruto = LoRa.packetSnr();

      // ADICIONADO Variáveis de recebimento do valores de rádio LoRa

      // NOVO: Recebe índice de configuração (0-71) em PacoteDL[0]
      radio_config_index = PacoteDL[1];

      // Valida índice
      if (radio_config_index <= 71) {
          // Armazena índice para usar após envio UL
          Serial.printf("[RX] Índice de configuração recebido: %d\n", radio_config_index);
      } else {
          Serial.printf("[RX] Índice INVÁLIDO recebido: %d (máximo: 71)\n", radio_config_index);
          radio_config_index = 63;  // Fallback para configuração padrão LONG Range
      }

      // PacoteDL[3] continua sendo TX Power (sem alteração)
      valor_novo_potencia_radio = PacoteDL[3];

      // Leitura dos bytes MAC de tempo e comando
      //tempo_radio               = uint8_t(PacoteDL[6]) * 1000UL;
      recebe_comando_nova_radio = PacoteDL[7];

      // --- Lógica de inicio da contagem para MAC4_COMANDO == 4 ---
      if (recebe_comando_nova_radio != 0) {

        if (!controle_ativo) {
          // Primeira vez que recebe o comando 4: inicia a contagem
          millis_inicio_controle = millis();
          controle_ativo         = true;

          Serial.println("[CONTROLE] Contagem iniciada. Tempo limite: ");
          //Serial.print((unsigned long)tempo_radio * 10UL * 1000UL);
          //Serial.println(" ms");

        } else {
          // Pacote com comando chegou novamente enquanto contagem ativa:
          // Reinicia a contagem com o novo tempo recebido
          millis_inicio_controle = millis();

          Serial.println("[CONTROLE] Contagem reiniciada. Novo tempo limite: ");
          //Serial.print((unsigned long)tempo_radio * 10UL * 1000UL);
          //Serial.println(" ms");
        }

      } else {
        // Chegou um pacote com comando diferente de 4: cancela contagem ativa
        if (controle_ativo) {
          Serial.println("[CONTROLE != 0] Contagem cancelada.");
          controle_ativo = false;
          millis_inicio_controle = 0;
        }
      }

      digitalWrite(LED_VERDE_PIN, LOW); // Fim da leitura do Pacote

      // Caso Pacote direcionado a este sensor, chama função MAC
      Mac_radio_receive_DL();

    }
  }
}  

//================ ENVIA O PACOTE UL ========
void Phy_radio_send_UL() {

  // Determina o offset baseado na frequência usada
  // (Ajuste para 164 se estiver usando 433MHz)
  int offset = 157; // Offset 157 para Frequência de 915MHz

  // Recupera o valor bruto (PacketRssi) para aplicar a nova fórmula
  int Rssi_DL_bruto = RSSI_dBm_DL + offset;

  if (SNR_DL_bruto >= 0) {
    // Sua fórmula com correção de linearidade (16/15)
    RSSI_dBm_DL = ((1.0666 * Rssi_DL_bruto) - offset); // 16/15 * RSSI - 157
  } else {
    // Fórmula para sinal abaixo do ruído (SNR < 0)
    RSSI_dBm_DL = ((Rssi_DL_bruto - offset) + (SNR_DL_bruto));
  }  
  
  #if defined(OLED_INTEGRADO)

    display.setTextSize(1);
    //  display.setCursor(0, 55);
    display.print("RSSI_DL : ");
    display.setTextSize(1);
    display.println(RSSI_dBm_DL, 0); 
    display.print("SNR_DL : ");
    display.setTextSize(1);
    display.println(Rssi_DL_bruto, 0);   

    // Escreve o buffer na tela Oled
    display.display();  
  #endif

  //--- Bloco que faz adequação da leitura de RSSI para um byte ---

  if(RSSI_dBm_DL > -10.5)  // Caso a RSSI medida esteja acima do valor superior -10,5 dBm
  {
   RSSI_DL = 127; // equivalente a -10,5 dBm 
  }

  if(RSSI_dBm_DL <= -10.5 && RSSI_dBm_DL >= -74) // Caso a RSSI medida esteja no intervalo [-10,5 dBm e -74 dBm]
  {
   RSSI_DL = ((RSSI_dBm_DL +74)*2) ;
  }

  if(RSSI_dBm_DL < -74) // Caso a RSSI medida esteja no intervalo ]-74 dBm e -138 dBm]
  {
   RSSI_DL = (((RSSI_dBm_DL +74)*2)+256) ;
  }

  // 1. Trava o valor entre -30 e +30 para evitar que o byte estoure
  if (SNR_DL_bruto < -30.0) SNR_DL_bruto = -30.0;
  if (SNR_DL_bruto > 30.0) SNR_DL_bruto = 30.0;

  // Usamos uint8_t (byte) para ocupar apenas 1 byte na memória.
  // Usamos a função round() para garantir que o número float seja 
  // arredondado corretamente antes de virar inteiro.
  SNR_DL = (uint8_t)round((SNR_DL_bruto + 30.0) * 4.0); // Offset de 30.0dB e passo de 0.25dB (* 4.0)

  // =================Informações de gerência do pacote Início da montagem do pacote de UL
  PacoteUL[0] = RSSI_DL;
  PacoteUL[1] = SNR_DL;

  // Pisca o LED de transmissão de pacote UL
  digitalWrite(LED_VERMELHO_PIN, HIGH); // Início da Transmissão

  LoRa.beginPacket();                 // Inicia o envio do pacote ao rádio
  
  for (int i = 0; i < TAMANHO_PACOTE_UL; i++) {
    LoRa.write(PacoteUL[i]);          // Envia byte a byte as informações para o Rádio
  }
  LoRa.endPacket();                   // Finaliza o envio do pacote
  LoRa.idle();  // Retorna ao modo standby/recepção
  
  digitalWrite(LED_VERMELHO_PIN, LOW); // Fim da Transmissão

  // Realiza a alteração das config. da Rádio LoRa apenas após o envio do segundo Pacote UL, 
  // e prepara o Nó Sensor para o terceiro ciclo já com as alterações realizadas
  if (confirma_novo_radio == 1){
    AplicarConfiguracoesRadio();
  }

  if (confirma_novo_radio_sensor == 5){
    contadorDL = 0;
    medidasLSS = 0;
    contadorUL = 0;
    contador_perda_DL = 0;
    uplink_mode = 0;
    lss_mode = 0;
    primeiro_setup = 1;
  }

}

// ============================================================
// FUNÇÃO Modifica configurações dos parâmetros de Rádio LoRa
// ============================================================

void AplicarConfiguracoesRadio() {

  if (confirma_novo_radio == 1){

    // Estrutura temporária para carregar os dados salvos na memória Flash (PROGMEM)
    RadioConfig config_atual;

    // Copia o registro da memória PROGMEM para a estrutura em RAM
    memcpy_P(&config_atual, &RADIO_CONFIG_LUT[radio_config_index], sizeof(RadioConfig));

    // Aloca os valores lidos da LUT nas variáveis de configuração do seu rádio
    valor_novo_spreadingfactor = config_atual.sf;
    valor_novo_bandwidth       = config_atual.bw;
    valor_novo_codingrate      = config_atual.cr;

    LoRa.sleep(); // Coloca em sleep para garantir a mudança de parâmetros

    LoRa.setSpreadingFactor(valor_novo_spreadingfactor);
    LoRa.setSignalBandwidth(valor_novo_bandwidth);
    LoRa.setCodingRate4(valor_novo_codingrate);
    LoRa.setTxPower(valor_novo_potencia_radio);                       // Potência de Transmissão (Configurado em bibliotecas.h)

    LoRa.idle();  // Retorna ao modo standby/recepção

    LoRa.idle(); // Retorna ao modo standby/recepção
    Serial.printf("[MAC] Índice de Reconfiguração : %d\n", radio_config_index);

    // Limpa flags da máquina de estado
    confirma_novo_radio_sensor = 0;
    confirma_novo_radio_base = 10;
    confirma_novo_radio = 0;
    recebe_comando_nova_radio = 0;
    primeiro_setup = 0;
    
    Serial.printf("[RADIO] Configuração %d aplicada e persistida\n", radio_config_index);

  }  

}


