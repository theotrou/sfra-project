import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from pymongo import MongoClient
from streamlit_folium import st_folium
import math

# ─── CONFIGURATION ──────────────────────────────────────────────────────────────
MONGO_URI       = "mongodb://127.0.0.1:27017/"
DB_NAME         = "appleSales"
COLLECTION_NAME = "sales"

# Coordonnées complètes des capitales
COUNTRY_COORDS = {
    # Europe
    "Albanie":               (41.3275, 19.8187),
    "Allemagne":             (52.5200, 13.4050),
    "Andorre":               (42.5063, 1.5218),
    "Arménie":               (40.1792, 44.4991),
    "Autriche":              (48.2082, 16.3738),
    "Azerbaïdjan":           (40.4093, 49.8671),
    "Biélorussie":           (53.9045, 27.5615),
    "Belgique":              (50.8503, 4.3517),
    "Bosnie-Herzégovine":    (43.8563, 18.4131),
    "Bulgarie":              (42.6977, 23.3219),
    "Chypre":                (35.1856, 33.3823),
    "Croatie":               (45.8144, 15.9780),
    "Danemark":              (55.6761, 12.5683),
    "Espagne":               (40.4168, -3.7038),
    "Estonie":               (59.4370, 24.7536),
    "Finlande":              (60.1699, 24.9384),
    "France":                (48.8566, 2.3522),
    "Géorgie":               (41.7151, 44.8271),
    "Grèce":                 (37.9838, 23.7275),
    "Hongrie":               (47.4979, 19.0402),
    "Irlande":               (53.3498, -6.2603),
    "Islande":               (64.1265, -21.8174),
    "Italie":                (41.9028, 12.4964),
    "Kazakhstan":            (51.1605, 71.4704),
    "Kosovo":                (42.6629, 21.1655),
    "Lettonie":              (56.9496, 24.1052),
    "Liechtenstein":         (47.1410, 9.5215),
    "Lituanie":              (54.6872, 25.2797),
    "Luxembourg":            (49.6116, 6.1319),
    "Malte":                 (35.9375, 14.3754),
    "Moldavie":              (47.0105, 28.8638),
    "Monaco":                (43.7384, 7.4246),
    "Monténégro":            (42.4304, 19.2594),
    "Norvège":               (59.9139, 10.7522),
    "Pays-Bas":              (52.3676, 4.9041),
    "Pologne":               (52.2297, 21.0122),
    "Portugal":              (38.7223, -9.1393),
    "République tchèque":    (50.0755, 14.4378),
    "Roumanie":              (44.4268, 26.1025),
    "Royaume-Uni":           (51.5074, -0.1278),
    "Russie":                (55.7558, 37.6176),
    "Saint-Marin":           (43.9424, 12.4578),
    "Serbie":                (44.7866, 20.4489),
    "Slovaquie":             (48.1486, 17.1077),
    "Slovénie":              (46.0569, 14.5058),
    "Suède":                 (59.3293, 18.0686),
    "Suisse":                (46.9480, 7.4474),
    "Turquie":               (39.9334, 32.8597),
    "Ukraine":               (50.4501, 30.5234),
    "Vatican":               (41.9029, 12.4534),
    # Autres
    "Brésil":                (-15.7939, -47.8828),
    "États-Unis":            (38.9072, -77.0369),
    "Japon":                 (35.6895, 139.6917),
    "Afrique du Sud":        (-25.7479, 28.2293),
}

# Presets de régions
REGION_PRESETS = {
    "Aucun": [],
    "Nordiques": ["Danemark", "Finlande", "Islande", "Norvège", "Suède"],
    "Europe de l'Ouest": ["France", "Allemagne", "Belgique", "Pays-Bas", "Luxembourg", "Irlande", "Suisse", "Autriche"],
    "Europe de l'Est": ["Pologne", "République tchèque", "Slovaquie", "Hongrie", "Bulgarie", "Roumanie"],
    "Asie": ["Japon", "Chypre", "Russie", "Kazakhstan", "Géorgie", "Arménie", "Azerbaïdjan"],
    "Amériques": ["États-Unis", "Brésil"],
}

# ─── CHARGEMENT DES DONNÉES ──────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_data():
    client = MongoClient(MONGO_URI)
    df = pd.DataFrame(list(
        client[DB_NAME][COLLECTION_NAME].find({})
    ))
    return df.dropna(subset=["purchaseDate","quantity","country"])

# ─── FONCTIONS DE VISUALISATION ─────────────────────────────────────────────────
def draw_bar_by_country(df: pd.DataFrame):
    agg = df.groupby("country", as_index=False)["quantity"].sum()
    fig = px.bar(
        agg,
        x="country",
        y="quantity",
        title="Ventes totales de pommes par pays",
        labels={"quantity": "Quantité vendue", "country": "Pays"}
    )
    st.plotly_chart(fig, use_container_width=True)


def draw_interactive_country_map(df: pd.DataFrame, map_height=700):
    stats = (
        df.groupby("country")
          .quantity
          .agg(total="sum", average="mean", maximum="max", count="count")
          .reset_index()
    )
    m = folium.Map(location=(54, 15), zoom_start=4)
    for _, row in stats.iterrows():
        country = row["country"]
        coords = COUNTRY_COORDS.get(country)
        if not coords:
            continue
        lat, lon = coords
        total     = int(row["total"])
        avg       = row["average"]
        maxi      = int(row["maximum"])
        cnt       = int(row["count"])
        radius    = math.sqrt(total) * 4
        popup_html = f"""
        <b>{country}</b><br>
        Total vendu : {total}<br>
        Transactions : {cnt}<br>
        Moyenne : {avg:.1f}<br>
        Maximum : {maxi}
        """
        folium.CircleMarker(
            location=(lat, lon),
            radius=radius,
            color="crimson",
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{country} – {total} pommes"
        ).add_to(m)
    folium.LayerControl().add_to(m)
    st_folium(m, width=1000, height=map_height)

# ─── APP STREAMLIT ───────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Dashboard ventes pommes", layout="wide")
    st.title("📊 Dashboard des ventes de pommes")

    df = load_data()
    pays = sorted(df["country"].unique())

    # Sidebar : presets + multiselect vide par défaut
    st.sidebar.header("Filtres")
    preset = st.sidebar.selectbox("Choisir un preset de région", list(REGION_PRESETS.keys()), index=0)
    preset_list = REGION_PRESETS[preset]
    default_countries = [c for c in preset_list if c in pays] if preset_list else []
    sel = st.sidebar.multiselect("Pays", pays, default=default_countries)
    # Aucun pays sélectionné -> df_filt vide
    df_filt = df[df["country"].isin(sel)]

    # Affichage du tableau des données
    st.markdown("### Extrait des ventes")
    st.dataframe(
        df_filt[["purchaseDate","quantity","country"]]
        .sort_values("purchaseDate")
        .reset_index(drop=True),
        use_container_width=True
    )

    # Affichage du bar chart
    st.markdown("### Ventes par pays")
    draw_bar_by_country(df_filt)

    # Carte en dessous, plus grande
    st.markdown("### Carte interactive des ventes")
    draw_interactive_country_map(df_filt, map_height=800)

    # Télécharger
    st.markdown("---")
    st.download_button(
        "Télécharger CSV", df_filt.to_csv(index=False).encode("utf-8"),
        "sales_export.csv", "text/csv"
    )

if __name__ == "__main__":
    main()
