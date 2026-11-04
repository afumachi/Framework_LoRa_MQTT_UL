//================ RECEBE O PACOTE DA CAMADA FÍSICA ========
void Mac_radio_receive_DL() { 
  // Aqui pode ser adicionado o Sleep Mode

  // Modo de trabalho do LSS [DL-UL ou somente UL]
  lss_mode = int(PacoteDL[4]);

  // Primeiro ciclo
    if ((recebe_comando_nova_radio == 1)){
     
        Serial.println("[RECONFIGURACAO DE RADIO RECEBIDO]");
        confirma_novo_radio_sensor = 2;
        
    }
    else if (recebe_comando_nova_radio == 3){
      //Serial.println("[LINK TEST]");
      confirma_novo_radio_sensor = 3;
    }
    else if (recebe_comando_nova_radio == 4){
      //Serial.println("[LSS DL-UL]");
      confirma_novo_radio_sensor = 4;
    }
    else if (recebe_comando_nova_radio == 5){
      //Serial.println("[LSS LAST PACK]");
      confirma_novo_radio_sensor = 5;
    }
    else if (recebe_comando_nova_radio == 6){
      //Serial.println("[LSS ONLY UL]");
      confirma_novo_radio_sensor = 6;
    }    

    if (lss_mode == 1){
      Serial.println("[LSS UL Mode ON]");
      confirma_novo_radio_sensor = 6;
      uplink_mode = 1;
    }    

    Net_radio_receive_DL();

}

//================ ENVIA O PACOTE À CAMADA FÍSICA ========
void Mac_radio_send_UL() {
  // Aqui pode ser adicionado o Sleep Mode

  // confirmação do primeiro ciclo  
  if (confirma_novo_radio_sensor == 2){
    // Confirmação do segundo ciclo para alteração das config. de rádio do Nó Sensor
    PacoteUL[7] = 2;
    Serial.println("MAC - PacoteUL[7] - RADIO RECONFIG : ");
    Serial.println(confirma_novo_radio_sensor);
    confirma_novo_radio = 1; // Habilita Nó Sensor a alterar as configurações de Rádio
    
  }
  else if (confirma_novo_radio_sensor == 3){
    //  Confirmação do terceiro ciclo confirmando a alteração das config. de rádio do Nó Sensor
    PacoteUL[7] = 3;
    Serial.println("MAC - PacoteUL[7] - LINK TEST: ");
    //Serial.println(confirma_novo_radio_sensor);
    recebe_comando_nova_radio = 0;
    confirma_novo_radio = 0;
    confirma_novo_radio_sensor = 0;
  }
  else if (confirma_novo_radio_sensor == 4){
    //  Confirmação do terceiro ciclo confirmando a alteração das config. de rádio do Nó Sensor
    PacoteUL[7] = 4;
    Serial.println("MAC - PacoteUL[7] - CICLE LSS DL-UL: ");
    //Serial.println(confirma_novo_radio_sensor);
    uplink_mode = 0;
    recebe_comando_nova_radio = 0;
    confirma_novo_radio = 0;
    confirma_novo_radio_sensor = 0;
  }
  else if (confirma_novo_radio_sensor == 6){
    //  Confirmação do terceiro ciclo confirmando a alteração das config. de rádio do Nó Sensor
    PacoteUL[7] = 6;
    Serial.println("MAC - PacoteUL[7] - CICLE LSS UL COUNT: ");      
  }
  else if (confirma_novo_radio_sensor == 5){
    //  Confirmação do terceiro ciclo confirmando a alteração das config. de rádio do Nó Sensor
    PacoteUL[7] = 5;
    Serial.println("MAC - PacoteUL[7] - LAST PACK LSS: ");
    //Serial.println(confirma_novo_radio_sensor);
    recebe_comando_nova_radio = 0;
    confirma_novo_radio = 0;
    confirma_novo_radio_sensor = 5;
      // Zera flag de contagem e variáveis de controle
    controle_ativo          = false;
    millis_inicio_controle  = 0;
    tempo_radio             = 0;
    confirma_novo_radio_base = 5; // AAF 17-09 Nó Sensor em Standy-by
    contadorDL = 0;
    medidasLSS = 0;
    contadorUL = 0;
    contador_perda_DL = 0;
    uplink_mode = 0;
    lss_mode = 0;
    primeiro_setup = 1;
  }

  if (lss_mode == 1){
    uplink_mode = 1;
    PacoteUL[7] = 6;
    Serial.println("MAC - PacoteUL[7] - CICLE LSS UL COUNT: ");  
  }

  Phy_radio_send_UL();
}
