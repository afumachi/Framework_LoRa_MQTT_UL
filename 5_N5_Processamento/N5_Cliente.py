# Abstração | Cliente [Luminosidade e LED] | N5 | WissTek-IoT | Framework DL-UL
# 13/10/2026
#====== Nível 5 - Cliente ======
# Extrai a luminosidade, calcula a média, aplica histerese e atualiza APLICACAO.txt e .tmp
import time
import os

# Caminho para salvamento dos parâmetros
PASTA_N4 = os.path.join("..", "4_N4_Armazenamento")
CAMINHO_PARAMETROS = os.path.join(PASTA_N4, "Parametros")

# Arquivos utilizados pelo nível 5 do cliente
arquivo_luminosidade = f"{PASTA_N4}/Dados_Processados/luminosidade.tmp"
arquivo_media = f"{PASTA_N4}/Dados_Processados/media_luminosidade.tmp"
caminho_cliente = os.path.join(CAMINHO_PARAMETROS, "parametros_cliente.txt")
caminho_aplicacao = os.path.join(CAMINHO_PARAMETROS, "cmd_led_amarelo.txt")

# Garante que a pasta de Dados_Processados existe
if not os.path.exists(f"{PASTA_N4}/Dados_Processados"):
    os.mkdir(f"{PASTA_N4}/Dados_Processados")

# Estado inicial do LED (0 = apagado)
estado_led_atual = 0

def ler_limiares():
    limiar_ligar = 2000 # Valor padrão caso não exista arquivo
    try:
        if os.path.exists(caminho_cliente):
            with open(caminho_cliente, "r") as f:
                limiar_ligar = int(float(f.readline().strip().replace(",", ".")))
    except:
        pass
    limiar_desligar = min(4095, limiar_ligar + 200)
    return limiar_ligar, limiar_desligar

while True:
    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    arquivos = os.listdir(f"{PASTA_N4}/Dados_Brutos")
    arquivos.sort()
    for nome in arquivos:
        if nome.endswith(".txt"):
            arquivo_entrada = f"{PASTA_N4}/Dados_Brutos/" + nome

    # Aguarda o N3 criar o arquivo de dados brutos
    if arquivo_entrada == "":
        time.sleep(1)
        continue

    # Abre o arquivo de dados brutos
    arquivo = open(arquivo_entrada,"r")
    linhas = arquivo.readlines()
    arquivo.close()

    # Listas que guardam os valores extraídos
    luminosidades = []
    estados_led = []

    # Começa em 1 para pular o cabeçalho do arquivo
    for i in range(1, len(linhas)):
        try:
            partes = linhas[i].split(",")

            # Pacote perdido: o N3 grava todos os bytes do UL com valor 9
            pacote_recebido = 0
            for j in range(20):
                if int(partes[22+j]) != 9:
                    pacote_recebido = 1
            if pacote_recebido == 0:
                continue

            # Luminosidade nos bytes UL_B18 (posição 40) e UL_B19 (posição 41)
            UL_B18 = int(partes[40])
            UL_B19 = int(partes[41])
            luminosidade = (UL_B18*256 + UL_B19)

            luminosidades.append(float(luminosidade))
            estados_led.append(0) # Placeholder inicial
        except (IndexError, ValueError):
            continue

    # Se ainda não há pacotes válidos (rodada nova), limpa os arquivos
    if len(luminosidades) == 0:
        open(arquivo_luminosidade,"w").close()
        open(arquivo_media,"w").close()
        time.sleep(1)
        continue

    # Lê os limiares atuais (com histerese de +200)
    limiar_ligar, limiar_desligar = ler_limiares()

    # Calcula a média acumulada e define o estado do LED por histerese
    soma = 0.0
    medias_calculadas = []
    
    for i in range(len(luminosidades)):
        soma = soma + luminosidades[i]
        media = soma / (i + 1)
        medias_calculadas.append(media)

        # Lógica de Histerese:
        # Se média < limiar_ligar -> Liga LED (1)
        # Se média > limiar_desligar -> Desliga LED (0)
        if media < limiar_ligar:
            estado_led_atual = 1
        elif media > limiar_desligar:
            estado_led_atual = 0
            
        estados_led[i] = estado_led_atual

    # Grava a luminosidade e o estado do LED corrigido em arquivo temporário
    f_lum = open(arquivo_luminosidade,"w")
    for i in range(len(luminosidades)):
        print(luminosidades[i], estados_led[i], file=f_lum)
    f_lum.close()

    # Grava a média da luminosidade
    f_media = open(arquivo_media,"w")
    for i in range(len(medias_calculadas)):
        print(medias_calculadas[i], file=f_media)
    f_media.close()

    # Escreve o comando final no arquivo APLICACAO.txt para consumo do gateway/downlink
    try:
        with open(caminho_aplicacao, "w") as f_app:
            f_app.write(str(estado_led_atual) + "\n")
    except Exception as e:
        print(f"[Erro] Não foi possível gravar em APLICACAO.txt: {e}")

    print(f"Arquivo = {arquivo_entrada} | Média = {round(medias_calculadas[-1],2)} | Limiar Ligar = {limiar_ligar} | Limiar Desligar = {limiar_desligar} | LED APLICACAO = {estado_led_atual}")
    time.sleep(1)

'''
# Abstração | Cliente [Luminosidade e LED] | N5 | WissTek-IoT | Framework DL-UL
# 13/10/2026
#====== Nível 5 - Cliente ======
# Extrai a luminosidade e o estado do LED dos dados brutos e calcula a média
import time
import os

# Caminho para salvamento dos parâmetros
PASTA_N4 = os.path.join("..", "4_N4_Armazenamento")
CAMINHO_PARAMETROS = os.path.join(PASTA_N4, "Parametros")

# Arquivos utilizados pelo nível 5 do cliente
arquivo_luminosidade = f"{PASTA_N4}/Dados_Processados/luminosidade.tmp"
arquivo_media = f"{PASTA_N4}/Dados_Processados/media_luminosidade.tmp"

# Garante que a pasta de Dados_Processados existe
if not os.path.exists(f"{PASTA_N4}/Dados_Processados"):
    os.mkdir(f"{PASTA_N4}/Dados_Processados")

while True:

    # Procura o último arquivo de dados brutos gravado no nível 4
    arquivo_entrada = ""
    arquivos = os.listdir(f"{PASTA_N4}/Dados_Brutos")
    arquivos.sort()
    for nome in arquivos:
        if nome.endswith(".txt"):
            arquivo_entrada = f"{PASTA_N4}/Dados_Brutos/" + nome

    # Aguarda o N3 criar o arquivo de dados brutos
    if arquivo_entrada == "":
        time.sleep(1)
        continue

    # Abre o arquivo de dados brutos
    arquivo = open(arquivo_entrada,"r")
    linhas = arquivo.readlines()
    arquivo.close()

    # Listas que guardam os valores extraídos
    luminosidades = []
    estados_led = []

    # Começa em 1 para pular o cabeçalho do arquivo
    for i in range(1,len(linhas)):
        # Linha incompleta (N3 ainda escrevendo) ou corrompida é descartada
        try:
            partes = linhas[i].split(",")

            # Pacote perdido: o N3 grava todos os bytes do UL com valor 9
            pacote_recebido = 0
            for j in range(20):
                if int(partes[22+j]) != 9:
                    pacote_recebido = 1
            if pacote_recebido == 0:
                continue

            # Estado do LED amarelo no byte UL_B16 (posição 38)
            UL_B16 = int(partes[38])

            # Luminosidade nos bytes UL_B18 (posição 40) e UL_B19 (posição 41)
            UL_B18 = int(partes[40])
            UL_B19 = int(partes[41])
            luminosidade = (UL_B18*256 + UL_B19)

            luminosidades.append(float(luminosidade))
            estados_led.append(UL_B16)
        except (IndexError, ValueError):
            continue

    # Se ainda não há pacotes válidos (rodada nova), limpa os arquivos para o N6 limpar o gráfico
    if len(luminosidades) == 0:
        open(arquivo_luminosidade,"w").close()
        open(arquivo_media,"w").close()
        time.sleep(1)
        continue

    # Grava a luminosidade e o estado do LED em arquivo temporário
    f_lum = open(arquivo_luminosidade,"w")
    for i in range(len(luminosidades)):
        print(luminosidades[i],estados_led[i],file=f_lum)
    f_lum.close()

    # Calcula a média acumulada da luminosidade
    soma = 0.0
    f_media = open(arquivo_media,"w")
    for i in range(len(luminosidades)):
        soma = soma + luminosidades[i]
        media = soma / (i + 1)
        print(media,file=f_media)
    f_media.close()

    print("Arquivo = ",arquivo_entrada," | Luminosidade = ",luminosidades[-1]," | LED = ",estados_led[-1]," | Amostras = ",len(luminosidades)," | Média = ",round(media,2))
    time.sleep(1)
'''
