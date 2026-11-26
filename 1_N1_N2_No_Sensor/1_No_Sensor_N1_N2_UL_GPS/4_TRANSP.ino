//================ RECEBE O PACOTE DE DL DA CAMADA DE REDE ========
void Transp_radio_receive_DL() { 

  medidasLSS = (((int(PacoteDL[14]))*256) + (PacoteDL[15]));
  Serial.print("medidasLSS : ");
  Serial.println(medidasLSS);
  contador_perda_DL = contador_perda_DL + 1;
  
  App_radio_receive_DL();

}


//================ ENVIA O PACOTE DE UL À CAMADA DE REDE ========
void Transp_radio_send_UL() { 

  //if ((confirma_novo_radio_sensor == 4) || (confirma_novo_radio_sensor == 5)){ 
    contadorUL = contadorUL + 1;  // Incrementa o contador de pacote de UL
    Serial.print("contadorUL : ");
    Serial.println(contadorUL);
  //}

  PacoteUL[12] = contador_perda_DL/256; //PacoteDL[DL_COUNTER_MSB];
  PacoteUL[13] = contador_perda_DL%256; //PacoteDL[DL_COUNTER_LSB];

  PacoteUL[14] = contadorUL/256; // = (contadorUL >> 8) & 0xFF; 
  PacoteUL[15] = contadorUL%256; // = contadorUL & 0xFF;

  if (uplink_mode == 1){
    if (contadorUL > medidasLSS){ // era >= aaf 09/11
      uplink_mode = 0;
      lss_mode = 0;
      contadorUL = 0;
      medidasLSS = 0;
      confirma_novo_radio_sensor = 5;
      primeiro_setup = 1;
    }
  }

  // neste ponto pode ser implementado um controle relacionado ao recebimento não sequencial de pacotes de DL
  
  #if defined(OLED_INTEGRADO)

    display.setTextSize(1);
    //display.setCursor(0, 35);
    display.print("Pkt_UL : ");
    display.setTextSize(1);
    display.println(contadorUL, 1); 

    // Escreve o buffer na tela Oled
    //display.display();  
  #endif
  
  Net_radio_send_UL();

}
