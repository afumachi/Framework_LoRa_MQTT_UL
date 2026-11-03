# Abstração | Gerência [RSSI, SNR e PSR] | N5 | WissTek-IoT | Framework LoRa
# 29/10/2026
# ====== Nível 5 - Gerência ======
# Extrai RSSI e SNR dos dados brutos e calcula a PSR gerando arquivos CSV dinâmicos por rodada
import time
import os
from datetime import datetime

# Pasta do Nível 4 (4_N4_Armazenamento)
PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"

# Garante que as pastas existem
if not os.path.exists(PASTA_PROCESSADOS):
    os.makedirs(PASTA_PROCESSADOS)

def formatar_pt_br(valor):
    """Converte o ponto decimal em vírgula para o Excel em português e formata como string"""
    return str(valor).replace('.', ',')

ultimo_arquivo_entrada = ""
arquivo_excel_csv = ""

while True:
    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    arquivos = os.listdir(f"{PASTA_N4}/Dados_Brutos")
    arquivos.sort()
    for nome in arquivos:
        if nome.endswith(".txt"):
            arquivo_entrada = f"{PASTA_N4}/Dados_Brutos/" + nome

    if not arquivo_entrada:
        print("Nenhum arquivo de dados brutos encontrado.")
        time.sleep(1)
        continue

    # Se detectou um NOVO arquivo de entrada, cria um novo arquivo CSV exclusivo para esta rodada
    if arquivo_entrada != ultimo_arquivo_entrada:
        ultimo_arquivo_entrada = arquivo_entrada
        timestamp_atual = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
        arquivo_excel_csv = os.path.join(PASTA_PROCESSADOS, f"Rodada_Gerencia_{timestamp_atual}.csv")
        print(f"\n[NOVO TESTE DETECTADO] Criando novo CSV: {arquivo_excel_csv}")

    # Abre o arquivo de dados brutos
    try:
        with open(arquivo_entrada, "r") as arquivo:
            linhas = arquivo.readlines()
    except Exception as e:
        print(f"Erro ao ler arquivo bruto: {e}")
        time.sleep(1)
        continue

    # Listas que guardam os valores calculados
    rssi_down = []
    rssi_up = []
    snr_down = []
    snr_up = []
    psr = []

    total_pacotes = 0
    pacotes_recebidos = 0
    RSSI_DL, RSSI_UL, SNR_DL, SNR_UL, PSR = 0, 0, 0, 0, 0

    for i in range(1, len(linhas)):
        partes = linhas[i].split(",")
        total_pacotes = total_pacotes + 1

        pacote_recebido = 0
        for j in range(10):
            if ((int(partes[23+j]) != 9) and ((int(partes[32]) == 1))):
                pacote_recebido = 1

        if pacote_recebido == 1:
            pacotes_recebidos = pacotes_recebidos + 1

            UL_B0 = int(partes[22]) 
            if UL_B0 == 127:
                RSSI_DL = -10.5
            elif UL_B0 > 128:
                RSSI_DL = ((UL_B0-256)/2.0)-74
            else:
                RSSI_DL = (UL_B0/2.0)-74

            UL_B1 = int(partes[23])
            SNR_DL = round(((UL_B1 / 4) - 30), 2)

            UL_B2 = int(partes[24])
            if UL_B2 == 127:
                RSSI_UL = -10.5          
            elif UL_B2 > 128:
                RSSI_UL = ((UL_B2-256)/2.0)-74
            else:
                RSSI_UL = (UL_B2/2.0)-74

            UL_B3 = int(partes[25])
            SNR_UL = round(((UL_B3 / 4) - 30), 2)

            rssi_down.append(RSSI_DL)
            rssi_up.append(RSSI_UL)
            snr_down.append(SNR_DL)
            snr_up.append(SNR_UL)
        else:
            rssi_down.append("")
            rssi_up.append("")
            snr_down.append("")
            snr_up.append("")

        PSR = round((pacotes_recebidos/total_pacotes)*100, 2)
        psr.append(PSR)

    # Grava/Atualiza os dados no CSV da rodada atual com tratamento de concorrência (PermissionError)
    sucesso_gravacao = False
    tentativas = 5
    while not sucesso_gravacao and tentativas > 0:
        try:
            with open(arquivo_excel_csv, "w", encoding="utf-8") as f_excel:
                print("RSSI_Downlink;RSSI_Uplink;SNR_Downlink;SNR_Uplink;PSR_Acumulada", file=f_excel)
                for i in range(len(psr)):
                    r_down = formatar_pt_br(rssi_down[i]) if rssi_down[i] != "" else ""
                    r_up = formatar_pt_br(rssi_up[i]) if rssi_up[i] != "" else ""
                    s_down = formatar_pt_br(snr_down[i]) if snr_down[i] != "" else ""
                    s_up = formatar_pt_br(snr_up[i]) if snr_up[i] != "" else ""
                    p_str = formatar_pt_br(psr[i])
                    print(f"{r_down};{r_up};{s_down};{s_up};{p_str}", file=f_excel)
            sucesso_gravacao = True
        except PermissionError:
            tentativas -= 1
            time.sleep(0.05)

    print(f"Arquivo = {arquivo_entrada} | CSV = {os.path.basename(arquivo_excel_csv)} | Pacotes = {total_pacotes} | Recebidos = {pacotes_recebidos} | PSR = {PSR}")
    time.sleep(1)
