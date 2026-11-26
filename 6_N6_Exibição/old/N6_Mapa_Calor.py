# Exibição | Mapa de Calor GPS [RSSI e SNR] | N6_GPS | WissTek-IoT | Framework LoRa
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
CMAP_CALOR = "jet"


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
        if abs(x1 - x0) <= 6.0 and abs(y1 - y0) <= 6.0:
            return z
    return 14


def baixar_fundo_google_maps(min_lon, max_lon, min_lat, max_lat, tipo_mapa="m", zoom=None):
    """
    Monta imagem de fundo do Google Maps (lyrs='m' mapa padrão ou 's'/'y' satélite/híbrido)
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
    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("FEE247 - NÍVEL 6 GPS - MAPA DE CALOR [RSSI & SNR] | GATEWAY LORA")
        self.raiz.geometry("1366x800")
        self.raiz.minsize(1120, 700)

        self.auto_refresh_var = tk.BooleanVar(value=True)
        self.tipo_mapa_var = tk.StringVar(value="m")
        self.raio_max_m_var = tk.StringVar(value="3000")
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

        ttk.Label(frame_gw, text="Latitude (°):").pack(side="left", padx=(2, 2))
        self.entry_gw_lat = ttk.Entry(frame_gw, width=14)
        self.entry_gw_lat.insert(0, "-23.068361")
        self.entry_gw_lat.pack(side="left", padx=(0, 8))

        ttk.Label(frame_gw, text="Longitude (°):").pack(side="left", padx=(2, 2))
        self.entry_gw_lon = ttk.Entry(frame_gw, width=14)
        self.entry_gw_lon.insert(0, "-46.858277")
        self.entry_gw_lon.pack(side="left", padx=(0, 8))

        ttk.Label(frame_gw, text="Altitude (m):").pack(side="left", padx=(2, 2))
        self.entry_gw_alt = ttk.Entry(frame_gw, width=10)
        self.entry_gw_alt.insert(0, "800.0")
        self.entry_gw_alt.pack(side="left", padx=(0, 10))

        btn_salvar_gw = ttk.Button(
            frame_gw, text="Salvar GW_GPS.txt", command=self.salvar_gw_gps
        )
        btn_salvar_gw.pack(side="left", padx=(0, 8))

        ttk.Label(frame_gw, text="Raio Máx. (m):").pack(side="left", padx=(6, 2))
        entry_raio = ttk.Entry(frame_gw, width=7, textvariable=self.raio_max_m_var)
        entry_raio.pack(side="left", padx=(0, 8))

        ttk.Label(frame_gw, text="Fundo Google Maps:").pack(side="left", padx=(4, 2))
        combo_mapa = ttk.Combobox(
            frame_gw,
            textvariable=self.tipo_mapa_var,
            values=["m", "y", "s"],
            width=4,
            state="readonly",
        )
        combo_mapa.pack(side="left", padx=(0, 8))

        chk_auto = ttk.Checkbutton(
            frame_gw, text="Atualizar (1s)", variable=self.auto_refresh_var
        )
        chk_auto.pack(side="left", padx=(0, 8))

        btn_atualizar = ttk.Button(
            frame_gw, text="Atualizar Agora", command=self.atualizar_mapas
        )
        btn_atualizar.pack(side="left", padx=(0, 4))

        btn_exportar = ttk.Button(
            frame_gw, text="Salvar Imagens", command=self.salvar_figuras
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
            self.aba_rssi, self.fig_rssi, self.ax_rssi, "RSSI_Uplink (dBm)"
        )

        self.aba_snr = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_snr, text="  Mapa de Calor — SNR_Uplink  ")
        self.fig_snr = Figure(figsize=(11, 5.5), dpi=100)
        self.ax_snr = self.fig_snr.add_subplot(111)
        self.canvas_snr, self.cbar_snr = self._montar_canvas_aba(
            self.aba_snr, self.fig_snr, self.ax_snr, "SNR_Uplink (dB)"
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
            print(f"[N6_GPS] Aviso ao carregar GW_GPS.txt: {e}")

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

    def _plotar_mapa_calor(
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
    ):
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

        if len(df) >= 4 and (np.ptp(lons) > 1e-7) and (np.ptp(lats) > 1e-7):
            pad_x = max(np.ptp(lons) * 0.08, 0.0005)
            pad_y = max(np.ptp(lats) * 0.08, 0.0005)
            gx = np.linspace(lons.min() - pad_x, lons.max() + pad_x, 110)
            gy = np.linspace(lats.min() - pad_y, lats.max() + pad_y, 110)
            GX, GY = np.meshgrid(gx, gy)
            GZ = griddata((lons, lats), vals, (GX, GY), method="linear")
            ax.pcolormesh(
                GX,
                GY,
                GZ,
                cmap=CMAP_CALOR,
                vmin=vmin,
                vmax=vmax,
                alpha=0.55,
                shading="auto",
                zorder=2,
            )

        sc = ax.scatter(
            lons,
            lats,
            c=vals,
            cmap=CMAP_CALOR,
            vmin=vmin,
            vmax=vmax,
            s=18,
            alpha=0.88,
            edgecolors="black",
            linewidths=0.25,
            zorder=3,
            label="Nó Sensor (amostras válidas)",
        )

        ax.scatter(
            [gw_lon],
            [gw_lat],
            marker="^",
            s=220,
            c="#111111",
            edgecolors="#FFFFFF",
            linewidths=1.5,
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

        if fundo_extent is not None:
            ax.set_xlim(fundo_extent[0], fundo_extent[1])
            ax.set_ylim(fundo_extent[2], fundo_extent[3])
        else:
            marg_x = max(np.ptp(lons) * 0.15, 0.001)
            marg_y = max(np.ptp(lats) * 0.15, 0.001)
            ax.set_xlim(min(lons.min(), gw_lon) - marg_x, max(lons.max(), gw_lon) + marg_x)
            ax.set_ylim(min(lats.min(), gw_lat) - marg_y, max(lats.max(), gw_lat) + marg_y)

        cbar.update_normal(sc)
        cbar.set_label(f"{label_barra}  [Quente = Alto | Frio = Baixo]", fontsize=8)

        ax.set_title(
            f"{titulo} | Amostras: {len(df)} | Dist. GW: {dists.min():.1f} m – {dists.max():.1f} m (Média: {dists.mean():.1f} m)",
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
            raio_max = 3000.0

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

        self._plotar_mapa_calor(
            self.fig_rssi,
            self.ax_rssi,
            self.canvas_rssi,
            self.cbar_rssi,
            df,
            "RSSI_Uplink",
            "Mapa de Calor — RSSI Uplink (dBm)",
            "RSSI_Uplink (dBm)",
            gw_lat,
            gw_lon,
            fundo_img,
            fundo_extent,
        )

        self._plotar_mapa_calor(
            self.fig_snr,
            self.ax_snr,
            self.canvas_snr,
            self.cbar_snr,
            df,
            "SNR_Uplink",
            "Mapa de Calor — SNR Uplink (dB)",
            "SNR_Uplink (dB)",
            gw_lat,
            gw_lon,
            fundo_img,
            fundo_extent,
        )

    def salvar_figuras(self):
        caminho_base = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialfile="Mapa_Calor_LoRa_GPS.png",
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
        if messagebox.askokcancel("Sair", "Deseja encerrar o N6_GPS?"):
            raiz.destroy()

    raiz.protocol("WM_DELETE_WINDOW", ao_fechar)
    raiz.mainloop()


if __name__ == "__main__":
    main()
