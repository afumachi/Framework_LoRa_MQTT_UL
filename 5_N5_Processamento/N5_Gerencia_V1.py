# Abstração | Gerência [RSSI, SNR e PSR] | N5 | WissTek-IoT | Framework LoRa
# ====== Nível 5 - Gerência ======
import time
import os
import math
from datetime import datetime

# Pasta do Nível 4 (4_N4_Armazenamento)
PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = f"{PASTA_N4}/Parametros"
PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"
ARQUIVO_PARAMETROS = f"{PASTA_PARAMETROS}/dados_processamento.txt"

# Garante que as pastas existem
if not os.path.exists(PASTA_PROCESSADOS):
    os.makedirs(PASTA_PROCESSADOS)
if not os.path.exists(PASTA_PARAMETROS):
    os.makedirs(PASTA_PARAMETROS)

def formatar_pt_br(valor):
    """Converte o ponto decimal em vírgula para o Excel em português e formata como string"""
    if valor == "" or valor is None:
        return ""
    return str(valor).replace('.', ',')

def ler_parametros():
    """Lê as janelas de média móvel para RSSI e SNR do arquivo dados_processamento.txt"""
    janela_rssi = 10
    janela_snr = 10
    if os.path.exists(ARQUIVO_PARAMETROS):
        try:
            with open(ARQUIVO_PARAMETROS, "r", encoding="utf-8") as f:
                linhas = f.readlines()
                for linha in linhas:
                    if "=" in linha:
                        chave, val = linha.strip().split("=")
                        chave = chave.strip().upper()
                        val = val.strip()
                        if chave == "JANELA_RSSI":
                            janela_rssi = max(1, int(val))
                        elif chave == "JANELA_SNR":
                            janela_snr = max(1, int(val))
        except Exception as e:
            print(f"[N5] Aviso ao ler parâmetros: {e}")
    return janela_rssi, janela_snr

def calcular_estatisticas_completas(lista):
    """Calcula média, desvio padrão amostral, máximo e mínimo de uma lista"""
    valores = [v for v in lista if v != "" and v is not None]
    n = len(valores)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    media = sum(valores) / n
    maximo = max(valores)
    minimo = min(valores)
    if n < 2:
        desvio = 0.0
    else:
        variancia = sum((x - media) ** 2 for x in valores) / (n - 1)
        desvio = math.sqrt(variancia)
    return media, desvio, maximo, minimo

ultimo_arquivo_entrada = ""
arquivo_excel_csv = ""

while True:
    janela_rssi, janela_snr = ler_parametros()

    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    if os.path.exists(f"{PASTA_N4}/Dados_Brutos"):
        arquivos = os.listdir(f"{PASTA_N4}/Dados_Brutos")
        arquivos.sort()
        for nome in arquivos:
            if nome.endswith(".txt"):
                arquivo_entrada = f"{PASTA_N4}/Dados_Brutos/" + nome

    if not arquivo_entrada:
        print("Nenhum arquivo de dados brutos encontrado.")
        time.sleep(1)
        continue

    # Se detectou um NOVO arquivo de entrada, cria um novo arquivo CSV exclusivo para a rodada
    if arquivo_entrada != ultimo_arquivo_entrada:
        ultimo_arquivo_entrada = arquivo_entrada
        timestamp_atual = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
        arquivo_excel_csv = os.path.join(PASTA_PROCESSADOS, f"Rodada_Gerencia_{timestamp_atual}.csv")
        print(f"\n[NOVO TESTE DETECTADO] Criando CSV único da rodada: {arquivo_excel_csv}")

    # Abre o arquivo de dados brutos
    try:
        with open(arquivo_entrada, "r") as arquivo:
            linhas = arquivo.readlines()
    except Exception as e:
        print(f"Erro ao ler arquivo bruto: {e}")
        time.sleep(1)
        continue

    rssi_down = []
    rssi_up = []
    snr_down = []
    snr_up = []
    psr = []
    rssi_up_ma = []
    snr_up_ma = []

    # Listas auxiliares para persistir as colunas laterais linha a linha
    pacotes_perdidos_col = []
    rssi_ma_media_col = []
    rssi_ma_desv_col = []
    rssi_ma_max_col = []
    rssi_ma_min_col = []
    snr_ma_media_col = []
    snr_ma_desv_col = []
    snr_ma_max_col = []
    snr_ma_min_col = []

    total_pacotes = 0
    pacotes_recebidos = 0
    pacotes_perdidos_total = 0
    RSSI_DL, RSSI_UL, SNR_DL, SNR_UL, PSR = 0, 0, 0, 0, 0

    buffer_rssi_mw = []
    buffer_snr = []

    for i in range(1, len(linhas)):
        partes = linhas[i].split(",")
        total_pacotes += 1

        pacote_recebido = 0
        for j in range(10):
            if ((int(partes[23+j]) != 9) and ((int(partes[32]) == 1))):
                pacote_recebido = 1

        if pacote_recebido == 1:
            pacotes_recebidos += 1

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

            # Média Móvel de RSSI em mW convertida para dBm
            rssi_mw = 10.0 ** (RSSI_UL / 10.0)
            buffer_rssi_mw.append(rssi_mw)
            if len(buffer_rssi_mw) > janela_rssi:
                buffer_rssi_mw.pop(0)
            media_mw = sum(buffer_rssi_mw) / len(buffer_rssi_mw)
            rssi_up_ma.append(round(10.0 * math.log10(media_mw), 2))

            # Média Móvel de SNR em dB
            buffer_snr.append(SNR_UL)
            if len(buffer_snr) > janela_snr:
                buffer_snr.pop(0)
            snr_up_ma.append(round(sum(buffer_snr) / len(buffer_snr), 2))

        else:
            rssi_down.append("")
            rssi_up.append("")
            snr_down.append("")
            snr_up.append("")
            rssi_up_ma.append(rssi_up_ma[-1] if rssi_up_ma else "")
            snr_up_ma.append(snr_up_ma[-1] if snr_up_ma else "")
            pacotes_perdidos_total += 1

        PSR = round((pacotes_recebidos/total_pacotes)*100, 2)
        psr.append(PSR)

        # Estatísticas cumulativas até o momento atual
        m_r, d_r, max_r, min_r = calcular_estatisticas_completas(rssi_up_ma)
        m_s, d_s, max_s, min_s = calcular_estatisticas_completas(snr_up_ma)

        pacotes_perdidos_col.append(pacotes_perdidos_total)
        rssi_ma_media_col.append(m_r)
        rssi_ma_desv_col.append(d_r)
        rssi_ma_max_col.append(max_r)
        rssi_ma_min_col.append(min_r)
        snr_ma_media_col.append(m_s)
        snr_ma_desv_col.append(d_s)
        snr_ma_max_col.append(max_s)
        snr_ma_min_col.append(min_s)

    # Gravação do CSV principal de amostras com a coluna Pacotes_Perdidos
    sucesso_gravacao = False
    tentativas = 5
    while not sucesso_gravacao and tentativas > 0:
        try:
            with open(arquivo_excel_csv, "w", encoding="utf-8") as f_excel:
                cabecalho = (
                    "RSSI_Downlink;RSSI_Uplink;SNR_Downlink;SNR_Uplink;PSR_Acumulada;"
                    "RSSI_Uplink_MA;SNR_Uplink_MA;Pacotes_Perdidos;"
                    "RSSI_MA_Media;RSSI_MA_DesvPad;RSSI_MA_Max;RSSI_MA_Min;"
                    "SNR_MA_Media;SNR_MA_DesvPad;SNR_MA_Max;SNR_MA_Min"
                )
                print(cabecalho, file=f_excel)
                
                for i in range(len(psr)):
                    r_down = formatar_pt_br(rssi_down[i])
                    r_up = formatar_pt_br(rssi_up[i])
                    s_down = formatar_pt_br(snr_down[i])
                    s_up = formatar_pt_br(snr_up[i])
                    p_str = formatar_pt_br(psr[i])
                    r_up_ma_str = formatar_pt_br(rssi_up_ma[i])
                    s_up_ma_str = formatar_pt_br(snr_up_ma[i])
                    p_perdidos = pacotes_perdidos_col[i]
                    
                    r_media = formatar_pt_br(round(rssi_ma_media_col[i], 2))
                    r_desv = formatar_pt_br(round(rssi_ma_desv_col[i], 2))
                    r_max = formatar_pt_br(round(rssi_ma_max_col[i], 2))
                    r_min = formatar_pt_br(round(rssi_ma_min_col[i], 2))
                    
                    s_media = formatar_pt_br(round(snr_ma_media_col[i], 2))
                    s_desv = formatar_pt_br(round(snr_ma_desv_col[i], 2))
                    s_max = formatar_pt_br(round(snr_ma_max_col[i], 2))
                    s_min = formatar_pt_br(round(snr_ma_min_col[i], 2))

                    linha = (
                        f"{r_down};{r_up};{s_down};{s_up};{p_str};"
                        f"{r_up_ma_str};{s_up_ma_str};{p_perdidos};"
                        f"{r_media};{r_desv};{r_max};{r_min};"
                        f"{s_media};{s_desv};{s_max};{s_min}"
                    )
                    print(linha, file=f_excel)
            sucesso_gravacao = True
        except PermissionError:
            tentativas -= 1
            time.sleep(0.05)

    print(f"--- [N5 ATUALIZADO] CSV Atualizado com Pacotes Perdidos reais: {os.path.basename(arquivo_excel_csv)} ---")
    time.sleep(1)


'''

# Abstração | Gerência [RSSI, SNR e PSR] | N5 | WissTek-IoT | Framework LoRa
# ====== Nível 5 - Gerência ======
import time
import os
import math
from datetime import datetime

# Pasta do Nível 4 (4_N4_Armazenamento)
PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = f"{PASTA_N4}/Parametros"
PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"
ARQUIVO_PARAMETROS = f"{PASTA_PARAMETROS}/dados_processamento.txt"

# Garante que as pastas existem
if not os.path.exists(PASTA_PROCESSADOS):
    os.makedirs(PASTA_PROCESSADOS)
if not os.path.exists(PASTA_PARAMETROS):
    os.makedirs(PASTA_PARAMETROS)

def formatar_pt_br(valor):
    """Converte o ponto decimal em vírgula para o Excel em português e formata como string"""
    if valor == "" or valor is None:
        return ""
    return str(valor).replace('.', ',')

def ler_parametros():
    """Lê as janelas de média móvel para RSSI e SNR do arquivo dados_processamento.txt"""
    janela_rssi = 10
    janela_snr = 10
    if os.path.exists(ARQUIVO_PARAMETROS):
        try:
            with open(ARQUIVO_PARAMETROS, "r", encoding="utf-8") as f:
                linhas = f.readlines()
                for linha in linhas:
                    if "=" in linha:
                        chave, val = linha.strip().split("=")
                        chave = chave.strip().upper()
                        val = val.strip()
                        if chave == "JANELA_RSSI":
                            janela_rssi = max(1, int(val))
                        elif chave == "JANELA_SNR":
                            janela_snr = max(1, int(val))
        except Exception as e:
            print(f"[N5] Aviso ao ler parâmetros: {e}")
    return janela_rssi, janela_snr

def calcular_estatisticas_completas(lista):
    """Calcula média, desvio padrão amostral, máximo e mínimo de uma lista"""
    valores = [v for v in lista if v != "" and v is not None]
    n = len(valores)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    media = sum(valores) / n
    maximo = max(valores)
    minimo = min(valores)
    if n < 2:
        desvio = 0.0
    else:
        variancia = sum((x - media) ** 2 for x in valores) / (n - 1)
        desvio = math.sqrt(variancia)
    return media, desvio, maximo, minimo

ultimo_arquivo_entrada = ""
arquivo_excel_csv = ""

while True:
    janela_rssi, janela_snr = ler_parametros()

    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    if os.path.exists(f"{PASTA_N4}/Dados_Brutos"):
        arquivos = os.listdir(f"{PASTA_N4}/Dados_Brutos")
        arquivos.sort()
        for nome in arquivos:
            if nome.endswith(".txt"):
                arquivo_entrada = f"{PASTA_N4}/Dados_Brutos/" + nome

    if not arquivo_entrada:
        print("Nenhum arquivo de dados brutos encontrado.")
        time.sleep(1)
        continue

    # Se detectou um NOVO arquivo de entrada, cria um novo arquivo CSV exclusivo para a rodada
    if arquivo_entrada != ultimo_arquivo_entrada:
        ultimo_arquivo_entrada = arquivo_entrada
        timestamp_atual = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")
        arquivo_excel_csv = os.path.join(PASTA_PROCESSADOS, f"Rodada_Gerencia_{timestamp_atual}.csv")
        print(f"\n[NOVO TESTE DETECTADO] Criando CSV único da rodada: {arquivo_excel_csv}")

    # Abre o arquivo de dados brutos
    try:
        with open(arquivo_entrada, "r") as arquivo:
            linhas = arquivo.readlines()
    except Exception as e:
        print(f"Erro ao ler arquivo bruto: {e}")
        time.sleep(1)
        continue

    rssi_down = []
    rssi_up = []
    snr_down = []
    snr_up = []
    psr = []
    rssi_up_ma = []
    snr_up_ma = []

    # Listas auxiliares para persistir as colunas de estatísticas linha a linha
    rssi_ma_media_col = []
    rssi_ma_desv_col = []
    rssi_ma_max_col = []
    rssi_ma_min_col = []
    snr_ma_media_col = []
    snr_ma_desv_col = []
    snr_ma_max_col = []
    snr_ma_min_col = []

    total_pacotes = 0
    pacotes_recebidos = 0
    pacotes_perdidos_total = 0
    RSSI_DL, RSSI_UL, SNR_DL, SNR_UL, PSR = 0, 0, 0, 0, 0

    buffer_rssi_mw = []
    buffer_snr = []

    for i in range(1, len(linhas)):
        partes = linhas[i].split(",")
        total_pacotes += 1

        pacote_recebido = 0
        for j in range(10):
            if ((int(partes[23+j]) != 9) and ((int(partes[32]) == 1))):
                pacote_recebido = 1          	

        if pacote_recebido == 1:
            pacotes_recebidos += 1

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

            # Média Móvel de RSSI em mW convertida para dBm
            rssi_mw = 10.0 ** (RSSI_UL / 10.0)
            buffer_rssi_mw.append(rssi_mw)
            if len(buffer_rssi_mw) > janela_rssi:
                buffer_rssi_mw.pop(0)
            media_mw = sum(buffer_rssi_mw) / len(buffer_rssi_mw)
            rssi_up_ma.append(round(10.0 * math.log10(media_mw), 2))

            # Média Móvel de SNR em dB
            buffer_snr.append(SNR_UL)
            if len(buffer_snr) > janela_snr:
                buffer_snr.pop(0)
            snr_up_ma.append(round(sum(buffer_snr) / len(buffer_snr), 2))

        else:
            rssi_down.append("")
            rssi_up.append("")
            snr_down.append("")
            snr_up.append("")
            rssi_up_ma.append(rssi_up_ma[-1] if rssi_up_ma else "")
            snr_up_ma.append(snr_up_ma[-1] if snr_up_ma else "")
            pacotes_perdidos_total += 1

        PSR = round((pacotes_recebidos/total_pacotes)*100, 2)
        psr.append(PSR)

        # Calcula estatísticas cumulativas até o momento atual do teste
        m_r, d_r, max_r, min_r = calcular_estatisticas_completas(rssi_up_ma)
        m_s, d_s, max_s, min_s = calcular_estatisticas_completas(snr_up_ma)

        rssi_ma_media_col.append(m_r)
        rssi_ma_desv_col.append(d_r)
        rssi_ma_max_col.append(max_r)
        rssi_ma_min_col.append(min_r)
        snr_ma_media_col.append(m_s)
        snr_ma_desv_col.append(d_s)
        snr_ma_max_col.append(max_s)
        snr_ma_min_col.append(min_s)

    # Gravação do CSV principal de amostras com as colunas laterais estendidas
    sucesso_gravacao = False
    tentativas = 5
    while not sucesso_gravacao and tentativas > 0:
        try:
            with open(arquivo_excel_csv, "w", encoding="utf-8") as f_excel:
                cabecalho = (
                    "RSSI_Downlink;RSSI_Uplink;SNR_Downlink;SNR_Uplink;PSR_Acumulada;"
                    "RSSI_Uplink_MA;SNR_Uplink_MA;"
                    "RSSI_MA_Media;RSSI_MA_DesvPad;RSSI_MA_Max;RSSI_MA_Min;"
                    "SNR_MA_Media;SNR_MA_DesvPad;SNR_MA_Max;SNR_MA_Min"
                )
                print(cabecalho, file=f_excel)
                
                for i in range(len(psr)):
                    r_down = formatar_pt_br(rssi_down[i])
                    r_up = formatar_pt_br(rssi_up[i])
                    s_down = formatar_pt_br(snr_down[i])
                    s_up = formatar_pt_br(snr_up[i])
                    p_str = formatar_pt_br(psr[i])
                    r_up_ma_str = formatar_pt_br(rssi_up_ma[i])
                    s_up_ma_str = formatar_pt_br(snr_up_ma[i])
                    
                    r_media = formatar_pt_br(round(rssi_ma_media_col[i], 2))
                    r_desv = formatar_pt_br(round(rssi_ma_desv_col[i], 2))
                    r_max = formatar_pt_br(round(rssi_ma_max_col[i], 2))
                    r_min = formatar_pt_br(round(rssi_ma_min_col[i], 2))
                    
                    s_media = formatar_pt_br(round(snr_ma_media_col[i], 2))
                    s_desv = formatar_pt_br(round(snr_ma_desv_col[i], 2))
                    s_max = formatar_pt_br(round(snr_ma_max_col[i], 2))
                    s_min = formatar_pt_br(round(snr_ma_min_col[i], 2))

                    linha = (
                        f"{r_down};{r_up};{s_down};{s_up};{p_str};"
                        f"{r_up_ma_str};{s_up_ma_str};"
                        f"{r_media};{r_desv};{r_max};{r_min};"
                        f"{s_media};{s_desv};{s_max};{s_min}"
                    )
                    print(linha, file=f_excel)
            sucesso_gravacao = True
        except PermissionError:
            tentativas -= 1
            time.sleep(0.05)

    print(f"--- [N5 ATUALIZADO] CSV Único Atualizado com colunas laterais: {os.path.basename(arquivo_excel_csv)} ---")
    time.sleep(1)
'''
'''
# Abstração | Gerência [RSSI, SNR e PSR] | N5 | WissTek-IoT | Framework LoRa
# ====== Nível 5 - Gerência ======
import time
import os
import math
from datetime import datetime

# Pasta do Nível 4 (4_N4_Armazenamento)
PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = f"{PASTA_N4}/Parametros"
PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"
ARQUIVO_PARAMETROS = f"{PASTA_PARAMETROS}/dados_processamento.txt"

# Garante que as pastas existem
if not os.path.exists(PASTA_PROCESSADOS):
    os.makedirs(PASTA_PROCESSADOS)
if not os.path.exists(PASTA_PARAMETROS):
    os.makedirs(PASTA_PARAMETROS)

def formatar_pt_br(valor):
    """Converte o ponto decimal em vírgula para o Excel em português e formata como string"""
    if valor == "" or valor is None:
        return ""
    return str(valor).replace('.', ',')

def ler_parametros():
    """Lê as janelas de média móvel para RSSI e SNR do arquivo dados_processamento.txt"""
    janela_rssi = 10
    janela_snr = 10
    if os.path.exists(ARQUIVO_PARAMETROS):
        try:
            with open(ARQUIVO_PARAMETROS, "r", encoding="utf-8") as f:
                linhas = f.readlines()
                for linha in linhas:
                    if "=" in linha:
                        chave, val = linha.strip().split("=")
                        chave = chave.strip().upper()
                        val = val.strip()
                        if chave == "JANELA_RSSI":
                            janela_rssi = max(1, int(val))
                        elif chave == "JANELA_SNR":
                            janela_snr = max(1, int(val))
        except Exception as e:
            print(f"[N5] Aviso ao ler parâmetros: {e}")
    return janela_rssi, janela_snr

def calcular_estatisticas_completas(lista):
    """Calcula média, desvio padrão amostral, máximo e mínimo de uma lista"""
    valores = [v for v in lista if v != "" and v is not None]
    n = len(valores)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    media = sum(valores) / n
    maximo = max(valores)
    minimo = min(valores)
    if n < 2:
        desvio = 0.0
    else:
        variancia = sum((x - media) ** 2 for x in valores) / (n - 1)
        desvio = math.sqrt(variancia)
    return media, desvio, maximo, minimo

ultimo_arquivo_entrada = ""
arquivo_excel_csv = ""

while True:
    janela_rssi, janela_snr = ler_parametros()

    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    if os.path.exists(f"{PASTA_N4}/Dados_Brutos"):
        arquivos = os.listdir(f"{PASTA_N4}/Dados_Brutos")
        arquivos.sort()
        for nome in arquivos:
            if nome.endswith(".txt"):
                arquivo_entrada = f"{PASTA_N4}/Dados_Brutos/" + nome

    if not arquivo_entrada:
        print("Nenhum arquivo de dados brutos encontrado.")
        time.sleep(1)
        continue

    # Se detectou um NOVO arquivo de entrada, cria um novo arquivo CSV exclusivo
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
    
    # Listas para Média Móvel
    rssi_up_ma = []
    snr_up_ma = []

    total_pacotes = 0
    pacotes_recebidos = 0
    pacotes_perdidos_total = 0
    RSSI_DL, RSSI_UL, SNR_DL, SNR_UL, PSR = 0, 0, 0, 0, 0

    buffer_rssi_mw = []
    buffer_snr = []

    for i in range(1, len(linhas)):
        partes = linhas[i].split(",")
        total_pacotes += 1

        pacote_recebido = 0
        for j in range(10):
            if ((int(partes[23+j]) != 9) and ((int(partes[32]) == 1))):
                pacote_recebido = 1
            else:
                pacotes_perdidos_total += 1

        if pacote_recebido == 1:
            pacotes_recebidos += 1

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

            # --- Média Móvel de RSSI em mW ---
            rssi_mw = 10.0 ** (RSSI_UL / 10.0)
            buffer_rssi_mw.append(rssi_mw)
            if len(buffer_rssi_mw) > janela_rssi:
                buffer_rssi_mw.pop(0)
            
            media_mw = sum(buffer_rssi_mw) / len(buffer_rssi_mw)
            media_rssi_dbm = round(10.0 * math.log10(media_mw), 2)
            rssi_up_ma.append(media_rssi_dbm)

            # --- Média Móvel de SNR em dB ---
            buffer_snr.append(SNR_UL)
            if len(buffer_snr) > janela_snr:
                buffer_snr.pop(0)
            
            media_snr_db = round(sum(buffer_snr) / len(buffer_snr), 2)
            snr_up_ma.append(media_snr_db)

        else:
            rssi_down.append("")
            rssi_up.append("")
            snr_down.append("")
            snr_up.append("")
            rssi_up_ma.append(rssi_up_ma[-1] if rssi_up_ma else "")
            snr_up_ma.append(snr_up_ma[-1] if snr_up_ma else "")

        PSR = round((pacotes_recebidos/total_pacotes)*100, 2)
        psr.append(PSR)

    # Estatísticas completas
    media_rssi_ma, desvio_rssi_ma, max_rssi_ma, min_rssi_ma = calcular_estatisticas_completas(rssi_up_ma)
    media_snr_ma, desvio_snr_ma, max_snr_ma, min_snr_ma = calcular_estatisticas_completas(snr_up_ma)

    # Gravação no CSV incluindo as colunas extras se necessário ou leitura direta no N6
    sucesso_gravacao = False
    tentativas = 5
    while not sucesso_gravacao and tentativas > 0:
        try:
            with open(arquivo_excel_csv, "w", encoding="utf-8") as f_excel:
                print("RSSI_Downlink;RSSI_Uplink;SNR_Downlink;SNR_Uplink;PSR_Acumulada;RSSI_Uplink_MA;SNR_Uplink_MA", file=f_excel)
                for i in range(len(psr)):
                    r_down = formatar_pt_br(rssi_down[i])
                    r_up = formatar_pt_br(rssi_up[i])
                    s_down = formatar_pt_br(snr_down[i])
                    s_up = formatar_pt_br(snr_up[i])
                    p_str = formatar_pt_br(psr[i])
                    r_up_ma_str = formatar_pt_br(rssi_up_ma[i])
                    s_up_ma_str = formatar_pt_br(snr_up_ma[i])
                    print(f"{r_down};{r_up};{s_down};{s_up};{p_str};{r_up_ma_str};{s_up_ma_str}", file=f_excel)
            sucesso_gravacao = True
        except PermissionError:
            tentativas -= 1
            time.sleep(0.05)

    print(f"--- [N5 ESTATÍSTICAS NÍVEL 5] ---")
    print(f"RSSI MM -> Média: {media_rssi_ma:.2f} | Máx: {max_rssi_ma:.2f} | Mín: {min_rssi_ma:.2f} | DesvPad: {desvio_rssi_ma:.2f}")
    print(f"SNR MM  -> Média: {media_snr_ma:.2f}  | Máx: {max_snr_ma:.2f}  | Mín: {min_snr_ma:.2f}  | DesvPad: {desvio_snr_ma:.2f}")
    print("-" * 50)

    time.sleep(1)


'''
    

'''
# Abstração | Gerência [RSSI, SNR e PSR] | N5 | WissTek-IoT | Framework LoRa
# ====== Nível 5 - Gerência ======
import time
import os
import math
from datetime import datetime

# Pasta do Nível 4 (4_N4_Armazenamento)
PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = f"{PASTA_N4}/Parametros"
PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"
ARQUIVO_PARAMETROS = f"{PASTA_PARAMETROS}/dados_processamento.txt"

# Garante que as pastas existem
if not os.path.exists(PASTA_PROCESSADOS):
    os.makedirs(PASTA_PROCESSADOS)
if not os.path.exists(PASTA_PARAMETROS):
    os.makedirs(PASTA_PARAMETROS)

def formatar_pt_br(valor):
    """Converte o ponto decimal em vírgula para o Excel em português e formata como string"""
    if valor == "" or valor is None:
        return ""
    return str(valor).replace('.', ',')

def ler_parametros():
    """Lê as janelas de média móvel para RSSI e SNR do arquivo dados_processamento.txt"""
    janela_rssi = 10
    janela_snr = 10
    if os.path.exists(ARQUIVO_PARAMETROS):
        try:
            with open(ARQUIVO_PARAMETROS, "r", encoding="utf-8") as f:
                linhas = f.readlines()
                for linha in linhas:
                    if "=" in linha:
                        chave, val = linha.strip().split("=")
                        chave = chave.strip().upper()
                        val = val.strip()
                        if chave == "JANELA_RSSI":
                            janela_rssi = max(1, int(val))
                        elif chave == "JANELA_SNR":
                            janela_snr = max(1, int(val))
        except Exception as e:
            print(f"[N5] Aviso ao ler parâmetros: {e}")
    return janela_rssi, janela_snr

def calcular_media_e_desvio(lista):
    """Calcula a média e o desvio padrão amostral de uma lista de valores numéricos"""
    valores = [v for v in lista if v != "" and v is not None]
    n = len(valores)
    if n == 0:
        return 0.0, 0.0
    media = sum(valores) / n
    if n < 2:
        desvio = 0.0
    else:
        variancia = sum((x - media) ** 2 for x in valores) / (n - 1)
        desvio = math.sqrt(variancia)
    return media, desvio

ultimo_arquivo_entrada = ""
arquivo_excel_csv = ""

while True:
    janela_rssi, janela_snr = ler_parametros()

    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    if os.path.exists(f"{PASTA_N4}/Dados_Brutos"):
        arquivos = os.listdir(f"{PASTA_N4}/Dados_Brutos")
        arquivos.sort()
        for nome in arquivos:
            if nome.endswith(".txt"):
                arquivo_entrada = f"{PASTA_N4}/Dados_Brutos/" + nome

    if not arquivo_entrada:
        print("Nenhum arquivo de dados brutos encontrado.")
        time.sleep(1)
        continue

    # Se detectou um NOVO arquivo de entrada, cria um novo arquivo CSV exclusivo
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
    
    # Listas para Média Móvel
    rssi_up_ma = []
    snr_up_ma = []

    total_pacotes = 0
    pacotes_recebidos = 0
    pacotes_perdidos_total = 0
    RSSI_DL, RSSI_UL, SNR_DL, SNR_UL, PSR = 0, 0, 0, 0, 0

    # Buffer de leituras válidas para a Janela Deslizante
    buffer_rssi_mw = []
    buffer_snr = []

    for i in range(1, len(linhas)):
        partes = linhas[i].split(",")
        total_pacotes += 1

        pacote_recebido = 0
        for j in range(10):
            if ((int(partes[23+j]) != 9) and ((int(partes[32]) == 1))):
                pacote_recebido = 1
            else:
                pacotes_perdidos_total += 1

        if pacote_recebido == 1:
            pacotes_recebidos += 1

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

            # --- Média Móvel de RSSI em mW ---
            rssi_mw = 10.0 ** (RSSI_UL / 10.0)
            buffer_rssi_mw.append(rssi_mw)
            if len(buffer_rssi_mw) > janela_rssi:
                buffer_rssi_mw.pop(0)
            
            media_mw = sum(buffer_rssi_mw) / len(buffer_rssi_mw)
            media_rssi_dbm = round(10.0 * math.log10(media_mw), 2)
            rssi_up_ma.append(media_rssi_dbm)

            # --- Média Móvel de SNR em dB ---
            buffer_snr.append(SNR_UL)
            if len(buffer_snr) > janela_snr:
                buffer_snr.pop(0)
            
            media_snr_db = round(sum(buffer_snr) / len(buffer_snr), 2)
            snr_up_ma.append(media_snr_db)

        else:
            rssi_down.append("")
            rssi_up.append("")
            snr_down.append("")
            snr_up.append("")
            # Mantém a última média móvel calculada se o pacote for perdido
            rssi_up_ma.append(rssi_up_ma[-1] if rssi_up_ma else "")
            snr_up_ma.append(snr_up_ma[-1] if snr_up_ma else "")

        PSR = round((pacotes_recebidos/total_pacotes)*100, 2)
        psr.append(PSR)

    # Cálculo da Média e Desvio Padrão das Média Móveis
    media_rssi_ma, desvio_rssi_ma = calcular_media_e_desvio(rssi_up_ma)
    media_snr_ma, desvio_snr_ma = calcular_media_e_desvio(snr_up_ma)

    # Grava/Atualiza os dados no CSV da rodada atual
    sucesso_gravacao = False
    tentativas = 5
    while not sucesso_gravacao and tentativas > 0:
        try:
            with open(arquivo_excel_csv, "w", encoding="utf-8") as f_excel:
                print("RSSI_Downlink;RSSI_Uplink;SNR_Downlink;SNR_Uplink;PSR_Acumulada;RSSI_Uplink_MA;SNR_Uplink_MA", file=f_excel)
                for i in range(len(psr)):
                    r_down = formatar_pt_br(rssi_down[i])
                    r_up = formatar_pt_br(rssi_up[i])
                    s_down = formatar_pt_br(snr_down[i])
                    s_up = formatar_pt_br(snr_up[i])
                    p_str = formatar_pt_br(psr[i])
                    r_up_ma_str = formatar_pt_br(rssi_up_ma[i])
                    s_up_ma_str = formatar_pt_br(snr_up_ma[i])
                    print(f"{r_down};{r_up};{s_down};{s_up};{p_str};{r_up_ma_str};{s_up_ma_str}", file=f_excel)
            sucesso_gravacao = True
        except PermissionError:
            tentativas -= 1
            time.sleep(0.05)

    # Exibição de Estatísticas em Formato de Texto
    print(f"--- [N5 ESTATÍSTICAS NÍVEL 5] ---")
    print(f"Arquivo = {arquivo_entrada} | CSV = {os.path.basename(arquivo_excel_csv)}")
    print(f"Pacotes Totais: {total_pacotes} | Recebidos: {pacotes_recebidos} | Perdidos: {pacotes_perdidos_total} | PSR: {PSR}%")
    print(f"Média Média Móvel RSSI UL: {media_rssi_ma:.2f} dBm | Desvio Padrão: {desvio_rssi_ma:.2f} dB")
    print(f"Média Média Móvel SNR UL: {media_snr_ma:.2f} dB | Desvio Padrão: {desvio_snr_ma:.2f} dB")
    print("-" * 50)

    time.sleep(1)
'''
