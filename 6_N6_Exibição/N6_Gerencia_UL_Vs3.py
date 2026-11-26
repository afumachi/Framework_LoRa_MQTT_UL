# Exibição | Gerência [RSSI, SNR e PSR] + Mapa de Calor GPS 2D | N6 | WissTek-IoT | Framework LoRa
# ====== Nível 6 - Gerência & Cobertura GPS ======
import os
import io
import glob
import math
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import pandas as pd
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
from PIL import Image
import matplotlib.style as style
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

style.use("ggplot")

# ===================== CONSTANTES GERAIS =====================
MAX_PONTOS = 10000
cor_rssi_up = "#FF3300"
cor_rssi_ma = "#1f77b4"
cor_snr_up = "#FF3300"
cor_snr_ma = "#1f77b4"
cor_psr = "#2ca02c"

PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = os.path.join(PASTA_N4, "Parametros")
PASTA_PROCESSADOS = os.path.join(PASTA_N4, "Dados_Processados")
PASTA_CACHE_TILES = os.path.join(PASTA_PARAMETROS, "cache_google_maps")

ARQUIVO_PARAMETROS = os.path.join(PASTA_PARAMETROS, "dados_processamento.txt")
ARQUIVO_GW_GPS = os.path.join(PASTA_PARAMETROS, "GW_GPS.txt")

os.makedirs(PASTA_N4, exist_ok=True)
os.makedirs(PASTA_PARAMETROS, exist_ok=True)
os.makedirs(PASTA_PROCESSADOS, exist_ok=True)
os.makedirs(PASTA_CACHE_TILES, exist_ok=True)

CMAP_CALOR = "turbo"
arquivo_csv_atual_ref = {"caminho": None}


# ===================== FUNÇÕES AUXILIARES GERÊNCIA (ABA 1) =====================
def salvar_parametros_n5(entry_janela_rssi, entry_janela_snr):
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


# ===================== FUNÇÕES AUXILIARES MAPA DE CALOR GPS (ABA 2) =====================
def calcular_distancia_haversine_m(lat1, lon1, lat2, lon2):
    """Calcula a distância horizontal em metros (fórmula de Haversine)."""
    raio_terra_m = 6371000.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)

    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    return 2.0 * raio_terra_m * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def calcular_distancia_3d_m(lat1, lon1, alt1, lat2, lon2, alt2):
    """Calcula a distância 3D em metros considerando altitude (quando disponível)."""
    d_horiz = np.asarray(calcular_distancia_haversine_m(lat1, lon1, lat2, lon2), dtype=float)
    if alt1 is None or alt2 is None:
        return d_horiz
    a1 = np.asarray(alt1, dtype=float)
    a2 = np.asarray(alt2, dtype=float)
    valid_alt = np.isfinite(a1) & np.isfinite(a2)
    dz = np.where(valid_alt, a2 - a1, 0.0)
    return np.sqrt(d_horiz ** 2 + dz ** 2)


def _lonlat_para_tile(lon, lat, zoom):
    lat_rad = math.radians(max(min(lat, 85.05112878), -85.05112878))
    n = 2.0 ** zoom
    xtile = (lon + 180.0) / 360.0 * n
    ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return xtile, ytile


def _tile_para_lonlat(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * ytile / n)))
    lat = math.degrees(lat_rad)
    return lon, lat


def _escolher_zoom_automatico(min_lon, max_lon, min_lat, max_lat):
    for z in range(18, 9, -1):
        x0, y0 = _lonlat_para_tile(min_lon, max_lat, z)
        x1, y1 = _lonlat_para_tile(max_lon, min_lat, z)
        if abs(x1 - x0) <= 6.0 and abs(y1 - y0) <= 6.0:
            return z
    return 15


def baixar_fundo_google_maps(min_lon, max_lon, min_lat, max_lat, tipo_mapa="m", zoom=None):
    """
    Monta imagem de fundo do Google Maps (lyrs='m' mapa padrão, 'y' híbrido, 's' satélite)
    com cache local em disco. Retorna (array_rgb, [west, east, south, north]) ou (None, None).
    """
    if zoom is None:
        zoom = _escolher_zoom_automatico(min_lon, max_lon, min_lat, max_lat)

    x_min_f, y_min_f = _lonlat_para_tile(min_lon, max_lat, zoom)
    x_max_f, y_max_f = _lonlat_para_tile(max_lon, min_lat, zoom)

    x_start = int(math.floor(min(x_min_f, x_max_f)))
    x_end = int(math.floor(max(x_min_f, x_max_f)))
    y_start = int(math.floor(min(y_min_f, y_max_f)))
    y_end = int(math.floor(max(y_min_f, y_max_f)))

    if (x_end - x_start + 1) > 20 or (y_end - y_start + 1) > 20:
        zoom = max(11, zoom - 1)
        x_min_f, y_min_f = _lonlat_para_tile(min_lon, max_lat, zoom)
        x_max_f, y_max_f = _lonlat_para_tile(max_lon, min_lat, zoom)
        x_start = int(math.floor(min(x_min_f, x_max_f)))
        x_end = int(math.floor(max(x_min_f, x_max_f)))
        y_start = int(math.floor(min(y_min_f, y_max_f)))
        y_end = int(math.floor(max(y_min_f, y_max_f)))

    cols = x_end - x_start + 1
    rows = y_end - y_start + 1
    tile_size = 256
    mosaico = Image.new("RGB", (cols * tile_size, rows * tile_size), (235, 235, 235))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WissTek-LoRa-N6/1.0"
    }

    tiles_ok = 0
    for ix, tx in enumerate(range(x_start, x_end + 1)):
        for iy, ty in enumerate(range(y_start, y_end + 1)):
            cache_file = os.path.join(
                PASTA_CACHE_TILES, f"gmap_{tipo_mapa}_z{zoom}_{tx}_{ty}.png"
            )
            tile_img = None
            if os.path.exists(cache_file):
                try:
                    tile_img = Image.open(cache_file).convert("RGB")
                except Exception:
                    tile_img = None

            if tile_img is None:
                url = f"https://mt1.google.com/vt/lyrs={tipo_mapa}&x={tx}&y={ty}&z={zoom}"
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        dados = resp.read()
                    tile_img = Image.open(io.BytesIO(dados)).convert("RGB")
                    tile_img.save(cache_file)
                except Exception:
                    tile_img = None

            if tile_img is not None:
                mosaico.paste(tile_img, (ix * tile_size, iy * tile_size))
                tiles_ok += 1

    if tiles_ok == 0:
        return None, None

    west, north = _tile_para_lonlat(x_start, y_start, zoom)
    east, south = _tile_para_lonlat(x_end + 1, y_end + 1, zoom)
    return np.asarray(mosaico), [west, east, south, north]


def _aplicar_vista_superior(ax, lat_ref, lon_c, lat_c, span_x, span_y, angulo_deg=0.0):
    """
    Define os limites em graus já compensados pela latitude, para que
    1 unidade horizontal e 1 vertical representem a mesma distância real.
    Usa a proporção real do painel, sem alterar a caixa do eixo.
    """
    fator = 1.0 / max(math.cos(math.radians(lat_ref)), 1e-6)
    ax.set_aspect("auto")

    bbox = ax.get_position()
    razao_painel = (bbox.width * ax.figure.get_figwidth()) / max(
        bbox.height * ax.figure.get_figheight(), 1e-6
    )

    ext_x = span_x * fator * 1.08
    ext_y = span_y * 1.08
    if ext_x / ext_y < razao_painel:
        ext_x = ext_y * razao_painel
    else:
        ext_y = ext_x / razao_painel

    ax.set_xlim(lon_c - ext_x / fator / 2, lon_c + ext_x / fator / 2)
    ax.set_ylim(lat_c - ext_y / 2, lat_c + ext_y / 2)


# ===================== CLASSE DA ABA 2: MAPA DE CALOR GPS 2D =====================
class PainelMapaCalorGPS:
    MODOS_VISUALIZACAO = ["Calor + Pontos", "Só Calor", "Só Pontos"]

    def __init__(self, parent_frame, raiz):
        self.parent = parent_frame
        self.raiz = raiz

        self.auto_refresh_var = tk.BooleanVar(value=False)
        self.tipo_mapa_var = tk.StringVar(value="m")
        self.modo_vis_var = tk.StringVar(value="Calor + Pontos")
        self.raio_max_m_var = tk.StringVar(value="1000")
        self.status_csv_var = tk.StringVar(value="CSV: Nenhum carregado")
        self.status_gw_var = tk.StringVar(value="Distância Nó -> GW: --")

        self._construir_painel_gateway()
        self._construir_abas_mapas()
        self._carregar_gw_gps_salvo()
        self._agendar_atualizacao()

    def _construir_painel_gateway(self):
        frame_gw = ttk.LabelFrame(
            self.parent,
            text=" Posição GPS do Gateway LoRa (Salvo em .../4_N4_Armazenamento/Parametros/GW_GPS.txt) ",
            padding=(8, 4),
        )
        frame_gw.pack(fill="x", padx=10, pady=(6, 2))

        ttk.Label(frame_gw, text="Lat (°):").pack(side="left", padx=(2, 2))
        self.entry_gw_lat = ttk.Entry(frame_gw, width=12)
        self.entry_gw_lat.insert(0, "-23.068361")
        self.entry_gw_lat.pack(side="left", padx=(0, 6))

        ttk.Label(frame_gw, text="Lon (°):").pack(side="left", padx=(2, 2))
        self.entry_gw_lon = ttk.Entry(frame_gw, width=12)
        self.entry_gw_lon.insert(0, "-46.858277")
        self.entry_gw_lon.pack(side="left", padx=(0, 6))

        ttk.Label(frame_gw, text="Alt (m):").pack(side="left", padx=(2, 2))
        self.entry_gw_alt = ttk.Entry(frame_gw, width=8)
        self.entry_gw_alt.insert(0, "800.0")
        self.entry_gw_alt.pack(side="left", padx=(0, 8))

        btn_salvar_gw = ttk.Button(
            frame_gw, text="Salvar Pos Gateway", command=self.salvar_gw_gps
        )
        btn_salvar_gw.pack(side="left", padx=(0, 8))

        ttk.Label(frame_gw, text="Raio (m):").pack(side="left", padx=(4, 2))
        entry_raio = ttk.Entry(frame_gw, width=6, textvariable=self.raio_max_m_var)
        entry_raio.pack(side="left", padx=(0, 8))

        ttk.Label(frame_gw, text="Modo:").pack(side="left", padx=(4, 2))
        combo_modo = ttk.Combobox(
            frame_gw,
            textvariable=self.modo_vis_var,
            values=self.MODOS_VISUALIZACAO,
            width=13,
            state="readonly",
        )
        combo_modo.pack(side="left", padx=(0, 8))
        combo_modo.bind("<<ComboboxSelected>>", lambda _e: self.atualizar_mapas())

        ttk.Label(frame_gw, text="Mapa:").pack(side="left", padx=(4, 2))
        combo_mapa = ttk.Combobox(
            frame_gw,
            textvariable=self.tipo_mapa_var,
            values=["m", "y", "s"],
            width=3,
            state="readonly",
        )
        combo_mapa.pack(side="left", padx=(0, 8))
        combo_mapa.bind("<<ComboboxSelected>>", lambda _e: self.atualizar_mapas())

        chk_auto = ttk.Checkbutton(
            frame_gw, text="Auto (10s)", variable=self.auto_refresh_var
        )
        chk_auto.pack(side="left", padx=(0, 6))

        btn_atualizar = ttk.Button(
            frame_gw, text="Atualizar", command=self.atualizar_mapas
        )
        btn_atualizar.pack(side="left", padx=(0, 4))

        btn_exportar = ttk.Button(
            frame_gw, text="Salvar PNG", command=self.salvar_figuras
        )
        btn_exportar.pack(side="right")

        frame_status = tk.Frame(self.parent)
        frame_status.pack(fill="x", padx=12, pady=(0, 2))
        ttk.Label(frame_status, textvariable=self.status_csv_var).pack(side="left")
        ttk.Label(frame_status, textvariable=self.status_gw_var).pack(side="right")

    def _construir_abas_mapas(self):
        self.notebook_mapas = ttk.Notebook(self.parent)
        self.notebook_mapas.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.aba_rssi = ttk.Frame(self.notebook_mapas)
        self.notebook_mapas.add(self.aba_rssi, text="  Mapa de Calor — RSSI UPLINK  ")
        self.fig_rssi = Figure(figsize=(11, 5.2), dpi=100)
        self.ax_rssi = self.fig_rssi.add_subplot(111)
        self.canvas_rssi, self.cbar_rssi = self._montar_canvas_aba(
            self.aba_rssi, self.fig_rssi, self.ax_rssi, "RSSI UPLINK (dBm)"
        )

        self.aba_snr = ttk.Frame(self.notebook_mapas)
        self.notebook_mapas.add(self.aba_snr, text="  Mapa de Calor — SNR UPLINK  ")
        self.fig_snr = Figure(figsize=(11, 5.2), dpi=100)
        self.ax_snr = self.fig_snr.add_subplot(111)
        self.canvas_snr, self.cbar_snr = self._montar_canvas_aba(
            self.aba_snr, self.fig_snr, self.ax_snr, "SNR UPLINK (dB)"
        )

    def _montar_canvas_aba(self, parent, fig, ax, label_cbar):
        canvas = FigureCanvasTkAgg(fig, master=parent)
        toolbar = NavigationToolbar2Tk(canvas, parent)
        toolbar.update()
        toolbar.pack(side="top", fill="x")
        canvas.get_tk_widget().pack(fill="both", expand=True)

        mappable = ax.scatter([], [], c=[], cmap=CMAP_CALOR)
        cbar = fig.colorbar(mappable, ax=ax, pad=0.02)
        cbar.set_label(label_cbar, fontsize=9)
        fig.subplots_adjust(left=0.07, right=0.92, bottom=0.10, top=0.93)
        return canvas, cbar

    def _parse_float(self, texto):
        if texto is None:
            return np.nan
        s = str(texto).strip().replace(",", ".")
        if s == "":
            return np.nan
        try:
            v = float(s)
            return v if math.isfinite(v) else np.nan
        except ValueError:
            return np.nan

    def _carregar_gw_gps_salvo(self):
        if not os.path.exists(ARQUIVO_GW_GPS):
            return
        try:
            dados = {}
            with open(ARQUIVO_GW_GPS, "r", encoding="utf-8") as f:
                for linha in f:
                    if "=" in linha:
                        k, v = linha.strip().split("=", 1)
                        dados[k.strip().upper()] = v.strip()
            if "LATITUDE" in dados:
                self.entry_gw_lat.delete(0, tk.END)
                self.entry_gw_lat.insert(0, dados["LATITUDE"])
            if "LONGITUDE" in dados:
                self.entry_gw_lon.delete(0, tk.END)
                self.entry_gw_lon.insert(0, dados["LONGITUDE"])
            if "ALTITUDE" in dados:
                self.entry_gw_alt.delete(0, tk.END)
                self.entry_gw_alt.insert(0, dados["ALTITUDE"])
        except Exception as e:
            print(f"[N6_Mapa_Calor] Aviso ao carregar GW_GPS.txt: {e}")

    def salvar_gw_gps(self):
        lat = self._parse_float(self.entry_gw_lat.get())
        lon = self._parse_float(self.entry_gw_lon.get())
        alt = self._parse_float(self.entry_gw_alt.get())

        if np.isnan(lat) or not (-90.0 <= lat <= 90.0):
            messagebox.showwarning("Coordenada Inválida", "Informe uma Latitude válida entre -90° e 90°.")
            return
        if np.isnan(lon) or not (-180.0 <= lon <= 180.0):
            messagebox.showwarning("Coordenada Inválida", "Informe uma Longitude válida entre -180° e 180°.")
            return
        if np.isnan(alt):
            alt = 0.0

        try:
            with open(ARQUIVO_GW_GPS, "w", encoding="utf-8") as f:
                f.write(f"LATITUDE={lat:.6f}\n")
                f.write(f"LONGITUDE={lon:.6f}\n")
                f.write(f"ALTITUDE={alt:.2f}\n")
            messagebox.showinfo("Sucesso", f"Coordenadas salvas em:\n{ARQUIVO_GW_GPS}")
            self.atualizar_mapas()
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar GW_GPS.txt:\n{e}")

    def _obter_ultimo_csv_n5(self):
        padrao = os.path.join(PASTA_PROCESSADOS, "Rodada_Gerencia_*.csv")
        arquivos = glob.glob(padrao)
        if not arquivos:
            return None
        arquivos.sort(key=os.path.getmtime)
        return arquivos[-1]

    def _ler_dados_validos_csv(self, caminho_csv):
        df = pd.read_csv(caminho_csv, sep=";", decimal=",", dtype=str)
        if df.empty:
            return pd.DataFrame()

        col_lat = df.columns[-3]
        col_lon = df.columns[-2]
        col_alt = df.columns[-1]

        out = pd.DataFrame()
        out["RSSI_Uplink"] = df["RSSI_Uplink"].apply(self._parse_float) if "RSSI_Uplink" in df.columns else np.nan
        out["SNR_Uplink"] = df["SNR_Uplink"].apply(self._parse_float) if "SNR_Uplink" in df.columns else np.nan
        out["LATITUDE"] = df[col_lat].apply(self._parse_float)
        out["LONGITUDE"] = df[col_lon].apply(self._parse_float)
        out["ALTITUDE"] = df[col_alt].apply(self._parse_float)

        valido = out.dropna(subset=["RSSI_Uplink", "SNR_Uplink", "LATITUDE", "LONGITUDE"]).copy()
        valido = valido[
            valido["LATITUDE"].between(-90.0, 90.0)
            & valido["LONGITUDE"].between(-180.0, 180.0)
            & ((valido["LATITUDE"] != 0.0) | (valido["LONGITUDE"] != 0.0))
        ]
        return valido.reset_index(drop=True)

    def _plotar_circulos_distancia_gw(self, ax, gw_lat, gw_lon, span_m):
        """
        Desenha círculos de distância concêntricos em torno da posição do Gateway
        com etiquetas posicionadas no sentido oposto (do centro para o canto inferior esquerdo: 225° / 5*pi/4).
        """
        if span_m <= 150:
            raios = [25, 50, 100, 150]
        elif span_m <= 400:
            raios = [50, 100, 150, 200]
        elif span_m <= 900:
            raios = [100, 250, 500, 750]
        else:
            raios = [250, 500, 750, 1000]

        metros_por_lat = 111320.0
        metros_por_lon = max(111320.0 * math.cos(math.radians(gw_lat)), 1.0)
        theta = np.linspace(0.0, 2.0 * np.pi, 180)

        # Ângulo oposto ao canto superior direito (pi/4 = 45°): canto inferior esquerdo (5*pi/4 = 225°)

        # alterado de pi/4 (45º, centro ao canto superior direito) para o 
        # sentido oposto 5 * pi/4 (225º, centro ao canto inferior esquerdo)
        
        # angulo_rotulo = math.pi / 4.0 # 45º

        angulo_rotulo = 5.0 * math.pi / 4.0 # 225º
        
        for r_m in raios:
            dlat = r_m / metros_por_lat
            dlon = r_m / metros_por_lon
            cx = gw_lon + dlon * np.cos(theta)
            cy = gw_lat + dlat * np.sin(theta)
            ax.plot(
                cx,
                cy,
                linestyle="--",
                linewidth=0.95,
                color="#1E1E1E",
                alpha=0.72,
                zorder=4,
            )
            ax.text(
                gw_lon + dlon * math.cos(angulo_rotulo),
                gw_lat + dlat * math.sin(angulo_rotulo),
                f"{r_m} m",
                fontsize=7.5,
                fontweight="bold",
                color="#111111",
                ha="right",
                va="top",
                bbox=dict(boxstyle="round,pad=0.15", fc="#FFFFFF", ec="none", alpha=0.75),
                zorder=4,
            )

    def _plotar_mapa_calor_2d(
        self,
        fig,
        ax,
        canvas,
        cbar,
        df,
        coluna_metrica,
        titulo,
        label_barra,
        gw_lat,
        gw_lon,
        fundo_img,
        fundo_extent,
        modo,
    ):
        ax.clear()

        if fundo_img is not None and fundo_extent is not None:
            ax.imshow(
                fundo_img,
                extent=fundo_extent,
                origin="upper",
                zorder=1,
            )

        if df.empty:
            ax.set_title(f"{titulo} — Sem dados GPS/RF válidos", fontsize=10)
            ax.set_xlabel("Longitude (°)")
            ax.set_ylabel("Latitude (°)")
            canvas.draw()
            return

        lons = df["LONGITUDE"].to_numpy(dtype=float)
        lats = df["LATITUDE"].to_numpy(dtype=float)
        vals = df[coluna_metrica].to_numpy(dtype=float)
        dists = df["DIST_GW_M"].to_numpy(dtype=float)

        vmin = float(np.nanmin(vals))
        vmax = float(np.nanmax(vals))
        if math.isclose(vmin, vmax):
            vmax = vmin + 1.0

        mostrar_calor = modo in ("Calor + Pontos", "Só Calor")
        mostrar_pontos = modo in ("Calor + Pontos", "Só Pontos")

        mappable_ref = None

        # 1. Mapa de calor 2D interpolado e mascarado apenas no entorno das amostras válidas
        if mostrar_calor and len(df) >= 4 and (np.ptp(lons) > 1e-7) and (np.ptp(lats) > 1e-7):
            gx = np.linspace(lons.min(), lons.max(), 140)
            gy = np.linspace(lats.min(), lats.max(), 140)
            GX, GY = np.meshgrid(gx, gy)
            GZ = griddata((lons, lats), vals, (GX, GY), method="linear")

            pts_amostra = np.column_stack([lons, lats])
            pts_grade = np.column_stack([GX.ravel(), GY.ravel()])
            dist_grade, _ = cKDTree(pts_amostra).query(pts_grade, k=1)

            raio_mascara_deg = max(min(np.ptp(lons), np.ptp(lats)) * 0.08, 0.0005)
            raio_mascara_deg = min(raio_mascara_deg, 0.0012)
            mascara_longe = (dist_grade.reshape(GX.shape) > raio_mascara_deg) | np.isnan(GZ)
            GZ_mascarado = np.ma.array(GZ, mask=mascara_longe)

            alpha_calor = 0.62 if modo == "Só Calor" else 0.45
            mappable_ref = ax.pcolormesh(
                GX,
                GY,
                GZ_mascarado,
                cmap=CMAP_CALOR,
                vmin=vmin,
                vmax=vmax,
                alpha=alpha_calor,
                shading="auto",
                zorder=2,
            )

        # 2. Pontos medidos do nó sensor
        if mostrar_pontos:
            tamanho_pt = 16 if modo == "Só Pontos" else 9
            alpha_pt = 0.90 if modo == "Só Pontos" else 0.72
            sc = ax.scatter(
                lons,
                lats,
                c=vals,
                cmap=CMAP_CALOR,
                vmin=vmin,
                vmax=vmax,
                s=tamanho_pt,
                alpha=alpha_pt,
                edgecolors="none",
                zorder=3,
                label="Nó Sensor (amostras válidas)",
            )
            if mappable_ref is None:
                mappable_ref = sc

        # 3. Círculos de distância em torno do Gateway LoRa
        span_m = max(float(np.nanmax(dists)), 100.0)
        self._plotar_circulos_distancia_gw(ax, gw_lat, gw_lon, span_m)

        # 4. Balão de posição GPS do Gateway LoRa
        ax.scatter(
            [gw_lon],
            [gw_lat],
            marker="^",
            s=210,
            c="#111111",
            edgecolors="#FFFFFF",
            linewidths=1.4,
            zorder=5,
            label="Gateway LoRa (Coordenadas GPS)",
        )
        ax.annotate(
            f"GW ({gw_lat:.5f}, {gw_lon:.5f})",
            xy=(gw_lon, gw_lat),
            xytext=(8, 10),
            textcoords="offset points",
            fontsize=8,
            fontweight="bold",
            color="#111111",
            bbox=dict(boxstyle="round,pad=0.25", fc="#FFFDE7", ec="#111111", alpha=0.92),
            zorder=6,
        )

        # 5. Enquadramento 2D focado na área das amostras + Gateway
        all_x = np.append(lons, gw_lon)
        all_y = np.append(lats, gw_lat)
        span_x = max(float(np.percentile(all_x, 99) - np.percentile(all_x, 1)), 0.002)
        span_y = max(float(np.percentile(all_y, 99) - np.percentile(all_y, 1)), 0.002)
        cx = float(np.median(all_x))
        cy = float(np.median(all_y))
        ax.set_xlim(cx - span_x * 0.65, cx + span_x * 0.65)
        ax.set_ylim(cy - span_y * 0.65, cy + span_y * 0.65)

        if mappable_ref is not None:
            cbar.update_normal(mappable_ref)
        cbar.set_label(f"{label_barra}  [ Fraco - Frio | Forte - Quente ]", fontsize=8)

        ax.set_title(
            f"{titulo} [{modo}] | Amostras: {len(df)} | Dist. GW: {dists.min():.1f} m – {dists.max():.1f} m (Média: {dists.mean():.1f} m)",
            fontsize=9.5,
        )
        ax.set_xlabel("Longitude (°)", fontsize=8)
        ax.set_ylabel("Latitude (°)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(loc="upper right", fontsize=8)

        ax.set_xlim(cx - span_x * 0.65, cx + span_x * 0.65)
        ax.set_ylim(cy - span_y * 0.65, cy + span_y * 0.65)

        _aplicar_vista_superior(ax, cy, cx, cy, span_x, span_y)

        if fundo_extent is not None:
            w, e, s, n = fundo_extent
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            ax.set_xlim(max(x0, w), min(x1, e))
            ax.set_ylim(max(y0, s), min(y1, n))

        if mappable_ref is not None:
            cbar.update_normal(mappable_ref)
        ax.legend(loc="upper right", fontsize=8)
        canvas.draw()

    def atualizar_mapas(self):
        gw_lat = self._parse_float(self.entry_gw_lat.get())
        gw_lon = self._parse_float(self.entry_gw_lon.get())
        gw_alt = self._parse_float(self.entry_gw_alt.get())
        if np.isnan(gw_lat):
            gw_lat = -23.068361
        if np.isnan(gw_lon):
            gw_lon = -46.858277

        raio_max = self._parse_float(self.raio_max_m_var.get())
        if np.isnan(raio_max) or raio_max <= 0:
            raio_max = 1000.0

        modo = self.modo_vis_var.get()
        if modo not in self.MODOS_VISUALIZACAO:
            modo = "Calor + Pontos"

        csv_path = self._obter_ultimo_csv_n5()
        if not csv_path:
            self.status_csv_var.set("CSV: Nenhum Rodada_Gerencia_*.csv encontrado em Dados_Processados")
            return

        self.status_csv_var.set(f"CSV: {os.path.basename(csv_path)}")

        try:
            df = self._ler_dados_validos_csv(csv_path)
        except Exception as e:
            self.status_csv_var.set(f"CSV: Erro ao ler ({e})")
            return

        if not df.empty:
            df["DIST_GW_M"] = calcular_distancia_3d_m(
                gw_lat, gw_lon, gw_alt, df["LATITUDE"], df["LONGITUDE"], df["ALTITUDE"]
            )
            df = df[df["DIST_GW_M"] <= raio_max].reset_index(drop=True)

        fundo_img, fundo_extent = None, None
        if not df.empty:
            todos_lons = np.append(df["LONGITUDE"].to_numpy(dtype=float), gw_lon)
            todos_lats = np.append(df["LATITUDE"].to_numpy(dtype=float), gw_lat)
            cen_lon = float(np.median(todos_lons))
            cen_lat = float(np.median(todos_lats))
            span_lon = max(np.ptp(todos_lons), 0.0012)
            span_lat = max(np.ptp(todos_lats), 0.0012)

            razao_painel = 1.9
            fator_cob = 2.2
            fator_lat_cos = 1.0 / max(math.cos(math.radians(cen_lat)), 1e-6)

            ext_lat = span_lat * fator_cob
            ext_lon = max(span_lon * fator_cob, ext_lat * razao_painel / fator_lat_cos)
            ext_lon = max(ext_lon, span_lon * fator_cob * 1.35)

            fundo_img, fundo_extent = baixar_fundo_google_maps(
                cen_lon - ext_lon / 2, cen_lon + ext_lon / 2,
                cen_lat - ext_lat / 2, cen_lat + ext_lat / 2,
                tipo_mapa=self.tipo_mapa_var.get(),
            )
            self.status_gw_var.set(
                f"Distância Nó -> GW: mín {df['DIST_GW_M'].min():.1f} m | "
                f"média {df['DIST_GW_M'].mean():.1f} m | máx {df['DIST_GW_M'].max():.1f} m"
            )
        else:
            self.status_gw_var.set("Distância Nó -> GW: --")

        self._plotar_mapa_calor_2d(
            self.fig_rssi,
            self.ax_rssi,
            self.canvas_rssi,
            self.cbar_rssi,
            df,
            "RSSI_Uplink",
            "Mapa de Calor 2D — RSSI UPLINK (dBm)",
            "RSSI UPLINK (dBm)",
            gw_lat,
            gw_lon,
            fundo_img,
            fundo_extent,
            modo,
        )

        self._plotar_mapa_calor_2d(
            self.fig_snr,
            self.ax_snr,
            self.canvas_snr,
            self.cbar_snr,
            df,
            "SNR_Uplink",
            "Mapa de Calor 2D — SNR UPLINK (dB)",
            "SNR UPLINK (dB)",
            gw_lat,
            gw_lon,
            fundo_img,
            fundo_extent,
            modo,
        )

    def salvar_figuras(self):
        caminho_base = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialfile="Mapa_Calor_2D_LoRa_GPS.png",
        )
        if not caminho_base:
            return
        raiz_arq, _ = os.path.splitext(caminho_base)
        self.fig_rssi.savefig(f"{raiz_arq}_RSSI.png", dpi=150)
        self.fig_snr.savefig(f"{raiz_arq}_SNR.png", dpi=150)
        messagebox.showinfo(
            "Exportado",
            f"Mapas salvos em:\n{raiz_arq}_RSSI.png\n{raiz_arq}_SNR.png",
        )

    def _agendar_atualizacao(self):
        if self.auto_refresh_var.get():
            self.atualizar_mapas()
        self.raiz.after(10000, self._agendar_atualizacao)


# ===================== INTERFACE PRINCIPAL UNIFICADA =====================
def main():
    raiz = tk.Tk()
    raiz.title("NÍVEL 6 - GERÊNCIA DE REDE, CONFIGURAÇÃO & MAPA DE CALOR GPS")
    raiz.geometry("1366x800")
    raiz.minsize(1150, 700)

    notebook_principal = ttk.Notebook(raiz)
    notebook_principal.pack(fill="both", expand=True, padx=6, pady=6)

    # -------------------------------------------------------------------------
    # ABA 1: GERÊNCIA [RSSI, SNR e PSR] (Original N6_Gerencia_UL_Vs2)
    # -------------------------------------------------------------------------
    aba_gerencia = ttk.Frame(notebook_principal)
    notebook_principal.add(aba_gerencia, text="  Gerência [RSSI, SNR e PSR]  ")

    # Painel Topo: RSSI & Máx/Mín/Média/DesvPad
    frame_topo = tk.Frame(aba_gerencia)
    frame_topo.pack(fill="x", padx=10, pady=2)

    label_up = tk.Label(frame_topo, text="RSSI UL: --", font=("Arial", 8, "bold"), bg=cor_rssi_up, fg="white", width=18)
    label_up.pack(side="left", padx=2)

    label_estat_rssi = tk.Label(frame_topo, text="MM Média: -- | Máx: -- | Mín: -- | DesvPad: --", font=("Arial", 8), fg="#333333")
    label_estat_rssi.pack(side="left", padx=10)

    tk.Label(frame_topo, text="Janela RSSI:", font=("Arial", 8)).pack(side="left", padx=(15, 2))
    entry_janela_rssi = tk.Entry(frame_topo, width=5, font=("Arial", 8))
    entry_janela_rssi.insert(0, "10")
    entry_janela_rssi.pack(side="left")

    def salvar_graficos_gerencia(fig1, fig2, fig3):
        arquivo = filedialog.asksaveasfilename(defaultextension=".png")
        if arquivo:
            fig1.savefig(arquivo.replace(".png", "_rssi.png"))
            fig2.savefig(arquivo.replace(".png", "_snr.png"))
            fig3.savefig(arquivo.replace(".png", "_psr.png"))
            messagebox.showinfo("Sucesso", "Gráficos salvos com sucesso!")

    btn_salvar = tk.Button(
        frame_topo,
        text="Salvar Gráficos",
        font=("Arial", 8, "bold"),
        command=lambda: salvar_graficos_gerencia(fig1, fig2, fig3),
    )
    btn_salvar.pack(side="right", padx=2)

    # --- GRÁFICO RSSI ---
    frame_rssi = tk.Frame(aba_gerencia)
    frame_rssi.pack(fill="both", expand=True, padx=10, pady=1)

    fig1 = Figure(figsize=(10, 2.0), dpi=100)
    ax1 = fig1.add_subplot(111)
    fig1.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
    canvas1 = FigureCanvasTkAgg(fig1, master=frame_rssi)
    canvas1.get_tk_widget().pack(fill="both", expand=True)

    # Painel SNR & Máx/Mín/Média/DesvPad
    frame_labels_snr = tk.Frame(aba_gerencia)
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
    frame_snr = tk.Frame(aba_gerencia)
    frame_snr.pack(fill="both", expand=True, padx=10, pady=1)

    fig2 = Figure(figsize=(10, 2.0), dpi=100)
    ax2 = fig2.add_subplot(111)
    fig2.subplots_adjust(left=0.05, right=0.98, top=0.86, bottom=0.16)
    canvas2 = FigureCanvasTkAgg(fig2, master=frame_snr)
    canvas2.get_tk_widget().pack(fill="both", expand=True)

    # Painel PSR & Limiar
    frame_label_psr = tk.Frame(aba_gerencia)
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
    frame_psr = tk.Frame(aba_gerencia)
    frame_psr.pack(fill="both", expand=True, padx=10, pady=1)

    fig3 = Figure(figsize=(10, 2.0), dpi=100)
    ax3 = fig3.add_subplot(111)
    fig3.subplots_adjust(left=0.05, right=0.98, top=0.84, bottom=0.20)
    canvas3 = FigureCanvasTkAgg(fig3, master=frame_psr)
    canvas3.get_tk_widget().pack(fill="both", expand=True)

    def atualizar_grafico_gerencia():
        rssi_up, rssi_ma = [], []
        snr_up, snr_ma = [], []
        psr = []
        pacotes_perdidos_lista = []

        salvar_parametros_n5(entry_janela_rssi, entry_janela_snr)

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

        max_len_bruto = max(
            len(rssi_up), len(rssi_ma), len(snr_up), len(snr_ma), len(psr), 0
        )
        alvo_len = min(max_len_bruto, MAX_PONTOS)
        rssi_up, rssi_ma, snr_up, snr_ma, psr = _alinhar_comprimentos(
            [rssi_up, rssi_ma, snr_up, snr_ma, psr], alvo_len
        )

        x_idx = list(range(alvo_len))
        x_lim = (0, max(alvo_len - 1, 1)) if alvo_len > 0 else (0, 1)

        rssi_up_validos = _valores_validos(rssi_up)
        snr_up_validos = _valores_validos(snr_up)
        psr_validos = _valores_validos(psr)

        label_up.config(text=f"RSSI UL: {round(rssi_up_validos[-1], 2)} dBm" if rssi_up_validos else "RSSI UL: --")
        label_snr_up.config(text=f"SNR UL: {round(snr_up_validos[-1], 2)} dB" if snr_up_validos else "SNR UL: --")
        label_psr.config(text=f"PSR atual: {round(psr_validos[-1], 2)} %" if psr_validos else "PSR atual: --")
        label_perdidos.config(text=f"Pacotes Perdidos: {pacotes_perdidos_lista[-1]}" if pacotes_perdidos_lista else "Pacotes Perdidos: --")

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
        raiz.after(1000, atualizar_grafico_gerencia)

    # -------------------------------------------------------------------------
    # ABA 2: MAPA DE CALOR GPS 2D [RSSI & SNR] (Integrado de N6_Mapa_Calor)
    # -------------------------------------------------------------------------
    aba_mapa_calor = ttk.Frame(notebook_principal)
    notebook_principal.add(aba_mapa_calor, text="  Mapa de Calor GPS 2D [RSSI & SNR]  ")
    painel_mapa = PainelMapaCalorGPS(aba_mapa_calor, raiz)

    # Inicia loop da Aba 1
    atualizar_grafico_gerencia()

    def fechar_janela():
        if messagebox.askokcancel("Sair", "Deseja fechar o monitor de gerência e mapa de calor?"):
            raiz.destroy()

    raiz.protocol("WM_DELETE_WINDOW", fechar_janela)
    raiz.mainloop()


if __name__ == "__main__":
    main()
