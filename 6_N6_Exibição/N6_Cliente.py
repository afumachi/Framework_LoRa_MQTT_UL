# Exibição | Cliente [Luminosidade e LED] | N6 | WissTek-IoT | Framework DL-UL
# 13/10/2026
#====== Nível 6 - Cliente ======
# Gráfico da luminosidade, da média e dos dois limiares de histerese, com o estado do LED
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.style as style
import os

style.use("ggplot")

# Pasta do Nível 4 (4_N4_Armazenamento)
PASTA_ARMAZENAMENTO = os.path.join("..", "4_N4_Armazenamento")
CAMINHO_PARAMETROS = os.path.join(PASTA_ARMAZENAMENTO, "Parametros")
CAMINHO_DADOS_PROCESSADOS = os.path.join(PASTA_ARMAZENAMENTO, "Dados_Processados")

os.makedirs(CAMINHO_PARAMETROS, exist_ok=True)
caminho_par_cliente = os.path.join(CAMINHO_PARAMETROS, "parametros_cliente.txt")

caminho_luminosidade = os.path.join(CAMINHO_DADOS_PROCESSADOS, "luminosidade.tmp")
caminho_media_luminosidade = os.path.join(CAMINHO_DADOS_PROCESSADOS, "media_luminosidade.tmp")

cor_luminosidade = "#1f77b4"
cor_media = "#ff7f0e"
cor_limiar_ligar = "#d62728"
cor_limiar_desligar = "#9467bd"
cor_led_aceso = "#e6b800"
cor_led_apagado = "#7f7f7f"

# ===================== ATUALIZA GRÁFICO =====================
def atualizar_grafico(ax1, canvas, raiz, label_lum, label_media, label_limiar, label_led):
    valores_lum = []
    valores_led = []
    valores_media = []
    limiar_ligar = None
    limiar_desligar = None

    # Lendo Luminosidade e LED
    try:
        with open(caminho_luminosidade, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        partes = linha.split()
                        valores_lum.append(float(partes[0]))
                        valores_led.append(int(partes[1]))
                    except (IndexError, ValueError):
                        pass
    except FileNotFoundError:
        pass

    # Lendo Média da Luminosidade
    try:
        with open(caminho_media_luminosidade, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        valores_media.append(float(linha))
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass

    # Lendo Limiares (Calculando o segundo limiar 50 pontos acima)
    try:
        with open(caminho_par_cliente, 'r') as f:
            limiar_ligar = int(float(f.readline().strip().replace(",", ".")))
            limiar_desligar = min(4095, limiar_ligar + 50)
    except (FileNotFoundError, ValueError):
        pass

    # Ajusta tamanhos diferentes
    if len(valores_media) < len(valores_lum):
        if len(valores_media) > 0:
            ultimo = valores_media[-1]
            while len(valores_media) < len(valores_lum):
                valores_media.append(ultimo)
        else:
            valores_media = valores_lum.copy()

    # Atualiza Labels
    if valores_lum:
        label_lum.config(text="Luminosidade atual: " + str(int(valores_lum[-1])))
    else:
        label_lum.config(text="Luminosidade atual: --")

    if valores_media:
        label_media.config(text="Média atual: " + str(round(valores_media[-1],2)))
    else:
        label_media.config(text="Média atual: --")

    if limiar_ligar is not None:
        label_limiar.config(text=f"Ligar: {limiar_ligar} | Desligar: {limiar_desligar}")
    else:
        label_limiar.config(text="Limiares: --")

    if valores_led and valores_led[-1] == 1:
        label_led.config(text="LED amarelo: ACESO", bg=cor_led_aceso)
    elif valores_led:
        label_led.config(text="LED amarelo: APAGADO", bg=cor_led_apagado)
    else:
        label_led.config(text="LED amarelo: --", bg=cor_led_apagado)

    # Gráfico
    ax1.clear()
    if valores_lum:
        ax1.plot(valores_lum, label="Luminosidade", linewidth=2, marker='o', markersize=4, color=cor_luminosidade)
        ax1.plot(valores_media, label="Média", linewidth=3, color=cor_media)
        
        x_aceso = [i for i in range(len(valores_led)) if valores_led[i] == 1]
        if x_aceso:
            ax1.scatter(x_aceso, [valores_lum[i] for i in x_aceso], label="LED aceso", s=60, color=cor_led_aceso, zorder=3)
        
        todos = valores_lum + valores_media
        if limiar_ligar is not None:
            ax1.axhline(limiar_ligar, label=f"Limiar Ligar ({limiar_ligar})", linewidth=2, linestyle="--", color=cor_limiar_ligar)
            ax1.axhline(limiar_desligar, label=f"Limiar Desligar ({limiar_desligar})", linewidth=2, linestyle=":", color=cor_limiar_desligar)
            todos = todos + [limiar_ligar, limiar_desligar]
            
        ax1.legend(loc='upper right', fontsize=9)
        val_min = min(todos)
        val_max = max(todos)
        margem = (val_max - val_min) * 0.10
        if margem == 0:
            margem = 100
        ax1.set_ylim(max(0, val_min - margem), min(4095, val_max + margem))

    ax1.set_title("Luminosidade, Média e Limiares de Histerese")
    ax1.set_ylabel("Intensidade (0-4095)")
    ax1.set_xlabel("Medidas da rodada (" + str(len(valores_lum)) + ")")

    canvas.draw()
    raiz.after(1000, atualizar_grafico, ax1, canvas, raiz, label_lum, label_media, label_limiar, label_led)

# ===================== BOTÕES =====================
def fechar():
    if messagebox.askokcancel("Sair","Deseja fechar o monitor?"):
        raiz.destroy()

def salvar(fig):
    arquivo = filedialog.asksaveasfilename(defaultextension=".png")
    if arquivo:
        fig.savefig(arquivo)

# ===================== INTERFACE =====================
raiz = tk.Tk()
raiz.title("FEE247 - NÍVEL 6 - CLIENTE")
raiz.geometry("1100x650")

frame_labels = tk.Frame(raiz)
frame_labels.pack(fill="x", padx=10, pady=10)

label_lum = tk.Label(frame_labels, text="Luminosidade atual: --", font=("Arial", 10, "bold"), bg=cor_luminosidade, fg="white", relief="ridge", bd=3, width=22, pady=8)
label_lum.pack(side="left", padx=5)

label_media = tk.Label(frame_labels, text="Média atual: --", font=("Arial", 10, "bold"), bg=cor_media, fg="white", relief="ridge", bd=3, width=18, pady=8)
label_media.pack(side="left", padx=5)

label_limiar = tk.Label(frame_labels, text="Limiares: --", font=("Arial", 10, "bold"), bg=cor_limiar_ligar, fg="white", relief="ridge", bd=3, width=24, pady=8)
label_limiar.pack(side="left", padx=5)

label_led = tk.Label(frame_labels, text="LED amarelo: --", font=("Arial", 10, "bold"), bg=cor_led_apagado, fg="white", relief="ridge", bd=3, width=20, pady=8)
label_led.pack(side="left", padx=5)

frame = tk.Frame(raiz)
frame.pack(fill="both", expand=True)

fig = Figure(figsize=(10, 5))
ax1 = fig.add_subplot(111)

canvas = FigureCanvasTkAgg(fig, master=frame)
canvas.get_tk_widget().pack(fill="both", expand=True)

btn = tk.Button(raiz, text="Salvar Gráfico", command=lambda: salvar(fig))
btn.pack(pady=5)

atualizar_grafico(ax1, canvas, raiz, label_lum, label_media, label_limiar, label_led)
raiz.protocol("WM_DELETE_WINDOW", fechar)

def fechar():
    if messagebox.askokcancel("Sair", "Deseja fechar o parametrizador?"):
            
        raiz.destroy()

raiz.protocol("WM_DELETE_WINDOW", fechar)
raiz.mainloop()

