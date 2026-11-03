// Camada Física PHY to Framework
//
// RECEBE PACOTE DOWNLINK
void Phy_serial_receive_DL() {

  // Parâmetros do LoRa caso primeira energização do módulo NodeMCU/ESP32
  if (primeiro_setup == 1) {

    LoRa.sleep();

    LoRa.setSpreadingFactor(spreadingFactorSetup);
    LoRa.setSignalBandwidth(signalBandwidthSetup);
    LoRa.setCodingRate4(codingRateDenominatorSetup);
    LoRa.setTxPower(txPower);

    LoRa.idle(); // Retorna ao modo standby-recepção

    // Zera flags e variáveis de controle
    aguardando_confirmacao_UL    = false;
    millis_inicio_aguarda_UL     = 0;
    tempo_radio                  = 0;
    recebe_comando_nova_radio    = 0;
    confirma_novo_radio_sensor   = 0;
    confirma_novo_radio_base = 0;
    confirma_novo_radio = 0;
    contadorDL = 0;
    contadorSS = 0;
    primeiro_setup = 0;
  }

  if (Serial.available() >= TAMANHO_PACOTE_DL) {  // Testa se tem 52 bytes na serial

    for (byte i = 0; i < TAMANHO_PACOTE_DL; i++)  // PacoteUL[#] é preenchido com zero e PacoteDL[#] recebe os bytes do buffer
    {
      PacoteDL[i] = Serial.read();  // Recebe os bytes do buffer para o pacote de transmissão
    }
    ID_gateway = PacoteDL[10]; // Identifica que gateway que está enviando o pacote de DL

    // ADICIONADO Variáveis de recebimento do valores de rádio LoRa

    //#if defined(PKLORA_ESP32)
    // Recebe o índice de configuração (0-71) do PacoteDL[0]
    uint8_t radio_config_index = PacoteDL[0];

    // Proteção contra índices fora do limite da tabela (0 a 71)
    // Valida índice
    if (radio_config_index <= 71) {
      // Armazena índice para usar após envio UL
      //Serial.printf("[PHY MQTT RX] Índice de configuração recebido: %d\n", radio_config_index);
    } else {
      //Serial.printf("[PHY MQTT RX] Índice INVÁLIDO recebido: %d (máximo: 71)\n", radio_config_index);
      radio_config_index = 8;  // Fallback para configuração padrão SHORT Range
    }

    // Estrutura temporária para carregar os dados salvos na memória Flash (PROGMEM)
    RadioConfig config_atual;

    // Copia o registro da memória PROGMEM para a estrutura em RAM
    memcpy_P(&config_atual, &RADIO_CONFIG_LUT[radio_config_index], sizeof(RadioConfig));

    // Aloca os valores lidos da LUT nas variáveis de configuração do seu rádio
    valor_novo_spreadingfactor = config_atual.sf;
    valor_novo_bandwidth       = config_atual.bw;
    valor_novo_codingrate      = config_atual.cr;

    //valor_novo_potencia_radio = 2;//PacoteDL[3];     // Byte DL[3] valor de rádio LoRa de Potência de Rádio LoRa
    lss_mode = int(PacoteDL[4]);
    tempo_radio = PacoteDL[6];                   // Byte DL[6] Recebe tempo de radio tx rx

    recebe_comando_nova_radio = PacoteDL[7];     // Byte DL[7] Recebe comando de reconfiguração de Rádio LoRa

    contador_medidas_total = (((PacoteDL[14])*256) + (PacoteDL[15])); // Número Total de medidas de teste LSS
    contador_medidas = (((PacoteDL[12])*256) + (PacoteDL[13]));     // Número de medidas corrente do teste LSS


    if ((recebe_comando_nova_radio == 1) ){
      // Radio Reconfig
      confirma_novo_radio_base = 2;
    }
    else if (recebe_comando_nova_radio == 3){
        // Link Test
        confirma_novo_radio_base = 3;
    }
    else if (recebe_comando_nova_radio == 4){
        // LSS DL-UL em Andamento
        confirma_novo_radio_base = 4;
    }
    else if (recebe_comando_nova_radio == 5){
        // Último pacote do LoRa Site Survey
        confirma_novo_radio_base = 5;
    }

    if (lss_mode == 1){
        // LSS UL Only
        confirma_novo_radio_base = 6;
        
        LoRa.sleep();
        LoRa.setSpreadingFactor(valor_novo_spreadingfactor);
        LoRa.setSignalBandwidth(valor_novo_bandwidth);
        LoRa.setCodingRate4(valor_novo_codingrate);
        LoRa.idle();  // Retorna ao modo standby/recepção

        Phy_radio_receive_UL();

    }
    else{
      Phy_radio_send_DL();  // chama a funcao de recepcao da camada de controle de acesso ao meio
    }

  }
}

// ENVIA PACOTE DL PARA NÓ SENSOR ATRAVÉS DO RF95
// O pacote DL recebido pelo MQTT proveniente do Nível 2_3 é enviado via LoRa para o Nó Sensor
void Phy_radio_send_DL() {

  // Pisca o LED de transmissão de pacote DL
  digitalWrite(LED_VERMELHO_PIN, HIGH);  // Início da Transmissão

/*

  LoRa.sleep();
  LoRa.setSpreadingFactor(valor_novo_spreadingfactor);
  LoRa.setSignalBandwidth(valor_novo_bandwidth);
  LoRa.setCodingRate4(valor_novo_codingrate);
  LoRa.idle();  // Retorna ao modo standby/recepção

*/

  LoRa.beginPacket();  // start packet
  for (int i = 0; i < TAMANHO_PACOTE_DL; i++) {
    LoRa.write(PacoteDL[i]);  // add data to packet
  }
  LoRa.endPacket();  // finish packet and send it
  LoRa.idle();  // Retorna ao modo standby/recepção

  // Pisca o LED de transmissão de pacote DL
  digitalWrite(LED_VERMELHO_PIN, LOW);  // FIM da Transmissão

}

//==================================================================================================================
//======================= PACOTE UL LINK - PACODE VINDO NÓ SENSOR ENCAMINHADO PARA PYTHON===========================
//==================================================================================================================
// Pacote que chega no RF95 vindo do nó sensor e é passado para o buffer de TX da serial
//--------------------------- RECEBE PACOTE UL VINDO DO NÓ SENSOR ATRAVÉS DO MÓDULO RF95

void Phy_radio_receive_UL() {

  // memset(PacoteUL, 0, sizeof(PacoteUL));
  // Escuta o Rádio LoRa se identificou algum Pacote
  uint8_t packetSize = LoRa.parsePacket();

  // Caso positivo, identifica o tamanho do Payload do Pacote
  if (packetSize) {

    digitalWrite(LED_VERDE_PIN, HIGH);  // Apaga Led Verde Indicando Inicio da leitura do Pacote

    // Realiza a leitura caso Payload do Pacote seja compatível com o Pacote de 52 Bytes
    if (packetSize >= TAMANHO_PACOTE_UL) {

      for (int i = 0; i < TAMANHO_PACOTE_UL; i++) {
        PacoteUL[i] = LoRa.read();
      }
  
      RSSI_dBm_UL = LoRa.packetRssi();
      SNR_UL_bruto = LoRa.packetSnr();

      // zera controle standby caso recebido Pacote_UL
      millis_standby_controle = millis();
      
      //===================================== IMPORTANTE - OPÇÃO VERIFICAÇÃO DE ENDEREÇO OU MODO PROMÍSCUO========================
      // Quando recebe o pacote a base pode verificar o endereço de destino ou trabalhar em modo promíscuo.
      //===================== QUANDO A BASE  VERIFICA O ENDENREÇO DE DESTINO O PACOTE SÓ É ENVIADO PARA A SERIAL CASO A BASE SEJA O DESTINATÁRIO - nesse caso descomentar o bloco abaixo
      // Esta é uma função originalmente da camada de rede, mas existe um cross-layer para verificação do endereço de destino, recebendo somente os pacotes que são destinados para a base
  
      digitalWrite(LED_VERDE_PIN, LOW);  // Fim da leitura do Pacote

      // Garante que Nó Sensor também recebeu comando de alteração de rádio e confirmou
      confirma_novo_radio_sensor = PacoteUL[7];  // PacoteUL[7] recebe confirmação do nó sensor do recebimento

      Phy_serial_send_UL();

    }
  }
}


// ====================

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
  SNR_UL = (uint8_t)round((SNR_UL_bruto + 30.0) * 4.0); // Offset de 30.0dB e passo de 0.25dB (* 4.0)

  // =================Informações de gerência do pacote
  PacoteUL[2] = RSSI_UL;  // aloca RSSI_UL
  PacoteUL[3] = SNR_UL;

  if ((confirma_novo_radio_base == 2) & (confirma_novo_radio_sensor == 2)){
    // Confirmação do segundo ciclo de ambos devices
    primeiro_setup = 0;
    PacoteUL[7] = 3;
    confirma_novo_radio = 1;
            
    valor_anterior_spreadingfactor = valor_atual_spreadingfactor;
    valor_anterior_bandwidth = valor_atual_bandwidth;
    valor_anterior_codingrate = valor_atual_codingrate;
    valor_anterior_potencia_radio = valor_atual_potencia_radio;

    valor_atual_spreadingfactor = valor_novo_spreadingfactor;
    valor_atual_bandwidth = valor_novo_bandwidth;
    valor_atual_codingrate = valor_novo_codingrate;
    valor_atual_potencia_radio = valor_novo_potencia_radio;

  }
  else if ((confirma_novo_radio_base == 3) & (confirma_novo_radio_sensor == 3)){
    // Link Test
    PacoteUL[7] = 4;
    confirma_novo_radio = 0;    
  }
  else if ((confirma_novo_radio_base == 4) & (confirma_novo_radio_sensor == 4)){
    // LSS DL-UL
    PacoteUL[7] = 6;
    confirma_novo_radio = 0;    
  }  
  else if ((confirma_novo_radio_base == 5) & (confirma_novo_radio_sensor == 5)){
    // LSS Last Pack
    PacoteUL[7] = 5;
    confirma_novo_radio = 0;    
  }
  else if ((confirma_novo_radio_base == 6) & (confirma_novo_radio_sensor == 6)){
    // LSS UL Only
    PacoteUL[7] = 7;
    confirma_novo_radio = 0;    
  }
  else if ((confirma_novo_radio_base == 1) & (confirma_novo_radio_sensor == 0)){
    // Indica ao Nível 3 que apenas um dos Devices LoRa (Base) recebeu/processou o Comando de alteração
    PacoteUL[7] = 1;
    confirma_novo_radio = 0;    
  }
  else if ((confirma_novo_radio_base == 0) & (confirma_novo_radio_sensor == 1)){
    // Indica ao Nível 3 que apenas um dos Devices LoRa (Nó Sensor) recebeu/processou o Comando de alteração
    PacoteUL[7] = 1;
    confirma_novo_radio = 0;    
  }

  if (confirma_novo_radio == 1) {
    AplicarConfiguracoesRadio();
  }

  // Transmissão do pacote pela serial do ESP32 para o script em Python
  for (int i = 0; i < TAMANHO_PACOTE_UL; i++) {
    Serial.write(PacoteUL[i]);
  }

}


void AplicarConfiguracoesRadio() {

  if (confirma_novo_radio == 1) {

    LoRa.sleep();                                         // Coloca em sleep para garantir a mudança de parâmetros
    //LoRa.setTxPower(valor_novo_potencia_radio);           // Potência de Transmissão (Configurado em bibliotecas.h)
    LoRa.setSpreadingFactor(valor_novo_spreadingfactor);  // Fator de Espalhamento  (Configurado em bibliotecas.h)
    LoRa.setSignalBandwidth(valor_novo_bandwidth);        // Banda do Sinal (Configurado em bibliotecas.h)
    LoRa.setCodingRate4(valor_novo_codingrate);           // Coding Rate  (Configurado em bibliotecas.h)
    LoRa.idle();                                       // Retorna ao modo standby/recepção

    confirma_novo_radio_sensor = 0;
    confirma_novo_radio_base = 0;
    confirma_novo_radio = 0;
    recebe_comando_nova_radio = 0;
    primeiro_setup = 0;
  }
}


// ============================================================
// FUNÇÃO AUXILIAR - Reseta estado para aguardar novo downlink serial
// ============================================================

void reset_gateway_para_setup_inicial() {

  // Zera flags e variáveis de controle
  aguardando_confirmacao_UL    = false;
  millis_inicio_aguarda_UL     = 0;
  tempo_radio                  = 0;
  recebe_comando_nova_radio    = 0;
  confirma_novo_radio_sensor   = 0;
  confirma_novo_radio_base = 0;
  confirma_novo_radio = 0;
  contadorDL = 0;
  contadorSS = 0;

  // Retorna rádio aos parâmetros de SETUP
  primeiro_setup = 1;
  PacoteUL[7] = 10; // Gateway Resetou para Máxima
}

