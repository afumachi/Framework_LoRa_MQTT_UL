#https://varun19299.github.io/ID4100-Wireless-Lab-IITM/posts/1-large-scale-fading/

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

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
# 2. CÁLCULOS DE MÉDIA MÓVEL (SLOW FADING) E FAST FADING (X[n])
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

mu_x, sigma_x = norm.fit(x_n)
bins_x = 45

ax3.hist(
    x_n, bins=bins_x, density=True,
    color="#2ecc71", edgecolor="#1e8449", alpha=0.85,
    label="Dados (X[n])"
)

eixo_x = np.linspace(min(x_n) - 2, max(x_n) + 2, 500)
pdf_x = norm.pdf(eixo_x, mu_x, sigma_x)
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
mu_rssi, sigma_rssi = norm.fit(rssi)
P_sens = -130.0  # Ajuste conforme a sensibilidade do seu SF/BW

prob_falha = norm.cdf(P_sens, loc=mu_rssi, scale=sigma_rssi) * 100
z_p = 2.33
margem_fading = z_p * sigma_rssi

fig5, (ax5_top, ax5_bot) = plt.subplots(2, 1, figsize=(11, 9))

# --- Painel Superior: Histograma da RSSI ---
eixo_rssi = np.linspace(min(rssi) - 5, max(rssi) + 5, 500)
pdf_rssi = norm.pdf(eixo_rssi, mu_rssi, sigma_rssi)

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
cdf_teorica = norm.cdf(eixo_rssi, mu_rssi, sigma_rssi)

ax5_bot.plot(rssi_ordenado, cdf_empirica, color="#2e86c1", linewidth=1.5, alpha=0.8, label="CDF Empírica (medidas)")
ax5_bot.plot(eixo_rssi, cdf_teorica, color="#d62728", linewidth=2.2, label="CDF Teórica (Ajuste Normal)")

ax5_bot.axvline(mu_rssi, color="black", linestyle="--", linewidth=1.5)
ax5_bot.axvline(P_sens, color="#1e8449", linestyle="--", linewidth=1.5)

ax5_bot.annotate(
    f"$P(RSSI < P_{{sens}}) = {prob_falha:.2f}\\%$",
    xy=(P_sens, norm.cdf(P_sens, mu_rssi, sigma_rssi)),
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
# GRÁFICO 6: Histograma RSSI com Margem de Fading MF_90 e P_90 (Conforme Figura)
# ==============================================================================
P_90 = norm.ppf(0.10, loc=mu_rssi, scale=sigma_rssi)
MF_90 = mu_rssi - P_90

fig6, ax6 = plt.subplots(figsize=(8.5, 5.5))
fig6.patch.set_facecolor("#fdf2f2")

ax6.hist(
    rssi, bins=25, density=True,
    color="#f59b9b", edgecolor="#e06666", alpha=0.75,
    label="Histograma RSSI"
)
ax6.plot(eixo_rssi, pdf_rssi, color="#e60000", linewidth=2.5, label="Curva Normal Ajustada")

ymax_6 = max(pdf_rssi) * 1.35
ax6.vlines(mu_rssi, 0, ymax_6 * 0.92, color="black", linestyle="--", linewidth=2.2)
ax6.text(
    mu_rssi + (sigma_rssi * 0.15), ymax_6 * 0.82,
    r"$\mathbf{\mu}$" + f"\n({mu_rssi:.1f} dBm)",
    color="black", fontsize=12, fontweight="bold", verticalalignment="center"
)

ax6.vlines(P_90, 0, ymax_6 * 0.72, color="#1e8449", linestyle="--", linewidth=2.2)
ax6.text(
    P_90, ymax_6 * 0.76,
    r"$\mathbf{P_{90}}$" + f"\n({P_90:.1f} dBm)",
    color="#1e8449", fontsize=12, fontweight="bold",
    horizontalalignment="center", verticalalignment="bottom"
)

ax6.text(
    0.5, 1.08,
    f"$\\mathbf{{MF_{{90}} = {MF_90:.1f}\\ dB}}$",
    transform=ax6.transAxes,
    fontsize=15, fontweight="bold", color="#1a1a1a",
    horizontalalignment="center", verticalalignment="center",
    bbox=dict(boxstyle="round,pad=0.45", facecolor="#fadbd8", edgecolor="#f1948a", linewidth=1.5)
)

ax6.set_ylim(0, ymax_6)
ax6.set_xlabel("RSSI (dBm)", fontsize=11, fontweight="bold")
ax6.set_ylabel("Densidade de probabilidade", fontsize=11, fontweight="bold")
ax6.grid(True, linestyle=":", alpha=0.4)
fig6.tight_layout()

# ==============================================================================
# GRÁFICO 7: Histogramas Cascateados de Slow Fading + Fast Fading (Prob. 90%)
# ==============================================================================
mu_slow, sigma_slow = norm.fit(rssi_mm10)
P90_slow = norm.ppf(0.10, loc=mu_slow, scale=sigma_slow)
MF_slow_90 = mu_slow - P90_slow

P90_fast_desvio = norm.ppf(0.10, loc=mu_x, scale=sigma_x)
MF_fast_90 = mu_x - P90_fast_desvio

MF_total_90 = MF_slow_90 + MF_fast_90
P90_total = mu_slow - MF_total_90

fig7, (ax7_slow, ax7_fast) = plt.subplots(2, 1, figsize=(11.5, 8.5), sharex=True)

# --- Painel Superior: Slow Fading ---
eixo_cascata = np.linspace(P90_total - 4 * sigma_x, max(rssi_mm10) + 4 * sigma_slow, 600)
pdf_slow = norm.pdf(eixo_cascata, mu_slow, sigma_slow)

ax7_slow.hist(
    rssi_mm10, bins=30, density=True,
    color="#5dade2", edgecolor="#2874a6", alpha=0.75,
    label=r"Histograma Slow Fading ($\overline{RSSI}[n]$ - Obstrução Lenta)"
)
ax7_slow.plot(eixo_cascata, pdf_slow, color="#1b4f72", linewidth=2.2, label=f"Ajuste Log-Normal ($\\sigma_{{slow}} = {sigma_slow:.2f}$ dB)")

x_fill_slow = eixo_cascata[eixo_cascata <= P90_slow]
ax7_slow.fill_between(x_fill_slow, 0, norm.pdf(x_fill_slow, mu_slow, sigma_slow), color="#e74c3c", alpha=0.45, label="Prob. Falha 10% (Confiabilidade 90%)")

ymax_s = max(pdf_slow) * 1.32
ax7_slow.axvline(mu_slow, color="black", linestyle="--", linewidth=1.8)
ax7_slow.axvline(P90_slow, color="#d35400", linestyle="--", linewidth=2.0)

ax7_slow.text(mu_slow + 0.25, ymax_s * 0.85, f"Média Path Loss\n$\\mu_{{slow}} = {mu_slow:.1f}$ dBm", fontsize=9.5, fontweight="bold")
ax7_slow.text(P90_slow - 0.25, ymax_s * 0.85, f"$P_{{90,slow}} = {P90_slow:.1f}$ dBm", fontsize=9.5, fontweight="bold", color="#d35400", ha="right")

ax7_slow.annotate("", xy=(P90_slow, ymax_s * 0.65), xytext=(mu_slow, ymax_s * 0.65), arrowprops=dict(arrowstyle="<->", color="#d35400", lw=2.0))
ax7_slow.text((mu_slow + P90_slow) / 2, ymax_s * 0.68, f"$MF_{{slow,90}} = {MF_slow_90:.2f}$ dB", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#d35400", bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#d35400", alpha=0.9))

ax7_slow.set_ylim(0, ymax_s)
ax7_slow.set_title("Gráfico 7A - Slow Fading (Large-Scale: Caminhão / Obstrução Estacionária) - Probabilidade 90%", fontsize=11.5, fontweight="bold")
ax7_slow.set_ylabel("Densidade de Probabilidade", fontsize=10)
ax7_slow.legend(loc="upper left", fontsize=8.5)

# --- Painel Inferior: Fast Fading ---
fast_deslocado = P90_slow + x_n
mu_fast_ancorado = P90_slow + mu_x
pdf_fast = norm.pdf(eixo_cascata, mu_fast_ancorado, sigma_x)

ax7_fast.hist(
    fast_deslocado, bins=35, density=True,
    color="#58d68d", edgecolor="#1e8449", alpha=0.75,
    label=r"Histograma Fast Fading ($P_{90,slow} + X[n]$ - Carro / Empilhadeira)"
)
ax7_fast.plot(eixo_cascata, pdf_fast, color="#145a32", linewidth=2.2, label=f"Ajuste Small-Scale ($\\sigma_{{fast}} = {sigma_x:.2f}$ dB)")

x_fill_fast = eixo_cascata[eixo_cascata <= P90_total]
ax7_fast.fill_between(x_fill_fast, 0, norm.pdf(x_fill_fast, mu_fast_ancorado, sigma_x), color="#e74c3c", alpha=0.45, label="Prob. Falha 10% (Confiabilidade 90%)")

ymax_f = max(pdf_fast) * 1.35
ax7_fast.axvline(P90_slow, color="#d35400", linestyle="--", linewidth=2.0)
ax7_fast.axvline(P90_total, color="#1e8449", linestyle="--", linewidth=2.2)

ax7_fast.text(P90_slow + 0.25, ymax_f * 0.85, f"Referência Slow\n$P_{{90,slow}} = {P90_slow:.1f}$ dBm", fontsize=9.5, fontweight="bold", color="#d35400")
ax7_fast.text(P90_total - 0.25, ymax_f * 0.85, f"$P_{{90,total}} = {P90_total:.1f}$ dBm", fontsize=9.5, fontweight="bold", color="#1e8449", ha="right")

ax7_fast.annotate("", xy=(P90_total, ymax_f * 0.65), xytext=(P90_slow, ymax_f * 0.65), arrowprops=dict(arrowstyle="<->", color="#1e8449", lw=2.0))
ax7_fast.text((P90_slow + P90_total) / 2, ymax_f * 0.68, f"$MF_{{fast,90}} = {MF_fast_90:.2f}$ dB", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#1e8449", bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#1e8449", alpha=0.9))

resumo_cascata = (
    f"Somatória das Margens (90%):\n"
    f"$MF_{{slow,90}} = {MF_slow_90:.2f}\\ dB$  (Large-Scale)\n"
    f"$MF_{{fast,90}} = {MF_fast_90:.2f}\\ dB$  (Small-Scale)\n"
    f"──────────────────────────\n"
    f"$MF_{{total,90}} = {MF_total_90:.2f}\\ dB$\n"
    f"$P_{{rx,min}}(90\\%) = {P90_total:.2f}\\ dBm$"
)
ax7_fast.text(
    0.02, 0.52, resumo_cascata, transform=ax7_fast.transAxes,
    fontsize=9.5, verticalalignment="center", horizontalalignment="left",
    bbox=dict(boxstyle="round,pad=0.55", facecolor="#fef9e7", edgecolor="#f7dc6f", linewidth=1.3)
)

ax7_fast.set_ylim(0, ymax_f)
ax7_fast.set_title("Gráfico 7B - Fast Fading (Small-Scale: Multipercurso Dinâmico) - Somatória de Margens (90%)", fontsize=11.5, fontweight="bold")
ax7_fast.set_xlabel("Potência Recebida / RSSI (dBm)", fontsize=10.5, fontweight="bold")
ax7_fast.set_ylabel("Densidade de Probabilidade", fontsize=10)
ax7_fast.legend(loc="upper right", fontsize=8.5)

fig7.tight_layout()

# ==============================================================================
# GRÁFICO 8: Diagrama de Enlace Analítico e Quantitativo (Baseado em Varun IITM)
# Integrando as margens calculadas do Slow Fading e Fast Fading para 90%
# ==============================================================================
fig8, ax8 = plt.subplots(figsize=(10, 8))

# Eixos e linhas de referência vertical (Potência / RSSI)
y_max_plot = mu_rssi + 5
y_min_plot = P90_total - 8

ax8.axhline(y=mu_rssi, xmin=0.1, xmax=0.9, color='black', linestyle=':', linewidth=1.2)
ax8.text(0.02, mu_rssi, f"Potência Média\n($\\mu = {mu_rssi:.1f}$ dBm)", fontsize=10, va='center', fontweight='bold')

ax8.axhline(y=P90_slow, xmin=0.1, xmax=0.9, color='#d35400', linestyle='--', linewidth=1.5)
ax8.text(0.02, P90_slow, f"Limiar Slow Fading\n($P_{{90,slow}} = {P90_slow:.1f}$ dBm)", fontsize=10, va='center', color='#d35400', fontweight='bold')

ax8.axhline(y=P90_total, xmin=0.1, xmax=0.9, color='#1e8449', linestyle='--', linewidth=1.5)
ax8.text(0.02, P90_total, f"Limiar Total (90%)\n($P_{{90,total}} = {P90_total:.1f}$ dBm)", fontsize=10, va='center', color='#1e8449', fontweight='bold')

# Curva 1: Perfil de Desvanecimento de Grande Escala (Slow Fading / Log-Normal)
y_vals_slow = np.linspace(mu_rssi - 2*sigma_slow, mu_rssi + 2*sigma_slow, 200)
x_curve_slow = 0.35 + 0.25 * norm.pdf(y_vals_slow, mu_rssi, sigma_slow) / norm.pdf(mu_rssi, mu_rssi, sigma_slow)
ax8.plot(x_curve_slow, y_vals_slow, color='#2980b9', linewidth=2.5)
ax8.fill_betweenx(y_vals_slow, 0.35, x_curve_slow, color='#85c1e9', alpha=0.3)
ax8.text(0.62, mu_rssi - 0.5, "Log-normal\nlarge-scale fading\n(Slow Fading)", fontsize=9.5, color='#1b4f72', fontweight='bold', va='center')

# Curva 2: Perfil de Desvanecimento de Pequena Escala (Fast Fading / Small-scale) ancorado em P90_slow
y_vals_fast = np.linspace(P90_slow - 2*sigma_x, P90_slow + 2*sigma_x, 200)
x_curve_fast = 0.35 + 0.25 * norm.pdf(y_vals_fast, P90_slow, sigma_x) / norm.pdf(P90_slow, P90_slow, sigma_x)
ax8.plot(x_curve_fast, y_vals_fast, color='#27ae60', linewidth=2.5)
ax8.fill_betweenx(y_vals_fast, 0.35, x_curve_fast, color='#a9dfbf', alpha=0.3)
ax8.text(0.62, P90_slow - 0.5, "Small-scale fading\n(Fast Fading X[n])", fontsize=9.5, color='#145a32', fontweight='bold', va='center')

# Setas indicando as Margens Calculadas (Cascata)
ax8.annotate("", xy=(0.28, P90_slow), xytext=(0.28, mu_rssi),
             arrowprops=dict(arrowstyle="<->", color="#d35400", lw=2.0))
ax8.text(0.24, (mu_rssi + P90_slow)/2, f"Large-Scale Margin\n$MF_{{slow,90}} = {MF_slow_90:.2f}$ dB", 
         ha='right', va='center', fontsize=9.5, fontweight='bold', color="#d35400",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#d35400", alpha=0.9))

ax8.annotate("", xy=(0.28, P90_total), xytext=(0.28, P90_slow),
             arrowprops=dict(arrowstyle="<->", color="#1e8449", lw=2.0))
ax8.text(0.24, (P90_slow + P90_total)/2, f"Small-Scale Margin\n$MF_{{fast,90}} = {MF_fast_90:.2f}$ dB", 
         ha='right', va='center', fontsize=9.5, fontweight='bold', color="#1e8449",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#1e8449", alpha=0.9))

# Caixa com a Somatória Final das Margens
resumo_grafico8 = (
    f"Somatória das Margens de Fading (90%):\n"
    f"• Large-Scale (Slow): {MF_slow_90:.2f} dB\n"
    f"• Small-Scale (Fast): {MF_fast_90:.2f} dB\n"
    f"─────────────────────────────\n"
    f"• Margem Total ($MF_{{total}}$): {MF_total_90:.2f} dB"
)
ax8.text(0.72, 0.15, resumo_grafico8, transform=ax8.transAxes,
         fontsize=10, verticalalignment='bottom', horizontalalignment='center',
         bbox=dict(boxstyle="round,pad=0.6", facecolor="#fef9e7", edgecolor="#f7dc6f", linewidth=1.5))

ax8.set_xlim(0.0, 1.0)
ax8.set_ylim(P90_total - 6, mu_rssi + 4)
ax8.set_ylabel("Nível de Potência / RSSI (dBm)", fontsize=11, fontweight='bold')
ax8.set_title("Gráfico 8 - Modelo de Enlace Analítico com Somatória de Margens de Fading (90%)", fontsize=12, fontweight='bold', pad=15)
ax8.get_xaxis().set_visible(False)  # Corrigido para 'False'
fig8.tight_layout()
'''
# ==============================================================================
# GRÁFICO 8: Diagrama de Enlace Analítico e Quantitativo (Baseado em Varun IITM)
# Integrando as margens calculadas do Slow Fading e Fast Fading para 90%
# ==============================================================================
fig8, ax8 = plt.subplots(figsize=(10, 8))

# Eixos e linhas de referência vertical (Potência / RSSI)
# Definimos faixas de potência proporcionais aos valores reais obtidos no arquivo
y_max_plot = mu_rssi + 5
y_min_plot = P90_total - 8

ax8.axhline(y=mu_rssi, xmin=0.1, xmax=0.9, color='black', linestyle=':', linewidth=1.2)
ax8.text(0.02, mu_rssi, f"Potência Média\n($\\mu = {mu_rssi:.1f}$ dBm)", fontsize=10, va='center', fontweight='bold')

ax8.axhline(y=P90_slow, xmin=0.1, xmax=0.9, color='#d35400', linestyle='--', linewidth=1.5)
ax8.text(0.02, P90_slow, f"Limiar Slow Fading\n($P_{{90,slow}} = {P90_slow:.1f}$ dBm)", fontsize=10, va='center', color='#d35400', fontweight='bold')

ax8.axhline(y=P90_total, xmin=0.1, xmax=0.9, color='#1e8449', linestyle='--', linewidth=1.5)
ax8.text(0.02, P90_total, f"Limiar Total (90%)\n($P_{{90,total}} = {P90_total:.1f}$ dBm)", fontsize=10, va='center', color='#1e8449', fontweight='bold')

# Curva 1: Perfil de Desvanecimento de Grande Escala (Slow Fading / Log-Normal)
# Desenhado deitada na vertical em torno de mu_rssi
y_vals_slow = np.linspace(mu_rssi - 2*sigma_slow, mu_rssi + 2*sigma_slow, 200)
x_curve_slow = 0.35 + 0.25 * norm.pdf(y_vals_slow, mu_rssi, sigma_slow) / norm.pdf(mu_rssi, mu_rssi, sigma_slow)
ax8.plot(x_curve_slow, y_vals_slow, color='#2980b9', linewidth=2.5)
ax8.fill_betweenx(y_vals_slow, 0.35, x_curve_slow, color='#85c1e9', alpha=0.3)
ax8.text(0.62, mu_rssi - 0.5, "Log-normal\nlarge-scale fading\n(Slow Fading)", fontsize=9.5, color='#1b4f72', fontweight='bold', va='center')

# Curva 2: Perfil de Desvanecimento de Pequena Escala (Fast Fading / Small-scale) ancorado em P90_slow
y_vals_fast = np.linspace(P90_slow - 2*sigma_x, P90_slow + 2*sigma_x, 200)
x_curve_fast = 0.35 + 0.25 * norm.pdf(y_vals_fast, P90_slow, sigma_x) / norm.pdf(P90_slow, P90_slow, sigma_x)
ax8.plot(x_curve_fast, y_vals_fast, color='#27ae60', linewidth=2.5)
ax8.fill_betweenx(y_vals_fast, 0.35, x_curve_fast, color='#a9dfbf', alpha=0.3)
ax8.text(0.62, P90_slow - 0.5, "Small-scale fading\n(Fast Fading X[n])", fontsize=9.5, color='#145a32', fontweight='bold', va='center')

# Setas indicando as Margens Calculadas (Cascata)
# Seta 1: Large-scale fading margin (MF_slow_90)
ax8.annotate("", xy=(0.28, P90_slow), xytext=(0.28, mu_rssi),
             arrowprops=dict(arrowstyle="<->", color="#d35400", lw=2.0))
ax8.text(0.24, (mu_rssi + P90_slow)/2, f"Large-Scale Margin\n$MF_{{slow,90}} = {MF_slow_90:.2f}$ dB", 
         ha='right', va='center', fontsize=9.5, fontweight='bold', color="#d35400",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#d35400", alpha=0.9))

# Seta 2: Small-scale fading margin (MF_fast_90)
ax8.annotate("", xy=(0.28, P90_total), xytext=(0.28, P90_slow),
             arrowprops=dict(arrowstyle="<->", color="#1e8449", lw=2.0))
ax8.text(0.24, (P90_slow + P90_total)/2, f"Small-Scale Margin\n$MF_{{fast,90}} = {MF_fast_90:.2f}$ dB", 
         ha='right', va='center', fontsize=9.5, fontweight='bold', color="#1e8449",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#1e8449", alpha=0.9))

# Caixa com a Somatória Final das Margens
resumo_grafico8 = (
    f"Somatória das Margens de Fading (90%):\n"
    f"• Large-Scale (Slow): {MF_slow_90:.2f} dB\n"
    f"• Small-Scale (Fast): {MF_fast_90:.2f} dB\n"
    f"─────────────────────────────\n"
    f"• Margem Total ($MF_{{total}}$): {MF_total_90:.2f} dB"
)
ax8.text(0.72, 0.15, resumo_grafico8, transform=ax8.transAxes,
         fontsize=10, verticalalignment='bottom', horizontalalignment='center',
         bbox=dict(boxstyle="round,pad=0.6", facecolor="#fef9e7", edgecolor="#f7dc6f", linewidth=1.5))

ax8.set_xlim(0.0, 1.0)
ax8.set_ylim(P90_total - 6, mu_rssi + 4)
ax8.set_ylabel("Nível de Potência / RSSI (dBm)", fontsize=11, fontweight='bold')
ax8.set_title("Gráfico 8 - Modelo de Enlace Analítico com Somatória de Margens de Fading (90%)", fontsize=12, fontweight='bold', pad=15)
ax8.get_xaxis().set_visible(False)
fig8.tight_layout()
'''
# ==============================================================================
# 3. EXIBIÇÃO E EXPORTAÇÃO DOS GRÁFICOS
# ==============================================================================
fig1.savefig(os.path.join(pasta_script, "Grafico_1_RSSI_MediaMovel.png"), dpi=300)
fig2.savefig(os.path.join(pasta_script, "Grafico_2_FastFading_Xn.png"), dpi=300)
fig3.savefig(os.path.join(pasta_script, "Grafico_3_Histograma_Xn.png"), dpi=300)
fig4.savefig(os.path.join(pasta_script, "Grafico_4_DesviosPadroes_5Paineis.png"), dpi=300)
fig5.savefig(os.path.join(pasta_script, "Grafico_5_Histograma_CDF_RSSI.png"), dpi=300)
fig6.savefig(os.path.join(pasta_script, "Grafico_6_Histograma_MF90.png"), dpi=300)
fig7.savefig(os.path.join(pasta_script, "Grafico_7_Slow_Fast_Fading_Cascata_90.png"), dpi=300)
fig8.savefig(os.path.join(pasta_script, "Grafico_8_LinkBudget_Calculado.png"), dpi=300)

print(f"Processamento concluído! Total de amostras lidas: {n_amostras}")
print(f"RSSI Médio (mu): {mu_rssi:.2f} dBm | Desvio Padrão RSSI: {sigma_rssi:.2f} dB")
print(f"Cascata Calculada 90% -> MF_slow: {MF_slow_90:.2f} dB + MF_fast: {MF_fast_90:.2f} dB = MF_total: {MF_total_90:.2f} dB")

plt.show()

'''
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

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
# 2. CÁLCULOS DE MÉDIA MÓVEL (SLOW FADING) E FAST FADING (X[n])
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

mu_x, sigma_x = norm.fit(x_n)
bins_x = 45

ax3.hist(
    x_n, bins=bins_x, density=True,
    color="#2ecc71", edgecolor="#1e8449", alpha=0.85,
    label="Dados (X[n])"
)

eixo_x = np.linspace(min(x_n) - 2, max(x_n) + 2, 500)
pdf_x = norm.pdf(eixo_x, mu_x, sigma_x)
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
mu_rssi, sigma_rssi = norm.fit(rssi)
P_sens = -130.0  # Ajuste conforme a sensibilidade do seu SF/BW

prob_falha = norm.cdf(P_sens, loc=mu_rssi, scale=sigma_rssi) * 100
z_p = 2.33
margem_fading = z_p * sigma_rssi

fig5, (ax5_top, ax5_bot) = plt.subplots(2, 1, figsize=(11, 9))

# --- Painel Superior: Histograma da RSSI ---
eixo_rssi = np.linspace(min(rssi) - 5, max(rssi) + 5, 500)
pdf_rssi = norm.pdf(eixo_rssi, mu_rssi, sigma_rssi)

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
cdf_teorica = norm.cdf(eixo_rssi, mu_rssi, sigma_rssi)

ax5_bot.plot(rssi_ordenado, cdf_empirica, color="#2e86c1", linewidth=1.5, alpha=0.8, label="CDF Empírica (medidas)")
ax5_bot.plot(eixo_rssi, cdf_teorica, color="#d62728", linewidth=2.2, label="CDF Teórica (Ajuste Normal)")

ax5_bot.axvline(mu_rssi, color="black", linestyle="--", linewidth=1.5)
ax5_bot.axvline(P_sens, color="#1e8449", linestyle="--", linewidth=1.5)

ax5_bot.annotate(
    f"$P(RSSI < P_{{sens}}) = {prob_falha:.2f}\\%$",
    xy=(P_sens, norm.cdf(P_sens, mu_rssi, sigma_rssi)),
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
# GRÁFICO 6: Histograma RSSI com Margem de Fading MF_90 e P_90 (Conforme Figura)
# ==============================================================================
P_90 = norm.ppf(0.10, loc=mu_rssi, scale=sigma_rssi)
MF_90 = mu_rssi - P_90

fig6, ax6 = plt.subplots(figsize=(8.5, 5.5))
fig6.patch.set_facecolor("#fdf2f2")

ax6.hist(
    rssi, bins=25, density=True,
    color="#f59b9b", edgecolor="#e06666", alpha=0.75,
    label="Histograma RSSI"
)
ax6.plot(eixo_rssi, pdf_rssi, color="#e60000", linewidth=2.5, label="Curva Normal Ajustada")

ymax_6 = max(pdf_rssi) * 1.35
ax6.vlines(mu_rssi, 0, ymax_6 * 0.92, color="black", linestyle="--", linewidth=2.2)
ax6.text(
    mu_rssi + (sigma_rssi * 0.15), ymax_6 * 0.82,
    r"$\mathbf{\mu}$" + f"\n({mu_rssi:.1f} dBm)",
    color="black", fontsize=12, fontweight="bold", verticalalignment="center"
)

ax6.vlines(P_90, 0, ymax_6 * 0.72, color="#1e8449", linestyle="--", linewidth=2.2)
ax6.text(
    P_90, ymax_6 * 0.76,
    r"$\mathbf{P_{90}}$" + f"\n({P_90:.1f} dBm)",
    color="#1e8449", fontsize=12, fontweight="bold",
    horizontalalignment="center", verticalalignment="bottom"
)

ax6.text(
    0.5, 1.08,
    f"$\\mathbf{{MF_{{90}} = {MF_90:.1f}\\ dB}}$",
    transform=ax6.transAxes,
    fontsize=15, fontweight="bold", color="#1a1a1a",
    horizontalalignment="center", verticalalignment="center",
    bbox=dict(boxstyle="round,pad=0.45", facecolor="#fadbd8", edgecolor="#f1948a", linewidth=1.5)
)

ax6.set_ylim(0, ymax_6)
ax6.set_xlabel("RSSI (dBm)", fontsize=11, fontweight="bold")
ax6.set_ylabel("Densidade de probabilidade", fontsize=11, fontweight="bold")
ax6.grid(True, linestyle=":", alpha=0.4)
fig6.tight_layout()

# ==============================================================================
# GRÁFICO 7: Histogramas Cascateados de Slow Fading + Fast Fading (Prob. 90%)
# ==============================================================================
mu_slow, sigma_slow = norm.fit(rssi_mm10)
P90_slow = norm.ppf(0.10, loc=mu_slow, scale=sigma_slow)
MF_slow_90 = mu_slow - P90_slow

P90_fast_desvio = norm.ppf(0.10, loc=mu_x, scale=sigma_x)
MF_fast_90 = mu_x - P90_fast_desvio

MF_total_90 = MF_slow_90 + MF_fast_90
P90_total = mu_slow - MF_total_90

fig7, (ax7_slow, ax7_fast) = plt.subplots(2, 1, figsize=(11.5, 8.5), sharex=True)

# --- Painel Superior: Slow Fading ---
eixo_cascata = np.linspace(P90_total - 4 * sigma_x, max(rssi_mm10) + 4 * sigma_slow, 600)
pdf_slow = norm.pdf(eixo_cascata, mu_slow, sigma_slow)

ax7_slow.hist(
    rssi_mm10, bins=30, density=True,
    color="#5dade2", edgecolor="#2874a6", alpha=0.75,
    label=r"Histograma Slow Fading ($\overline{RSSI}[n]$ - Obstrução Lenta)"
)
ax7_slow.plot(eixo_cascata, pdf_slow, color="#1b4f72", linewidth=2.2, label=f"Ajuste Log-Normal ($\\sigma_{{slow}} = {sigma_slow:.2f}$ dB)")

x_fill_slow = eixo_cascata[eixo_cascata <= P90_slow]
ax7_slow.fill_between(x_fill_slow, 0, norm.pdf(x_fill_slow, mu_slow, sigma_slow), color="#e74c3c", alpha=0.45, label="Prob. Falha 10% (Confiabilidade 90%)")

ymax_s = max(pdf_slow) * 1.32
ax7_slow.axvline(mu_slow, color="black", linestyle="--", linewidth=1.8)
ax7_slow.axvline(P90_slow, color="#d35400", linestyle="--", linewidth=2.0)

ax7_slow.text(mu_slow + 0.25, ymax_s * 0.85, f"Média Path Loss\n$\\mu_{{slow}} = {mu_slow:.1f}$ dBm", fontsize=9.5, fontweight="bold")
ax7_slow.text(P90_slow - 0.25, ymax_s * 0.85, f"$P_{{90,slow}} = {P90_slow:.1f}$ dBm", fontsize=9.5, fontweight="bold", color="#d35400", ha="right")

ax7_slow.annotate("", xy=(P90_slow, ymax_s * 0.65), xytext=(mu_slow, ymax_s * 0.65), arrowprops=dict(arrowstyle="<->", color="#d35400", lw=2.0))
ax7_slow.text((mu_slow + P90_slow) / 2, ymax_s * 0.68, f"$MF_{{slow,90}} = {MF_slow_90:.2f}$ dB", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#d35400", bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#d35400", alpha=0.9))

ax7_slow.set_ylim(0, ymax_s)
ax7_slow.set_title("Gráfico 7A - Slow Fading (Large-Scale: Caminhão / Obstrução Estacionária) - Probabilidade 90%", fontsize=11.5, fontweight="bold")
ax7_slow.set_ylabel("Densidade de Probabilidade", fontsize=10)
ax7_slow.legend(loc="upper left", fontsize=8.5)

# --- Painel Inferior: Fast Fading ---
fast_deslocado = P90_slow + x_n
mu_fast_ancorado = P90_slow + mu_x
pdf_fast = norm.pdf(eixo_cascata, mu_fast_ancorado, sigma_x)

ax7_fast.hist(
    fast_deslocado, bins=35, density=True,
    color="#58d68d", edgecolor="#1e8449", alpha=0.75,
    label=r"Histograma Fast Fading ($P_{90,slow} + X[n]$ - Carro / Empilhadeira)"
)
ax7_fast.plot(eixo_cascata, pdf_fast, color="#145a32", linewidth=2.2, label=f"Ajuste Small-Scale ($\\sigma_{{fast}} = {sigma_x:.2f}$ dB)")

x_fill_fast = eixo_cascata[eixo_cascata <= P90_total]
ax7_fast.fill_between(x_fill_fast, 0, norm.pdf(x_fill_fast, mu_fast_ancorado, sigma_x), color="#e74c3c", alpha=0.45, label="Prob. Falha 10% (Confiabilidade 90%)")

ymax_f = max(pdf_fast) * 1.35
ax7_fast.axvline(P90_slow, color="#d35400", linestyle="--", linewidth=2.0)
ax7_fast.axvline(P90_total, color="#1e8449", linestyle="--", linewidth=2.2)

ax7_fast.text(P90_slow + 0.25, ymax_f * 0.85, f"Referência Slow\n$P_{{90,slow}} = {P90_slow:.1f}$ dBm", fontsize=9.5, fontweight="bold", color="#d35400")
ax7_fast.text(P90_total - 0.25, ymax_f * 0.85, f"$P_{{90,total}} = {P90_total:.1f}$ dBm", fontsize=9.5, fontweight="bold", color="#1e8449", ha="right")

ax7_fast.annotate("", xy=(P90_total, ymax_f * 0.65), xytext=(P90_slow, ymax_f * 0.65), arrowprops=dict(arrowstyle="<->", color="#1e8449", lw=2.0))
ax7_fast.text((P90_slow + P90_total) / 2, ymax_f * 0.68, f"$MF_{{fast,90}} = {MF_fast_90:.2f}$ dB", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#1e8449", bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#1e8449", alpha=0.9))

resumo_cascata = (
    f"Somatória das Margens (90%):\n"
    f"$MF_{{slow,90}} = {MF_slow_90:.2f}\\ dB$  (Large-Scale)\n"
    f"$MF_{{fast,90}} = {MF_fast_90:.2f}\\ dB$  (Small-Scale)\n"
    f"──────────────────────────\n"
    f"$MF_{{total,90}} = {MF_total_90:.2f}\\ dB$\n"
    f"$P_{{rx,min}}(90\\%) = {P90_total:.2f}\\ dBm$"
)
ax7_fast.text(
    0.02, 0.52, resumo_cascata, transform=ax7_fast.transAxes,
    fontsize=9.5, verticalalignment="center", horizontalalignment="left",
    bbox=dict(boxstyle="round,pad=0.55", facecolor="#fef9e7", edgecolor="#f7dc6f", linewidth=1.3)
)

ax7_fast.set_ylim(0, ymax_f)
ax7_fast.set_title("Gráfico 7B - Fast Fading (Small-Scale: Multipercurso Dinâmico) - Somatória de Margens (90%)", fontsize=11.5, fontweight="bold")
ax7_fast.set_xlabel("Potência Recebida / RSSI (dBm)", fontsize=10.5, fontweight="bold")
ax7_fast.set_ylabel("Densidade de Probabilidade", fontsize=10)
ax7_fast.legend(loc="upper right", fontsize=8.5)

fig7.tight_layout()

# ==============================================================================
# GRÁFICO 8: Diagrama Conceitual do Modelo de Enlace (Link Budget Cascata)
# ==============================================================================
fig8, ax8 = plt.subplots(figsize=(10, 7))

# Eixos principais e linhas de referência
ax8.axhline(y=10, xmin=0.05, xmax=0.95, color='black', linewidth=1.2)
ax8.text(0.02, 9.5, "Power\ntransmitted", fontsize=10, va='top')
ax8.text(0.85, 10.2, "Distance", fontsize=10, va='bottom')

# Posições Tx e Rx
tx_x = 0.15
rx_x = 0.55
ax8.vlines(tx_x, 9.8, 10.2, color='black', linewidth=2)
ax8.text(tx_x, 10.3, "Tx", fontsize=11, fontweight='bold', ha='center')

ax8.vlines(rx_x, 0.5, 10.2, color='black', linewidth=1.5)
ax8.text(rx_x, 10.3, "Rx", fontsize=11, fontweight='bold', ha='center')

# Linha de Perda de Percurso Média (Mean Path Loss)
ax8.plot([tx_x, rx_x], [10, 5.5], color='black', linewidth=2)
ax8.text(0.32, 7.4, "Mean\npath loss", fontsize=10, ha='center', va='center')

mean_rx_y = 5.5
ax8.axhline(y=mean_rx_y, xmin=rx_x, xmax=0.85, color='black', linestyle='--', linewidth=0.8, alpha=0.5)

# Distribuição de Grande Escala (Log-normal large-scale fading)
y_ls = np.linspace(3.8, 7.2, 200)
pdf_ls = 0.12 * np.exp(-((y_ls - mean_rx_y)**2) / 0.4)
ax8.plot(rx_x + pdf_ls, y_ls, color='black', linewidth=1.8)
ax8.text(rx_x + 0.15, 6.5, "Log-normal\nlarge-scale fading", fontsize=10, va='center')

p90_slow_y = 4.2
ax8.axhline(y=p90_slow_y, xmin=rx_x, xmax=0.85, color='black', linewidth=1)

ax8.annotate("", xy=(rx_x + 0.08, mean_rx_y), xytext=(rx_x + 0.08, p90_slow_y),
             arrowprops=dict(arrowstyle="<->", color="black", lw=1.5))
ax8.text(rx_x + 0.10, (mean_rx_y + p90_slow_y)/2, "Large-scale\nfading margin", fontsize=9, va='center', ha='left')

# Distribuição de Pequena Escala (Small-scale fading) ancorada em P90_slow
y_ss = np.linspace(1.8, 5.2, 200)
pdf_ss = 0.12 * np.exp(-((y_ss - p90_slow_y)**2) / 0.35)
ax8.plot(rx_x + pdf_ss, y_ss, color='black', linewidth=1.8)

p90_total_y = 2.5
ax8.axhline(y=p90_total_y, xmin=rx_x, xmax=0.85, color='black', linewidth=1)

ax8.annotate("", xy=(rx_x + 0.08, p90_slow_y), xytext=(rx_x + 0.08, p90_total_y),
             arrowprops=dict(arrowstyle="<->", color="black", lw=1.5))
ax8.text(rx_x + 0.10, (p90_slow_y + p90_total_y)/2, "Small-scale\nfading margin", fontsize=9, va='center', ha='left')

# Caudas hachuradas (probabilidade de falha ~1-2%)
y_fill1 = np.linspace(p90_slow_y - 0.4, p90_slow_y, 50)
x_fill1 = 0.12 * np.exp(-((y_fill1 - mean_rx_y)**2) / 0.4)
ax8.fill_betweenx(y_fill1, rx_x, rx_x + x_fill1, color='gray', hatch='//', alpha=0.6)
ax8.text(rx_x - 0.02, p90_slow_y - 0.2, "≈1 ~ 2%", fontsize=9, ha='right', va='center')

y_fill2 = np.linspace(p90_total_y - 0.4, p90_total_y, 50)
x_fill2 = 0.12 * np.exp(-((y_fill2 - p90_slow_y)**2) / 0.35)
ax8.fill_betweenx(y_fill2, rx_x, rx_x + x_fill2, color='gray', hatch='//', alpha=0.6)
ax8.text(rx_x - 0.02, p90_total_y - 0.2, "≈1 ~ 2%", fontsize=9, ha='right', va='center')

ax8.axhline(y=1.0, xmin=0.05, xmax=0.95, color='black', linewidth=1.2)
ax8.text(0.02, 1.0, "Power\nreceived", fontsize=10, va='center')

ax8.set_xlim(0, 1.0)
ax8.set_ylim(0, 11)
ax8.axis('off')
ax8.set_title("Gráfico 8 - Modelo Conceitual de Margens de Enlace (Link Budget)", fontsize=12, fontweight='bold', pad=15)
fig8.tight_layout()

# ==============================================================================
# 3. EXIBIÇÃO E EXPORTAÇÃO DOS GRÁFICOS
# ==============================================================================
fig1.savefig(os.path.join(pasta_script, "Grafico_1_RSSI_MediaMovel.png"), dpi=300)
fig2.savefig(os.path.join(pasta_script, "Grafico_2_FastFading_Xn.png"), dpi=300)
fig3.savefig(os.path.join(pasta_script, "Grafico_3_Histograma_Xn.png"), dpi=300)
fig4.savefig(os.path.join(pasta_script, "Grafico_4_DesviosPadroes_5Paineis.png"), dpi=300)
fig5.savefig(os.path.join(pasta_script, "Grafico_5_Histograma_CDF_RSSI.png"), dpi=300)
fig6.savefig(os.path.join(pasta_script, "Grafico_6_Histograma_MF90.png"), dpi=300)
fig7.savefig(os.path.join(pasta_script, "Grafico_7_Slow_Fast_Fading_Cascata_90.png"), dpi=300)
fig8.savefig(os.path.join(pasta_script, "Grafico_8_Modelo_LinkBudget.png"), dpi=300)

print(f"Processamento concluído! Total de amostras lidas: {n_amostras}")
print(f"RSSI Médio (mu): {mu_rssi:.2f} dBm | Desvio Padrão RSSI: {sigma_rssi:.2f} dB")
print(f"Limiar P_90 (Global): {P_90:.2f} dBm | Margem Global MF_90: {MF_90:.2f} dB")
print(f"Cascata 90% -> MF_slow: {MF_slow_90:.2f} dB + MF_fast: {MF_fast_90:.2f} dB = MF_total: {MF_total_90:.2f} dB")

plt.show()
'''
'''
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

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
# 2. CÁLCULOS DE MÉDIA MÓVEL (SLOW FADING) E FAST FADING (X[n])
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

mu_x, sigma_x = norm.fit(x_n)
bins_x = 45

ax3.hist(
    x_n, bins=bins_x, density=True,
    color="#2ecc71", edgecolor="#1e8449", alpha=0.85,
    label="Dados (X[n])"
)

eixo_x = np.linspace(min(x_n) - 2, max(x_n) + 2, 500)
pdf_x = norm.pdf(eixo_x, mu_x, sigma_x)
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
mu_rssi, sigma_rssi = norm.fit(rssi)
P_sens = -130.0  # Ajuste conforme a sensibilidade do seu SF/BW

prob_falha = norm.cdf(P_sens, loc=mu_rssi, scale=sigma_rssi) * 100
z_p = 2.33
margem_fading = z_p * sigma_rssi

fig5, (ax5_top, ax5_bot) = plt.subplots(2, 1, figsize=(11, 9))

# --- Painel Superior: Histograma da RSSI ---
eixo_rssi = np.linspace(min(rssi) - 5, max(rssi) + 5, 500)
pdf_rssi = norm.pdf(eixo_rssi, mu_rssi, sigma_rssi)

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
cdf_teorica = norm.cdf(eixo_rssi, mu_rssi, sigma_rssi)

ax5_bot.plot(rssi_ordenado, cdf_empirica, color="#2e86c1", linewidth=1.5, alpha=0.8, label="CDF Empírica (medidas)")
ax5_bot.plot(eixo_rssi, cdf_teorica, color="#d62728", linewidth=2.2, label="CDF Teórica (Ajuste Normal)")

ax5_bot.axvline(mu_rssi, color="black", linestyle="--", linewidth=1.5)
ax5_bot.axvline(P_sens, color="#1e8449", linestyle="--", linewidth=1.5)

ax5_bot.annotate(
    f"$P(RSSI < P_{{sens}}) = {prob_falha:.2f}\\%$",
    xy=(P_sens, norm.cdf(P_sens, mu_rssi, sigma_rssi)),
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
# GRÁFICO 6: Histograma RSSI com Margem de Fading MF_90 e P_90 (Conforme Figura)
# ==============================================================================
P_90 = norm.ppf(0.10, loc=mu_rssi, scale=sigma_rssi)
MF_90 = mu_rssi - P_90

fig6, ax6 = plt.subplots(figsize=(8.5, 5.5))
fig6.patch.set_facecolor("#fdf2f2")

ax6.hist(
    rssi, bins=25, density=True,
    color="#f59b9b", edgecolor="#e06666", alpha=0.75,
    label="Histograma RSSI"
)
ax6.plot(eixo_rssi, pdf_rssi, color="#e60000", linewidth=2.5, label="Curva Normal Ajustada")

ymax_6 = max(pdf_rssi) * 1.35
ax6.vlines(mu_rssi, 0, ymax_6 * 0.92, color="black", linestyle="--", linewidth=2.2)
ax6.text(
    mu_rssi + (sigma_rssi * 0.15), ymax_6 * 0.82,
    r"$\mathbf{\mu}$" + f"\n({mu_rssi:.1f} dBm)",
    color="black", fontsize=12, fontweight="bold", verticalalignment="center"
)

ax6.vlines(P_90, 0, ymax_6 * 0.72, color="#1e8449", linestyle="--", linewidth=2.2)
ax6.text(
    P_90, ymax_6 * 0.76,
    r"$\mathbf{P_{90}}$" + f"\n({P_90:.1f} dBm)",
    color="#1e8449", fontsize=12, fontweight="bold",
    horizontalalignment="center", verticalalignment="bottom"
)

ax6.text(
    0.5, 1.08,
    f"$\\mathbf{{MF_{{90}} = {MF_90:.1f}\\ dB}}$",
    transform=ax6.transAxes,
    fontsize=15, fontweight="bold", color="#1a1a1a",
    horizontalalignment="center", verticalalignment="center",
    bbox=dict(boxstyle="round,pad=0.45", facecolor="#fadbd8", edgecolor="#f1948a", linewidth=1.5)
)

ax6.set_ylim(0, ymax_6)
ax6.set_xlabel("RSSI (dBm)", fontsize=11, fontweight="bold")
ax6.set_ylabel("Densidade de probabilidade", fontsize=11, fontweight="bold")
ax6.grid(True, linestyle=":", alpha=0.4)
fig6.tight_layout()

# ==============================================================================
# GRÁFICO 7: Histogramas Cascateados de Slow Fading + Fast Fading (Prob. 90%)
# Baseado em: varun19299.github.io/ID4100-Wireless-Lab-IITM/posts/1-large-scale-fading/
# ==============================================================================
# 1) Ajuste estatístico do Slow Fading (Média Móvel: obstrução caminhão/parado)
mu_slow, sigma_slow = norm.fit(rssi_mm10)
P90_slow = norm.ppf(0.10, loc=mu_slow, scale=sigma_slow)
MF_slow_90 = mu_slow - P90_slow  # Margem Large-Scale (Slow Fading) para 90%

# 2) Ajuste estatístico do Fast Fading (X[n]: multipercurso carro/empilhadeira)
# Centrado no nível de referência P90_slow para compor a cascata de margens
P90_fast_desvio = norm.ppf(0.10, loc=mu_x, scale=sigma_x)
MF_fast_90 = mu_x - P90_fast_desvio  # Margem Small-Scale (Fast Fading) para 90%

# 3) Somatória das Margens de Fading e Potência Mínima Garantida (90% em cada estágio)
MF_total_90 = MF_slow_90 + MF_fast_90
P90_total = mu_slow - MF_total_90  # Equivalente a P90_slow - MF_fast_90

fig7, (ax7_slow, ax7_fast) = plt.subplots(2, 1, figsize=(11.5, 8.5), sharex=True)

# --- Painel Superior: Slow Fading (Log-Normal Large-Scale Fading) ---
eixo_cascata = np.linspace(P90_total - 4 * sigma_x, max(rssi_mm10) + 4 * sigma_slow, 600)
pdf_slow = norm.pdf(eixo_cascata, mu_slow, sigma_slow)

ax7_slow.hist(
    rssi_mm10, bins=30, density=True,
    color="#5dade2", edgecolor="#2874a6", alpha=0.75,
    label=r"Histograma Slow Fading ($\overline{RSSI}[n]$ - Obstrução Lenta)"
)
ax7_slow.plot(eixo_cascata, pdf_slow, color="#1b4f72", linewidth=2.2, label=f"Ajuste Log-Normal ($\\sigma_{{slow}} = {sigma_slow:.2f}$ dB)")

# Área sombreada da cauda de 10% de falha (90% de confiabilidade acima de P90_slow)
x_fill_slow = eixo_cascata[eixo_cascata <= P90_slow]
ax7_slow.fill_between(x_fill_slow, 0, norm.pdf(x_fill_slow, mu_slow, sigma_slow), color="#e74c3c", alpha=0.45, label="Prob. Falha 10% (Confiabilidade 90%)")

# Linhas verticais e seta da Margem de Slow Fading
ymax_s = max(pdf_slow) * 1.32
ax7_slow.axvline(mu_slow, color="black", linestyle="--", linewidth=1.8)
ax7_slow.axvline(P90_slow, color="#d35400", linestyle="--", linewidth=2.0)

ax7_slow.text(mu_slow + 0.25, ymax_s * 0.85, f"Média Path Loss\n$\\mu_{{slow}} = {mu_slow:.1f}$ dBm", fontsize=9.5, fontweight="bold")
ax7_slow.text(P90_slow - 0.25, ymax_s * 0.85, f"$P_{{90,slow}} = {P90_slow:.1f}$ dBm", fontsize=9.5, fontweight="bold", color="#d35400", ha="right")

# Seta horizontal indicando MF_slow_90
ax7_slow.annotate(
    "", xy=(P90_slow, ymax_s * 0.65), xytext=(mu_slow, ymax_s * 0.65),
    arrowprops=dict(arrowstyle="<->", color="#d35400", lw=2.0)
)
ax7_slow.text(
    (mu_slow + P90_slow) / 2, ymax_s * 0.68,
    f"$MF_{{slow,90}} = {MF_slow_90:.2f}$ dB",
    ha="center", va="bottom", fontsize=10, fontweight="bold", color="#d35400",
    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#d35400", alpha=0.9)
)

ax7_slow.set_ylim(0, ymax_s)
ax7_slow.set_title("Gráfico 7A - Slow Fading (Large-Scale: Caminhão / Obstrução Estacionária) - Probabilidade 90%", fontsize=11.5, fontweight="bold")
ax7_slow.set_ylabel("Densidade de Probabilidade", fontsize=10)
ax7_slow.legend(loc="upper left", fontsize=8.5)

# --- Painel Inferior: Fast Fading (Small-Scale Fading) ancorado em P90_slow ---
# Desloca X[n] para o patamar de P90_slow para visualizar a cascata de margens
fast_deslocado = P90_slow + x_n
mu_fast_ancorado = P90_slow + mu_x
pdf_fast = norm.pdf(eixo_cascata, mu_fast_ancorado, sigma_x)

ax7_fast.hist(
    fast_deslocado, bins=35, density=True,
    color="#58d68d", edgecolor="#1e8449", alpha=0.75,
    label=r"Histograma Fast Fading ($P_{90,slow} + X[n]$ - Carro / Empilhadeira)"
)
ax7_fast.plot(eixo_cascata, pdf_fast, color="#145a32", linewidth=2.2, label=f"Ajuste Small-Scale ($\\sigma_{{fast}} = {sigma_x:.2f}$ dB)")

# Área sombreada da cauda de 10% do Fast Fading
x_fill_fast = eixo_cascata[eixo_cascata <= P90_total]
ax7_fast.fill_between(x_fill_fast, 0, norm.pdf(x_fill_fast, mu_fast_ancorado, sigma_x), color="#e74c3c", alpha=0.45, label="Prob. Falha 10% (Confiabilidade 90%)")

ymax_f = max(pdf_fast) * 1.35
ax7_fast.axvline(P90_slow, color="#d35400", linestyle="--", linewidth=2.0)
ax7_fast.axvline(P90_total, color="#1e8449", linestyle="--", linewidth=2.2)

ax7_fast.text(P90_slow + 0.25, ymax_f * 0.85, f"Referência Slow\n$P_{{90,slow}} = {P90_slow:.1f}$ dBm", fontsize=9.5, fontweight="bold", color="#d35400")
ax7_fast.text(P90_total - 0.25, ymax_f * 0.85, f"$P_{{90,total}} = {P90_total:.1f}$ dBm", fontsize=9.5, fontweight="bold", color="#1e8449", ha="right")

# Seta horizontal indicando MF_fast_90
ax7_fast.annotate(
    "", xy=(P90_total, ymax_f * 0.65), xytext=(P90_slow, ymax_f * 0.65),
    arrowprops=dict(arrowstyle="<->", color="#1e8449", lw=2.0)
)
ax7_fast.text(
    (P90_slow + P90_total) / 2, ymax_f * 0.68,
    f"$MF_{{fast,90}} = {MF_fast_90:.2f}$ dB",
    ha="center", va="bottom", fontsize=10, fontweight="bold", color="#1e8449",
    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#1e8449", alpha=0.9)
)

# Quadro resumo da Somatória das Margens de Fading
resumo_cascata = (
    f"Somatória das Margens (90%):\n"
    f"$MF_{{slow,90}} = {MF_slow_90:.2f}\\ dB$  (Large-Scale)\n"
    f"$MF_{{fast,90}} = {MF_fast_90:.2f}\\ dB$  (Small-Scale)\n"
    f"──────────────────────────\n"
    f"$MF_{{total,90}} = {MF_total_90:.2f}\\ dB$\n"
    f"$P_{{rx,min}}(90\\%) = {P90_total:.2f}\\ dBm$"
)
ax7_fast.text(
    0.02, 0.52, resumo_cascata, transform=ax7_fast.transAxes,
    fontsize=9.5, verticalalignment="center", horizontalalignment="left",
    bbox=dict(boxstyle="round,pad=0.55", facecolor="#fef9e7", edgecolor="#f7dc6f", linewidth=1.3)
)

ax7_fast.set_ylim(0, ymax_f)
ax7_fast.set_title("Gráfico 7B - Fast Fading (Small-Scale: Multipercurso Dinâmico) - Somatória de Margens (90%)", fontsize=11.5, fontweight="bold")
ax7_fast.set_xlabel("Potência Recebida / RSSI (dBm)", fontsize=10.5, fontweight="bold")
ax7_fast.set_ylabel("Densidade de Probabilidade", fontsize=10)
ax7_fast.legend(loc="upper right", fontsize=8.5)

fig7.tight_layout()

# ==============================================================================
# 3. EXIBIÇÃO E EXPORTAÇÃO DOS GRÁFICOS
# ==============================================================================
fig1.savefig(os.path.join(pasta_script, "Grafico_1_RSSI_MediaMovel.png"), dpi=300)
fig2.savefig(os.path.join(pasta_script, "Grafico_2_FastFading_Xn.png"), dpi=300)
fig3.savefig(os.path.join(pasta_script, "Grafico_3_Histograma_Xn.png"), dpi=300)
fig4.savefig(os.path.join(pasta_script, "Grafico_4_DesviosPadroes_5Paineis.png"), dpi=300)
fig5.savefig(os.path.join(pasta_script, "Grafico_5_Histograma_CDF_RSSI.png"), dpi=300)
fig6.savefig(os.path.join(pasta_script, "Grafico_6_Histograma_MF90.png"), dpi=300)
fig7.savefig(os.path.join(pasta_script, "Grafico_7_Slow_Fast_Fading_Cascata_90.png"), dpi=300)

print(f"Processamento concluído! Total de amostras lidas: {n_amostras}")
print(f"RSSI Médio (mu): {mu_rssi:.2f} dBm | Desvio Padrão RSSI: {sigma_rssi:.2f} dB")
print(f"Limiar P_90 (Global): {P_90:.2f} dBm | Margem Global MF_90: {MF_90:.2f} dB")
print(f"Cascata 90% -> MF_slow: {MF_slow_90:.2f} dB + MF_fast: {MF_fast_90:.2f} dB = MF_total: {MF_total_90:.2f} dB")

plt.show()

'''
'''

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

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

mu_x, sigma_x = norm.fit(x_n)
bins_x = 45

ax3.hist(
    x_n, bins=bins_x, density=True,
    color="#2ecc71", edgecolor="#1e8449", alpha=0.85,
    label="Dados (X[n])"
)

eixo_x = np.linspace(min(x_n) - 2, max(x_n) + 2, 500)
pdf_x = norm.pdf(eixo_x, mu_x, sigma_x)
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
mu_rssi, sigma_rssi = norm.fit(rssi)
P_sens = -130.0  # Ajuste conforme a sensibilidade do seu SF/BW

prob_falha = norm.cdf(P_sens, loc=mu_rssi, scale=sigma_rssi) * 100
z_p = 2.33
margem_fading = z_p * sigma_rssi

fig5, (ax5_top, ax5_bot) = plt.subplots(2, 1, figsize=(11, 9))

# --- Painel Superior: Histograma da RSSI ---
eixo_rssi = np.linspace(min(rssi) - 5, max(rssi) + 5, 500)
pdf_rssi = norm.pdf(eixo_rssi, mu_rssi, sigma_rssi)

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
cdf_teorica = norm.cdf(eixo_rssi, mu_rssi, sigma_rssi)

ax5_bot.plot(rssi_ordenado, cdf_empirica, color="#2e86c1", linewidth=1.5, alpha=0.8, label="CDF Empírica (medidas)")
ax5_bot.plot(eixo_rssi, cdf_teorica, color="#d62728", linewidth=2.2, label="CDF Teórica (Ajuste Normal)")

ax5_bot.axvline(mu_rssi, color="black", linestyle="--", linewidth=1.5)
ax5_bot.axvline(P_sens, color="#1e8449", linestyle="--", linewidth=1.5)

ax5_bot.annotate(
    f"$P(RSSI < P_{{sens}}) = {prob_falha:.2f}\\%$",
    xy=(P_sens, norm.cdf(P_sens, mu_rssi, sigma_rssi)),
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
# GRÁFICO 6: Histograma RSSI com Margem de Fading MF_90 e P_90 (Conforme Figura)
# ==============================================================================
# P_90: Nível de potência superado em 90% do tempo (percentil 10% da distribuição)
P_90 = norm.ppf(0.10, loc=mu_rssi, scale=sigma_rssi)
MF_90 = mu_rssi - P_90  # Margem de fading para 90% de confiabilidade (z_90 = 1.2816 * sigma)

fig6, ax6 = plt.subplots(figsize=(8.5, 5.5))
fig6.patch.set_facecolor("#fdf2f2")  # Fundo rosado suave como na figura de referência

# Histograma em tons de vermelho/salmão
ax6.hist(
    rssi, bins=25, density=True,
    color="#f59b9b", edgecolor="#e06666", alpha=0.75,
    label="Histograma RSSI"
)

# Curva PDF ajustada em vermelho forte
ax6.plot(eixo_rssi, pdf_rssi, color="#e60000", linewidth=2.5, label="Curva Normal Ajustada")

# Linha tracejada preta na média (mu)
ymax_6 = max(pdf_rssi) * 1.35
ax6.vlines(mu_rssi, 0, ymax_6 * 0.92, color="black", linestyle="--", linewidth=2.2)
ax6.text(
    mu_rssi + (sigma_rssi * 0.15), ymax_6 * 0.82,
    r"$\mathbf{\mu}$" + f"\n({mu_rssi:.1f} dBm)",
    color="black", fontsize=12, fontweight="bold", verticalalignment="center"
)

# Linha tracejada verde em P_90
ax6.vlines(P_90, 0, ymax_6 * 0.72, color="#1e8449", linestyle="--", linewidth=2.2)
ax6.text(
    P_90, ymax_6 * 0.76,
    r"$\mathbf{P_{90}}$" + f"\n({P_90:.1f} dBm)",
    color="#1e8449", fontsize=12, fontweight="bold",
    horizontalalignment="center", verticalalignment="bottom"
)

# Caixa de destaque no topo com MF_90
ax6.text(
    0.5, 1.08,
    f"$\\mathbf{{MF_{{90}} = {MF_90:.1f}\\ dB}}$",
    transform=ax6.transAxes,
    fontsize=15, fontweight="bold", color="#1a1a1a",
    horizontalalignment="center", verticalalignment="center",
    bbox=dict(boxstyle="round,pad=0.45", facecolor="#fadbd8", edgecolor="#f1948a", linewidth=1.5)
)

ax6.set_ylim(0, ymax_6)
ax6.set_xlabel("RSSI (dBm)", fontsize=11, fontweight="bold")
ax6.set_ylabel("Densidade de probabilidade", fontsize=11, fontweight="bold")
ax6.grid(True, linestyle=":", alpha=0.4)
fig6.tight_layout()

# ==============================================================================
# 3. EXIBIÇÃO E EXPORTAÇÃO DOS GRÁFICOS
# ==============================================================================
fig1.savefig(os.path.join(pasta_script, "Grafico_1_RSSI_MediaMovel.png"), dpi=300)
fig2.savefig(os.path.join(pasta_script, "Grafico_2_FastFading_Xn.png"), dpi=300)
fig3.savefig(os.path.join(pasta_script, "Grafico_3_Histograma_Xn.png"), dpi=300)
fig4.savefig(os.path.join(pasta_script, "Grafico_4_DesviosPadroes_5Paineis.png"), dpi=300)
fig5.savefig(os.path.join(pasta_script, "Grafico_5_Histograma_CDF_RSSI.png"), dpi=300)
fig6.savefig(os.path.join(pasta_script, "Grafico_6_Histograma_MF90.png"), dpi=300)

print(f"Processamento concluído! Total de amostras lidas: {n_amostras}")
print(f"RSSI Médio (mu): {mu_rssi:.2f} dBm | Desvio Padrão RSSI: {sigma_rssi:.2f} dB")
print(f"Limiar P_90: {P_90:.2f} dBm | Margem de Fading MF_90: {MF_90:.2f} dB")
print(f"Desvio Padrão Fast Fading X[n]: {sigma_x:.2f} dB")

plt.show()

'''
'''
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# ==============================================================================
# 1. LEITURA E PRÉ-PROCESSAMENTO DOS DADOS
# ==============================================================================
# Garante que o arquivo seja buscado na mesma pasta onde o script está salvo
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
# Equação 1: Média Móvel causal de janela k = 10 -> (1/10) * sum_{i=0}^{9} RSSI[k-i]
# min_periods=10 faz os 9 primeiros pontos serem NaN (ou min_periods=1 para preencher desde o início)
rssi_mm10 = pd.Series(rssi).rolling(window=10, min_periods=1).mean().values

# Equação 2: Fast Fading X[n] = RSSI[n] - RSSI_medio[n]
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

mu_x, sigma_x = norm.fit(x_n)
bins_x = 45

# Histograma normalizado para densidade de probabilidade
ax3.hist(
    x_n, bins=bins_x, density=True,
    color="#2ecc71", edgecolor="#1e8449", alpha=0.85,
    label="Dados (X[n])"
)

# Curva Gaussiana teórica ajustada
eixo_x = np.linspace(min(x_n) - 2, max(x_n) + 2, 500)
pdf_x = norm.pdf(eixo_x, mu_x, sigma_x)
ax3.plot(
    eixo_x, pdf_x, "r--", linewidth=2.2,
    label=f"Ajuste Normal ($\\mu \\approx {mu_x:.2f}$, $\\sigma = {sigma_x:.2f}$ dB)"
)

# Caixa de texto informativa no canto superior direito (estilo da figura)
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
# Cálculo dos desvios padrões móveis com janelas N = 10, 50 e 200
std_n10 = pd.Series(x_n).rolling(window=10, min_periods=1).std().fillna(0).values
std_n50 = pd.Series(x_n).rolling(window=50, min_periods=1).std().fillna(0).values
std_n200 = pd.Series(x_n).rolling(window=200, min_periods=1).std().fillna(0).values

fig4, axes = plt.subplots(5, 1, figsize=(13, 12), sharex=True)

# Subplot 1: Sinal bruto + Média móvel
axes[0].plot(amostras, rssi, color="#1f77b4", linewidth=0.7, label="Sinal bruto")
axes[0].plot(amostras, rssi_mm10, color="#d62728", linewidth=1.3, label="Média móvel (variações lentas)")
axes[0].set_title("1. Sinal bruto (variações lentas + rápidas)", loc="left", fontsize=10, fontweight="bold")
axes[0].set_ylabel("Amplitude\n(dBm)", fontsize=9)
axes[0].legend(loc="upper right", fontsize=8)

# Subplot 2: Variável aleatória X[n]
axes[1].plot(amostras, x_n, color="#1b7837", linewidth=0.7, label="X[n] = Sinal bruto - Média móvel")
axes[1].axhline(0, color="gray", linestyle=":", linewidth=0.8)
axes[1].set_title("2. Variável aleatória (componente de variação rápida)", loc="left", fontsize=10, fontweight="bold")
axes[1].set_ylabel("Amplitude\n(dB)", fontsize=9)
axes[1].legend(loc="upper right", fontsize=8)

# Subplot 3: Desvio padrão móvel Janela N = 10
axes[2].plot(amostras, std_n10, color="#d62728", linewidth=0.9)
axes[2].set_title("3. Desvio padrão móvel de X[n] - Janela N = 10", loc="left", fontsize=10, fontweight="bold")
axes[2].set_ylabel("Desvio padrão\n(dB)", fontsize=9)

# Subplot 4: Desvio padrão móvel Janela N = 50
axes[3].plot(amostras, std_n50, color="#2ca02c", linewidth=1.1)
axes[3].set_title("4. Desvio padrão móvel de X[n] - Janela N = 50", loc="left", fontsize=10, fontweight="bold")
axes[3].set_ylabel("Desvio padrão\n(dB)", fontsize=9)

# Subplot 5: Desvio padrão móvel Janela N = 200
axes[4].plot(amostras, std_n200, color="#0000cc", linewidth=1.3)
axes[4].set_title("5. Desvio padrão móvel de X[n] - Janela N = 200", loc="left", fontsize=10, fontweight="bold")
axes[4].set_ylabel("Desvio padrão\n(dB)", fontsize=9)
axes[4].set_xlabel("Tempo (amostras)", fontsize=10)

fig4.suptitle("Gráfico 4 - Decomposição de Variações Lentas/Rápidas e Desvio Padrão Móvel", fontsize=13, fontweight="bold", y=0.995)
fig4.tight_layout()

# ==============================================================================
# GRÁFICO 5: Histograma da RSSI e Função de Distribuição Acumulada (CDF)
# ==============================================================================
# Parâmetros estatísticos do RSSI e Sensibilidade do Receptor (ex: LoRa SF12 = -137 dBm ou SF7 = -123 dBm)
mu_rssi, sigma_rssi = norm.fit(rssi)
P_sens = -130.0  # Ajuste este valor conforme o SF/BW do seu enlace LoRa (ex: -125, -130, -137 dBm)

# Probabilidade de falha do enlace P(RSSI < P_sens) usando a distribuição normal ajustada
prob_falha = norm.cdf(P_sens, loc=mu_rssi, scale=sigma_rssi) * 100
# Margem de fading para 1% de indisponibilidade (p = 1% -> z_p = 2.33)
z_p = 2.33
margem_fading = z_p * sigma_rssi

fig5, (ax5_top, ax5_bot) = plt.subplots(2, 1, figsize=(11, 9))

# --- Painel Superior: Histograma da RSSI ---
eixo_rssi = np.linspace(min(rssi) - 5, max(rssi) + 5, 500)
pdf_rssi = norm.pdf(eixo_rssi, mu_rssi, sigma_rssi)

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
# CDF Empírica (dados reais ordenados) + CDF Teórica (Normal ajustada)
rssi_ordenado = np.sort(rssi)
cdf_empirica = np.arange(1, len(rssi_ordenado) + 1) / len(rssi_ordenado)
cdf_teorica = norm.cdf(eixo_rssi, mu_rssi, sigma_rssi)

ax5_bot.plot(rssi_ordenado, cdf_empirica, color="#2e86c1", linewidth=1.5, alpha=0.8, label="CDF Empírica (medidas)")
ax5_bot.plot(eixo_rssi, cdf_teorica, color="#d62728", linewidth=2.2, label="CDF Teórica (Ajuste Normal)")

ax5_bot.axvline(mu_rssi, color="black", linestyle="--", linewidth=1.5)
ax5_bot.axvline(P_sens, color="#1e8449", linestyle="--", linewidth=1.5)

# Anotação da probabilidade de falha P(RSSI < P_sens)
ax5_bot.annotate(
    f"$P(RSSI < P_{{sens}}) = {prob_falha:.2f}\\%$",
    xy=(P_sens, norm.cdf(P_sens, mu_rssi, sigma_rssi)),
    xytext=(P_sens - 8, 0.25),
    color="#1e8449", fontweight="bold", fontsize=10,
    arrowprops=dict(arrowstyle="->", color="#1e8449", lw=1.5)
)

# Caixa de cálculo de Margem de Fading e Falha (estilo da figura)
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
# Salva automaticamente todas as figuras em alta resolução na mesma pasta
fig1.savefig(os.path.join(pasta_script, "Grafico_1_RSSI_MediaMovel.png"), dpi=300)
fig2.savefig(os.path.join(pasta_script, "Grafico_2_FastFading_Xn.png"), dpi=300)
fig3.savefig(os.path.join(pasta_script, "Grafico_3_Histograma_Xn.png"), dpi=300)
fig4.savefig(os.path.join(pasta_script, "Grafico_4_DesviosPadroes_5Paineis.png"), dpi=300)
fig5.savefig(os.path.join(pasta_script, "Grafico_5_Histograma_CDF_RSSI.png"), dpi=300)

print(f"Processamento concluído! Total de amostras lidas: {n_amostras}")
print(f"RSSI Médio: {mu_rssi:.2f} dBm | Desvio Padrão RSSI: {sigma_rssi:.2f} dB")
print(f"Desvio Padrão Fast Fading X[n]: {sigma_x:.2f} dB")

plt.show()
'''
