# Exibição | Gerência [RSSI, SNR e PSR] | N6 | WissTek-IoT | Framework LoRa
# ====== Nível 6 - Gerência ======
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.style as style
import os
import glob
import math

style.use("ggplot")

MAX_PONTOS = 10000
cor_rssi_up = "#FF3300"
cor_rssi_ma = "#1f77b4"
cor_snr_up = "#FF3300"
cor_snr_ma = "#1f77b4"
cor_psr = "#2ca02c"

PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = f"{PASTA_N4}/Parametros"
PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"
ARQUIVO_PARAMETROS = f"{PASTA_PARAMETROS}/dados_processamento.txt"

if not os.path.exists(PASTA_N4):
    os.mkdir(PASTA_N4)
if not os.path.exists(PASTA_PARAMETROS):
    os.mkdir(PASTA_PARAMETROS)

arquivo_csv_atual_ref = {"caminho": None}


def salvar_parametros_n5():
    try:
        j_rssi = str(int(entry_janela_rssi.get()))
        j_snr = str(int(entry_janela_snr.get()))
        with open(ARQUIVO_PARAMETROS, "w", encoding="utf-8") as f:
            f.write(f"JANELA_RSSI={j_rssi}\n")
            f.write(f"JANELA_SNR={j_snr}\n")
    except ValueError:
        pass


def _parse_float_ou_nan(texto):
    if texto is None:
        return math.nan
    limpo = str(texto).strip().replace(",", ".")
    if limpo == "":
        return math.nan
    try:
        val = float(limpo)
        return val if math.isfinite(val) else math.nan
    except ValueError:
        return math.nan


def _valores_validos(serie):
    return [x for x in serie if x is not None and not math.isnan(x)]


def calcular_estatisticas_completas(lista):
    valores = _valores_validos(lista)
    n = len(valores)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    media = sum(valores) / n
    maximo = max(valores)
    minimo = min(valores)
    if n < 2:
        desvio = 0.0
    else:
        var = sum((x - media) ** 2 for x in valores) / (n - 1)
        desvio = math.sqrt(var)
    return media, desvio, maximo, minimo


def _alinhar_comprimentos(series, alvo_len):
    """Garante que todas as séries tenham exatamente alvo_len elementos, alinhando pelo fim."""
    alinhadas = []
    for s in series:
        if len(s) > alvo_len:
            alinhadas.append(s[-alvo_len:])
        elif len(s) < alvo_len:
            alinhadas.append([math.nan] * (alvo_len - len(s)) + list(s))
        else:
            alinhadas.append(list(s))
    return alinhadas


def atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz):
    rssi_up, rssi_ma = [], []
    snr_up, snr_ma = [], []
    psr = []
    pacotes_perdidos_lista = []

    salvar_parametros_n5()

    padrao_busca = os.path.join(PASTA_PROCESSADOS, "Rodada_Gerencia_*.csv")
    arquivos_csv = glob.glob(padrao_busca)

    if arquivos_csv:
        arquivos_csv.sort(key=os.path.getmtime)
        ultimo_csv = arquivos_csv[-1]

        if ultimo_csv != arquivo_csv_atual_ref["caminho"]:
            arquivo_csv_atual_ref["caminho"] = ultimo_csv

        try:
            with open(arquivo_csv_atual_ref["caminho"], "r", encoding="utf-8") as f:
                linhas = f.readlines()
                for linha in linhas[1:]:
                    linha = linha.strip()
                    if not linha:
                        continue
                    try:
                        partes = linha.split(";")
                        r_up_val = _parse_float_ou_nan(partes[1]) if len(partes) > 1 else math.nan
                        s_up_val = _parse_float_ou_nan(partes[3]) if len(partes) > 3 else math.nan
                        p_val = _parse_float_ou_nan(partes[4]) if len(partes) > 4 else math.nan
                        r_ma_val = _parse_float_ou_nan(partes[5]) if len(partes) > 5 else math.nan
                        s_ma_val = _parse_float_ou_nan(partes[6]) if len(partes) > 6 else math.nan
                        p_perd_val = _parse_float_ou_nan(partes[7]) if len(partes) > 7 else math.nan

                        rssi_up.append(r_up_val)
                        snr_up.append(s_up_val)
                        psr.append(p_val)
                        rssi_ma.append(r_ma_val)
                        snr_ma.append(s_ma_val)
                        if not math.isnan(p_perd_val):
                            pacotes_perdidos_lista.append(int(p_perd_val))
                    except Exception:
                        pass
        except (PermissionError, FileNotFoundError):
            pass

    # Nivelar comprimentos antes de aplicar a janela deslizante MAX_PONTOS
    max_len_bruto = max(
        len(rssi_up), len(rssi_ma), len(snr_up), len(snr_ma), len(psr), 0
    )
    alvo_len = min(max_len_bruto, MAX_PONTOS)
    rssi_up, rssi_ma, snr_up, snr_ma, psr = _alinhar_comprimentos(
        [rssi_up, rssi_ma, snr_up, snr_ma, psr], alvo_len
    )

    # Vetor de índices X comum a todas as séries e gráficos
    x_idx = list(range(alvo_len))
    x_lim = (0, max(alvo_len - 1, 1)) if alvo_len > 0 else (0, 1)

    # --- Atualizar Labels e Textos Estatísticos ---
    rssi_up_validos = _valores_validos(rssi_up)
    snr_up_validos = _valores_validos(snr_up)
    psr_validos = _valores_validos(psr)

    if rssi_up_validos:
        label_up.config(text=f"RSSI UL: {round(rssi_up_validos[-1], 2)} dBm")
    else:
        label_up.config(text="RSSI UL: --")

    if snr_up_validos:
        label_snr_up.config(text=f"SNR UL: {round(snr_up_validos[-1], 2)} dB")
    else:
        label_snr_up.config(text="SNR UL: --")

    if psr_validos:
        label_psr.config(text=f"PSR atual: {round(psr_validos[-1], 2)} %")
    else:
        label_psr.config(text="PSR atual: --")

    if pacotes_perdidos_lista:
        label_perdidos.config(text=f"Pacotes Perdidos: {pacotes_perdidos_lista[-1]}")
    else:
        label_perdidos.config(text="Pacotes Perdidos: --")

    med_r, desv_r, max_r, min_r = calcular_estatisticas_completas(rssi_ma)
    med_s, desv_s, max_s, min_s = calcular_estatisticas_completas(snr_ma)

    label_estat_rssi.config(
        text=f"Média: {med_r:.2f} dBm    |    Máx: {max_r:.2f} dBm    |    Mín: {min_r:.2f} dBm    |    Desvio Padrão: {desv_r:.2f} dB"
    )
    label_estat_snr.config(
        text=f"Média: {med_s:.2f} dB    |    Máx: {max_s:.2f} dB    |    Mín: {min_s:.2f} dB    |    Desvio Padrão: {desv_s:.2f} dB"
    )

    # --- GRÁFICO 1: RSSI ---
    ax1.clear()
    ax1.margins(x=0)
    rssi_ma_validos = _valores_validos(rssi_ma)

    if rssi_up_validos:
        ax1.plot(x_idx, rssi_up, label="RSSI Bruto (dBm)", linewidth=1.2, alpha=0.5, color=cor_rssi_up)
    if rssi_ma_validos:
        ax1.plot(x_idx, rssi_ma, label="Média Móvel (dB)", linewidth=1.2, color=cor_rssi_ma)
    if rssi_up_validos or rssi_ma_validos:
        ax1.legend(loc="upper right", fontsize=7)
        todos_rssi = rssi_up_validos + rssi_ma_validos
        val_min, val_max = min(todos_rssi), max(todos_rssi)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax1.set_ylim(val_min - margem, val_max + margem)

    ax1.set_xlim(*x_lim)
    ax1.set_title("RSSI LoRa (Uplink)", fontsize=9, pad=2)
    ax1.set_ylabel("RSSI (dBm)", fontsize=7)
    ax1.tick_params(labelsize=6)

    # --- GRÁFICO 2: SNR ---
    ax2.clear()
    ax2.margins(x=0)
    snr_ma_validos = _valores_validos(snr_ma)

    if snr_up_validos:
        ax2.plot(x_idx, snr_up, label="SNR Bruto (dB)", linewidth=1.2, alpha=0.5, color=cor_snr_up)
    if snr_ma_validos:
        ax2.plot(x_idx, snr_ma, label="Média Móvel (dB)", linewidth=1.2, color=cor_snr_ma)
    if snr_up_validos or snr_ma_validos:
        ax2.legend(loc="upper right", fontsize=7)
        todos_snr = snr_up_validos + snr_ma_validos
        val_min, val_max = min(todos_snr), max(todos_snr)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax2.set_ylim(val_min - margem, val_max + margem)

    ax2.set_xlim(*x_lim)
    ax2.set_title("SNR LoRa (Uplink)", fontsize=9, pad=2)
    ax2.set_ylabel("SNR (dB)", fontsize=7)
    ax2.tick_params(labelsize=6)

    # --- GRÁFICO 3: PSR + LIMIAR ---
    ax3.clear()
    ax3.margins(x=0)

    try:
        limiar_val = float(entry_limiar_psr.get().replace(",", "."))
    except ValueError:
        limiar_val = 95.0

    if psr_validos:
        ax3.plot(x_idx, psr, label="PSR (%)", linewidth=1.8, color=cor_psr)
        ax3.axhline(y=limiar_val, color="red", linestyle="--", linewidth=1.0, label=f"Limiar ({limiar_val}%)")
        ax3.legend(loc="lower right", fontsize=7)
        val_min, val_max = min(psr_validos), max(psr_validos)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax3.set_ylim(max(0, val_min - margem), min(105, val_max + margem))

    ax3.set_xlim(*x_lim)
    ax3.set_title("Packet Success Rate - PSR", fontsize=9, pad=2)
    ax3.set_ylabel("PSR (%)", fontsize=7)
    ax3.set_xlabel("Amostras", fontsize=7)
    ax3.tick_params(labelsize=6)

    canvas1.draw()
    canvas2.draw()
    canvas3.draw()
    raiz.after(1000, atualizar_grafico, ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz)


# ===================== INTERFACE TKINTER =====================
raiz = tk.Tk()
raiz.title("FEE247 - NÍVEL 6 - GERÊNCIA & CONFIGURAÇÃO")
raiz.geometry("1350x780")
raiz.minsize(1150, 700)

# Painel Topo: RSSI & Máx/Mín/Média/DesvPad
frame_topo = tk.Frame(raiz)
frame_topo.pack(fill="x", padx=10, pady=2)

label_up = tk.Label(frame_topo, text="RSSI UL: --", font=("Arial", 8, "bold"), bg=cor_rssi_up, fg="white", width=18)
label_up.pack(side="left", padx=2)

label_estat_rssi = tk.Label(frame_topo, text="MM Média: -- | Máx: -- | Mín: -- | DesvPad: --", font=("Arial", 8), fg="#333333")
label_estat_rssi.pack(side="left", padx=10)

tk.Label(frame_topo, text="Janela RSSI:", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_janela_rssi = tk.Entry(frame_topo, width=5, font=("Arial", 8))
entry_janela_rssi.insert(0, "10")
entry_janela_rssi.pack(side="left")


def salvar(fig1, fig2, fig3):
    arquivo = filedialog.asksaveasfilename(defaultextension=".png")
    if arquivo:
        fig1.savefig(arquivo.replace(".png", "_rssi.png"))
        fig2.savefig(arquivo.replace(".png", "_snr.png"))
        fig3.savefig(arquivo.replace(".png", "_psr.png"))
        messagebox.showinfo("Sucesso", "Gráficos salvos com sucesso!")


btn_salvar = tk.Button(frame_topo, text="Salvar Gráficos", font=("Arial", 8, "bold"), command=lambda: salvar(fig1, fig2, fig3))
btn_salvar.pack(side="right", padx=2)

# --- GRÁFICO RSSI ---
frame_rssi = tk.Frame(raiz)
frame_rssi.pack(fill="both", expand=True, padx=10, pady=1)

fig1 = Figure(figsize=(10, 2.0), dpi=100)
ax1 = fig1.add_subplot(111)
fig1.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas1 = FigureCanvasTkAgg(fig1, master=frame_rssi)
canvas1.get_tk_widget().pack(fill="both", expand=True)

# Painel SNR & Máx/Mín/Média/DesvPad
frame_labels_snr = tk.Frame(raiz)
frame_labels_snr.pack(fill="x", padx=10, pady=2)

label_snr_up = tk.Label(frame_labels_snr, text="SNR UL: --", font=("Arial", 8, "bold"), bg=cor_snr_up, fg="white", width=18)
label_snr_up.pack(side="left", padx=2)

label_estat_snr = tk.Label(frame_labels_snr, text="MM Média: -- | Máx: -- | Mín: -- | DesvPad: --", font=("Arial", 8), fg="#333333")
label_estat_snr.pack(side="left", padx=10)

tk.Label(frame_labels_snr, text="Janela SNR:", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_janela_snr = tk.Entry(frame_labels_snr, width=5, font=("Arial", 8))
entry_janela_snr.insert(0, "10")
entry_janela_snr.pack(side="left")

# --- GRÁFICO SNR ---
frame_snr = tk.Frame(raiz)
frame_snr.pack(fill="both", expand=True, padx=10, pady=1)

fig2 = Figure(figsize=(10, 2.0), dpi=100)
ax2 = fig2.add_subplot(111)
fig2.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas2 = FigureCanvasTkAgg(fig2, master=frame_snr)
canvas2.get_tk_widget().pack(fill="both", expand=True)

# Painel PSR & Limiar
frame_label_psr = tk.Frame(raiz)
frame_label_psr.pack(fill="x", padx=10, pady=2)

label_psr = tk.Label(frame_label_psr, text="PSR atual: --", font=("Arial", 8, "bold"), bg=cor_psr, fg="white", width=18)
label_psr.pack(side="left", padx=2)

label_perdidos = tk.Label(frame_label_psr, text="Pacotes Perdidos: --", font=("Arial", 8, "bold"), fg="#d62728")
label_perdidos.pack(side="left", padx=15)

tk.Label(frame_label_psr, text="Limiar PSR (%):", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_limiar_psr = tk.Entry(frame_label_psr, width=6, font=("Arial", 8))
entry_limiar_psr.insert(0, "95")
entry_limiar_psr.pack(side="left")

# --- GRÁFICO PSR ---
frame_psr = tk.Frame(raiz)
frame_psr.pack(fill="both", expand=True, padx=10, pady=1)

fig3 = Figure(figsize=(10, 2.0), dpi=100)
ax3 = fig3.add_subplot(111)
fig3.subplots_adjust(left=0.05, right=0.98, top=0.84, bottom=0.20)
canvas3 = FigureCanvasTkAgg(fig3, master=frame_psr)
canvas3.get_tk_widget().pack(fill="both", expand=True)

atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz)


def fechar_janela():
    if messagebox.askokcancel("Sair", "Deseja fechar o monitor de gerência?"):
        raiz.destroy()


raiz.protocol("WM_DELETE_WINDOW", fechar_janela)
raiz.mainloop()

'''
# Exibição | Gerência [RSSI, SNR e PSR] | N6 | WissTek-IoT | Framework LoRa
# ====== Nível 6 - Gerência ======
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.style as style
import os
import glob
import math

style.use("ggplot")

MAX_PONTOS = 10000
cor_rssi_up = "#FF3300"#"#FF4500"
cor_rssi_ma = "#1f77b4"
cor_snr_up = "#FF3300"
cor_snr_ma = "#1f77b4"
cor_psr = "#2ca02c"

PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = f"{PASTA_N4}/Parametros"
PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"
ARQUIVO_PARAMETROS = f"{PASTA_PARAMETROS}/dados_processamento.txt"

if not os.path.exists(PASTA_N4):
    os.mkdir(PASTA_N4)
if not os.path.exists(PASTA_PARAMETROS):
    os.mkdir(PASTA_PARAMETROS)

arquivo_csv_atual_ref = {"caminho": None}

def salvar_parametros_n5():
    try:
        j_rssi = str(int(entry_janela_rssi.get()))
        j_snr = str(int(entry_janela_snr.get()))
        with open(ARQUIVO_PARAMETROS, "w", encoding="utf-8") as f:
            f.write(f"JANELA_RSSI={j_rssi}\n")
            f.write(f"JANELA_SNR={j_snr}\n")
    except ValueError:
        pass

def calcular_estatisticas_completas(lista):
    valores = [x for x in lista if x != "" and x is not None]
    n = len(valores)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    media = sum(valores) / n
    maximo = max(valores)
    minimo = min(valores)
    if n < 2:
        desvio = 0.0
    else:
        var = sum((x - media) ** 2 for x in valores) / (n - 1)
        desvio = math.sqrt(var)
    return media, desvio, maximo, minimo

def atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz):
    rssi_up, rssi_ma = [], []
    snr_up, snr_ma = [], []   
    psr = []
    pacotes_perdidos_lista = []

    salvar_parametros_n5()

    padrao_busca = os.path.join(PASTA_PROCESSADOS, "Rodada_Gerencia_*.csv")
    arquivos_csv = glob.glob(padrao_busca)
    
    if arquivos_csv:
        arquivos_csv.sort(key=os.path.getmtime)
        ultimo_csv = arquivos_csv[-1]
        
        if ultimo_csv != arquivo_csv_atual_ref["caminho"]:
            arquivo_csv_atual_ref["caminho"] = ultimo_csv

        try:
            with open(arquivo_csv_atual_ref["caminho"], 'r', encoding='utf-8') as f:
                linhas = f.readlines()
                for linha in linhas[1:]:
                    linha = linha.strip()
                    if linha:
                        try:
                            partes = linha.split(";")
                            r_up = partes[1].replace(",", ".") if partes[1] != "" else ""
                            s_up = partes[3].replace(",", ".") if partes[3] != "" else ""
                            p_val = partes[4].replace(",", ".") if partes[4] != "" else ""
                            r_ma = partes[5].replace(",", ".") if (len(partes) > 5 and partes[5] != "") else ""
                            s_ma = partes[6].replace(",", ".") if (len(partes) > 6 and partes[6] != "") else ""
                            p_perd = partes[7].replace(",", ".") if (len(partes) > 7 and partes[7] != "") else ""

                            rssi_up.append(float(r_up) if r_up != "" else "")
                            snr_up.append(float(s_up) if s_up != "" else "")
                            psr.append(float(p_val) if p_val != "" else "")
                            rssi_ma.append(float(r_ma) if r_ma != "" else "")
                            snr_ma.append(float(s_ma) if s_ma != "" else "")
                            pacotes_perdidos_lista.append(int(float(p_perd)) if p_perd != "" else 0)
                        except Exception:
                            pass
        except (PermissionError, FileNotFoundError):
            pass

    # Aplicar janela deslizante visual nos gráficos
    rssi_up = rssi_up[-MAX_PONTOS:]
    rssi_ma = rssi_ma[-MAX_PONTOS:]
    snr_up = snr_up[-MAX_PONTOS:]    
    snr_ma = snr_ma[-MAX_PONTOS:]
    psr = psr[-MAX_PONTOS:]

    # --- Atualizar Labels e Textos Estatísticos ---
    if rssi_up and rssi_up[-1] != "":
        label_up.config(text=f"RSSI UL: {round(rssi_up[-1], 2)} dBm")
    else:
        label_up.config(text="RSSI UL: --")

    if snr_up and snr_up[-1] != "":
        label_snr_up.config(text=f"SNR UL: {round(snr_up[-1], 2)} dB")
    else:
        label_snr_up.config(text="SNR UL: --")

    if psr and psr[-1] != "":
        label_psr.config(text=f"PSR atual: {round(psr[-1], 2)} %")
    else:
        label_psr.config(text="PSR atual: --")

    # Exibe o valor exato lido da coluna de pacotes perdidos acumulados
    if pacotes_perdidos_lista:
        label_perdidos.config(text=f"Pacotes Perdidos: {pacotes_perdidos_lista[-1]}")
    else:
        label_perdidos.config(text="Pacotes Perdidos: --")

    # Estatísticas (Média, Desvio Padrão, Máximo e Mínimo)
    med_r, desv_r, max_r, min_r = calcular_estatisticas_completas(rssi_ma)
    med_s, desv_s, max_s, min_s = calcular_estatisticas_completas(snr_ma)
    
    label_estat_rssi.config(text=f"Média: {med_r:.2f} dBm    |    Máx: {max_r:.2f} dBm    |    Mín: {min_r:.2f} dBm    |    Desvio Padrão: {desv_r:.2f} dB")
    label_estat_snr.config(text=f"Média: {med_s:.2f} dB    |    Máx: {max_s:.2f} dB    |    Mín: {min_s:.2f} dB    |    Desvio Padrão: {desv_s:.2f} dB")

    # --- GRÁFICO 1: RSSI ---
    ax1.clear()
    r_plot = [x for x in rssi_up if x != ""]
    rma_plot = [x for x in rssi_ma if x != ""]
    if r_plot:
        ax1.plot(r_plot, label="RSSI Bruto (dBm)", linewidth=1.2, alpha=0.5, color=cor_rssi_up)
        if rma_plot:
            ax1.plot(rma_plot, label="Média Móvel (dB)", linewidth=1.2, color=cor_rssi_ma)
        ax1.legend(loc='upper right', fontsize=7)
        val_min, val_max = min(r_plot), max(r_plot)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax1.set_ylim(val_min - margem, val_max + margem)

    ax1.set_title("RSSI LoRa (Uplink)", fontsize=9, pad=2)
    ax1.set_ylabel("RSSI (dBm)", fontsize=7)
    ax1.tick_params(labelsize=6)

    # --- GRÁFICO 2: SNR ---
    ax2.clear()
    s_plot = [x for x in snr_up if x != ""]
    sma_plot = [x for x in snr_ma if x != ""]
    if s_plot:
        ax2.plot(s_plot, label="SNR Bruto (dB)", linewidth=1.2, alpha=0.5, color=cor_snr_up)
        if sma_plot:
            ax2.plot(sma_plot, label="Média Móvel (dB)", linewidth=1.2, color=cor_snr_ma)
        ax2.legend(loc='upper right', fontsize=7)
        val_min, val_max = min(s_plot), max(s_plot)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax2.set_ylim(val_min - margem, val_max + margem)

    ax2.set_title("SNR LoRa (Uplink)", fontsize=9, pad=2)
    ax2.set_ylabel("SNR (dB)", fontsize=7)
    ax2.tick_params(labelsize=6)

    # --- GRÁFICO 3: PSR + LIMIAR ---
    ax3.clear()
    psr_plot = [x for x in psr if x != ""]
    
    try:
        limiar_val = float(entry_limiar_psr.get().replace(",", "."))
    except ValueError:
        limiar_val = 95.0

    if psr_plot:
        ax3.plot(psr_plot, label="PSR (%)", linewidth=1.8, color=cor_psr)
        ax3.axhline(y=limiar_val, color='red', linestyle='--', linewidth=1.0, label=f"Limiar ({limiar_val}%)")
        ax3.legend(loc='lower right', fontsize=7)
        val_min, val_max = min(psr_plot), max(psr_plot)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax3.set_ylim(max(0, val_min - margem), min(105, val_max + margem))

    ax3.set_title("Packet Success Rate - PSR", fontsize=9, pad=2)
    ax3.set_ylabel("PSR (%)", fontsize=7)
    ax3.set_xlabel("Amostras", fontsize=7)
    ax3.tick_params(labelsize=6)

    canvas1.draw()
    canvas2.draw()
    canvas3.draw()
    raiz.after(1000, atualizar_grafico, ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz)

# ===================== INTERFACE TKINTER =====================
raiz = tk.Tk()
raiz.title("FEE247 - NÍVEL 6 - GERÊNCIA & CONFIGURAÇÃO")
raiz.geometry("1350x780")
raiz.minsize(1150, 700)

# Painel Topo: RSSI & Máx/Mín/Média/DesvPad
frame_topo = tk.Frame(raiz)
frame_topo.pack(fill="x", padx=10, pady=2)

label_up = tk.Label(frame_topo, text="RSSI UL: --", font=("Arial", 8, "bold"), bg=cor_rssi_up, fg="white", width=18)
label_up.pack(side="left", padx=2)

label_estat_rssi = tk.Label(frame_topo, text="MM Média: -- | Máx: -- | Mín: -- | DesvPad: --", font=("Arial", 8), fg="#333333")
label_estat_rssi.pack(side="left", padx=10)

tk.Label(frame_topo, text="Janela RSSI:", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_janela_rssi = tk.Entry(frame_topo, width=5, font=("Arial", 8))
entry_janela_rssi.insert(0, "10")
entry_janela_rssi.pack(side="left")

btn_salvar = tk.Button(frame_topo, text="Salvar Gráficos", font=("Arial", 8, "bold"), command=lambda: salvar(fig1, fig2, fig3))
btn_salvar.pack(side="right", padx=2)

def salvar(fig1, fig2, fig3):
    arquivo = filedialog.asksaveasfilename(defaultextension=".png")
    if arquivo:
        fig1.savefig(arquivo.replace(".png", "_rssi.png"))
        fig2.savefig(arquivo.replace(".png", "_snr.png"))
        fig3.savefig(arquivo.replace(".png", "_psr.png"))
        messagebox.showinfo("Sucesso", "Gráficos salvos com sucesso!")

# --- GRÁFICO RSSI ---
frame_rssi = tk.Frame(raiz)
frame_rssi.pack(fill="both", expand=True, padx=10, pady=1)

fig1 = Figure(figsize=(10, 2.0), dpi=100)
ax1 = fig1.add_subplot(111)
fig1.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas1 = FigureCanvasTkAgg(fig1, master=frame_rssi)
canvas1.get_tk_widget().pack(fill="both", expand=True)

# Painel SNR & Máx/Mín/Média/DesvPad
frame_labels_snr = tk.Frame(raiz)
frame_labels_snr.pack(fill="x", padx=10, pady=2)

label_snr_up = tk.Label(frame_labels_snr, text="SNR UL: --", font=("Arial", 8, "bold"), bg=cor_snr_up, fg="white", width=18)
label_snr_up.pack(side="left", padx=2)

label_estat_snr = tk.Label(frame_labels_snr, text="MM Média: -- | Máx: -- | Mín: -- | DesvPad: --", font=("Arial", 8), fg="#333333")
label_estat_snr.pack(side="left", padx=10)

tk.Label(frame_labels_snr, text="Janela SNR:", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_janela_snr = tk.Entry(frame_labels_snr, width=5, font=("Arial", 8))
entry_janela_snr.insert(0, "10")
entry_janela_snr.pack(side="left")

# --- GRÁFICO SNR ---
frame_snr = tk.Frame(raiz)
frame_snr.pack(fill="both", expand=True, padx=10, pady=1)

fig2 = Figure(figsize=(10, 2.0), dpi=100)
ax2 = fig2.add_subplot(111)
fig2.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas2 = FigureCanvasTkAgg(fig2, master=frame_snr)
canvas2.get_tk_widget().pack(fill="both", expand=True)

# Painel PSR & Limiar
frame_label_psr = tk.Frame(raiz)
frame_label_psr.pack(fill="x", padx=10, pady=2)

label_psr = tk.Label(frame_label_psr, text="PSR atual: --", font=("Arial", 8, "bold"), bg=cor_psr, fg="white", width=18)
label_psr.pack(side="left", padx=2)

label_perdidos = tk.Label(frame_label_psr, text="Pacotes Perdidos: --", font=("Arial", 8, "bold"), fg="#d62728")
label_perdidos.pack(side="left", padx=15)

tk.Label(frame_label_psr, text="Limiar PSR (%):", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_limiar_psr = tk.Entry(frame_label_psr, width=6, font=("Arial", 8))
entry_limiar_psr.insert(0, "95")
entry_limiar_psr.pack(side="left")

# --- GRÁFICO PSR ---
frame_psr = tk.Frame(raiz)
frame_psr.pack(fill="both", expand=True, padx=10, pady=1)

fig3 = Figure(figsize=(10, 2.0), dpi=100)
ax3 = fig3.add_subplot(111)
fig3.subplots_adjust(left=0.05, right=0.98, top=0.84, bottom=0.20)
canvas3 = FigureCanvasTkAgg(fig3, master=frame_psr)
canvas3.get_tk_widget().pack(fill="both", expand=True)

atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz)

def fechar_janela():
    if messagebox.askokcancel("Sair", "Deseja fechar o monitor de gerência?"):
        raiz.destroy()

raiz.protocol("WM_DELETE_WINDOW", fechar_janela)
raiz.mainloop()

'''
'''
# Exibição | Gerência [RSSI, SNR e PSR] | N6 | WissTek-IoT | Framework LoRa
# ====== Nível 6 - Gerência ======
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.style as style
import os
import glob
import math

style.use("ggplot")

MAX_PONTOS = 600
cor_rssi_up = "#ff7f0e"
cor_rssi_ma = "#1f77b4"
cor_snr_up = "#ff7f0e"
cor_snr_ma = "#1f77b4"#"#9467bd"
cor_psr = "#2ca02c"

PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = f"{PASTA_N4}/Parametros"
PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"
ARQUIVO_PARAMETROS = f"{PASTA_PARAMETROS}/dados_processamento.txt"

if not os.path.exists(PASTA_N4):
    os.mkdir(PASTA_N4)
if not os.path.exists(PASTA_PARAMETROS):
    os.mkdir(PASTA_PARAMETROS)

arquivo_csv_atual_ref = {"caminho": None}

def salvar_parametros_n5():
    try:
        j_rssi = str(int(entry_janela_rssi.get()))
        j_snr = str(int(entry_janela_snr.get()))
        with open(ARQUIVO_PARAMETROS, "w", encoding="utf-8") as f:
            f.write(f"JANELA_RSSI={j_rssi}\n")
            f.write(f"JANELA_SNR={j_snr}\n")
    except ValueError:
        pass

def calcular_estatisticas_completas(lista):
    valores = [x for x in lista if x != "" and x is not None]
    n = len(valores)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    media = sum(valores) / n
    maximo = max(valores)
    minimo = min(valores)
    if n < 2:
        desvio = 0.0
    else:
        var = sum((x - media) ** 2 for x in valores) / (n - 1)
        desvio = math.sqrt(var)
    return media, desvio, maximo, minimo

def atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz):
    rssi_up, rssi_ma = [], []
    snr_up, snr_ma = [], []   
    psr = []

    salvar_parametros_n5()

    padrao_busca = os.path.join(PASTA_PROCESSADOS, "Rodada_Gerencia_*.csv")
    arquivos_csv = glob.glob(padrao_busca)
    
    if arquivos_csv:
        arquivos_csv.sort(key=os.path.getmtime)
        ultimo_csv = arquivos_csv[-1]
        
        if ultimo_csv != arquivo_csv_atual_ref["caminho"]:
            arquivo_csv_atual_ref["caminho"] = ultimo_csv

        try:
            with open(arquivo_csv_atual_ref["caminho"], 'r', encoding='utf-8') as f:
                linhas = f.readlines()
                for linha in linhas[1:]:
                    linha = linha.strip()
                    if linha:
                        try:
                            partes = linha.split(";")
                            r_up = partes[1].replace(",", ".") if partes[1] != "" else ""
                            s_up = partes[3].replace(",", ".") if partes[3] != "" else ""
                            p_val = partes[4].replace(",", ".") if partes[4] != "" else ""
                            r_ma = partes[5].replace(",", ".") if (len(partes) > 5 and partes[5] != "") else ""
                            s_ma = partes[6].replace(",", ".") if (len(partes) > 6 and partes[6] != "") else ""

                            rssi_up.append(float(r_up) if r_up != "" else "")
                            snr_up.append(float(s_up) if s_up != "" else "")
                            psr.append(float(p_val) if p_val != "" else "")
                            rssi_ma.append(float(r_ma) if r_ma != "" else "")
                            snr_ma.append(float(s_ma) if s_ma != "" else "")
                        except Exception:
                            pass
        except (PermissionError, FileNotFoundError):
            pass

    # Aplicar janela deslizante visual
    rssi_up = rssi_up[-MAX_PONTOS:]
    rssi_ma = rssi_ma[-MAX_PONTOS:]
    snr_up = snr_up[-MAX_PONTOS:]    
    snr_ma = snr_ma[-MAX_PONTOS:]
    psr = psr[-MAX_PONTOS:]

    # --- Atualizar Labels e Textos Estatísticos ---
    if rssi_up and rssi_up[-1] != "":
        label_up.config(text=f"RSSI UL: {round(rssi_up[-1], 2)} dBm")
    else:
        label_up.config(text="RSSI UL: --")

    if snr_up and snr_up[-1] != "":
        label_snr_up.config(text=f"SNR UL: {round(snr_up[-1], 2)} dB")
    else:
        label_snr_up.config(text="SNR UL: --")

    if psr and psr[-1] != "":
        label_psr.config(text=f"PSR atual: {round(psr[-1], 2)} %")
    else:
        label_psr.config(text="PSR atual: --")

    # Estatísticas (Média, Desvio Padrão, Máximo e Mínimo)
    med_r, desv_r, max_r, min_r = calcular_estatisticas_completas(rssi_ma)
    med_s, desv_s, max_s, min_s = calcular_estatisticas_completas(snr_ma)
    
    label_estat_rssi.config(text=f"MM Média: {med_r:.2f} dBm | Máx: {max_r:.2f} | Mín: {min_r:.2f} | DesvPad: {desv_r:.2f}")
    label_estat_snr.config(text=f"MM Média: {med_s:.2f} dB | Máx: {max_s:.2f} | Mín: {min_s:.2f} | DesvPad: {desv_s:.2f}")

    total_pts = len(psr)
    if total_pts > 0 and psr[-1] != "":
        perdidos_est = int(round(total_pts * (100.0 - psr[-1]) / 100.0))
        label_perdidos.config(text=f"Pacotes Perdidos: {perdidos_est}")
    else:
        label_perdidos.config(text="Pacotes Perdidos: --")

    # --- GRÁFICO 1: RSSI ---
    ax1.clear()
    r_plot = [x for x in rssi_up if x != ""]
    rma_plot = [x for x in rssi_ma if x != ""]
    if r_plot:
        ax1.plot(r_plot, label="RSSI Bruto (dBm)", linewidth=1.8, alpha=0.5, color=cor_rssi_up)
        if rma_plot:
            ax1.plot(rma_plot, label="Média Móvel (dB)", linewidth=1.0, color=cor_rssi_ma)
        ax1.legend(loc='upper right', fontsize=7)
        val_min, val_max = min(r_plot), max(r_plot)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax1.set_ylim(val_min - margem, val_max + margem)

    ax1.set_title("RSSI LoRa (Uplink)", fontsize=9, pad=2)
    ax1.set_ylabel("RSSI (dBm)", fontsize=7)
    ax1.tick_params(labelsize=6)

    # --- GRÁFICO 2: SNR ---
    ax2.clear()
    s_plot = [x for x in snr_up if x != ""]
    sma_plot = [x for x in snr_ma if x != ""]
    if s_plot:
        ax2.plot(s_plot, label="SNR Bruto (dB)", linewidth=1.8, alpha=0.5, color=cor_snr_up)
        if sma_plot:
            ax2.plot(sma_plot, label="Média Móvel (dB)", linewidth=1.0, color=cor_snr_ma)
        ax2.legend(loc='upper right', fontsize=7)
        val_min, val_max = min(s_plot), max(s_plot)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax2.set_ylim(val_min - margem, val_max + margem)

    ax2.set_title("SNR LoRa (Uplink)", fontsize=9, pad=2)
    ax2.set_ylabel("SNR (dB)", fontsize=7)
    ax2.tick_params(labelsize=6)

    # --- GRÁFICO 3: PSR + LIMIAR ---
    ax3.clear()
    psr_plot = [x for x in psr if x != ""]
    
    try:
        limiar_val = float(entry_limiar_psr.get().replace(",", "."))
    except ValueError:
        limiar_val = 95.0

    if psr_plot:
        ax3.plot(psr_plot, label="PSR (%)", linewidth=1.8, color=cor_psr)
        ax3.axhline(y=limiar_val, color='red', linestyle='--', linewidth=1.0, label=f"Limiar ({limiar_val}%)")
        ax3.legend(loc='lower right', fontsize=7)
        val_min, val_max = min(psr_plot), max(psr_plot)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax3.set_ylim(max(0, val_min - margem), min(105, val_max + margem))

    ax3.set_title("Packet Success Rate - PSR", fontsize=9, pad=2)
    ax3.set_ylabel("PSR (%)", fontsize=7)
    ax3.set_xlabel("Amostras", fontsize=7)
    ax3.tick_params(labelsize=6)

    canvas1.draw()
    canvas2.draw()
    canvas3.draw()
    raiz.after(1000, atualizar_grafico, ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz)

# ===================== INTERFACE TKINTER =====================
raiz = tk.Tk()
raiz.title("FEE247 - NÍVEL 6 - GERÊNCIA & CONFIGURAÇÃO")
raiz.geometry("1350x780")
raiz.minsize(1150, 700)

# Painel Topo: RSSI & Máx/Mín/Média/DesvPad
frame_topo = tk.Frame(raiz)
frame_topo.pack(fill="x", padx=10, pady=2)

label_up = tk.Label(frame_topo, text="RSSI UL: --", font=("Arial", 8, "bold"), bg=cor_rssi_up, fg="white", width=18)
label_up.pack(side="left", padx=2)

label_estat_rssi = tk.Label(frame_topo, text="MM Média: -- | Máx: -- | Mín: -- | DesvPad: --", font=("Arial", 8), fg="#333333")
label_estat_rssi.pack(side="left", padx=10)

tk.Label(frame_topo, text="Janela RSSI:", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_janela_rssi = tk.Entry(frame_topo, width=5, font=("Arial", 8))
entry_janela_rssi.insert(0, "10")
entry_janela_rssi.pack(side="left")

btn_salvar = tk.Button(frame_topo, text="Salvar Gráficos", font=("Arial", 8, "bold"), command=lambda: salvar(fig1, fig2, fig3))
btn_salvar.pack(side="right", padx=2)

def salvar(fig1, fig2, fig3):
    arquivo = filedialog.asksaveasfilename(defaultextension=".png")
    if arquivo:
        fig1.savefig(arquivo.replace(".png", "_rssi.png"))
        fig2.savefig(arquivo.replace(".png", "_snr.png"))
        fig3.savefig(arquivo.replace(".png", "_psr.png"))
        messagebox.showinfo("Sucesso", "Gráficos salvos com sucesso!")

# --- GRÁFICO RSSI ---
frame_rssi = tk.Frame(raiz)
frame_rssi.pack(fill="both", expand=True, padx=10, pady=1)

fig1 = Figure(figsize=(10, 2.0), dpi=100)
ax1 = fig1.add_subplot(111)
fig1.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas1 = FigureCanvasTkAgg(fig1, master=frame_rssi)
canvas1.get_tk_widget().pack(fill="both", expand=True)

# Painel SNR & Máx/Mín/Média/DesvPad
frame_labels_snr = tk.Frame(raiz)
frame_labels_snr.pack(fill="x", padx=10, pady=2)

label_snr_up = tk.Label(frame_labels_snr, text="SNR UL: --", font=("Arial", 8, "bold"), bg=cor_snr_up, fg="white", width=18)
label_snr_up.pack(side="left", padx=2)

label_estat_snr = tk.Label(frame_labels_snr, text="MM Média: -- | Máx: -- | Mín: -- | DesvPad: --", font=("Arial", 8), fg="#333333")
label_estat_snr.pack(side="left", padx=10)

tk.Label(frame_labels_snr, text="Janela SNR:", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_janela_snr = tk.Entry(frame_labels_snr, width=5, font=("Arial", 8))
entry_janela_snr.insert(0, "10")
entry_janela_snr.pack(side="left")

# --- GRÁFICO SNR ---
frame_snr = tk.Frame(raiz)
frame_snr.pack(fill="both", expand=True, padx=10, pady=1)

fig2 = Figure(figsize=(10, 2.0), dpi=100)
ax2 = fig2.add_subplot(111)
fig2.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas2 = FigureCanvasTkAgg(fig2, master=frame_snr)
canvas2.get_tk_widget().pack(fill="both", expand=True)

# Painel PSR & Limiar
frame_label_psr = tk.Frame(raiz)
frame_label_psr.pack(fill="x", padx=10, pady=2)

label_psr = tk.Label(frame_label_psr, text="PSR atual: --", font=("Arial", 8, "bold"), bg=cor_psr, fg="white", width=18)
label_psr.pack(side="left", padx=2)

label_perdidos = tk.Label(frame_label_psr, text="Pacotes Perdidos: --", font=("Arial", 8, "bold"), fg="#d62728")
label_perdidos.pack(side="left", padx=15)

tk.Label(frame_label_psr, text="Limiar PSR (%):", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_limiar_psr = tk.Entry(frame_label_psr, width=6, font=("Arial", 8))
entry_limiar_psr.insert(0, "95")
entry_limiar_psr.pack(side="left")

# --- GRÁFICO PSR ---
frame_psr = tk.Frame(raiz)
frame_psr.pack(fill="both", expand=True, padx=10, pady=1)

fig3 = Figure(figsize=(10, 2.0), dpi=100)
ax3 = fig3.add_subplot(111)
fig3.subplots_adjust(left=0.05, right=0.98, top=0.84, bottom=0.20)
canvas3 = FigureCanvasTkAgg(fig3, master=frame_psr)
canvas3.get_tk_widget().pack(fill="both", expand=True)

atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz)

def fechar_janela():
    if messagebox.askokcancel("Sair", "Deseja fechar o monitor de gerência?"):
        raiz.destroy()

raiz.protocol("WM_DELETE_WINDOW", fechar_janela)
raiz.mainloop()
'''


'''
# Exibição | Gerência [RSSI, SNR e PSR] | N6 | WissTek-IoT | Framework LoRa
# ====== Nível 6 - Gerência ======
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.style as style
import os
import glob
import math

style.use("ggplot")

MAX_PONTOS = 600
cor_rssi_up = "#ff7f0e"
cor_rssi_ma = "#1f77b4"
cor_snr_up = "#ff7f0e"
cor_snr_ma = "#9467bd"
cor_psr = "#2ca02c"

PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = f"{PASTA_N4}/Parametros"
PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"
ARQUIVO_PARAMETROS = f"{PASTA_PARAMETROS}/dados_processamento.txt"

if not os.path.exists(PASTA_N4):
    os.mkdir(PASTA_N4)
if not os.path.exists(PASTA_PARAMETROS):
    os.mkdir(PASTA_PARAMETROS)

arquivo_csv_atual_ref = {"caminho": None}

def salvar_parametros_n5():
    """Grava as configurações alteradas nos Entrys para o arquivo de parâmetros do N5"""
    try:
        j_rssi = str(int(entry_janela_rssi.get()))
        j_snr = str(int(entry_janela_snr.get()))
        with open(ARQUIVO_PARAMETROS, "w", encoding="utf-8") as f:
            f.write(f"JANELA_RSSI={j_rssi}\n")
            f.write(f"JANELA_SNR={j_snr}\n")
    except ValueError:
        pass

def calcular_estatisticas(lista):
    valores = [x for x in lista if x != "" and x is not None]
    n = len(valores)
    if n == 0:
        return 0.0, 0.0
    media = sum(valores) / n
    if n < 2:
        desvio = 0.0
    else:
        var = sum((x - media) ** 2 for x in valores) / (n - 1)
        desvio = math.sqrt(var)
    return media, desvio

def atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz):
    rssi_up, rssi_ma = [], []
    snr_up, snr_ma = [], []   
    psr = []

    salvar_parametros_n5()

    padrao_busca = os.path.join(PASTA_PROCESSADOS, "Rodada_Gerencia_*.csv")
    arquivos_csv = glob.glob(padrao_busca)
    
    if arquivos_csv:
        arquivos_csv.sort(key=os.path.getmtime)
        ultimo_csv = arquivos_csv[-1]
        
        if ultimo_csv != arquivo_csv_atual_ref["caminho"]:
            arquivo_csv_atual_ref["caminho"] = ultimo_csv

        try:
            with open(arquivo_csv_atual_ref["caminho"], 'r', encoding='utf-8') as f:
                linhas = f.readlines()
                for linha in linhas[1:]:
                    linha = linha.strip()
                    if linha:
                        try:
                            partes = linha.split(";")
                            r_up = partes[1].replace(",", ".") if partes[1] != "" else ""
                            s_up = partes[3].replace(",", ".") if partes[3] != "" else ""
                            p_val = partes[4].replace(",", ".") if partes[4] != "" else ""
                            r_ma = partes[5].replace(",", ".") if (len(partes) > 5 and partes[5] != "") else ""
                            s_ma = partes[6].replace(",", ".") if (len(partes) > 6 and partes[6] != "") else ""

                            rssi_up.append(float(r_up) if r_up != "" else "")
                            snr_up.append(float(s_up) if s_up != "" else "")
                            psr.append(float(p_val) if p_val != "" else "")
                            rssi_ma.append(float(r_ma) if r_ma != "" else "")
                            snr_ma.append(float(s_ma) if s_ma != "" else "")
                        except Exception:
                            pass
        except (PermissionError, FileNotFoundError):
            pass

    # Aplicar janela deslizante visual
    rssi_up = rssi_up[-MAX_PONTOS:]
    rssi_ma = rssi_ma[-MAX_PONTOS:]
    snr_up = snr_up[-MAX_PONTOS:]    
    snr_ma = snr_ma[-MAX_PONTOS:]
    psr = psr[-MAX_PONTOS:]

    # --- Atualizar Labels e Estatísticas ---
    if rssi_up and rssi_up[-1] != "":
        label_up.config(text=f"RSSI UL: {round(rssi_up[-1], 2)} dBm")
    else:
        label_up.config(text="RSSI UL: --")

    if snr_up and snr_up[-1] != "":
        label_snr_up.config(text=f"SNR UL: {round(snr_up[-1], 2)} dB")
    else:
        label_snr_up.config(text="SNR UL: --")

    if psr and psr[-1] != "":
        label_psr.config(text=f"PSR atual: {round(psr[-1], 2)} %")
    else:
        label_psr.config(text="PSR atual: --")

    # Estatísticas de Média e Desvio Padrão
    med_r, desv_r = calcular_estatisticas(rssi_ma)
    med_s, desv_s = calcular_estatisticas(snr_ma)
    label_estat_rssi.config(text=f"Média MM: {med_r:.2f} dBm | DesvPad: {desv_r:.2f}")
    label_estat_snr.config(text=f"Média MM: {med_s:.2f} dB | DesvPad: {desv_s:.2f}")

    # Pacotes Perdidos (estimados a partir da PSR final e contagem)
    total_pts = len(psr)
    if total_pts > 0 and psr[-1] != "":
        perdidos_est = int(round(total_pts * (100.0 - psr[-1]) / 100.0))
        label_perdidos.config(text=f"Pacotes Perdidos: {perdidos_est}")
    else:
        label_perdidos.config(text="Pacotes Perdidos: --")

    # --- GRÁFICO 1: RSSI ---
    ax1.clear()
    r_plot = [x for x in rssi_up if x != ""]
    rma_plot = [x for x in rssi_ma if x != ""]
    if r_plot:
        ax1.plot(r_plot, label="RSSI Bruto (dBm)", linewidth=0.8, alpha=0.5, color=cor_rssi_up)
        if rma_plot:
            ax1.plot(rma_plot, label="Média Móvel (mW)", linewidth=1.8, color=cor_rssi_ma)
        ax1.legend(loc='upper right', fontsize=7)
        val_min, val_max = min(r_plot), max(r_plot)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax1.set_ylim(val_min - margem, val_max + margem)

    ax1.set_title("RSSI LoRa (Uplink)", fontsize=9, pad=2)
    ax1.set_ylabel("RSSI (dBm)", fontsize=7)
    ax1.tick_params(labelsize=6)

    # --- GRÁFICO 2: SNR ---
    ax2.clear()
    s_plot = [x for x in snr_up if x != ""]
    sma_plot = [x for x in snr_ma if x != ""]
    if s_plot:
        ax2.plot(s_plot, label="SNR Bruto (dB)", linewidth=0.8, alpha=0.5, color=cor_snr_up)
        if sma_plot:
            ax2.plot(sma_plot, label="Média Móvel (dB)", linewidth=1.8, color=cor_snr_ma)
        ax2.legend(loc='upper right', fontsize=7)
        val_min, val_max = min(s_plot), max(s_plot)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax2.set_ylim(val_min - margem, val_max + margem)

    ax2.set_title("SNR LoRa (Uplink)", fontsize=9, pad=2)
    ax2.set_ylabel("SNR (dB)", fontsize=7)
    ax2.tick_params(labelsize=6)

    # --- GRÁFICO 3: PSR + LIMIAR AJUSTÁVEL ---
    ax3.clear()
    psr_plot = [x for x in psr if x != ""]
    
    try:
        limiar_val = float(entry_limiar_psr.get().replace(",", "."))
    except ValueError:
        limiar_val = 98.0

    if psr_plot:
        ax3.plot(psr_plot, label="PSR (%)", linewidth=1.2, color=cor_psr)
        ax3.axhline(y=limiar_val, color='red', linestyle='--', linewidth=1.5, label=f"Limiar ({limiar_val}%)")
        ax3.legend(loc='lower right', fontsize=7)
        val_min, val_max = min(psr_plot), max(psr_plot)
        margem = max(5.0, (val_max - val_min) * 0.10)
        ax3.set_ylim(max(0, val_min - margem), min(105, val_max + margem))

    ax3.set_title("Packet Success Rate - PSR", fontsize=9, pad=2)
    ax3.set_ylabel("PSR (%)", fontsize=7)
    ax3.set_xlabel("Amostras", fontsize=7)
    ax3.tick_params(labelsize=6)

    canvas1.draw()
    canvas2.draw()
    canvas3.draw()
    raiz.after(1000, atualizar_grafico, ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz)

# ===================== INTERFACE TKINTER =====================
raiz = tk.Tk()
raiz.title("FEE247 - NÍVEL 6 - GERÊNCIA & CONFIGURAÇÃO")
raiz.geometry("1300x780")
raiz.minsize(1100, 700)

# Painel Topo: Controles RSSI e Janela Média Móvel
frame_topo = tk.Frame(raiz)
frame_topo.pack(fill="x", padx=10, pady=2)

label_up = tk.Label(frame_topo, text="RSSI UL: --", font=("Arial", 8, "bold"), bg=cor_rssi_up, fg="white", width=18)
label_up.pack(side="left", padx=2)

label_estat_rssi = tk.Label(frame_topo, text="Média MM: -- | DesvPad: --", font=("Arial", 8), fg="#333333")
label_estat_rssi.pack(side="left", padx=10)

tk.Label(frame_topo, text="Janela RSSI:", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_janela_rssi = tk.Entry(frame_topo, width=5, font=("Arial", 8))
entry_janela_rssi.insert(0, "10")
entry_janela_rssi.pack(side="left")

btn_salvar = tk.Button(frame_topo, text="Salvar Gráficos", font=("Arial", 8, "bold"), command=lambda: salvar(fig1, fig2, fig3))
btn_salvar.pack(side="right", padx=2)

def salvar(fig1, fig2, fig3):
    arquivo = filedialog.asksaveasfilename(defaultextension=".png")
    if arquivo:
        fig1.savefig(arquivo.replace(".png", "_rssi.png"))
        fig2.savefig(arquivo.replace(".png", "_snr.png"))
        fig3.savefig(arquivo.replace(".png", "_psr.png"))
        messagebox.showinfo("Sucesso", "Gráficos salvos com sucesso!")

# --- GRÁFICO RSSI ---
frame_rssi = tk.Frame(raiz)
frame_rssi.pack(fill="both", expand=True, padx=10, pady=1)

fig1 = Figure(figsize=(10, 2.0), dpi=100)
ax1 = fig1.add_subplot(111)
fig1.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas1 = FigureCanvasTkAgg(fig1, master=frame_rssi)
canvas1.get_tk_widget().pack(fill="both", expand=True)

# Painel SNR
frame_labels_snr = tk.Frame(raiz)
frame_labels_snr.pack(fill="x", padx=10, pady=2)

label_snr_up = tk.Label(frame_labels_snr, text="SNR UL: --", font=("Arial", 8, "bold"), bg=cor_snr_up, fg="white", width=18)
label_snr_up.pack(side="left", padx=2)

label_estat_snr = tk.Label(frame_labels_snr, text="Média MM: -- | DesvPad: --", font=("Arial", 8), fg="#333333")
label_estat_snr.pack(side="left", padx=10)

tk.Label(frame_labels_snr, text="Janela SNR:", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_janela_snr = tk.Entry(frame_labels_snr, width=5, font=("Arial", 8))
entry_janela_snr.insert(0, "10")
entry_janela_snr.pack(side="left")

# --- GRÁFICO SNR ---
frame_snr = tk.Frame(raiz)
frame_snr.pack(fill="both", expand=True, padx=10, pady=1)

fig2 = Figure(figsize=(10, 2.0), dpi=100)
ax2 = fig2.add_subplot(111)
fig2.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas2 = FigureCanvasTkAgg(fig2, master=frame_snr)
canvas2.get_tk_widget().pack(fill="both", expand=True)

# Painel PSR & Limiar
frame_label_psr = tk.Frame(raiz)
frame_label_psr.pack(fill="x", padx=10, pady=2)

label_psr = tk.Label(frame_label_psr, text="PSR atual: --", font=("Arial", 8, "bold"), bg=cor_psr, fg="white", width=18)
label_psr.pack(side="left", padx=2)

label_perdidos = tk.Label(frame_label_psr, text="Pacotes Perdidos: --", font=("Arial", 8, "bold"), fg="#d62728")
label_perdidos.pack(side="left", padx=15)

tk.Label(frame_label_psr, text="Limiar PSR (%):", font=("Arial", 8)).pack(side="left", padx=(15, 2))
entry_limiar_psr = tk.Entry(frame_label_psr, width=6, font=("Arial", 8))
entry_limiar_psr.insert(0, "98")
entry_limiar_psr.pack(side="left")

# --- GRÁFICO PSR ---
frame_psr = tk.Frame(raiz)
frame_psr.pack(fill="both", expand=True, padx=10, pady=1)

fig3 = Figure(figsize=(10, 2.0), dpi=100)
ax3 = fig3.add_subplot(111)
fig3.subplots_adjust(left=0.05, right=0.98, top=0.84, bottom=0.20)
canvas3 = FigureCanvasTkAgg(fig3, master=frame_psr)
canvas3.get_tk_widget().pack(fill="both", expand=True)

atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz)

def fechar_janela():
    if messagebox.askokcancel("Sair", "Deseja fechar o monitor de gerência?"):
        raiz.destroy()

raiz.protocol("WM_DELETE_WINDOW", fechar_janela)
raiz.mainloop()
'''
