import os
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==============================================================================
# FUNÇÕES ANALÍTICAS DA DISTRIBUIÇÃO NORMAL (SUBSTITUI SCIPY)
# ==============================================================================
def normal_pdf(x, mu, sigma):
    """Calcula a Densidade de Probabilidade (PDF) da Distribuição Normal."""
    return (1.0 / (sigma * np.sqrt(2.0 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

def normal_cdf(x, mu, sigma):
    """Calcula a Função de Distribuição Acumulada (CDF) da Distribuição Normal."""
    z = (np.asarray(x) - mu) / (sigma * np.sqrt(2.0))
    erf_vec = np.vectorize(math.erf)
    res = 0.5 * (1.0 + erf_vec(z))
    return float(res) if np.isscalar(x) else res

# ==============================================================================
# 1. LEITURA E PRÉ-PROCESSAMENTO DOS DADOS
# ==============================================================================
pasta_script = os.path.dirname(os.path.abspath(__file__))
caminho_arquivo = os.path.join(pasta_script, "medidas.xlsx")

# Lê as colunas A e B (independente do nome exato do cabeçalho)
df = pd.read_excel(caminho_arquivo, usecols=[0, 1])
df.columns = ["RSSI_Uplink", "SNR_Uplink"]

# Converte strings com vírgula decimal para float, caso o Excel exporte como texto
for col in ["RSSI_Uplink", "SNR_Uplink"]:
    if df[col].dtype == object:
        df[col] = df[col].astype(str).str.replace(",", ".").astype(float)

df = df.dropna(subset=["RSSI_Uplink"]).reset_index(drop=True)
rssi = df["RSSI_Uplink"].values
n_amostras = len(rssi)
amostras = np.arange(1, n_amostras + 1)

# ==============================================================================
# 2. CÁLCULOS DE MÉDIA MÓVEL E FAST FADING (X[n])
# ==============================================================================
# Média Móvel causal de janela k = 10 -> (1/10) * sum_{i=0}^{9} RSSI[k-i]
rssi_mm10 = pd.Series(rssi).rolling(window=10, min_periods=1).mean().values

# Fast Fading X[n] = RSSI[n] - RSSI_medio[n]
x_n = rssi - rssi_mm10

# Configuração global de estilo
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3
plt.rcParams["grid.linestyle"] = "--"

# ==============================================================================
# GRÁFICO 1: RSSI Uplink [dBm] e Média Móvel RSSI [dBm] (Janela k = 10)
# ==============================================================================
fig1, ax1 = plt.subplots(figsize=(12, 5))
ax1.plot(amostras, rssi, color="#1f77b4", alpha=0.65, linewidth=0.9, label="RSSI Uplink [dBm]")
ax1.plot(amostras, rssi_mm10, color="#d62728", linewidth=1.8, label="Média Móvel RSSI [dBm] (k = 10)")

ax1.set_title("Gráfico 1 - RSSI Uplink [dBm] e Média Móvel Deslizante (k = 10)", fontsize=12, fontweight="bold")
ax1.set_xlabel("Amostras [n]", fontsize=10)
ax1.set_ylabel("RSSI [dBm]", fontsize=10)
ax1.legend(loc="best")
fig1.tight_layout()

# ==============================================================================
# GRÁFICO 2: Fast Fading X[n] = RSSI[n] - Média Móvel[n]
# ==============================================================================
fig2, ax2 = plt.subplots(figsize=(12, 5))
ax2.plot(amostras, x_n, color="#1b7837", linewidth=0.8, label=r"$X[n] = RSSI[n] - \overline{RSSI}[n]$")
ax2.axhline(0, color="black", linestyle="--", linewidth=1, alpha=0.7)

ax2.set_title("Gráfico 2 - Componente de Variação Rápida (Fast Fading) X[n]", fontsize=12, fontweight="bold")
ax2.set_xlabel("Amostras [n]", fontsize=10)
ax2.set_ylabel("Amplitude X[n] [dB]", fontsize=10)
ax2.legend(loc="best")
fig2.tight_layout()

# ==============================================================================
# GRÁFICO 3: Histograma de X[n] e Ajuste Normal (Conforme Figura)
# ==============================================================================
fig3, ax3 = plt.subplots(figsize=(10, 5.5))

mu_x = np.mean(x_n)
sigma_x = np.std(x_n, ddof=0)
bins_x = 45

ax3.hist(
    x_n, bins=bins_x, density=True,
    color="#2ecc71", edgecolor="#1e8449", alpha=0.85,
    label="Dados (X[n])"
)

eixo_x = np.linspace(min(x_n) - 2, max(x_n) + 2, 500)
pdf_x = normal_pdf(eixo_x, mu_x, sigma_x)
ax3.plot(
    eixo_x, pdf_x, "r--", linewidth=2.2,
    label=f"Ajuste Normal ($\\mu \\approx {mu_x:.2f}$, $\\sigma = {sigma_x:.2f}$ dB)"
)

texto_box = (
    f"$\\mathbf{{\\sigma = {sigma_x:.2f}\\ dB}}$\n"
    f"(estimado)\n"
    f"────────────────\n"
    f"$\\mu \\approx {mu_x:.2f}\\ dB$"
)
ax3.text(
    0.96, 0.85, texto_box, transform=ax3.transAxes,
    fontsize=11, verticalalignment="top", horizontalalignment="right",
    bbox=dict(boxstyle="round,pad=0.6", facecolor="#eafaf1", edgecolor="#a9dfbf", linewidth=1.2)
)

ax3.set_title("Gráfico 3 - Histograma da Variável Aleatória X[n] (Fast Fading)", fontsize=12, fontweight="bold")
ax3.set_xlabel("X[n] (dB)", fontsize=11)
ax3.set_ylabel("Probabilidade (Densidade)", fontsize=11)
ax3.legend(loc="upper left", frameon=True)
fig3.tight_layout()

# ==============================================================================
# GRÁFICO 4: Painel de 5 Subgráficos (Sinal Bruto, X[n] e Desvios Padrões Móveis)
# ==============================================================================
std_n10 = pd.Series(x_n).rolling(window=10, min_periods=1).std().fillna(0).values
std_n50 = pd.Series(x_n).rolling(window=50, min_periods=1).std().fillna(0).values
std_n200 = pd.Series(x_n).rolling(window=200, min_periods=1).std().fillna(0).values

fig4, axes = plt.subplots(5, 1, figsize=(13, 12), sharex=True)

axes[0].plot(amostras, rssi, color="#1f77b4", linewidth=0.7, label="Sinal bruto")
axes[0].plot(amostras, rssi_mm10, color="#d62728", linewidth=1.3, label="Média móvel (variações lentas)")
axes[0].set_title("1. Sinal bruto (variações lentas + rápidas)", loc="left", fontsize=10, fontweight="bold")
axes[0].set_ylabel("Amplitude\n(dBm)", fontsize=9)
axes[0].legend(loc="upper right", fontsize=8)

axes[1].plot(amostras, x_n, color="#1b7837", linewidth=0.7, label="X[n] = Sinal bruto - Média móvel")
axes[1].axhline(0, color="gray", linestyle=":", linewidth=0.8)
axes[1].set_title("2. Variável aleatória (componente de variação rápida)", loc="left", fontsize=10, fontweight="bold")
axes[1].set_ylabel("Amplitude\n(dB)", fontsize=9)
axes[1].legend(loc="upper right", fontsize=8)

axes[2].plot(amostras, std_n10, color="#d62728", linewidth=0.9)
axes[2].set_title("3. Desvio padrão móvel de X[n] - Janela N = 10", loc="left", fontsize=10, fontweight="bold")
axes[2].set_ylabel("Desvio padrão\n(dB)", fontsize=9)

axes[3].plot(amostras, std_n50, color="#2ca02c", linewidth=1.1)
axes[3].set_title("4. Desvio padrão móvel de X[n] - Janela N = 50", loc="left", fontsize=10, fontweight="bold")
axes[3].set_ylabel("Desvio padrão\n(dB)", fontsize=9)

axes[4].plot(amostras, std_n200, color="#0000cc", linewidth=1.3)
axes[4].set_title("5. Desvio padrão móvel de X[n] - Janela N = 200", loc="left", fontsize=10, fontweight="bold")
axes[4].set_ylabel("Desvio padrão\n(dB)", fontsize=9)
axes[4].set_xlabel("Tempo (amostras)", fontsize=10)

fig4.suptitle("Gráfico 4 - Decomposição de Variações Lentas/Rápidas e Desvio Padrão Móvel", fontsize=13, fontweight="bold", y=0.995)
fig4.tight_layout()

# ==============================================================================
# GRÁFICO 5: Histograma da RSSI e Função de Distribuição Acumulada (CDF)
# ==============================================================================
mu_rssi = np.mean(rssi)
sigma_rssi = np.std(rssi, ddof=0)
P_sens = -130.0  # Ajuste conforme a sensibilidade do seu SF/BW

prob_falha = normal_cdf(P_sens, mu_rssi, sigma_rssi) * 100
z_p = 2.33
margem_fading = z_p * sigma_rssi

fig5, (ax5_top, ax5_bot) = plt.subplots(2, 1, figsize=(11, 9))

# --- Painel Superior: Histograma da RSSI ---
eixo_rssi = np.linspace(min(rssi) - 5, max(rssi) + 5, 500)
pdf_rssi = normal_pdf(eixo_rssi, mu_rssi, sigma_rssi)

ax5_top.hist(
    rssi, bins=35, density=True,
    color="#85c1e9", edgecolor="#2e86c1", alpha=0.85,
    label="Histograma (medidas)"
)
ax5_top.plot(
    eixo_rssi, pdf_rssi, color="#d62728", linewidth=2,
    label="Ajuste log-normal\n(gaussiana em dB)"
)
ax5_top.axvline(mu_rssi, color="black", linestyle="--", linewidth=1.5, label=f"Média $\\overline{{P}}_r = {mu_rssi:.2f}$ dBm")
ax5_top.axvline(P_sens, color="#1e8449", linestyle="--", linewidth=1.5, label=f"Sensibilidade $P_{{sens}} = {P_sens:.0f}$ dBm")

ax5_top.set_title("Gráfico 5A - Histograma da RSSI", fontsize=12, fontweight="bold")
ax5_top.set_xlabel("RSSI (dBm)", fontsize=10)
ax5_top.set_ylabel("Densidade de probabilidade", fontsize=10)
ax5_top.legend(loc="upper right", fontsize=9)

# --- Painel Inferior: Função de Distribuição Acumulada (CDF) ---
rssi_ordenado = np.sort(rssi)
cdf_empirica = np.arange(1, len(rssi_ordenado) + 1) / len(rssi_ordenado)
cdf_teorica = normal_cdf(eixo_rssi, mu_rssi, sigma_rssi)

ax5_bot.plot(rssi_ordenado, cdf_empirica, color="#2e86c1", linewidth=1.5, alpha=0.8, label="CDF Empírica (medidas)")
ax5_bot.plot(eixo_rssi, cdf_teorica, color="#d62728", linewidth=2.2, label="CDF Teórica (Ajuste Normal)")

ax5_bot.axvline(mu_rssi, color="black", linestyle="--", linewidth=1.5)
ax5_bot.axvline(P_sens, color="#1e8449", linestyle="--", linewidth=1.5)

ax5_bot.annotate(
    f"$P(RSSI < P_{{sens}}) = {prob_falha:.2f}\\%$",
    xy=(P_sens, normal_cdf(P_sens, mu_rssi, sigma_rssi)),
    xytext=(P_sens - 8, 0.25),
    color="#1e8449", fontweight="bold", fontsize=10,
    arrowprops=dict(arrowstyle="->", color="#1e8449", lw=1.5)
)

texto_cdf = (
    f"Probabilidade de falha do enlace:\n"
    f"$P(RSSI < P_{{sens}}) = {prob_falha:.2f}\\%$\n\n"
    f"Margem de fading (MF):\n"
    f"$MF = z_p \\cdot \\sigma$\n\n"
    f"Exemplo ($p = 1\\%$):\n"
    f"$z_p = 2,33$\n"
    f"$MF = 2,33 \\cdot {sigma_rssi:.2f} = {margem_fading:.2f}\\ dB$"
)
ax5_bot.text(
    0.98, 0.52, texto_cdf, transform=ax5_bot.transAxes,
    fontsize=9.5, verticalalignment="center", horizontalalignment="right",
    bbox=dict(boxstyle="round,pad=0.6", facecolor="#fdedec", edgecolor="#f5b7b1", linewidth=1.2)
)

ax5_bot.set_title("Gráfico 5B - Função de Distribuição Acumulada (CDF)", fontsize=12, fontweight="bold")
ax5_bot.set_xlabel("RSSI (dBm)", fontsize=10)
ax5_bot.set_ylabel("Probabilidade $P(RSSI \\leq x)$", fontsize=10)
ax5_bot.set_ylim(-0.02, 1.05)
ax5_bot.legend(loc="upper left", fontsize=9)

fig5.tight_layout()

# ==============================================================================
# 3. EXIBIÇÃO E EXPORTAÇÃO DOS GRÁFICOS
# ==============================================================================
fig1.savefig(os.path.join(pasta_script, "Grafico_1_RSSI_MediaMovel.png"), dpi=300)
fig2.savefig(os.path.join(pasta_script, "Grafico_2_FastFading_Xn.png"), dpi=300)
fig3.savefig(os.path.join(pasta_script, "Grafico_3_Histograma_Xn.png"), dpi=300)
fig4.savefig(os.path.join(pasta_script, "Grafico_4_DesviosPadroes_5Paineis.png"), dpi=300)
fig5.savefig(os.path.join(pasta_script, "Grafico_5_Histograma_CDF_RSSI.png"), dpi=300)

print(f"Processamento concluído! Total de amostras lidas: {n_amostras}")
print(f"RSSI Médio: {mu_rssi:.2f} dBm | Desvio Padrão RSSI: {sigma_rssi:.2f} dB")
print(f"Desvio Padrão Fast Fading X[n]: {sigma_x:.2f} dB")

plt.show()
