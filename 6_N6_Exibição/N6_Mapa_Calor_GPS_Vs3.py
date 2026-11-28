# Exibição | Mapa de Calor GPS 2D [RSSI e SNR] | N6_Mapa_Calor | WissTek-IoT | Framework LoRa
# ====== Gerência GPS ======
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

# Pastas e arquivos do Framework LoRa
PASTA_N4 = "../4_N4_Armazenamento"
PASTA_PARAMETROS = os.path.join(PASTA_N4, "Parametros")
PASTA_PROCESSADOS = os.path.join(PASTA_N4, "Dados_Processados")
PASTA_CACHE_TILES = os.path.join(PASTA_PARAMETROS, "cache_google_maps")
ARQUIVO_GW_GPS = os.path.join(PASTA_PARAMETROS, "GW_GPS.txt")

os.makedirs(PASTA_PARAMETROS, exist_ok=True)
os.makedirs(PASTA_PROCESSADOS, exist_ok=True)
os.makedirs(PASTA_CACHE_TILES, exist_ok=True)

# Colormap térmico: valores mais altos (quentes) -> vermelho/laranja; mais baixos (frios) -> azul/ciano
CMAP_CALOR = "turbo"



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


class AplicacaoN6GPS:
    MODOS_VISUALIZACAO = ["Calor + Pontos", "Só Calor", "Só Pontos"]

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title(" MAPA DE CALOR LoRa-LoRaWAN [RSSI & SNR] | COBERTURA LoRa-LoRaWAN ")
        self.raiz.geometry("1366x800")
        self.raiz.minsize(1140, 700)

        self.auto_refresh_var = tk.BooleanVar(value=False)
        self.tipo_mapa_var = tk.StringVar(value="m")
        self.modo_vis_var = tk.StringVar(value="Calor + Pontos")
        self.raio_max_m_var = tk.StringVar(value="1000")
        self.csv_selecionado_var = tk.StringVar(value="")
        self.status_csv_var = tk.StringVar(value="CSV: Nenhum carregado")
        self.status_gw_var = tk.StringVar(value="Distância Nó -> GW: --")

        self._construir_painel_gateway()
        self._construir_abas_mapas()
        self._carregar_gw_gps_salvo()
        self.atualizar_mapas()
        self._agendar_atualizacao()

    def _construir_painel_gateway(self):
        frame_gw = ttk.LabelFrame(
            self.raiz,
            text=" Posição GPS do Gateway LoRa (Salvo em .../4_N4_Armazenamento/Parametros/GW_GPS.txt) ",
            padding=(8, 6),
        )
        frame_gw.pack(fill="x", padx=10, pady=(8, 4))

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

        btn_importar_csv = ttk.Button(
            frame_gw, text="Importar CSV", command=self.importar_csv
        )
        btn_importar_csv.pack(side="left", padx=(0, 4))

        btn_atualizar = ttk.Button(
            frame_gw, text="Atualizar", command=self.atualizar_mapas
        )
        btn_atualizar.pack(side="left", padx=(0, 4))

        btn_exportar = ttk.Button(
            frame_gw, text="Salvar PNG", command=self.salvar_figuras
        )
        btn_exportar.pack(side="right")

        frame_status = tk.Frame(self.raiz)
        frame_status.pack(fill="x", padx=12, pady=(0, 4))
        ttk.Label(frame_status, textvariable=self.status_csv_var).pack(side="left")
        ttk.Label(frame_status, textvariable=self.status_gw_var).pack(side="right")


    def _construir_abas_mapas(self):
        self.notebook = ttk.Notebook(self.raiz)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Aba 1: Mapa de Calor RSSI
        self.aba_rssi = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_rssi, text="  Mapa de Calor — RSSI UPLINK  ")
        self.fig_rssi = Figure(figsize=(11, 5.5), dpi=100)
        self.ax_rssi = self.fig_rssi.add_subplot(111)
        self.canvas_rssi, self.cbar_rssi = self._montar_canvas_aba(
            self.aba_rssi, self.fig_rssi, self.ax_rssi, "RSSI UPLINK (dBm)"
        )

        # Aba 2: Mapa de Calor SNR
        self.aba_snr = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_snr, text="  Mapa de Calor — SNR UPLINK  ")
        self.fig_snr = Figure(figsize=(11, 5.5), dpi=100)
        self.ax_snr = self.fig_snr.add_subplot(111)
        self.canvas_snr, self.cbar_snr = self._montar_canvas_aba(
            self.aba_snr, self.fig_snr, self.ax_snr, "SNR UPLINK (dB)"
        )

        # Aba 3: Gráficos RSSI UPLINK e SNR UPLINK x DISTANCIA_GW_M
        self.aba_dist = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_dist, text="  RSSI & SNR × Distância GW  ")

        # Faixa compacta de parâmetros no topo da aba
        frame_param = ttk.LabelFrame(
            self.aba_dist,
            text=" Parâmetros do Modelo P_RX(d) [Log-Distance + Shadowing + Perda Sistêmica + Margem Fading] ",
            padding=(6, 4),
        )
        frame_param.pack(fill="x", padx=8, pady=(6, 2))

        def _add_campo(rotulo, valor_padrao, largura=6):
            ttk.Label(frame_param, text=rotulo).pack(side="left", padx=(4, 2))
            ent = ttk.Entry(frame_param, width=largura)
            ent.insert(0, str(valor_padrao))
            ent.pack(side="left", padx=(0, 4))
            return ent

        self.entry_ptx_dbm = _add_campo("P_TX (dBm):", "20.0", 5)
        self.entry_gtx_dbi = _add_campo("G_TX (dBi):", "2.0", 5)
        self.entry_grx_dbi = _add_campo("G_RX (dBi):", "2.0", 5)
        self.entry_freq_mhz = _add_campo("Freq (MHz):", "915.0", 6)
        self.entry_del_m = _add_campo("d_EL (m):", "10.0", 5)
        self.entry_beta_pl = _add_campo("β:", "2.2", 5)
        self.entry_shadow_db = _add_campo("Shadowing σ (dB):", "4.0", 5)
        self.entry_lsist_db = _add_campo("L_sist (dB):", "1.5", 5)
        self.entry_mfade_db = _add_campo("Margem Fade (dB):", "0.0", 5)

        btn_aplicar_modelo = ttk.Button(
            frame_param,
            text="Aplicar Modelo",
            command=self.atualizar_mapas,
        )
        btn_aplicar_modelo.pack(side="right", padx=(6, 2))

        self.fig_dist = Figure(figsize=(11, 5.4), dpi=100)
        self.ax_dist_rssi = self.fig_dist.add_subplot(211)
        self.ax_dist_snr = self.fig_dist.add_subplot(212, sharex=self.ax_dist_rssi)

        self.canvas_dist = FigureCanvasTkAgg(self.fig_dist, master=self.aba_dist)
        toolbar_dist = NavigationToolbar2Tk(self.canvas_dist, self.aba_dist)
        toolbar_dist.update()
        toolbar_dist.pack(side="top", fill="x")
        self.canvas_dist.get_tk_widget().pack(fill="both", expand=True)
        self.fig_dist.subplots_adjust(left=0.07, right=0.96, bottom=0.10, top=0.91, hspace=0.25)
    
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

    def importar_csv(self):
        """Abre diálogo para importar um arquivo CSV e gerar o mapa de calor."""
        pasta_inicial = PASTA_PROCESSADOS if os.path.isdir(PASTA_PROCESSADOS) else os.getcwd()
        caminho = filedialog.askopenfilename(
            title="Importar Arquivo CSV para Mapa de Calor",
            initialdir=pasta_inicial,
            filetypes=[
                ("Arquivos CSV", "*.csv"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not caminho:
            return

        self.csv_selecionado_var.set(caminho)
        self.auto_refresh_var.set(False)
        self.atualizar_mapas()

    def _obter_csv_ativo(self):
        """Retorna (caminho_csv, modo_origem) priorizando CSV importado manualmente."""
        csv_manual = self.csv_selecionado_var.get().strip()
        if csv_manual:
            if os.path.exists(csv_manual):
                return csv_manual, "Manual"
            return None, "Manual"

        padrao = os.path.join(PASTA_PROCESSADOS, "Rodada_Gerencia_*.csv")
        arquivos = glob.glob(padrao)
        if not arquivos:
            return None, "Auto"
        arquivos.sort(key=os.path.getmtime)
        return arquivos[-1], "Auto"

    def _encontrar_coluna(self, colunas, candidatas):
        mapa_lower = {str(c).strip().lower(): c for c in colunas}
        for cand in candidatas:
            chave = cand.strip().lower()
            if chave in mapa_lower:
                return mapa_lower[chave]
        for col in colunas:
            col_l = str(col).strip().lower()
            if any(cand.strip().lower() in col_l for cand in candidatas):
                return col
        return None


    def _ler_dados_validos_csv(self, caminho_csv):
        df = pd.read_csv(caminho_csv, sep=";", decimal=",", dtype=str)
        if df.shape[1] < 3:
            df = pd.read_csv(caminho_csv, sep=",", decimal=".", dtype=str)
        if df.empty or df.shape[1] < 3:
            return pd.DataFrame()

        col_rssi = self._encontrar_coluna(df.columns, ["RSSI_Uplink", "rssi_uplink", "rssi"])
        col_snr = self._encontrar_coluna(df.columns, ["SNR_Uplink", "snr_uplink", "snr"])
        col_lat = self._encontrar_coluna(df.columns, ["LATITUDE", "latitude", "lat"]) or df.columns[-3]
        col_lon = self._encontrar_coluna(df.columns, ["LONGITUDE", "longitude", "lon", "lng"]) or df.columns[-2]
        col_alt = self._encontrar_coluna(df.columns, ["ALTITUDE", "altitude", "alt"]) or df.columns[-1]
        col_dist = self._encontrar_coluna(df.columns, ["DISTANCIA_GW_M", "distancia_gw_m", "dist_gw_m"])

        out = pd.DataFrame()
        out["RSSI_Uplink"] = df[col_rssi].apply(self._parse_float) if col_rssi is not None else np.nan
        out["SNR_Uplink"] = df[col_snr].apply(self._parse_float) if col_snr is not None else np.nan
        out["LATITUDE"] = df[col_lat].apply(self._parse_float)
        out["LONGITUDE"] = df[col_lon].apply(self._parse_float)
        out["ALTITUDE"] = df[col_alt].apply(self._parse_float) if col_alt is not None else np.nan
        out["DISTANCIA_GW_M"] = df[col_dist].apply(self._parse_float) if col_dist is not None else np.nan

        valido = out.dropna(subset=["RSSI_Uplink", "SNR_Uplink", "LATITUDE", "LONGITUDE"]).copy()
        valido = valido[
            valido["LATITUDE"].between(-90.0, 90.0)
            & valido["LONGITUDE"].between(-180.0, 180.0)
            & ((valido["LATITUDE"] != 0.0) | (valido["LONGITUDE"] != 0.0))
        ]
        return valido.reset_index(drop=True)


    def _plotar_graficos_distancia(self, df):
        self.ax_dist_rssi.clear()
        self.ax_dist_snr.clear()

        if df.empty or "DIST_GW_M" not in df.columns:
            self.ax_dist_rssi.set_title("RSSI & SNR UPLINK × Distância GW — Sem dados válidos", fontsize=10)
            self.ax_dist_snr.set_xlabel("DISTANCIA_GW_M (m)", fontsize=9)
            self.canvas_dist.draw()
            return

        df_ord = df.dropna(subset=["DIST_GW_M", "RSSI_Uplink", "SNR_Uplink"]).sort_values("DIST_GW_M")
        dists = df_ord["DIST_GW_M"].to_numpy(dtype=float)
        rssis = df_ord["RSSI_Uplink"].to_numpy(dtype=float)
        snrs = df_ord["SNR_Uplink"].to_numpy(dtype=float)

        # Leitura dos campos da faixa compacta
        p_tx_dbm = self._parse_float(self.entry_ptx_dbm.get())
        g_tx_dbi = self._parse_float(self.entry_gtx_dbi.get())
        g_rx_dbi = self._parse_float(self.entry_grx_dbi.get())
        freq_mhz = self._parse_float(self.entry_freq_mhz.get())
        d_el_m = self._parse_float(self.entry_del_m.get())
        beta_pl = self._parse_float(self.entry_beta_pl.get())
        sigma_sh_db = self._parse_float(self.entry_shadow_db.get())
        l_sist_db = self._parse_float(self.entry_lsist_db.get())
        m_fade_db = self._parse_float(self.entry_mfade_db.get())

        p_tx_dbm = 20.0 if np.isnan(p_tx_dbm) else p_tx_dbm
        g_tx_dbi = 0.0 if np.isnan(g_tx_dbi) else g_tx_dbi
        g_rx_dbi = 0.0 if np.isnan(g_rx_dbi) else g_rx_dbi
        freq_mhz = 915.0 if (np.isnan(freq_mhz) or freq_mhz <= 0) else freq_mhz
        d_el_m = 10.0 if (np.isnan(d_el_m) or d_el_m <= 0) else d_el_m
        beta_pl = 2.0 if np.isnan(beta_pl) else beta_pl
        sigma_sh_db = 0.0 if (np.isnan(sigma_sh_db) or sigma_sh_db < 0) else sigma_sh_db
        l_sist_db = 0.0 if (np.isnan(l_sist_db) or l_sist_db < 0) else l_sist_db
        m_fade_db = 0.0 if np.isnan(m_fade_db) else abs(m_fade_db)

        # Gráfico 1: RSSI UPLINK medido x Potência RX calculada pelo modelo
        self.ax_dist_rssi.scatter(
            dists, rssis, s=16, alpha=0.55, color="#1f77b4", label="RSSI Uplink Medido"
        )

        valid_dist = dists > 0
        if np.count_nonzero(valid_dist) >= 2:
            c_mps = 299792458.0
            lamb = c_mps / (freq_mhz * 1e6)
            d_min = max(float(dists[valid_dist].min()), 0.1)
            d_max = max(float(dists[valid_dist].max()), d_min + 0.1)
            d_curve = np.linspace(d_min, d_max, 250)

            perda_del_db = 10.0 * np.log10((4.0 * np.pi * d_el_m / lamb) ** 2)
            perda_beta_db = 10.0 * beta_pl * np.log10(np.maximum(d_curve / d_el_m, 1e-9))
            prx_calc = p_tx_dbm + g_tx_dbi + g_rx_dbi - perda_del_db - perda_beta_db - l_sist_db

            self.ax_dist_rssi.plot(
                d_curve,
                prx_calc,
                "--",
                color="#d62728",
                linewidth=2.0,
                label=f"P_RX Calc. (β={beta_pl:.2f}, d_EL={d_el_m:.1f}m, L_sist={l_sist_db:.1f}dB)",
            )

            if sigma_sh_db > 0:
                self.ax_dist_rssi.fill_between(
                    d_curve,
                    prx_calc - sigma_sh_db,
                    prx_calc + sigma_sh_db,
                    color="#d62728",
                    alpha=0.15,
                    label=f"Shadowing ±{sigma_sh_db:.1f} dB",
                )

            if m_fade_db > 0:
                self.ax_dist_rssi.plot(
                    d_curve,
                    prx_calc - m_fade_db,
                    ":",
                    color="#8b0000",
                    linewidth=1.5,
                    label=f"Margem Fading (-{m_fade_db:.1f} dB)",
                )

        self.ax_dist_rssi.set_ylabel("RSSI / P_RX (dBm)", fontsize=9)
        self.ax_dist_rssi.set_title(
            f"Comparação RSSI Uplink × P_RX Calculado e SNR Uplink × DISTANCIA_GW_M | "
            f"Amostras: {len(df_ord)} | Alcance: {dists.min():.1f} m – {dists.max():.1f} m",
            fontsize=9.5,
        )
        self.ax_dist_rssi.grid(True, alpha=0.5)
        self.ax_dist_rssi.legend(loc="upper right", fontsize=7.5, ncol=2)
        self.ax_dist_rssi.tick_params(labelsize=8)

        # Gráfico 2: SNR UPLINK x DISTANCIA_GW_M
        self.ax_dist_snr.scatter(
            dists, snrs, s=16, alpha=0.55, color="#2ca02c", label="Amostras SNR Uplink"
        )
        self.ax_dist_snr.axhline(0.0, color="#555555", linestyle=":", linewidth=1.0, alpha=0.8)
        self.ax_dist_snr.set_xlabel("DISTANCIA_GW_M (m)", fontsize=9)
        self.ax_dist_snr.set_ylabel("SNR UPLINK (dB)", fontsize=9)
        self.ax_dist_snr.grid(True, alpha=0.5)
        self.ax_dist_snr.legend(loc="upper right", fontsize=8)
        self.ax_dist_snr.tick_params(labelsize=8)

        self.canvas_dist.draw()
    
    
    def _plotar_circulos_distancia_gw(self, ax, gw_lat, gw_lon, span_m):
        """Desenha círculos de distância concêntricos em torno da posição do Gateway."""
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
                #gw_lon + dlon * math.cos(math.pi / 4.0),
                #gw_lat + dlat * math.sin(math.pi / 4.0),
                gw_lon + dlon * math.cos(angulo_rotulo),
                gw_lat + dlat * math.sin(angulo_rotulo),                
                f"{r_m} m",
                fontsize=7.5,
                fontweight="bold",
                color="#111111",
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

        _aplicar_vista_superior(
            ax, cy, cx, cy, span_x, span_y,
        )

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

        csv_path, origem_csv = self._obter_csv_ativo()
        if not csv_path:
            if origem_csv == "Manual":
                self.status_csv_var.set("CSV [Manual]: Arquivo não encontrado")
            else:
                self.status_csv_var.set("CSV [Auto]: Nenhum Rodada_Gerencia_*.csv encontrado em Dados_Processados")
            return

        self.status_csv_var.set(f"CSV [{origem_csv}]: {os.path.basename(csv_path)}")

        try:
            df = self._ler_dados_validos_csv(csv_path)
        except Exception as e:
            self.status_csv_var.set(f"CSV [{origem_csv}]: Erro ao ler ({e})")
            if origem_csv == "Manual":
                messagebox.showerror("Erro ao Importar CSV", f"Não foi possível processar o arquivo:\n{e}")
            return

        # Dentro de atualizar_mapas(), logo após ler df:
        if not df.empty:
            dist_calc = calcular_distancia_3d_m(
                gw_lat, gw_lon, gw_alt, df["LATITUDE"], df["LONGITUDE"], df["ALTITUDE"]
            )
            # Prioriza DISTANCIA_GW_M vinda do CSV; usa cálculo 3D apenas onde estiver ausente/inválida
            df["DIST_GW_M"] = np.where(
                np.isfinite(df["DISTANCIA_GW_M"]) & (df["DISTANCIA_GW_M"] >= 0.0),
                df["DISTANCIA_GW_M"],
                dist_calc,
            )
            df = df[df["DIST_GW_M"] <= raio_max].reset_index(drop=True)

        # ... (após chamar self._plotar_mapa_calor_2d para RSSI e SNR) ...
        self._plotar_graficos_distancia(df)
        

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
        self.fig_dist.savefig(f"{raiz_arq}_Distancia_GW.png", dpi=150)
        messagebox.showinfo(
            "Exportado",
            f"Gráficos salvos em:\n{raiz_arq}_RSSI.png\n{raiz_arq}_SNR.png\n{raiz_arq}_Distancia_GW.png",
        )
        
    def _agendar_atualizacao(self):
        if self.auto_refresh_var.get():
            self.atualizar_mapas()
        self.raiz.after(10000, self._agendar_atualizacao)


def main():
    raiz = tk.Tk()
    app = AplicacaoN6GPS(raiz)

    def ao_fechar():
        if messagebox.askokcancel("Sair", "Deseja encerrar o N6_Mapa_Calor?"):
            raiz.destroy()

    raiz.protocol("WM_DELETE_WINDOW", ao_fechar)
    raiz.mainloop()


if __name__ == "__main__":
    main()
