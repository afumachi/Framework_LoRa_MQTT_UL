
# ===== Bibliotecas =====
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import math
import time
import struct
from time import localtime, strftime
import os
import pandas as pd
import threading

global comando, medidas, tempo, medida_atual, arquivo_log_dados
global Contador_pkt_DL, tempo_entre_pacotes, estado_mqtt
global ID_sensor, ID_gateway, Pacote_DL, Pacote_UL, pacote_recebido
global Comando_LED_amarelo, St_LED_amarelo, Tamanho_pacote
global BROKER, PORTA_MQTT, TOPIC_DL, TOPIC_UL, MQTT_QOS
global broker_mqtt, porta_broker, topico_mqtt_dl, topico_mqtt_ul, qos_mqtt

# ===== Configurações Padrão MQTT (Serão sobrescritas via MQTT.txt) =====
BROKER        = "www.tpm.dev.br"
PORTA_MQTT    = 1883
TOPIC_DL      = "mot_mqtt_SEU_RA/gateway/downlink"
TOPIC_UL      = "mot_mqtt_SEU_RA/gateway/uplink"
MQTT_QOS      = 1

estado_mqtt = 0
Pacote_UL_payload = None

# ===== Arquivo Log globais =====
lock_arquivo_log = threading.Lock()

# ===== Variáveis globais =====
Tamanho_pacote = 20

# Cria os pacotes de DL e UL
Pacote_DL = [0] * Tamanho_pacote
Pacote_UL = [0] * Tamanho_pacote

for i in range(Tamanho_pacote):
   Pacote_DL[i] = 0

# Evento para sinalizar chegada de pacote UL via MQTT
Pacote_UL_status = threading.Event()
Pacote_UL_payload = bytearray(Tamanho_pacote)

# Variáveis de Controle
comando = 0
medidas = 100
medida_atual = 0
tempo = 2.0
condicao_start = 0
arquivo_log_dados = 0

# =============== Camada de aplicação DL
Comando_LED_amarelo = 0  # Inicia apagado
St_LED_amarelo = 0

# ================ Camada de Transporte DL
Contador_pkt_DL = 0
perda_PK_RX = 0

# ================ Camada MAC
tempo_entre_pacotes = 2.0
pacote_recebido = 0

# ================ Camada de Rede DL
ID_sensor = 1
ID_gateway = 0

# ================ Broker MQTT
broker_mqtt = BROKER
porta_broker = PORTA_MQTT
topico_mqtt_dl = TOPIC_DL
topico_mqtt_ul = TOPIC_UL
qos_mqtt = MQTT_QOS

# Caminho da Pasta de armazenamento (Caminho Relativo)
PASTA_ARMAZENAMENTO = os.path.join("..", "4_N4_Armazenamento")
caminho_parametros = os.path.join(PASTA_ARMAZENAMENTO, "Parametros")
caminho_dados_brutos = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

os.makedirs(caminho_dados_brutos, exist_ok=True)
os.makedirs(caminho_parametros, exist_ok=True)

# ===== Callbacks MQTT =====
def on_connect(client, userdata, flags, reason_code, properties):
    global estado_mqtt
    if reason_code == 0:
        print(f"[MQTT] Conectado ao Broker MQTT com sucesso ({BROKER}:{PORTA_MQTT}).")
        client.subscribe(TOPIC_UL, qos=MQTT_QOS)
        print(f"[MQTT] Inscrito no tópico: {TOPIC_UL} (QoS{MQTT_QOS})")
        estado_mqtt = 1
    else:
        print(f"[MQTT] Falha na conexão. Código: {reason_code}")
        estado_mqtt = 0

def on_publish(client, userdata, mid, reason_code, properties):
    pass

def on_message(client, userdata, msg):
    global Pacote_UL_payload
    payload = msg.payload
    if len(payload) >= Tamanho_pacote:
        Pacote_UL_payload = bytearray(payload[:Tamanho_pacote])
        Pacote_UL_status.set()

def on_disconnect(client, userdata, flags, reason_code, properties):
    global estado_mqtt
    if reason_code != 0:
        print(f"[MQTT] Desconectado inesperadamente (rc={reason_code}).")      
        estado_mqtt = 0

# ===== Inicialização do cliente MQTT =====
client = mqtt.Client(CallbackAPIVersion.VERSION2)
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect
client.on_publish    = on_publish

def reconfigurar_e_conectar_mqtt(novo_broker, nova_porta, novo_topico_dl, novo_topico_ul, novo_qos):
    """
    Desconecta do broker atual, atualiza as variáveis de rede e aguarda a nova conexão.
    """
    global BROKER, PORTA_MQTT, TOPIC_DL, TOPIC_UL, MQTT_QOS, estado_mqtt

    alterou = (
        novo_broker != BROKER or
        nova_porta != PORTA_MQTT or
        novo_topico_dl != TOPIC_DL or
        novo_topico_ul != TOPIC_UL or
        novo_qos != MQTT_QOS or
        not client.is_connected()
    )

    if alterou:
        print("[MQTT] Atualizando configurações e reconectando...")
        try:
            # 1. Desconecta explicitamente antes de mudar os parâmetros
            if client.is_connected():
                client.loop_stop()
                client.disconnect()
            
            BROKER = novo_broker
            PORTA_MQTT = nova_porta
            TOPIC_DL = novo_topico_dl
            TOPIC_UL = novo_topico_ul
            MQTT_QOS = novo_qos

            # 2. Inicia nova conexão
            client.connect(BROKER, PORTA_MQTT, keepalive=60)
            client.loop_start()
            
            # 3. Aguarda ativamente a reconexão (timeout de até 5 segundos)
            timeout = time.time() + 5.0
            while not client.is_connected() and time.time() < timeout:
                time.sleep(0.1)
                
            if client.is_connected():
                print(f"[MQTT] Reconexão bem-sucedida com {BROKER}:{PORTA_MQTT}")
            else:
                print(f"[MQTT Erro] Tempo limite excedido ao tentar conectar em {BROKER}:{PORTA_MQTT}")
                
        except Exception as e:
            print(f"[MQTT Erro] Não foi possível conectar ao broker {BROKER}:{PORTA_MQTT} -> {e}")

def salvar_parametros_mqtt(cmd, num_med, t_pacote, brk, porta, top_dl, top_ul, qos_val):
    """
    Grava todas as 8 variáveis no arquivo MQTT.txt preservando a estrutura completa.
    """
    path_param = os.path.join(caminho_parametros, 'MQTT.txt')
    try:
        with open(path_param, 'w', encoding='utf-8') as f:
            f.write(f"{cmd}\n")
            f.write(f"{num_med}\n")
            f.write(f"{t_pacote}\n")
            f.write(f"{brk}\n")
            f.write(f"{porta}\n")
            f.write(f"{top_dl}\n")
            f.write(f"{top_ul}\n")
            f.write(f"{qos_val}\n")
        print("[MQTT] Arquivo MQTT.txt atualizado com sucesso.")
    except Exception as e:
        print(f"[Erro] Falha ao salvar arquivo MQTT.txt: {e}")

def ler_cmd_led_amarelo():
    caminho_led = os.path.join(caminho_parametros, "cmd_led_amarelo.txt")
    try:
        with open(caminho_led, "r", encoding="utf-8") as arquivo:
            conteudo = arquivo.read().strip()
            valor = int(conteudo)
            return valor if valor in (0, 1) else 0
    except (FileNotFoundError, ValueError):
        return 0

# ========== DOWNLINK MQTT ==========
def downlink():
   global Contador_pkt_DL, tempo_entre_pacotes
   global ID_sensor, ID_gateway, Pacote_DL, Pacote_UL, medida_atual

   for i in range(Tamanho_pacote):
       Pacote_DL[i] = 0

   Comando_LED_amarelo = int(ler_cmd_led_amarelo())
   Pacote_DL[16] = Comando_LED_amarelo

   Pacote_DL[12] = (medida_atual >> 8) & 0xFF
   Pacote_DL[13] = medida_atual & 0xFF         
        
   Pacote_DL[8] = ID_sensor
   Pacote_DL[9] = ID_gateway
   Pacote_DL[4] = int(tempo_entre_pacotes)
                
   Pacote_UL_status.clear()
   result = client.publish(TOPIC_DL, bytes(Pacote_DL), qos=MQTT_QOS)
                
   if client.is_connected():
      try:
         result.wait_for_publish(timeout=tempo_entre_pacotes)
      except RuntimeError as e:
         print(f"[MQTT Erro] Falha ao aguardar publicação: {e}")
      except Exception as e:
         print(f"[Erro] Outro erro ocorreu: {e}")
   else:
      print("[MQTT] Cliente desconectado ao tentar publicar.")

# ========== UPLINK MQTT ==========
def uplink():
   global Pacote_UL, Pacote_DL, medida_atual, pacote_recebido, tempo_entre_pacotes, St_LED_amarelo

   Pacote_UL_novo = Pacote_UL_status.wait(timeout=tempo_entre_pacotes)
   
   if Pacote_UL_novo:
      Pacote_UL_status.clear()
      Pacote_UL = Pacote_UL_payload          
      if len(Pacote_UL) == Tamanho_pacote:
         pacote_recebido = 1
         St_LED_amarelo = Pacote_UL[16]
         print('Pacote = ', medida_atual, ' | Pacote UL recebido | STATUS LED = ', St_LED_amarelo)
   else:
      pacote_recebido = 0

# ===== Loop principal =====
print("\n========== Gateway LoRa - Comunicação MQTT ==========")
print("\n Aguardando Comando de INICIAR...")

# Conexão inicial
try:
    client.connect(BROKER, PORTA_MQTT, keepalive=60)
    client.loop_start()
except Exception as e:
    print(f"[MQTT Inicialização] Aguardando leitura de parâmetros... ({e})")

try:
    while True:
        # Leitura constante do arquivo de parâmetros do Usuário Nível 6
        path_param = os.path.join(caminho_parametros, 'MQTT.txt')
        if os.path.exists(path_param):
            with open(path_param, 'r', encoding='utf-8') as Parametros_r:
                linhas = [l.strip() for l in Parametros_r.readlines()]
                
            if len(linhas) >= 8:
                condicao_start = int(linhas[0]) if linhas[0] else 0
                num_medidas    = int(linhas[1]) if linhas[1] else 100
                tempo          = float(linhas[2].replace(',', '.')) if linhas[2] else 2.0
                broker_mqtt    = linhas[3] if linhas[3] else BROKER
                porta_broker   = int(linhas[4]) if linhas[4] else PORTA_MQTT
                topico_mqtt_dl = linhas[5] if linhas[5] else TOPIC_DL
                topico_mqtt_ul = linhas[6] if linhas[6] else TOPIC_UL
                qos_mqtt       = int(linhas[7]) if linhas[7] else MQTT_QOS
            
                tempo_entre_pacotes = tempo

        if (condicao_start == 1):

             if (medida_atual == 0):
                # 1. Aplica a reconfiguração e aguarda a conexão ser estabelecida ANTES de iniciar as medidas
                reconfigurar_e_conectar_mqtt(broker_mqtt, porta_broker, topico_mqtt_dl, topico_mqtt_ul, qos_mqtt)
                
                if (arquivo_log_dados == 0):
                     print("################## LSS - Iniciando Medições LoRa #################")
                     filename1 = strftime(os.path.join(caminho_dados_brutos, "Rodada_Teste_%Y_%m_%d_%H-%M-%S.txt"))
           
                     Log_dados = open(filename1, 'w')
                     print("Arquivo de log: %s" % filename1)
                     Cabecalho = 'Time stamp,Contador,DL_B0,DL_B1,DL_B2,DL_B3,DL_B4,DL_B5,DL_B6,DL_B7,DL_B8,DL_B9,DL_B10,DL_B11,DL_B12,DL_B13,DL_B14,DL_B15,DL_B16,DL_B17,DL_B18,DL_B19,DL_B20,DL_B21,DL_B22,DL_B23,DL_B24,DL_B25,DL_B26,DL_B27,DL_B28,DL_B29,UL_B0,UL_B1,UL_B2,UL_B3,UL_B4,UL_B5,UL_B6,UL_B7,UL_B8,UL_B9,UL_B10,UL_B11,UL_B12,UL_B13,UL_B14,UL_B15,UL_B16,UL_B17,UL_B18,UL_B19,UL_B20,UL_B21,UL_B22,UL_B23,UL_B24,UL_B25,UL_B26,UL_B27,UL_B28,UL_B29'
                     print(Cabecalho, file=Log_dados)
                     arquivo_log_dados = 1
                     time.sleep(1)

             Tempo_gasto = 0
             Tempo_inicio_pacote = time.time()
              
             # ================ Envio de pacote de DL
             if(medida_atual < (num_medidas)):
                medida_atual = medida_atual + 1
                print("### LoRa MQTT -> Medida: ", medida_atual, "de ", num_medidas)
                
                downlink()

                time.sleep(tempo_entre_pacotes)
                
                pacote_recebido = 0

                uplink()
                
                if (pacote_recebido == 1):    
                   Dados_DL = ''
                   Dados_UL = ''
                   for i in range(Tamanho_pacote):
                      if i == 0:
                         Dados_DL = str(Pacote_DL[i])
                         Dados_UL = str(Pacote_UL[i])
                      else:
                         Dados_DL = Dados_DL + ', ' + str(Pacote_DL[i])
                         Dados_UL = Dados_UL + ', ' + str(Pacote_UL[i])
                   Tempo = time.asctime()
                   print(Tempo + ', ' + str(medida_atual) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)

                   with lock_arquivo_log:                      
                      Dados_log = Tempo + ',' + str(medida_atual) + ',' + Dados_DL + ',' + Dados_UL
                      print(Dados_log, file=Log_dados)
                      Log_dados.flush()

                elif(pacote_recebido == 0):
                   perda_PK_RX = perda_PK_RX + 1
                   print('Cont = ', medida_atual, ' PERDEU N PACOTES ', perda_PK_RX)
                   Dados_DL = ''
                   Dados_UL = ''
                   
                   for i in range(Tamanho_pacote):
                      if i == 0:
                         Dados_DL = str(Pacote_DL[i])
                         Dados_UL = '9'
                      else:
                         Dados_DL = Dados_DL + ', ' + str(Pacote_DL[i])
                         Dados_UL = Dados_UL + ', 9'
                   Tempo = time.asctime()
                   print(Tempo + ', ' + str(medida_atual) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)

                   with lock_arquivo_log:
                      Dados_log = Tempo + ',' + str(medida_atual) + ',' + Dados_DL + ',' + Dados_UL
                      print(Dados_log, file=Log_dados)
                      Log_dados.flush()

                Tempo_gasto = time.time() - Tempo_inicio_pacote
                print('Tempo Entre Pacotes = ', Tempo_gasto)

             elif (medida_atual >= num_medidas):       
                 # Término natural das medições: Salva os parâmetros com comando 0 mantendo as 8 variáveis
                 salvar_parametros_mqtt(0, num_medidas, tempo, broker_mqtt, porta_broker, topico_mqtt_dl, topico_mqtt_ul, qos_mqtt)
                 
                 print('Pacotes enviados = ', medida_atual, ' Pacotes perdidos = ', perda_PK_RX)
                 print('Tempo Entre Pacotes = ', Tempo_gasto)
                 medida_atual = 0
                 Contador_pkt_DL = 0
                 arquivo_log_dados = 0           
                 try:
                     Log_dados.close()
                 except (AttributeError, NameError):
                     pass
                 print('[LoRa MQTT] Fim da Execução')

        elif(condicao_start == 2):
            print('[LoRa MQTT] Execução em pausa')
            time.sleep(1)
          
        elif((condicao_start == 0) or (medida_atual == condicao_start)):
            comando = 0
            medida_atual = 0
            Contador_pkt_DL = 0
            perda_PK_RX = 0
            arquivo_log_dados = 0
            
            # Ao parar pelo N6, salva todas as 8 variáveis com comando 0
            salvar_parametros_mqtt(0, num_medidas, tempo, broker_mqtt, porta_broker, topico_mqtt_dl, topico_mqtt_ul, qos_mqtt)
          
            try:
                Log_dados.close()
            except (AttributeError, NameError):
                pass
              
            print('[LoRa MQTT] Fim da Execução... comando = PARAR')
            time.sleep(1)

        else:
            print('[LoRa MQTT] Condição Start...', condicao_start)
            comando = 0
            medida_atual = medida_atual - 1
            time.sleep(1)

except KeyboardInterrupt:
   print("\n[Ctrl + C] Interrompido pelo usuário.")
   try:
       Log_dados.close()
   except (AttributeError, NameError):
       pass
   medida_atual = 0
   arquivo_log_dados = 0
   salvar_parametros_mqtt(0, num_medidas, tempo, broker_mqtt, porta_broker, topico_mqtt_dl, topico_mqtt_ul, qos_mqtt)
   print('[LoRa MQTT] Fim da Execução')
   client.loop_stop()
   client.disconnect()
finally:
   client.loop_stop()
   if client.is_connected():
       client.disconnect()
   print("[LoRa MQTT] Desconectado do broker.")
