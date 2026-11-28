# Abstração | Gerência [RSSI, SNR e PSR] | N5 | WissTek-IoT | Framework LoRa
# ====== Nível 5 - Gerência ======
import time
import os
import math
from datetime import datetime

# Pastas e arquivos do Framework LoRa
PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = os.path.join(PASTA_N4, "Parametros")
PASTA_PROCESSADOS = os.path.join(PASTA_N4, "Dados_Processados")
PASTA_CACHE_TILES = os.path.join(PASTA_PARAMETROS, "cache_google_maps")
ARQUIVO_GW_GPS = os.path.join(PASTA_PARAMETROS, "GW_GPS.txt")
ARQUIVO_PARAMETROS = os.path.join(PASTA_PARAMETROS, "dados_processamento.txt")

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
                        chave, val = linha.strip().split("=", 1)
                        chave = chave.strip().upper()
                        val = val.strip()
                        if chave == "JANELA_RSSI":
                            janela_rssi = max(1, int(val))
                        elif chave == "JANELA_SNR":
                            janela_snr = max(1, int(val))
        except Exception as e:
            print(f"[N5] Aviso ao ler parâmetros: {e}")
    return janela_rssi, janela_snr


def ler_gw_gps():
    """Lê LATITUDE, LONGITUDE e ALTITUDE do Gateway a partir de GW_GPS.txt"""
    gw_lat = None
    gw_lon = None
    gw_alt = 0.0
    if os.path.exists(ARQUIVO_GW_GPS):
        try:
            with open(ARQUIVO_GW_GPS, "r", encoding="utf-8") as f:
                for linha in f:
                    if "=" in linha:
                        chave, val = linha.strip().split("=", 1)
                        chave = chave.strip().upper()
                        val = val.strip().replace(",", ".")
                        if chave == "LATITUDE":
                            gw_lat = float(val)
                        elif chave == "LONGITUDE":
                            gw_lon = float(val)
                        elif chave == "ALTITUDE":
                            gw_alt = float(val)
        except Exception as e:
            print(f"[N5] Aviso ao ler GW_GPS.txt: {e}")
    return gw_lat, gw_lon, gw_alt


def gps_valido(lat, lon, alt):
    """Verifica se as coordenadas GPS do nó sensor (Latitude, Longitude, Altitude) são válidas"""
    if lat == "" or lon == "" or alt == "" or lat is None or lon is None or alt is None:
        return False
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        alt_f = float(alt)
    except (ValueError, TypeError):
        return False

    if not (math.isfinite(lat_f) and math.isfinite(lon_f) and math.isfinite(alt_f)):
        return False
    if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
        return False
    if lat_f == 0.0 and lon_f == 0.0:
        return False
    if not (-500.0 <= alt_f <= 9000.0):
        return False
    return True


def calcula_distancia_enlace(gw_lat, gw_lon, gw_alt, lat, lon, alt):
    """Calcula a distância 3D em metros entre o nó sensor e o Gateway (Haversine + diferença de altitude)"""
    r_terra = 6371000.0
    phi1 = math.radians(gw_lat)
    phi2 = math.radians(lat)
    dphi = math.radians(lat - gw_lat)
    dlambda = math.radians(lon - gw_lon)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    dist_2d = r_terra * c

    dist_3d = math.sqrt(dist_2d ** 2 + (alt - gw_alt) ** 2)
    return round(dist_3d, 2)


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
    gw_lat, gw_lon, gw_alt = ler_gw_gps()

    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    pasta_brutos = os.path.join(PASTA_N4, "Dados_Brutos")
    if os.path.exists(pasta_brutos):
        arquivos = os.listdir(pasta_brutos)
        arquivos.sort()
        for nome in arquivos:
            if nome.endswith(".txt"):
                arquivo_entrada = os.path.join(pasta_brutos, nome)

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
        with open(arquivo_entrada, "r", encoding="utf-8", errors="ignore") as arquivo:
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
    latitude = []
    longitude = []
    altitude = []
    distancia_gw_col = []
    timestamp_col = []
    contador_col = []

    total_pacotes = 0
    pacotes_recebidos = 0
    pacotes_perdidos_total = 0
    RSSI_DL, RSSI_UL, SNR_DL, SNR_UL, PSR = 0, 0, 0, 0, 0

    buffer_rssi_mw = []
    buffer_snr = []

    for i in range(1, len(linhas)):
        if not linhas[i].strip():
            continue
        partes = linhas[i].strip().split(",")
        total_pacotes += 1

        ts_linha = partes[0].strip() if len(partes) > 0 else ""
        cnt_linha = partes[1].strip() if len(partes) > 1 else ""
        timestamp_col.append(ts_linha)
        contador_col.append(cnt_linha)

        pacote_recebido = 0
        try:
            for j in range(10):
                if ((int(partes[23 + j]) != 9) and ((int(partes[32]) == 1))):
                    pacote_recebido = 1
        except (IndexError, ValueError):
            pacote_recebido = 0

        if pacote_recebido == 1:
            pacotes_recebidos += 1

            UL_B0 = int(partes[22])
            if UL_B0 == 127:
                RSSI_DL = -10.5
            elif UL_B0 > 128:
                RSSI_DL = ((UL_B0 - 256) / 2.0) - 74
            else:
                RSSI_DL = (UL_B0 / 2.0) - 74

            UL_B1 = int(partes[23])
            SNR_DL = round(((UL_B1 / 4) - 30), 2)

            UL_B2 = int(partes[24])
            if UL_B2 == 127:
                RSSI_UL = -10.5
            elif UL_B2 > 128:
                RSSI_UL = ((UL_B2 - 256) / 2.0) - 74
            else:
                RSSI_UL = (UL_B2 / 2.0) - 74

            UL_B3 = int(partes[25])
            SNR_UL = round(((UL_B3 / 4) - 30), 2)

            rssi_down.append(RSSI_DL)
            rssi_up.append(RSSI_UL)
            snr_down.append(SNR_DL)
            snr_up.append(SNR_UL)

            lat_calc, lon_calc, alt_calc = "", "", ""
            dist_calc = ""

            try:
                lat_raw = ((int(partes[42]) << 24) | (int(partes[43]) << 16) | (int(partes[44]) << 8) | int(partes[45]))
                if lat_raw & 0x80000000:
                    lat_raw -= 0x100000000
                lat_calc = lat_raw / 1e6

                lon_raw = ((int(partes[46]) << 24) | (int(partes[47]) << 16) | (int(partes[48]) << 8) | int(partes[49]))
                if lon_raw & 0x80000000:
                    lon_raw -= 0x100000000
                lon_calc = lon_raw / 1e6

                alt_raw = ((int(partes[50]) << 8) | int(partes[51]))
                if alt_raw & 0x8000:
                    alt_raw -= 0x10000
                alt_calc = float(alt_raw)

                if gps_valido(lat_calc, lon_calc, alt_calc):
                    latitude.append(lat_calc)
                    longitude.append(lon_calc)
                    altitude.append(alt_calc)

                    if gw_lat is not None and gw_lon is not None:
                        dist_calc = calcula_distancia_enlace(
                            gw_lat, gw_lon, gw_alt, lat_calc, lon_calc, alt_calc
                        )
                    distancia_gw_col.append(dist_calc)
                else:
                    latitude.append("")
                    longitude.append("")
                    altitude.append("")
                    distancia_gw_col.append("")
            except (IndexError, ValueError):
                latitude.append("")
                longitude.append("")
                altitude.append("")
                distancia_gw_col.append("")

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
            latitude.append("")
            longitude.append("")
            altitude.append("")
            distancia_gw_col.append("")
            pacotes_perdidos_total += 1

        PSR = round((pacotes_recebidos / total_pacotes) * 100, 2)
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

    # Gravação do CSV principal de amostras
    sucesso_gravacao = False
    tentativas = 5
    while not sucesso_gravacao and tentativas > 0:
        try:
            with open(arquivo_excel_csv, "w", encoding="utf-8") as f_excel:
                cabecalho = (
                    "RSSI_Downlink;RSSI_Uplink;SNR_Downlink;SNR_Uplink;PSR_Acumulada;"
                    "RSSI_Uplink_MA;SNR_Uplink_MA;Pacotes_Perdidos;"
                    "RSSI_MA_Media;RSSI_MA_DesvPad;RSSI_MA_Max;RSSI_MA_Min;"
                    "SNR_MA_Media;SNR_MA_DesvPad;SNR_MA_Max;SNR_MA_Min;"
                    "LATITUDE;LONGITUDE;ALTITUDE;DISTANCIA_GW_M;TIMESTAMP;CONTADOR"
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

                    g_lat = formatar_pt_br(round(latitude[i], 6)) if latitude[i] != "" else ""
                    g_lon = formatar_pt_br(round(longitude[i], 6)) if longitude[i] != "" else ""
                    g_alt = formatar_pt_br(int(round(altitude[i], 0))) if altitude[i] != "" else ""
                    g_dist = formatar_pt_br(round(distancia_gw_col[i], 2)) if distancia_gw_col[i] != "" else ""
                    ts_str = timestamp_col[i]
                    cnt_str = contador_col[i]

                    linha = (
                        f"{r_down};{r_up};{s_down};{s_up};{p_str};"
                        f"{r_up_ma_str};{s_up_ma_str};{p_perdidos};"
                        f"{r_media};{r_desv};{r_max};{r_min};"
                        f"{s_media};{s_desv};{s_max};{s_min};"
                        f"{g_lat};{g_lon};{g_alt};{g_dist};{ts_str};{cnt_str}"
                    )
                    print(linha, file=f_excel)
            sucesso_gravacao = True
        except PermissionError:
            tentativas -= 1
            time.sleep(0.05)

    print(f"--- [N5 ATUALIZADO] CSV Atualizado com Pacotes Perdidos reais: {os.path.basename(arquivo_excel_csv)} ---")
    time.sleep(1)
