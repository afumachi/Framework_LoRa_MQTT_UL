
# Exibição | Mapa de Calor GPS 2D [RSSI e SNR] | N6_Mapa_Calor | WissTek-IoT | Framework LoRa
# ====== Nível 6 - Gerência GPS ======
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

    if (x_end - x_start + 1) > 8 or (y_end - y_start + 1) > 8:
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
                    with urllib.request.urlopen(req, timeout=2.5) as resp:
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


class AplicacaoN6GPS:
    MODOS_VISUALIZACAO = ["Calor + Pontos", "Só Calor", "Só Pontos"]

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title(" NÍVEL 6 - MAPA DE CALOR LORA [RSSI & SNR] | COBERTURA LORA ")
        self.raiz.geometry("1366x800")
        self.raiz.minsize(1140, 700)

        self.auto_refresh_var = tk.BooleanVar(value=False)#aaf True
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
            frame_gw, text="Auto (1s)", variable=self.auto_refresh_var
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

        frame_status = tk.Frame(self.raiz)
        frame_status.pack(fill="x", padx=12, pady=(0, 4))
        ttk.Label(frame_status, textvariable=self.status_csv_var).pack(side="left")
        ttk.Label(frame_status, textvariable=self.status_gw_var).pack(side="right")

    def _construir_abas_mapas(self):
        self.notebook = ttk.Notebook(self.raiz)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.aba_rssi = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_rssi, text="  Mapa de Calor — RSSI UPLINK  ")
        self.fig_rssi = Figure(figsize=(11, 5.5), dpi=100)
        self.ax_rssi = self.fig_rssi.add_subplot(111)
        self.canvas_rssi, self.cbar_rssi = self._montar_canvas_aba(
            self.aba_rssi, self.fig_rssi, self.ax_rssi, "RSSI UPLINK (dBm)"
        )

        self.aba_snr = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_snr, text="  Mapa de Calor — SNR UPLINK  ")
        self.fig_snr = Figure(figsize=(11, 5.5), dpi=100)
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
        fig.tight_layout()
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
                gw_lon + dlon * math.cos(math.pi / 4.0),
                gw_lat + dlat * math.sin(math.pi / 4.0),
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
                aspect="auto",#"equal",#="auto",
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
        cbar.set_label(f"{label_barra}  [Quente | Frio]", fontsize=8)

        ax.set_title(
            f"{titulo} [{modo}] | Amostras: {len(df)} | Dist. GW: {dists.min():.1f} m – {dists.max():.1f} m (Média: {dists.mean():.1f} m)",
            fontsize=9.5,
        )
        ax.set_xlabel("Longitude (°)", fontsize=8)
        ax.set_ylabel("Latitude (°)", fontsize=8)
        ax.tick_params(labelsize=7)
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
            dx = max(np.ptp(todos_lons) * 0.12, 0.0012)
            dy = max(np.ptp(todos_lats) * 0.12, 0.0012)
            fundo_img, fundo_extent = baixar_fundo_google_maps(
                todos_lons.min() - dx,
                todos_lons.max() + dx,
                todos_lats.min() - dy,
                todos_lats.max() + dy,
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
        self.raiz.after(1000, self._agendar_atualizacao)


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

'''

# Exibição | Mapa de Calor GPS 2D [RSSI e SNR] | N6_Mapa_Calor | WissTek-IoT | Framework LoRa
# ====== Nível 6 - Gerência GPS ======
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

    if (x_end - x_start + 1) > 8 or (y_end - y_start + 1) > 8:
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
                    with urllib.request.urlopen(req, timeout=2.5) as resp:
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


class AplicacaoN6GPS:
    MODOS_VISUALIZACAO = ["Calor + Pontos", "Só Calor", "Só Pontos"]

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("FEE247 - NÍVEL 6 GPS - MAPA DE CALOR 2D [RSSI & SNR] | GATEWAY LORA")
        self.raiz.geometry("1366x800")
        self.raiz.minsize(1140, 700)

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
            frame_gw, text="Salvar GW_GPS.txt", command=self.salvar_gw_gps
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
            frame_gw, text="Auto (1s)", variable=self.auto_refresh_var
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

        frame_status = tk.Frame(self.raiz)
        frame_status.pack(fill="x", padx=12, pady=(0, 4))
        ttk.Label(frame_status, textvariable=self.status_csv_var).pack(side="left")
        ttk.Label(frame_status, textvariable=self.status_gw_var).pack(side="right")

    def _construir_abas_mapas(self):
        self.notebook = ttk.Notebook(self.raiz)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.aba_rssi = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_rssi, text="  Mapa de Calor — RSSI UPLINK  ")
        self.fig_rssi = Figure(figsize=(11, 5.5), dpi=100)
        self.ax_rssi = self.fig_rssi.add_subplot(111)
        self.canvas_rssi, self.cbar_rssi = self._montar_canvas_aba(
            self.aba_rssi, self.fig_rssi, self.ax_rssi, "RSSI UPLINK (dBm)"
        )

        self.aba_snr = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_snr, text="  Mapa de Calor — SNR UPLINK  ")
        self.fig_snr = Figure(figsize=(11, 5.5), dpi=100)
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
        cbar = fig.colorbar(mappable, ax=ax, pad=0.02, fraction=0.035)
        cbar.set_label(label_cbar, fontsize=9)
        fig.subplots_adjust(left=0.06, right=0.80, top=0.90, bottom=0.11)
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
        """Desenha círculos de distância concêntricos em torno da posição do Gateway."""
        if span_m <= 150:
            raios = [25, 50, 100]
        elif span_m <= 400:
            raios = [50, 100, 200]
        elif span_m <= 900:
            raios = [100, 250, 500, 750]
        else:
            raios = [250, 500, 750, 1000]

        metros_por_lat = 111320.0
        metros_por_lon = max(111320.0 * math.cos(math.radians(gw_lat)), 1.0)
        theta = np.linspace(0.0, 2.0 * np.pi, 180)

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
                gw_lon + dlon * math.cos(math.pi / 4.0),
                gw_lat + dlat * math.sin(math.pi / 4.0),
                f"{r_m} m",
                fontsize=7.5,
                fontweight="bold",
                color="#111111",
                bbox=dict(boxstyle="round,pad=0.15", fc="#FFFFFF", ec="none", alpha=0.82),
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
                aspect="equal",
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

        # 1. Mapa de calor 2D interpolado com grade fina e máscara próxima às amostras
        if mostrar_calor and len(df) >= 4 and (np.ptp(lons) > 1e-7) and (np.ptp(lats) > 1e-7):
            gx = np.linspace(lons.min(), lons.max(), 220)
            gy = np.linspace(lats.min(), lats.max(), 220)
            GX, GY = np.meshgrid(gx, gy)
            GZ = griddata((lons, lats), vals, (GX, GY), method="linear")

            pts_amostra = np.column_stack([lons, lats])
            pts_grade = np.column_stack([GX.ravel(), GY.ravel()])
            dist_grade, _ = cKDTree(pts_amostra).query(pts_grade, k=1)

            raio_mascara_deg = max(min(np.ptp(lons), np.ptp(lats)) * 0.08, 0.0005)
            raio_mascara_deg = min(raio_mascara_deg, 0.0012)
            mascara_longe = (dist_grade.reshape(GX.shape) > raio_mascara_deg) | np.isnan(GZ)
            GZ_mascarado = np.ma.array(GZ, mask=mascara_longe)

            alpha_calor = 0.62 if modo == "Só Calor" else 0.46
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

        # 4. Posição GPS do Gateway LoRa
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

        # 5. Enquadramento mais amplo na horizontal com proporção geográfica real
        all_x = np.append(lons, gw_lon)
        all_y = np.append(lats, gw_lat)
        min_x, max_x = float(np.min(all_x)), float(np.max(all_x))
        min_y, max_y = float(np.min(all_y)), float(np.max(all_y))
        cx = 0.5 * (min_x + max_x)
        cy = 0.5 * (min_y + max_y)

        fator_lat = max(math.cos(math.radians(gw_lat)), 0.1)
        semi_y = max((max_y - min_y) * 0.62, 0.0020)
        semi_x_dados = max((max_x - min_x) * 0.65, 0.0025)
        semi_x_amplo = (semi_y * 1.55) / fator_lat
        semi_x = max(semi_x_dados, semi_x_amplo)

        ax.set_xlim(cx - semi_x, cx + semi_x)
        ax.set_ylim(cy - semi_y, cy + semi_y)
        ax.set_aspect(1.0 / fator_lat, adjustable="box")

        if mappable_ref is not None:
            cbar.update_normal(mappable_ref)
        cbar.set_label(f"{label_barra}  [Quente = Alto | Frio = Baixo]", fontsize=8)

        ax.set_title(
            f"{titulo} [{modo}] | Amostras: {len(df)} | Dist. GW: {dists.min():.1f} m – {dists.max():.1f} m (Média: {dists.mean():.1f} m)",
            fontsize=9.5,
        )
        ax.set_xlabel("Longitude (°)", fontsize=8)
        ax.set_ylabel("Latitude (°)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(
            loc="upper left",
            bbox_to_anchor=(1.01, 1.0),
            borderaxespad=0.0,
            fontsize=8,
            framealpha=0.95,
        )
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
            raio_max = 2000.0

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
            dx = max(np.ptp(todos_lons) * 0.15, 0.0015)
            dy = max(np.ptp(todos_lats) * 0.15, 0.0015)
            fundo_img, fundo_extent = baixar_fundo_google_maps(
                todos_lons.min() - dx,
                todos_lons.max() + dx,
                todos_lats.min() - dy,
                todos_lats.max() + dy,
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
            "Mapa de Calor 2D — RSSI Uplink (dBm)",
            "RSSI_Uplink (dBm)",
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
            "Mapa de Calor 2D — SNR Uplink (dB)",
            "SNR_Uplink (dB)",
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
        self.raiz.after(1000, self._agendar_atualizacao)


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


'''
'''


# Exibição | Mapa de Calor GPS 2D [RSSI e SNR] | N6_Mapa_Calor | WissTek-IoT | Framework LoRa
# ====== Nível 6 - Gerência GPS ======
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
    for z in range(18, 8, -1):
        x0, y0 = _lonlat_para_tile(min_lon, max_lat, z)
        x1, y1 = _lonlat_para_tile(max_lon, min_lat, z)
        if abs(x1 - x0) <= 7.0 and abs(y1 - y0) <= 7.0:
            return z
    return 14


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

    if (x_end - x_start + 1) > 9 or (y_end - y_start + 1) > 9:
        zoom = max(10, zoom - 1)
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
                    with urllib.request.urlopen(req, timeout=2.5) as resp:
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


class AplicacaoN6GPS:
    MODOS_VISUALIZACAO = ["Calor + Pontos", "Só Calor", "Só Pontos"]

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("FEE247 - NÍVEL 6 GPS - MAPA DE CALOR 2D [RSSI & SNR] | GATEWAY LORA")
        self.raiz.geometry("1366x800")
        self.raiz.minsize(1140, 700)

        self.auto_refresh_var = tk.BooleanVar(value=True)
        self.tipo_mapa_var = tk.StringVar(value="m")
        self.modo_vis_var = tk.StringVar(value="Calor + Pontos")
        self.raio_max_m_var = tk.StringVar(value="5000")
        self.status_csv_var = tk.StringVar(value="CSV: Nenhum carregado")
        self.status_gw_var = tk.StringVar(value="Distância Nó -> GW: --")

        # Controle para preservar zoom/pan do usuário durante atualização automática
        self._forcar_enquadramento = True
        self._ultimo_csv_visto = None
        self._limites_salvos = {"rssi": None, "snr": None}

        self._construir_painel_gateway()
        self._construir_abas_mapas()
        self._carregar_gw_gps_salvo()
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
            frame_gw, text="Salvar GW_GPS.txt", command=self.salvar_gw_gps
        )
        btn_salvar_gw.pack(side="left", padx=(0, 8))

        ttk.Label(frame_gw, text="Raio (m):").pack(side="left", padx=(4, 2))
        entry_raio = ttk.Entry(frame_gw, width=6, textvariable=self.raio_max_m_var)
        entry_raio.pack(side="left", padx=(0, 8))
        entry_raio.bind("<Return>", lambda _e: self.solicitar_enquadramento_total())

        ttk.Label(frame_gw, text="Modo:").pack(side="left", padx=(4, 2))
        combo_modo = ttk.Combobox(
            frame_gw,
            textvariable=self.modo_vis_var,
            values=self.MODOS_VISUALIZACAO,
            width=13,
            state="readonly",
        )
        combo_modo.pack(side="left", padx=(0, 8))
        combo_modo.bind("<<ComboboxSelected>>", lambda _e: self.atualizar_mapas(manter_vista=True))

        ttk.Label(frame_gw, text="Mapa:").pack(side="left", padx=(4, 2))
        combo_mapa = ttk.Combobox(
            frame_gw,
            textvariable=self.tipo_mapa_var,
            values=["m", "y", "s"],
            width=3,
            state="readonly",
        )
        combo_mapa.pack(side="left", padx=(0, 8))
        combo_mapa.bind("<<ComboboxSelected>>", lambda _e: self.atualizar_mapas(manter_vista=True))

        chk_auto = ttk.Checkbutton(
            frame_gw, text="Auto (1s)", variable=self.auto_refresh_var
        )
        chk_auto.pack(side="left", padx=(0, 6))

        btn_enquadrar = ttk.Button(
            frame_gw, text="Enquadrar Todos", command=self.solicitar_enquadramento_total
        )
        btn_enquadrar.pack(side="left", padx=(0, 4))

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

        self.aba_rssi = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_rssi, text="  Mapa de Calor — RSSI_Uplink  ")
        self.fig_rssi = Figure(figsize=(11, 5.5), dpi=100)
        self.ax_rssi = self.fig_rssi.add_subplot(111)
        self.canvas_rssi, self.cbar_rssi = self._montar_canvas_aba(
            self.aba_rssi, self.fig_rssi, self.ax_rssi, "RSSI_Uplink (dBm)", "rssi"
        )

        self.aba_snr = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_snr, text="  Mapa de Calor — SNR_Uplink  ")
        self.fig_snr = Figure(figsize=(11, 5.5), dpi=100)
        self.ax_snr = self.fig_snr.add_subplot(111)
        self.canvas_snr, self.cbar_snr = self._montar_canvas_aba(
            self.aba_snr, self.fig_snr, self.ax_snr, "SNR_Uplink (dB)", "snr"
        )

    def _montar_canvas_aba(self, parent, fig, ax, label_cbar, chave_vista):
        canvas = FigureCanvasTkAgg(fig, master=parent)
        toolbar = NavigationToolbar2Tk(canvas, parent)
        toolbar.update()
        toolbar.pack(side="top", fill="x")
        canvas.get_tk_widget().pack(fill="both", expand=True)

        mappable = ax.scatter([], [], c=[], cmap=CMAP_CALOR)
        cbar = fig.colorbar(mappable, ax=ax, pad=0.02, fraction=0.04)
        cbar.set_label(label_cbar, fontsize=9)
        fig.subplots_adjust(left=0.07, right=0.95, top=0.92, bottom=0.10)

        def _registrar_vista(_evento=None):
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            if xlim != (0.0, 1.0) or ylim != (0.0, 1.0):
                self._limites_salvos[chave_vista] = (xlim, ylim)

        canvas.mpl_connect("button_release_event", _registrar_vista)
        canvas.mpl_connect("scroll_event", _registrar_vista)
        return canvas, cbar

    def solicitar_enquadramento_total(self):
        self._forcar_enquadramento = True
        self._limites_salvos = {"rssi": None, "snr": None}
        self.atualizar_mapas(manter_vista=False)

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
            self.solicitar_enquadramento_total()
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
        """Desenha círculos de distância concêntricos em torno da posição do Gateway."""
        if span_m <= 150:
            raios = [25, 50, 100]
        elif span_m <= 400:
            raios = [50, 100, 200]
        elif span_m <= 1000:
            raios = [100, 250, 500]
        elif span_m <= 2500:
            raios = [250, 500, 1000]
        else:
            raios = [500, 1000, 2000]

        metros_por_lat = 111320.0
        metros_por_lon = max(111320.0 * math.cos(math.radians(gw_lat)), 1.0)
        theta = np.linspace(0.0, 2.0 * np.pi, 180)

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
                gw_lon + dlon * math.cos(math.pi / 4.0),
                gw_lat + dlat * math.sin(math.pi / 4.0),
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
        chave_vista,
        manter_vista,
    ):
        vista_anterior = self._limites_salvos.get(chave_vista)
        if vista_anterior is None and not self._forcar_enquadramento:
            xlim_atual = ax.get_xlim()
            ylim_atual = ax.get_ylim()
            if xlim_atual != (0.0, 1.0) or ylim_atual != (0.0, 1.0):
                vista_anterior = (xlim_atual, ylim_atual)

        ax.clear()

        if fundo_img is not None and fundo_extent is not None:
            ax.imshow(
                fundo_img,
                extent=fundo_extent,
                origin="upper",
                aspect="auto",
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
            label="Gateway LoRa (Balão GPS)",
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

        # 5. Enquadramento completo de todos os pontos válidos + GW (ou preserva zoom/pan)
        if manter_vista and vista_anterior is not None and not self._forcar_enquadramento:
            ax.set_xlim(vista_anterior[0])
            ax.set_ylim(vista_anterior[1])
        else:
            all_x = np.append(lons, gw_lon)
            all_y = np.append(lats, gw_lat)
            min_x, max_x = float(np.min(all_x)), float(np.max(all_x))
            min_y, max_y = float(np.min(all_y)), float(np.max(all_y))
            marg_x = max((max_x - min_x) * 0.15, 0.0012)
            marg_y = max((max_y - min_y) * 0.15, 0.0012)
            novo_xlim = (min_x - marg_x, max_x + marg_x)
            novo_ylim = (min_y - marg_y, max_y + marg_y)
            ax.set_xlim(novo_xlim)
            ax.set_ylim(novo_ylim)
            self._limites_salvos[chave_vista] = (novo_xlim, novo_ylim)

        if mappable_ref is not None:
            cbar.update_normal(mappable_ref)
        cbar.set_label(f"{label_barra}  [Quente = Alto | Frio = Baixo]", fontsize=8)

        ax.set_title(
            f"{titulo} [{modo}] | Amostras: {len(df)} | Dist. GW: {dists.min():.1f} m – {dists.max():.1f} m (Média: {dists.mean():.1f} m)",
            fontsize=9.5,
        )
        ax.set_xlabel("Longitude (°)", fontsize=8)
        ax.set_ylabel("Latitude (°)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(loc="upper right", fontsize=8)
        canvas.draw()

    def atualizar_mapas(self, manter_vista=True):
        gw_lat = self._parse_float(self.entry_gw_lat.get())
        gw_lon = self._parse_float(self.entry_gw_lon.get())
        gw_alt = self._parse_float(self.entry_gw_alt.get())
        if np.isnan(gw_lat):
            gw_lat = -23.068361
        if np.isnan(gw_lon):
            gw_lon = -46.858277

        raio_max = self._parse_float(self.raio_max_m_var.get())
        if np.isnan(raio_max) or raio_max <= 0:
            raio_max = 5000.0

        modo = self.modo_vis_var.get()
        if modo not in self.MODOS_VISUALIZACAO:
            modo = "Calor + Pontos"

        csv_path = self._obter_ultimo_csv_n5()
        if not csv_path:
            self.status_csv_var.set("CSV: Nenhum Rodada_Gerencia_*.csv encontrado em Dados_Processados")
            return

        if csv_path != self._ultimo_csv_visto:
            self._ultimo_csv_visto = csv_path
            self._forcar_enquadramento = True
            self._limites_salvos = {"rssi": None, "snr": None}

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
            dx = max(np.ptp(todos_lons) * 0.25, 0.002)
            dy = max(np.ptp(todos_lats) * 0.25, 0.002)
            fundo_img, fundo_extent = baixar_fundo_google_maps(
                todos_lons.min() - dx,
                todos_lons.max() + dx,
                todos_lats.min() - dy,
                todos_lats.max() + dy,
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
            "Mapa de Calor 2D — RSSI Uplink (dBm)",
            "RSSI_Uplink (dBm)",
            gw_lat,
            gw_lon,
            fundo_img,
            fundo_extent,
            modo,
            "rssi",
            manter_vista,
        )

        self._plotar_mapa_calor_2d(
            self.fig_snr,
            self.ax_snr,
            self.canvas_snr,
            self.cbar_snr,
            df,
            "SNR_Uplink",
            "Mapa de Calor 2D — SNR Uplink (dB)",
            "SNR_Uplink (dB)",
            gw_lat,
            gw_lon,
            fundo_img,
            fundo_extent,
            modo,
            "snr",
            manter_vista,
        )

        self._forcar_enquadramento = False

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
            self.atualizar_mapas(manter_vista=True)
        self.raiz.after(1000, self._agendar_atualizacao)


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


'''
