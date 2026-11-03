// ====== FUNÇÃO RECEBE PACOTE DA CAMADA DE REDE
void Net_radio_receive_DL() {
  if(PacoteDL[8] == ID_sensor) {  // Só passa para a camada superior se for o destino final do pacote
    //Serial.println("Pacote DL é para este Nó Sensor");

    Transp_radio_receive_DL();
  }
}

// ====== ENVIA PACOTE CAMADA REDE
void Net_radio_send_UL() {

  PacoteUL[8] = PacoteDL[10];   // Inverte os endereços de Origem e Destino no pacote de UL
  PacoteUL[10] = ID_sensor;     // Insere My_ID

  Mac_radio_send_UL();
}