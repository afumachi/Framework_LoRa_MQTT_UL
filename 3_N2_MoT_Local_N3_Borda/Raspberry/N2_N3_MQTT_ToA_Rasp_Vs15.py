# MoT LoRa + Borda + MQTT | Entrada Serial via Teclado e Ciclo Contínuo (Com Filtro UL)
import serial
import math
import time
import os
from serial.tools import list_ports  # Importa a ferramenta de escaneamento
import threading
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

# ========================== 1 - Configurações e Variáveis MQTT ==========================
BROKER      = "www.tpm.dev.br"
PORTA_MQTT  = 1883

TOPIC_DL    = "mot_mqtt_194104/gateway/downlink"  
TOPIC_UL    = "mot_mqtt_194104/gateway/uplink"    

MQTT_QOS    = 1
estado_mqtt = 0

TAMANHO_PACOTE_DL = 20
TAMANHO_PACOTE_UL = 00

global Pacote_DL_payload, Pacote_UL
Pacote_DL_payload = bytearray(TAMANHO_PACOTE_DL)
Pacote_UL = bytearray(TAMANHO_PACOTE_UL)

for i in range(len(Pacote_DL_payload)):
    Pacote_DL_payload[i] = 0

for i in range(len(Pacote_UL)):
    Pacote_UL[i] = 0
    
pacote_dl_event = threading.Event()
lock_serial = threading.Lock()

# ========================== 2 - Tabela LUT (72 combinações) ==========================
RADIO_CONFIG_LUT = [
    # SF=7 (0-11)
    (7, 125000, 5), (7, 125000, 6), (7, 125000, 7), (7, 125000, 8),
    (7, 250000, 5), (7, 250000, 6), (7, 250000, 7), (7, 250000, 8),
    (7, 500000, 5), (7, 500000, 6), (7, 500000, 7), (7, 500000, 8),
    # SF=8 (12-23)
    (8, 125000, 5), (8, 125000, 6), (8, 125000, 7), (8, 125000, 8),
    (8, 250000, 5), (8, 250000, 6), (8, 250000, 7), (8, 250000, 8),
    (8, 500000, 5), (8, 500000, 6), (8, 500000, 7), (8, 500000, 8),
    # SF=9 (24-35)
    (9, 125000, 5), (9, 125000, 6), (9, 125000, 7), (9, 125000, 8),
    (9, 250000, 5), (9, 250000, 6), (9, 250000, 7), (9, 250000, 8),
    (9, 500000, 5), (9, 500000, 6), (9, 500000, 7), (9, 500000, 8),
    # SF=10 (36-47)
    (10, 125000, 5), (10, 125000, 6), (10, 125000, 7), (10, 125000, 8),
    (10, 250000, 5), (10, 250000, 6), (10, 250000, 7), (10, 250000, 8),
    (10, 500000, 5), (10, 500000, 6), (10, 500000, 7), (10, 500000, 8),
    # SF=11 (48-59)
    (11, 125000, 5), (11, 125000, 6), (11, 125000, 7), (11, 125000, 8),
    (11, 250000, 5), (11, 250000, 6), (11, 250000, 7), (11, 250000, 8),
    (11, 500000, 5), (11, 500000, 6), (11, 500000, 7), (11, 500000, 8),
    # SF=12 (60-71)
    (12, 125000, 5), (12, 125000, 6), (12, 125000, 7), (12, 125000, 8),
    (12, 250000, 5), (12, 250000, 6), (12, 250000, 7), (12, 250000, 8),
    (12, 500000, 5), (12, 500000, 6), (12, 500000, 7), (12, 500000, 8),
]

# ========================== 3 - Callbacks MQTT ==========================
def on_connect(client, userdata, flags, reason_code, properties):
    global estado_mqtt
    if reason_code == 0:
        print("[MQTT] Conectado ao Broker com sucesso.")
        client.subscribe(TOPIC_DL, qos=MQTT_QOS)
        print(f"[MQTT] Inscrito no tópico de Downlink: {TOPIC_DL} (QoS{MQTT_QOS})")
        estado_mqtt = 1
    else:
        print(f"[MQTT] Falha na conexão. Código: {reason_code}")
        estado_mqtt = 0

def on_message(client, userdata, msg):
    global Pacote_DL_payload
    payload = msg.payload
    if len(payload) >= TAMANHO_PACOTE_DL:
        Pacote_DL_payload = bytearray(payload[:TAMANHO_PACOTE_DL])
        pacote_dl_event.set()

def on_disconnect(client, userdata, flags, reason_code, properties):
    global estado_mqtt
    estado_mqtt = 0
    print(f"[MQTT] Desconectado (rc={reason_code}). Tentando reconectar...")

client = mqtt.Client(CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.reconnect_delay_set(min_delay=1, max_delay=15)

print("[MQTT] Conectando ao broker MQTT...")
client.connect_async(host=BROKER, port=PORTA_MQTT, keepalive=15)
client.loop_start()

timeout_conexao = 2
inicio = time.time()
while estado_mqtt == 0 and (time.time() - inicio) < timeout_conexao:
    time.sleep(0.2)

# ========================== 4 - Função de Cálculo ToA ==========================
def calcular_toa_por_lut(lut_index):
    if 0 <= lut_index < len(RADIO_CONFIG_LUT):
        sf, bw_hz, cr = RADIO_CONFIG_LUT[lut_index]
    else:
        sf, bw_hz, cr = (12, 125000, 8)

    tempo_simbolo = (2**sf) / bw_hz
    tempo_preambulo = (8 + 4.25) * tempo_simbolo
    low_dr_opt = 1 if tempo_simbolo > 0.016 else 0
    
    valor_CR = cr - 4 if cr >= 5 else 1
    
    n_pacote = (8 * TAMANHO_PACOTE_UL - 4 * sf + 28 + 16 * 1 - 20 * 0) / (4 * (sf - 2 * low_dr_opt))
    n_payload_simbolo = 8 + max(math.ceil(n_pacote) * (valor_CR + 4), 0)
    
    toa_s = ((tempo_preambulo + (n_payload_simbolo * tempo_simbolo)) * 1000) / 1000.0
    return toa_s

# código para Linux Rasp

import serial
import time
from serial.tools import list_ports  # Importa a ferramenta de escaneamento

# ========================== 5 - Configuração da Porta Serial ==========================
print("\n========== Configuração da Porta Serial Automática ==========")

porta_com = None

# 1. Escanear portas seriais ativas no sistema
portas_disponiveis = list(list_ports.comports())

# 2. Filtrar apenas portas que possuem características de placas USB (NodeMCU/ESP32 geralmente usam chips CH340, CP210x, etc.)
# No Linux elas aparecem como /dev/ttyUSBx ou /dev/ttyACMx
portas_validas = [p.device for p in portas_disponiveis if "ttyUSB" in p.device or "ttyACM" in p.device]

if len(portas_validas) == 1:
    # Cenário Ideal: Apenas o seu ESP32/NodeMCU está conectado
    porta_com = portas_validas[0]
    print(f"[Auto-Detect] Uma única placa foi encontrada: {porta_com}")
    
elif len(portas_validas) > 1:
    # Cenário de conflito: Mais de um dispositivo USB-Serial conectado
    print("[Aviso] Mais de um dispositivo USB-Serial foi detectado:")
    for i, p in enumerate(portas_validas):
        print(f" [{i}] -> {p}")
    idx = input("Digite o número correspondente à porta do ESP32: ").strip()
    try:
        porta_com = portas_validas[int(idx)]
    except:
        print("[Erro] Seleção inválida. Encerrando.")
        exit(1)
else:
    # Nenhuma porta USB detectada automaticamente (Pode estar desconectada ou sem driver)
    print("[Aviso] Nenhuma porta USB-Serial foi detectada automaticamente.")
    n_serial_input = input("Por favor, digite o nome da porta manualmente (ex: ttyUSB0): ").strip()
    porta_com = n_serial_input if n_serial_input.startswith("/dev/") else "/dev/" + n_serial_input

'''
# 3. Conexão com a porta definida
# código para linux rasp
try:
    ser = serial.Serial(porta_com, 115200, timeout=0.2, parity=serial.PARITY_NONE)
    
    # Controle de DTR/RTS para resetar a placa corretamente ao iniciar
    ser.dtr = False
    ser.rts = False
    time.sleep(0.1)
    ser.dtr = True
    ser.rts = True
    time.sleep(1.5)
    
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print(f"[Serial] Conectado com sucesso à porta {porta_com}")
except Exception as e:
    print(f"[Erro] Falha ao abrir a porta serial {porta_com}: {e}")
    print("[Dica] Verifique se seu usuário tem permissão (sudo usermod -aG dialout $USER)")
    client.loop_stop()
    client.disconnect()
    exit(1)


'''
# código para windowns
# ========================== 5 - Configuração da Porta Serial ==========================
print("\n========== Configuração da Porta Serial ==========")
n_serial_input = input("Digite o número da porta COM em que o gateway LoRa está conectado (ex: 3 para COM3): ").strip()
porta_com = "COM" + n_serial_input

try:
    ser = serial.Serial(porta_com, 115200, timeout=0.2, parity=serial.PARITY_NONE)
    ser.setDTR(False)
    ser.setRTS(False)
    time.sleep(0.1)
    ser.setDTR(True)
    ser.setRTS(True)
    time.sleep(1.5)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print(f"[Serial] Conectado com sucesso à porta {porta_com}")
except Exception as e:
    print(f"[Erro] Falha ao abrir a porta serial {porta_com}: {e}")
    client.loop_stop()
    client.disconnect()
    exit(1)


# ========================== 6 - Loop Principal ==========================
print("\n========== Gateway MQTT + Borda Serial Iniciado (Modo Contínuo) ==========")

try:
    contador_ciclo = 0

    while True:
        contador_ciclo += 1
        print(f"\n[Ciclo {contador_ciclo}] Aguardando pacote de Downlink no tópico MQTT: {TOPIC_DL}...")
        
        pacote_dl_event.clear()
        pacote_dl_event.wait()

        Pacote_DL = list(Pacote_DL_payload)
        
        lut_index_dl = Pacote_DL[0] if len(Pacote_DL) > 0 else 0
        toa_calculado = calcular_toa_por_lut(lut_index_dl)

        Tempo_inicial_RX = time.time()

        # escreve Pacote DL na Serial
        if (len(Pacote_DL) >= TAMANHO_PACOTE_DL):
            ser.reset_input_buffer()
            for byte_dl in Pacote_DL:
                ser.write(bytes([byte_dl]))
            ser.flush()
            time.sleep(0.05)

        # ======== COLETA UPLINK VIA SERIAL ========
        Pacote_UL = b''
        ## Delay de 2x ToA + 200ms
        Tempo_limite_RX = (2 * toa_calculado) + 0.2
        print(f"[LoRa] DL enviado. LUT Index: {lut_index_dl} | ToA: {toa_calculado:.3f}s | Delay total: {Tempo_limite_RX:.3f}s...")


        while len(Pacote_UL) < TAMANHO_PACOTE_UL and (time.time() - Tempo_inicial_RX) < Tempo_limite_RX:
            Pacote_UL = Pacote_UL + ser.read(TAMANHO_PACOTE_UL - len(Pacote_UL))

        # Imprime o resultado final (em formato hexadecimal, excelente para depurar pacotes de bytes)
        print("Pacote UL final (Hex):", Pacote_UL.hex())

        # Validação se o pacote capturado é um eco de texto (começa com 'P' de "PacoteDL...")
        # Caso seja texto e não os 30 bytes binários esperados, descartamos para não publicar lixo fixo.
        if len(Pacote_UL) >= TAMANHO_PACOTE_UL:
            # Verifica se porventura começou com texto legível de log do ESP32 ("Pacote")
            if Pacote_UL[0:6] == b'Pacote' or (Pacote_UL[0] == 80 and Pacote_UL[1] == 97):
                print("[Aviso] Detectado eco de texto na serial em vez de dados binários do Uplink. Descartando leitura...")
                Pacote_UL = bytearray([9] * TAMANHO_PACOTE_UL)
            
            print(f"[Serial] Pacote UL de 30 bytes processado com sucesso.")
            client.publish(TOPIC_UL, bytes(Pacote_UL), qos=MQTT_QOS)
            print(f"[MQTT] Pacote UL publicado no tópico: {TOPIC_UL}")
        else:
            print(f"[Aviso] Timeout ou tamanho incorreto na serial ({len(Pacote_UL)}/30 bytes). Publicando uplink nulo.")
            Pacote_UL = bytearray([9] * TAMANHO_PACOTE_UL)
            client.publish(TOPIC_UL, bytes(Pacote_UL), qos=MQTT_QOS)
            print(f"[MQTT] Pacote UL nulo publicado no tópico: {TOPIC_UL}")

except KeyboardInterrupt:
    print("\n[Ctrl + C] Interrompido pelo usuário.")
finally:
    try:
        ser.close()
        print("[Serial] Porta serial fechada.")
    except:
        pass
    try:
        client.loop_stop()
        client.disconnect()
        print("[MQTT] Desconectado do broker.")
    except:
        pass
    print("[Sistema] Fim da Execução.")
