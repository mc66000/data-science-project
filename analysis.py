"""
Macau Public Toilets — Distribution & Accessibility Analysis (整合版)
Data : macau_toilets.csv (data.gov.mo, IAM)
Run  : python analysis.py
Output:
    ./figures/fig1_region_count.png      各區廁所數量
    ./figures/fig2_accessibility.png     無障礙 / 親子覆蓋率
    ./figures/fig3_map.png               澳門地圖 + 廁所分佈（有底圖）
    ./figures/fig4_wholeday.png          全日開放廁所分析
    ./macau_toilets_map.html             互動地圖（需 folium）

Install:
    pip install pandas numpy matplotlib
    pip install geopandas contextily      # 選用：真實澳門底圖
    pip install folium                    # 選用：互動地圖
"""
import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =============================================================================
# 0. 設定
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "Datasets", "macau_toilets.csv")
OUT_DIR = os.path.join(BASE_DIR, "figures")

os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "PingFang TC",
                                   "Heiti TC", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

ORDER = ["Macau Peninsula", "Taipa", "Coloane"]
COLORS = {"Macau Peninsula": "#4C72B0",
          "Taipa": "#55A868",
          "Coloane": "#C44E52"}

# 設施編號前綴 → 分區
PREFIX_REGION = {
    **{p: "Coloane" for p in ["C", "GC", "JC", "LC"]},
    **{p: "Taipa" for p in ["T", "CT", "GT", "JT", "LT", "MT"]},
    **{p: "Macau Peninsula" for p in ["M", "AM", "CM", "GM", "IM",
                                       "JM", "LM", "MM", "TM", "VM"]},
}

# 需要用到嘅欄位（讀檔時會做容錯對應）
# 必要欄位（缺就報錯）
NEEDED_COLS = ["nameEn", "location", "hasDwc", "hasFwc", "openHourEn"]
# 選用欄位（缺就補預設值）
OPTIONAL_COLS = {"tempClose": False}

# 選用套件偵測
try:
    import geopandas as gpd
    import contextily as cx
    from shapely.geometry import Point
    HAS_BASEMAP = True
except ImportError:
    HAS_BASEMAP = False

try:
    import folium
    from folium.plugins import MarkerCluster
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False


# =============================================================================
# 1. 讀取與清洗
# =============================================================================
def to_bool(series: pd.Series) -> pd.Series:
    """'TRUE'/'FALSE' 字串 → 布林值"""
    return series.astype(str).str.strip().str.upper() == "TRUE"


def parse_latlon(s):
    """'lat,lon' 字串 → (lat, lon)，失敗回傳 (None, None)"""
    try:
        lat, lon = str(s).split(",")
        return float(lat), float(lon)
    except Exception:
        return None, None


def classify_region(name_en: str) -> str:
    m = re.match(r"^([A-Za-z]+)", str(name_en).strip())
    prefix = m.group(1).upper() if m else ""
    return PREFIX_REGION.get(prefix, "Other")


WHOLE_DAY_RE = re.compile(
    r"whole\s*day|all\s*day|24\s*-?\s*h(ou)?rs?|00:00\s*-\s*24:00|全日|全天|24\s*小時",
    re.IGNORECASE,
)

def is_whole_day(hours) -> bool:
    return bool(WHOLE_DAY_RE.search(str(hours)))


def load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise SystemExit(f"搵唔到檔案：{path}")

    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = df.columns.str.strip()

    # 情況一：淨係一欄 → 多數係第一行有一個標題列，真表頭喺第二行
    if len(df.columns) == 1:
        df = pd.read_csv(path, encoding="utf-8-sig", skiprows=1)
        df.columns = df.columns.str.strip()

    # 跳咗一行之後仲係一欄，先至真係分隔符問題
    if len(df.columns) == 1:
        for sep in [";", "\t"]:
            try_df = pd.read_csv(path, encoding="utf-8-sig",
                                 skiprows=1, sep=sep)
            if len(try_df.columns) > 1:
                df = try_df
                df.columns = df.columns.str.strip()
                break
        else:
            raise SystemExit(
                f"試過 skiprows + 逗號/分號/tab 都係一欄，請人手檢查檔案。\n"
                f"欄名：{df.columns[0]!r}")

    # ↓↓↓ 以下同之前一樣：對應欄名、to_bool、parse_latlon…
    lower = {c.lower(): c for c in df.columns}
    rename = {lower[n.lower()]: n for n in NEEDED_COLS
              if n.lower() in lower and lower[n.lower()] != n}
    df = df.rename(columns=rename)

    
    missing = [n for n in NEEDED_COLS if n not in df.columns]
    if missing:
        raise SystemExit(
            f"CSV 缺少欄位 {missing}\n實際欄位：{list(df.columns)}")

    # 補返冇提供嘅選用欄
    for col, default in OPTIONAL_COLS.items():
        if col not in df.columns:
            df[col] = default

    # tempClose 可能係補出嚟嘅布林，或 CSV 入面嘅 TRUE/FALSE 字串
    for col in ["hasDwc", "hasFwc", "tempClose"]:
        df[col] = to_bool(df[col]) 
    df[["lat", "lon"]] = df["location"].apply(
        lambda s: pd.Series(parse_latlon(s)))
    df["region"] = df["nameEn"].apply(classify_region)
    df["wholeDay"] = df["openHourEn"].apply(is_whole_day)
    return df

# =============================================================================
# 2. 統計
# =============================================================================
def summarize(df: pd.DataFrame) -> pd.DataFrame:
    s = df.groupby("region").agg(
        total=("nameEn", "count"),
        dwc=("hasDwc", "sum"),
        fwc=("hasFwc", "sum"),
        wholeday=("wholeDay", "sum"),
        closed=("tempClose", "sum"),
    )
    s["dwc_%"] = (s["dwc"] / s["total"] * 100).round(1)
    s["fwc_%"] = (s["fwc"] / s["total"] * 100).round(1)
    s["wholeday_%"] = (s["wholeday"] / s["total"] * 100).round(1)
    return s.reindex([r for r in ORDER if r in s.index])


def print_summary(df: pd.DataFrame, s: pd.DataFrame):
    print("=== District Summary ===")
    print(s.to_string())
    print(f"\nTotal toilets      : {len(df)}")
    print(f"Barrier-free (DWC) : {df['hasDwc'].sum()} "
          f"({df['hasDwc'].mean()*100:.1f}%)")
    print(f"Parent-child (FWC) : {df['hasFwc'].sum()} "
          f"({df['hasFwc'].mean()*100:.1f}%)")
    print(f"Whole-day open     : {df['wholeDay'].sum()} "
          f"({df['wholeDay'].mean()*100:.1f}%)")
    print(f"Temporarily closed : {df['tempClose'].sum()}")
    missing = df["lat"].isna().sum()
    if missing:
        names = df.loc[df["lat"].isna(), "nameEn"].astype(str).head(3)
        print(f"\n⚠ {missing} row(s) with missing coordinates "
              f"(e.g. {', '.join(names)})")


# =============================================================================
# 3. 圖表
# =============================================================================
def fig1_region_count(s: pd.DataFrame):
    plt.figure(figsize=(8, 5))
    bars = plt.bar(s.index, s["total"], color=[COLORS[r] for r in s.index])
    plt.bar_label(bars, fmt="%d")
    plt.title("Number of Public Toilets by District in Macau")
    plt.ylabel("Number of toilets")
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/fig1_region_count.png", dpi=150)
    plt.close()


def fig2_accessibility(s: pd.DataFrame):
    x, w = np.arange(len(s)), 0.35
    plt.figure(figsize=(9, 5))
    b1 = plt.bar(x - w/2, s["dwc_%"], w, label="Barrier-free %", color="#4C72B0")
    b2 = plt.bar(x + w/2, s["fwc_%"], w, label="Parent-child %", color="#DD8452")
    plt.bar_label(b1, fmt="%.1f%%")
    plt.bar_label(b2, fmt="%.1f%%")
    plt.xticks(x, s.index)
    plt.ylabel("Share of district's toilets (%)")
    plt.title("Barrier-free & Parent-child Coverage by District")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/fig2_accessibility.png", dpi=150)
    plt.close()


def fig3_map(df: pd.DataFrame):
    """澳門地圖 + 廁所分佈。有 contextily 就貼真實底圖，否則純散點。"""
    geo = df.dropna(subset=["lat", "lon"]).copy()
    fig, ax = plt.subplots(figsize=(10, 10))

    if HAS_BASEMAP:
        # 關鍵：WGS84 → Web Mercator，先至同網絡底圖對齊
        gdf = gpd.GeoDataFrame(
            geo,
            geometry=[Point(xy) for xy in zip(geo["lon"], geo["lat"])],
            crs="EPSG:4326",
        ).to_crs(epsg=3857)

        for region, c in COLORS.items():
            sub = gdf[gdf["region"] == region]
            if len(sub):
                sub.plot(ax=ax, color=c, markersize=45, edgecolor="white",
                         linewidth=0.5, alpha=0.9,
                         label=f"{region} (n={len(sub)})")

        fwc = gdf[gdf["hasFwc"]]
        if len(fwc):
            fwc.plot(ax=ax, facecolor="none", edgecolor="red",
                     markersize=160, linewidth=1.6,
                     label="Has parent-child (FWC)")

        try:
            cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik,
                           zoom=14)
        except Exception as e:
            print(f"⚠ 底圖下載失敗（可能無網絡）：{e}")
        ax.set_axis_off()
        subtitle = "with OpenStreetMap basemap"
    else:
        for region, c in COLORS.items():
            sub = geo[geo["region"] == region]
            ax.scatter(sub["lon"], sub["lat"], s=45, c=c,
                       label=f"{region} (n={len(sub)})",
                       edgecolors="white", linewidths=0.5, alpha=0.9)
        fwc = geo[geo["hasFwc"]]
        ax.scatter(fwc["lon"], fwc["lat"], s=160, facecolors="none",
                   edgecolors="red", linewidths=1.6,
                   label="Has parent-child (FWC)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.set_aspect("equal", adjustable="datalim")
        subtitle = "lat/lon scatter — install geopandas+contextily for basemap"

    ax.set_title("Geographic Distribution of Macau Public Toilets\n"
                 f"(coloured by district; red ring = parent-child; {subtitle})")
    ax.legend(loc="upper left", fontsize=9)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/fig3_map.png", dpi=150)
    plt.close()


def fig4_wholeday(s: pd.DataFrame):
    """全日開放 vs 全部廁所（遊客實際可用數量）"""
    x, w = np.arange(len(s)), 0.35
    plt.figure(figsize=(9, 5))
    b1 = plt.bar(x - w/2, s["total"], w, label="All toilets", color="#BBBBBB")
    b2 = plt.bar(x + w/2, s["wholeday"], w, label="Whole-day open",
                 color=[COLORS[r] for r in s.index])
    plt.bar_label(b1, fmt="%d")
    plt.bar_label(b2, labels=[f"{v}\n({p:.0f}%)" for v, p
                              in zip(s["wholeday"], s["wholeday_%"])])
    plt.xticks(x, s.index)
    plt.ylabel("Number of toilets")
    plt.title("Whole-day Open Toilets by District (tourist-usable network)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/fig4_wholeday.png", dpi=150)
    plt.close()


def folium_map(df: pd.DataFrame, path=None):
    """互動地圖（需 folium + 網絡）"""
    if path is None:
        path = os.path.join(BASE_DIR, "macau_toilets_map.html")
    if not HAS_FOLIUM:
        print("(folium 未安裝，跳過互動地圖；pip install folium 可啟用)")
        return
    geo = df.dropna(subset=["lat", "lon"])
    m = folium.Map(location=[22.17, 113.55], zoom_start=12,
                   tiles="OpenStreetMap")
    cluster = MarkerCluster().add_to(m)
    for _, r in geo.iterrows():
        tags = [t for t, ok in [("Barrier-free", r["hasDwc"]),
                                 ("Parent-child", r["hasFwc"]),
                                 ("Whole-day", r["wholeDay"]),
                                 ("⚠ TEMP CLOSED", r["tempClose"])] if ok]
        color = ("black" if r["tempClose"] else
                 "red" if r["hasFwc"] else
                 "blue" if r["hasDwc"] else "gray")
        popup = (f"<b>{r['nameEn']}</b><br>{r.get('addressEn', '')}<br>"
                 f"{', '.join(tags) or 'Standard'}")
        folium.CircleMarker([r["lat"], r["lon"]], radius=5, color=color,
                            fill=True, fill_opacity=0.8,
                            popup=folium.Popup(popup, max_width=250)
                            ).add_to(cluster)
    m.save(path)
    print(f"Interactive map saved: {path} "
          "(red=parent-child, blue=barrier-free, gray=standard)")


# =============================================================================
# 4. 主程式
# =============================================================================
def main():
    df = load_data(CSV_PATH)

    # 睇吓 openHourEn 有邊幾種寫法，方便確認 whole-day regex 有冇漏
    print("\n=== openHourEn 寫法（前 15 種）===")
    print(df["openHourEn"].value_counts(dropna=False).head(15))

    s = summarize(df)
    print()
    print_summary(df, s)

    fig1_region_count(s)
    fig2_accessibility(s)
    fig3_map(df)
    fig4_wholeday(s)
    print(f"\nCharts saved to ./figures/  "
          f"(basemap: {'ON' if HAS_BASEMAP else 'OFF'})")

    folium_map(df)


if __name__ == "__main__":
    main()