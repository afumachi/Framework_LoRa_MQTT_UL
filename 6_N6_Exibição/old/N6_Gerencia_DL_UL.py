# Exibição | Gerência [RSSI, SNR e PSR] | N6 | WissTek-IoT | Framework LoRa
# 29/10/2026 (Atualizado para rastrear e ler o último CSV gerado dinamicamente)
# ====== Nível 6 - Gerência ======
# Gráficos de RSSI, SNR, PSR e Controle de LED Amarelo
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.style as style
import os
import glob

style.use("ggplot")

MAX_PONTOS = 600
cor_rssi_down = "#1f77b4"
cor_rssi_up = "#ff7f0e"
cor_snr_down = "#1f77b4"
cor_snr_up = "#ff7f0e"
cor_psr = "#2ca02c"

# Configuração do caminho do LED amarelo e pastas
PASTA_N4 = "../4_N4_Armazenamento"
if not os.path.exists(PASTA_N4):
    os.mkdir(PASTA_N4)
if not os.path.exists(f"{PASTA_N4}/Parametros"):
    os.mkdir(f"{PASTA_N4}/Parametros")
caminho_cmd_led = f"{PASTA_N4}/Parametros/cmd_led_amarelo.txt"

PASTA_PROCESSADOS = f"{PASTA_N4}/Dados_Processados"

# Variável global para rastrear o arquivo CSV atual que está sendo lido
arquivo_csv_atual_ref = {"caminho": None}

def salvar_cmd_led(valor):
    try:
        with open(caminho_cmd_led, "w") as f:
            f.write(str(valor))
        print(f"Valor do LED {valor} salvo em: {caminho_cmd_led}")
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível salvar o comando do LED: {e}")

# ===================== ATUALIZA GRÁFICOS =====================
def atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz, label_down, label_up, label_snr_down, label_snr_up, label_psr):
    rssi_down = []
    rssi_up = []
    snr_down = []
    snr_up = []   
    psr = []

    # Procura dinamicamente o último arquivo CSV gerado pelo N5 na pasta Dados_Processados
    padrao_busca = os.path.join(PASTA_PROCESSADOS, "Rodada_Gerencia_*.csv")
    arquivos_csv = glob.glob(padrao_busca)
    
    if arquivos_csv:
        # Ordena por data de modificação/criação para pegar sempre o mais recente
        arquivos_csv.sort(key=os.path.getmtime)
        ultimo_csv = arquivos_csv[-1]
        
        # Se mudou de arquivo (nova rodada iniciada), avisa no console
        if ultimo_csv != arquivo_csv_atual_ref["caminho"]:
            print(f"[N6] Alternando para o novo arquivo CSV da rodada: {os.path.basename(ultimo_csv)}")
            arquivo_csv_atual_ref["caminho"] = ultimo_csv

        # ===================== LEITURA DO CSV ATUAL (Modo Run) =====================
        try:
            with open(arquivo_csv_atual_ref["caminho"], 'r', encoding='utf-8') as f:
                linhas = f.readlines()
                for linha in linhas[1:]: # Pula cabeçalho
                    linha = linha.strip()
                    if linha:
                        try:
                            partes = linha.split(";")
                            r_down = partes[0].replace(",", ".") if partes[0] != "" else ""
                            r_up = partes[1].replace(",", ".") if partes[1] != "" else ""
                            s_down = partes[2].replace(",", ".") if partes[2] != "" else ""
                            s_up = partes[3].replace(",", ".") if partes[3] != "" else ""
                            p_val = partes[4].replace(",", ".") if partes[4] != "" else ""

                            rssi_down.append(float(r_down) if r_down != "" else "")
                            rssi_up.append(float(r_up) if r_up != "" else "")
                            snr_down.append(float(s_down) if s_down != "" else "")
                            snr_up.append(float(s_up) if s_up != "" else "")
                            psr.append(float(p_val) if p_val != "" else "")
                        except Exception:
                            pass
        except (PermissionError, FileNotFoundError):
            # Caso o N5 esteja escrevendo no exato milissegundo da leitura, ignora o ciclo atual sem travar
            pass

    # ===================== JANELA DESLIZANTE =====================
    rssi_down = rssi_down[-MAX_PONTOS:]
    rssi_up = rssi_up[-MAX_PONTOS:]
    snr_down = snr_down[-MAX_PONTOS:]
    snr_up = snr_up[-MAX_PONTOS:]    
    psr = psr[-MAX_PONTOS:]

    # ===================== LABELS =====================
    if rssi_down and rssi_down[-1] != "":
        label_down.config(text="RSSI DL atual: " + str(round(rssi_down[-1],2)) + " dBm")
    else:
        label_down.config(text="RSSI DL atual: --")

    if rssi_up and rssi_up[-1] != "":
        label_up.config(text="RSSI UL atual: " + str(round(rssi_up[-1],2)) + " dBm")
    else:
        label_up.config(text="RSSI UL atual: --")

    if snr_down and snr_down[-1] != "":
        label_snr_down.config(text="SNR DL atual: " + str(round(snr_down[-1],2)) + " dB")
    else:
        label_snr_down.config(text="SNR DL atual: --")

    if snr_up and snr_up[-1] != "":
        label_snr_up.config(text="SNR UL atual: " + str(round(snr_up[-1],2)) + " dB")
    else:
        label_snr_up.config(text="SNR UL atual: --")

    if psr and psr[-1] != "":
        label_psr.config(text="PSR atual: " + str(round(psr[-1],2)) + " %")
    else:
        label_psr.config(text="PSR atual: --")

    # Filtra valores vazios para plotagem correta nos gráficos
    r_down_plot = [x for x in rssi_down if x != ""]
    r_up_plot = [x for x in rssi_up if x != ""]
    s_down_plot = [x for x in snr_down if x != ""]
    s_up_plot = [x for x in snr_up if x != ""]
    psr_plot = [x for x in psr if x != ""]

    # ===================== GRÁFICO RSSI =====================
    ax1.clear()
    if r_down_plot:
        ax1.plot(r_down_plot, label="RSSI Downlink (dBm)", linewidth=1.2, marker='o', markersize=1.0, color=cor_rssi_down)
    if r_up_plot:
        ax1.plot(r_up_plot, label="RSSI Uplink (dBm)", linewidth=1.2, marker='s', markersize=1.0, color=cor_rssi_up)
    if r_down_plot or r_up_plot:
        ax1.legend(loc='upper right', fontsize=7)
        todos_rssi = r_down_plot + r_up_plot
        val_min = min(todos_rssi)
        val_max = max(todos_rssi)
        margem = (val_max - val_min) * 0.10
        if margem == 0:
            margem = 5
        ax1.set_ylim(val_min - margem, val_max + margem)

    ax1.set_title("RSSI LoRa (Downlink / Uplink)", fontsize=9, pad=2)
    ax1.set_ylabel("RSSI (dBm)", fontsize=7)
    ax1.tick_params(labelsize=6)

    # ===================== GRÁFICO SNR =====================
    ax2.clear()
    if s_down_plot:
        ax2.plot(s_down_plot, label="SNR Downlink (dB)", linewidth=1.2, marker='o', markersize=1.0, color=cor_snr_down)
    if s_up_plot:
        ax2.plot(s_up_plot, label="SNR Uplink (dB)", linewidth=1.2, marker='s', markersize=1.0, color=cor_snr_up)
    if s_down_plot or s_up_plot:
        ax2.legend(loc='upper right', fontsize=7)
        todos_snr = s_down_plot + s_up_plot
        val_snr_min = min(todos_snr)
        val_snr_max = max(todos_snr)
        margem_snr = (val_snr_max - val_snr_min) * 0.10
        if margem_snr == 0:
            margem_snr = 5
        ax2.set_ylim(val_snr_min - margem_snr, val_snr_max + margem_snr)

    ax2.set_title("SNR LoRa (Downlink / Uplink)", fontsize=9, pad=2)
    ax2.set_ylabel("SNR (dB)", fontsize=7)
    ax2.tick_params(labelsize=6)

    # ===================== GRÁFICO PSR =====================
    ax3.clear()
    if psr_plot:
        ax3.plot(psr_plot, label="PSR (%)", linewidth=1.2, marker='o', markersize=1.0, color=cor_psr)
        ax3.legend(loc='upper right', fontsize=7)
        val_min = min(psr_plot)
        val_max = max(psr_plot)
        margem = (val_max - val_min) * 0.10
        if margem == 0:
            margem = 5
        ax3.set_ylim(max(0, val_min - margem), min(105, val_max + margem))

    ax3.set_title("Packet Success Rate - PSR", fontsize=9, pad=2)
    ax3.set_ylabel("PSR (%)", fontsize=7)
    ax3.set_xlabel("Últimas " + str(MAX_PONTOS) + " medidas", fontsize=7)
    ax3.tick_params(labelsize=6)

    # ===================== ATUALIZA =====================
    canvas1.draw()
    canvas2.draw()
    canvas3.draw()
    raiz.after(1000, atualizar_grafico, ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz, label_down, label_up, label_snr_down, label_snr_up, label_psr)

# ===================== BOTÕES / AÇÕES =====================
def fechar():
    if messagebox.askokcancel("Sair", "Deseja fechar o monitor?"):
        raiz.destroy()

def salvar(fig1, fig2, fig3):
    arquivo = filedialog.asksaveasfilename(defaultextension=".png")
    if arquivo:
        fig1.savefig(arquivo.replace(".png", "_rssi.png"))
        fig2.savefig(arquivo.replace(".png", "_snr.png"))
        fig3.savefig(arquivo.replace(".png", "_psr.png"))
        messagebox.showinfo("Sucesso", "Gráficos salvos com sucesso!")

# ===================== INTERFACE =====================
raiz = tk.Tk()
raiz.title("FEE247 - NÍVEL 6 - GERÊNCIA")
raiz.geometry("1300x740")
raiz.minsize(1100, 700)

# Frame Superior: Status de RSSI e Controles de Ação/LED
frame_topo = tk.Frame(raiz)
frame_topo.pack(fill="x", padx=10, pady=(2, 1))

# Sub-frame para Labels RSSI
frame_labels_rssi = tk.Frame(frame_topo)
frame_labels_rssi.pack(side="left")

label_down = tk.Label(frame_labels_rssi, text="RSSI DL atual: --", font=("Arial", 8, "bold"), bg=cor_rssi_down, fg="white", relief="ridge", bd=2, width=22, pady=1)
label_down.pack(side="left", padx=2)

label_up = tk.Label(frame_labels_rssi, text="RSSI UL atual: --", font=("Arial", 8, "bold"), bg=cor_rssi_up, fg="white", relief="ridge", bd=2, width=22, pady=1)
label_up.pack(side="left", padx=2)

# Sub-frame para Controles (LED Amarelo e Salvar Gráficos)
frame_controles = tk.Frame(frame_topo)
frame_controles.pack(side="right", padx=2)

opcao_led = tk.IntVar(value=0)
tk.Label(frame_controles, text="LED Amarelo:", font=("Arial", 8, "bold")).pack(side="left", padx=2)
tk.Radiobutton(frame_controles, text="0", variable=opcao_led, value=0, command=lambda: salvar_cmd_led(opcao_led.get())).pack(side="left")
tk.Radiobutton(frame_controles, text="1", variable=opcao_led, value=1, command=lambda: salvar_cmd_led(opcao_led.get())).pack(side="left")

btn_salvar = tk.Button(frame_controles, text="Salvar Gráficos", font=("Arial", 8, "bold"), command=lambda: salvar(fig1, fig2, fig3))
btn_salvar.pack(side="left", padx=(8, 0))


# ===================== GRÁFICO DAS RSSIS =====================
frame_rssi = tk.Frame(raiz)
frame_rssi.pack(fill="both", expand=True, padx=10, pady=1)

fig1 = Figure(figsize=(10, 2.0), dpi=100)
ax1 = fig1.add_subplot(111)
fig1.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas1 = FigureCanvasTkAgg(fig1, master=frame_rssi)
canvas1.get_tk_widget().pack(fill="both", expand=True)


# ===================== LABELS DAS SNRS =====================
frame_labels_snr = tk.Frame(raiz)
frame_labels_snr.pack(fill="x", padx=10, pady=(2, 1))

label_snr_down = tk.Label(frame_labels_snr, text="SNR DL atual: --", font=("Arial", 8, "bold"), bg=cor_snr_down, fg="white", relief="ridge", bd=2, width=22, pady=1)
label_snr_down.pack(side="left", padx=2)

label_snr_up = tk.Label(frame_labels_snr, text="SNR UL atual: --", font=("Arial", 8, "bold"), bg=cor_snr_up, fg="white", relief="ridge", bd=2, width=22, pady=1)
label_snr_up.pack(side="left", padx=2)


# ===================== GRÁFICO DAS SNRS =====================
frame_snr = tk.Frame(raiz)
frame_snr.pack(fill="both", expand=True, padx=10, pady=1)

fig2 = Figure(figsize=(10, 2.0), dpi=100)
ax2 = fig2.add_subplot(111)
fig2.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
canvas2 = FigureCanvasTkAgg(fig2, master=frame_snr)
canvas2.get_tk_widget().pack(fill="both", expand=True)


# ===================== LABEL DA PSR =====================
frame_label_psr = tk.Frame(raiz)
frame_label_psr.pack(fill="x", padx=10, pady=(2, 1))

label_psr = tk.Label(frame_label_psr, text="PSR atual: --", font=("Arial", 8, "bold"), bg=cor_psr, fg="white", relief="ridge", bd=2, width=20, pady=1)
label_psr.pack(side="left", padx=2)


# ===================== GRÁFICO DA PSR =====================
frame_psr = tk.Frame(raiz)
frame_psr.pack(fill="both", expand=True, padx=10, pady=1)

fig3 = Figure(figsize=(10, 2.0), dpi=100)
ax3 = fig3.add_subplot(111)
fig3.subplots_adjust(left=0.05, right=0.98, top=0.84, bottom=0.20)
canvas3 = FigureCanvasTkAgg(fig3, master=frame_psr)
canvas3.get_tk_widget().pack(fill="both", expand=True)


# ===================== INICIALIZAÇÃO =====================
atualizar_grafico(ax1, ax2, ax3, canvas1, canvas2, canvas3, raiz, label_down, label_up, label_snr_down, label_snr_up, label_psr)

def fechar_janela():
    if messagebox.askokcancel("Sair", "Deseja fechar o parametrizador?"):
        raiz.destroy()

raiz.protocol("WM_DELETE_WINDOW", fechar_janela)

raiz.mainloop()
