# MoT LoRa + Borda | N2 e N3 | WissTek-IoT | Framework LoRa Local
# 15/10/2026 - Branquinho - Guilherme - Anderson

# ========================== 1 - Bibliotecas
import serial
import math
import time
import struct
from time import localtime, strftime
import os

global comando, medidas, tempo, medida_atual, arquivo_log_dados, num_medidas
global Contador_pkt_DL, num_medidas_total, tempo_entre_pacotes, estado_mqtt
global ID_sensor, ID_gateway, Pacote_DL, Pacote_UL, pacote_recebido, primeiro_pacote_recebido
global Comando_LED_amarelo, St_LED_amarelo, Tamanho_pacote, Tempo_inicial_RX, Tempo_limite_RX

Tamanho_pacote = 20

# ========================= 2 - Variáveis e arquivos
Pacote_DL = [0]*Tamanho_pacote
PacoteUL  = [0]*Tamanho_pacote


# Variáveis de Controle
comando = 0
medidas = 100
medida_atual = 0
num_medidas = 0
tempo = 2.0
condicao_start = 0
arquivo_log_dados = 0

# ================ Camada MAC
tempo_entre_pacotes = 2.0
pacote_recebido = 0
primeiro_pacote_recebido = 0
Tempo_inicial_RX = 0
Tempo_limite_RX = 0

# ================ Camada Transporte
Contador_pkt_DL = 0
num_medidas_total = 0

# Caminho da Pasta de armazenamento (Caminho Relativo)
PASTA_ARMAZENAMENTO = os.path.join("..", "4_N4_Armazenamento")

# Caminhos dos arquivos de armazenamento e leitura de parâmetros
caminho_parametros = os.path.join(PASTA_ARMAZENAMENTO, "Parametros")
caminho_dados      = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Brutos")

for i in range(Tamanho_pacote):
   Pacote_DL[i] = 0
   PacoteUL[i]  = 0

Grava_log = 1

os.makedirs(caminho_dados, exist_ok=True)
os.makedirs(caminho_parametros, exist_ok=True)
caminho_led = os.path.join(caminho_parametros, "cmd_led_amarelo.txt")
caminho_txt_parametros = os.path.join(caminho_parametros, "PARAMETROS.txt")

Cabecalho = 'Time stamp,Contador,DL_B0,DL_B1,DL_B2,DL_B3,DL_B4,DL_B5,DL_B6,DL_B7,DL_B8,DL_B9,DL_B10,DL_B11,DL_B12,DL_B13,DL_B14,DL_B15,DL_B16,DL_B17,DL_B18,DL_B19,UL_B0,UL_B1,UL_B2,UL_B3,UL_B4,UL_B5,UL_B6,UL_B7,UL_B8,UL_B9,UL_B10,UL_B11,UL_B12,UL_B13,UL_B14,UL_B15,UL_B16,UL_B17,UL_B18,UL_B19'

def ler_parametros_arquivo():
   if not os.path.exists(caminho_txt_parametros):
      return None
   try:
      with open(caminho_txt_parametros, "r") as f:
         linhas = [linha.strip() for linha in f.readlines()]
         if len(linhas) >= 4:
            comando = int(linhas[0])
            medidas = int(linhas[1])
            tempo = float(linhas[2].replace(",", "."))
            n_serial = str(linhas[3])
            return comando, medidas, tempo, n_serial
   except Exception:
      pass
   return None



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
   global Contador_pkt_DL, num_medidas_total, tempo_entre_pacotes, primeiro_pacote_recebido
   global ID_sensor, ID_gateway, Pacote_DL, Pacote_UL, medida_atual, num_medidas

   try:
      for i in range(Tamanho_pacote):
          Pacote_DL[i] = 0

      # Camada de Aplicação
      Comando_LED_amarelo = int(ler_cmd_led_amarelo())
      Pacote_DL[16] = Comando_LED_amarelo

      # Camada de Transporte
      Contador_pkt_DL = Contador_pkt_DL + 1
      Pacote_DL[12] = (Contador_pkt_DL >> 8) & 0xFF
      Pacote_DL[13] = Contador_pkt_DL & 0xFF
      Pacote_DL[14] = (num_medidas_total >> 8) & 0xFF
      Pacote_DL[15] = num_medidas_total & 0xFF
      
      # Camada de Rede        
      Pacote_DL[8] = ID_sensor
      Pacote_DL[9] = ID_gateway

      # Camada de MAC
      if (primeiro_pacote_recebido == 0):
         # Indica modo Uplink após recepção do 1º Pacote
         Pacote_DL[4] = 1
      Pacote_DL[6] = int(tempo_entre_pacotes)
                   
      ser.reset_input_buffer()
      for Bytes_DL in range(Tamanho_pacote):
          ser.write(chr(Pacote_DL[Bytes_DL]).encode('latin1'))
      ser.flush()
      time.sleep(0.05)
      #print('Pacote = ', Contador_pkt_DL, ' | Pacote DL enviado')
   except (serial.SerialException, OSError) as e:
      raise ConnectionError(f"Gateway desconectado na escrita: {e}")

# ========== UPLINK MQTT ==========
def uplink():
   global Pacote_UL, Pacote_DL, medida_atual, pacote_recebido, primeiro_pacote_recebido, tempo_entre_pacotes
   global Tempo_inicial_RX, Tempo_limite_RX, St_LED_amarelo, Tamanho_pacote

   Tempo_inicial_RX = time.time()
   # ======== COLETA UPLINK VIA SERIAL ========
   Pacote_UL = b''
   Tempo_limite_RX = Tempo_entre_pacotes - 0.2
   if Tempo_limite_RX < 0.5:
      Tempo_limite_RX = 0.5

   while len(Pacote_UL) < Tamanho_pacote and (time.time() - Tempo_inicial_RX) < Tempo_limite_RX:
      Pacote_UL = Pacote_UL + ser.read(Tamanho_pacote - len(Pacote_UL))

      if len(Pacote_UL) == Tamanho_pacote:
         pacote_recebido = 1

         if ((pacote_recebido == 1) and (primeiro_pacote_recebido == 0)):
            primeiro_pacote_recebido = 1
            #print(" Primeiro Pacote Recebido ")

         St_LED_amarelo = Pacote_UL[16]
         # print('Pacote = ', medida_atual, ' | Pacote UL recebido | STATUS LED = ', St_LED_amarelo)
      else:
         pacote_recebido = 0


print("\n========== Aguardando Configuração Inicial via Painel (PARAMETROS.txt) ==========")

config = None
while config is None:
   config = ler_parametros_arquivo()
   if config is None:
      time.sleep(1)

_, num_medidas_total, Tempo_entre_pacotes, n_serial = config
n_serial1 = int(n_serial) - 1

print(f"[Config] Porta COM: {n_serial} | Tempo entre pacotes: {Tempo_entre_pacotes}s | Medidas: {num_medidas_total}")

ser = serial.Serial("COM"+str(n_serial), 115200, timeout=0.5, parity=serial.PARITY_NONE)

ser.setDTR(False)
ser.setRTS(False)
time.sleep(0.1)
ser.setDTR(True)
ser.setRTS(True)
time.sleep(1.5)

ser.reset_input_buffer()
ser.reset_output_buffer()

Comando_LED_amarelo = 0  
Contador_pkt_DL = 0
perda_PK_RX     = 0
ID_sensor = 1
ID_gateway = 0

print("\n========== Gateway LoRa - Comunicação Local (Controlado por Painel) ==========")

try:
    j = 1
    Log_dados = None
    filename1 = None
    estado_anterior = 0
    rodada_concluida = False

    while True:
        # Bloco de tentativa de execução com monitoramento de conexão do Gateway
        try:       

           config_atual = ler_parametros_arquivo()
           if config_atual:
               comando, num_medidas_total, Tempo_entre_pacotes, _ = config_atual
           else:
               comando = 0

           if comando == 1 and rodada_concluida:
               rodada_concluida = False
               estado_anterior = 0

           if comando == 0:
               if Log_dados and not Log_dados.closed:
                   Log_dados.close()
                   print(f'[LoRa] Teste PARADO. Arquivo de log fechado.')
               Log_dados = None
               j = 1
               Contador_pkt_DL = 0
               perda_PK_RX = 0
               rodada_concluida = False
               time.sleep(0.5)
               estado_anterior = 0
               primeiro_pacote_recebido = 0
               continue

           if comando == 2:
               if estado_anterior != 2 and not rodada_concluida:
                   print('[LoRa] Teste PAUSADO pelo operador.')
                   estado_anterior = 2
               time.sleep(0.5)
               continue

           if comando == 1 and not rodada_concluida:
               if Log_dados is None or Log_dados.closed:
                  filename1 = strftime(os.path.join(caminho_dados, "Rodada_Teste_%Y_%m_%d_%H-%M-%S.txt"))
                  Log_dados = open(filename1, 'w')
                  print("Novo arquivo de log criado: %s" % filename1)
                  print(Cabecalho, file=Log_dados)
                  j = 1
                  perda_PK_RX = 0

               if estado_anterior != 1:
                  print('[LoRa] Teste INICIADO / RETOMADO.')
                  estado_anterior = 1

               # Verifica se atingiu o limite de medidas da rodada
               if j > num_medidas_total:
                  #print(f'[LoRa] Final das medidas ({num_medidas_total}).')
                  print('Pacotes enviados = ', num_medidas_total, ' Pacotes perdidos = ', perda_PK_RX)
                  print('Tempo Entre Pacotes = ', Tempo_gasto)
                  if Log_dados and not Log_dados.closed:
                     Log_dados.close()
                     print('[LoRa] Arquivo de log salvo e fechado com sucesso.')
                  Log_dados = None
                  primeiro_pacote_recebido = 0
                  perda_PK_RX = 0
                  
                  # Escreve 0 automaticamente na primeira linha do PARAMETROS.txt para parar o teste
                  try:
                     if config_atual:
                        _, m_v, t_v, s_v = config_atual
                        with open(caminho_txt_parametros, "w") as pf:
                           pf.write("0\n")
                           pf.write(f"{m_v}\n")
                           pf.write(f"{t_v}\n")
                           pf.write(f"{s_v}\n")
                  except Exception as e:
                     print(f"[Erro] Falha ao atualizar PARAMETROS.txt para 0: {e}")

                  rodada_concluida = True
                  time.sleep(1)
                  continue

               Tempo_inicio_pacote = time.time()

               if (primeiro_pacote_recebido == 0):
                  # Chama a função dowlink()
                  downlink()
                                  
               # Chama a função uplink()
               pacote_recebido = 0
               uplink()

               if len(Pacote_UL) == Tamanho_pacote:
                  print('Pacote = ', j, ' | Pacote UL recebido | LED = ', Comando_LED_amarelo)
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
                  print(Tempo + ', ' + str(j) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)
                  
                  if Grava_log == 1 and Log_dados and not Log_dados.closed:
                     Dados_log = Tempo + ',' + str(j) + ',' + Dados_DL + ',' + Dados_UL
                     print(Dados_log, file=Log_dados)
                     Log_dados.flush()
               else:
                  ser.reset_input_buffer()
                  perda_PK_RX += 1
                  print('Cont = ', j, ' PERDEU PACOTE ')
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
                  print(Tempo + ', ' + str(j) + ', Downlink: ' + Dados_DL + ' Uplink: ' + Dados_UL)

                  if Grava_log == 1 and Log_dados and not Log_dados.closed:
                     Dados_log = Tempo + ',' + str(j) + ',' + Dados_DL + ',' + Dados_UL
                     print(Dados_log, file=Log_dados)
                     Log_dados.flush()

               j += 1
               Tempo_gasto = time.time() - Tempo_inicio_pacote
               if Tempo_gasto < Tempo_entre_pacotes:
                  time.sleep(Tempo_entre_pacotes - Tempo_gasto)
           else:
               time.sleep(0.5)

        except (serial.SerialException, OSError, ConnectionError) as e:
           print("\n[Aviso] Conexão com o Gateway perdida! Aguardando reconexão física do cabo...")
            
           # Fecha a porta anterior com segurança se houver alguma referência aberta
           try:
               ser.close()
           except:
               pass

           # Loop contínuo de tentativa de reconexão até o usuário plugá-lo de volta
           while True:
               try:
                   time.sleep(3) # Tenta a cada 3 segundos
                   ser = serial.Serial("COM" + str(n_serial), 115200, timeout=0.5, parity=serial.PARITY_NONE)
                   ser.setDTR(False)
                   ser.setRTS(False)
                   time.sleep(0.1)
                   ser.setDTR(True)
                   ser.setRTS(True)
                   time.sleep(1.5)
                   ser.reset_input_buffer()
                   ser.reset_output_buffer()
                   print("\n[Sucesso] Gateway reconectado! Retomando o teste...")
                   break # Sai do loop de reconexão e volta ao loop principal do teste
               except (serial.SerialException, FileNotFoundError):
                   # Enquanto o cabo estiver desligado, exibe pontos na tela sem quebrar o script
                   print(".", end="", flush=True)
               except Exception as ex:
                   # Outros erros inesperados durante a tentativa
                   print(f"\n[Erro inesperado na reconexão: {ex}]. Tentando novamente...")

        #
        '''
        except (serial.SerialException, OSError, ConnectionError) as e:
           print("\n[Aviso] Conexão com o Gateway perdida! Tentando reconectar...")
            
           # Tenta fechar a porta anterior se ainda existir
           try:
               ser.close()
           except:
               pass

           # Loop de tentativa de reconexão a cada 3 segundos
           while True:
               try:
                   time.sleep(3)
                   ser = serial.Serial("COM" + str(n_serial), 115200, timeout=0.5, parity=serial.PARITY_NONE)
                   ser.setDTR(False)
                   ser.setRTS(False)
                   time.sleep(0.1)
                   ser.setDTR(True)
                   ser.setRTS(True)
                   time.sleep(1.5)
                   ser.reset_input_buffer()
                   ser.reset_output_buffer()
                   print("[Sucesso] Gateway reconectado com sucesso! Retomando teste...")
                   break
               except Exception:
                   print(".", end="", flush=True)
        '''
        
except KeyboardInterrupt:
   print("\n[Ctrl + C] Interrompido pelo usuário.")
   try:
      if Grava_log == 1 and 'Log_dados' in locals() and Log_dados and not Log_dados.closed:
         Log_dados.close()
   except:
      pass
   print('[LoRa] Fim da Execução')
finally:
   try:
      ser.close()
      print("[Serial] Porta serial fechada.")
   except:
      pass
