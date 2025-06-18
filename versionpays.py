import streamlit as st
import pandas as pd
import plotly.express as px
import folium
import json
from pymongo import MongoClient
from streamlit_folium import st_folium
from folium import Choropleth
import math

# ─── CONFIGURATION ──────────────────────────────────────────────────────────────
MONGO_URI       = "mongodb://127.0.0.1:27017/"
DB_NAME         = "appleSales"
COLLECTION_NAME = "sales"

# Dictionnaire Français → ISO A3
ISO_MAP = {
    "Albanie": "ALB", "Allemagne": "DEU", "Andorre": "AND", "Arménie": "ARM",
    "Autriche": "AUT", "Azerbaïdjan": "AZE", "Biélorussie": "BLR", "Belgique": "BEL",
    "Bosnie-Herzégovine": "BIH", "Bulgarie": "BGR", "Chypre": "CYP", "Croatie": "HRV",
    "Danemark": "DNK", "Espagne": "ESP", "Estonie": "EST", "Finlande": "FIN",
    "France": "FRA", "Géorgie": "GEO", "Grèce": "GRC", "Hongrie": "HUN",
    "Irlande": "IRL", "Islande": "ISL", "Italie": "ITA", "Kazakhstan": "KAZ",
    "Kosovo": "XKX", "Lettonie": "LVA", "Liechtenstein": "LIE", "Lituanie": "LTU",
    "Luxembourg": "LUX", "Malte": "MLT", "Moldavie": "MDA", "Monaco": "MCO",
    "Monténégro": "MNE", "Norvège": "NOR", "Pays-Bas": "NLD", "Pologne": "POL",
    "Portugal": "PRT", "République tchèque": "CZE", "Roumanie": "ROU",
    "Royaume-Uni": "GBR", "Russie": "RUS", "Saint-Marin": "SMR", "Serbie": "SRB",
    "Slovaquie": "SVK", "Slovénie": "SVN", "Suède": "SWE", "Suisse": "CHE",
    "Turquie": "TUR", "Ukraine": "UKR", "Vatican": "VAT",
    "Brésil": "BRA", "États-Unis": "USA", "Japon": "JPN", "Afrique du Sud": "ZAF"
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
    df = df.dropna(subset=["purchaseDate", "quantity", "country"])
    df["ISO_A3"] = df["country"].map(ISO_MAP)
    return df

@st.cache_data(ttl=600)
def load_geojson(path="C:/Users/PC/Documents/safr-projet/countriesgeo.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# ─── FONCTIONS DE VISUALISATION ─────────────────────────────────────────────────
def draw_bar_by_country(df: pd.DataFrame, width: int, height: int):
    agg = df.groupby("country", as_index=False)["quantity"].sum()
    fig = px.bar(
        agg,
        x="country",
        y="quantity",
        title="Ventes totales de pommes par pays",
        labels={"quantity": "Quantité vendue", "country": "Pays"},
        width=width,
        height=height
    )
    st.plotly_chart(fig, use_container_width=False)


def draw_interactive_country_map(df: pd.DataFrame, map_height=800):
    # Agrégation par ISO
    stats = (
        df.groupby("ISO_A3", as_index=False)
          .quantity
          .agg(total="sum", transactions="count")
          .rename(columns={"quantity": "total"})
    )
    # Calculer aussi moyenne et maximum si besoin
    extras = (
        df.groupby("ISO_A3", as_index=False)
          .quantity
          .agg(average="mean", maximum="max")
    )
    stats = stats.merge(extras, on="ISO_A3", how="left")

    geojson_data = load_geojson()

    # Créer la carte
    m = folium.Map(location=(54, 15), zoom_start=4)

    # Choropleth pour le remplissage
    Choropleth(
        geo_data=geojson_data,
        name="Ventes de pommes",
        data=stats,
        columns=["ISO_A3", "total"],
        key_on="feature.id",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Total de pommes vendues",
        highlight=True
    ).add_to(m)

    # Ajouter un GeoJson pour les tooltips
    def style_tooltip(feature):
        return {
            'fillColor': 'transparent', 'color': 'transparent', 'weight': 0
        }

    tooltip_fields = ['country', 'total', 'transactions', 'average', 'maximum']
    # Préparer les propriétés de chaque feature
    for feat in geojson_data['features']:
        iso = feat.get('id')
        row = stats[stats.ISO_A3 == iso]
        if not row.empty:
            feat['properties']['country'] = row.iloc[0]['ISO_A3']  # ou mapping inverse
            feat['properties']['total'] = int(row.iloc[0]['total'])
            feat['properties']['transactions'] = int(row.iloc[0]['transactions'])
            feat['properties']['average'] = round(row.iloc[0]['average'], 1)
            feat['properties']['maximum'] = int(row.iloc[0]['maximum'])
        else:
            feat['properties']['country'] = feat['id']
            feat['properties']['total'] = 0
            feat['properties']['transactions'] = 0
            feat['properties']['average'] = 0
            feat['properties']['maximum'] = 0

    folium.GeoJson(
        geojson_data,
        name="Info",
        style_function=style_tooltip,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=["Code ISO:", "Total vendu:", "Transactions:", "Moyenne:", "Maximum:"],
            localize=True,
            sticky=True,
            labels=True
        )
    ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=1200, height=map_height)

# ─── APP STREAMLIT ───────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Dashboard ventes pommes", layout="wide")
    st.title("📊 Dashboard des ventes de pommes")

    # 1) Charger les données
    df = load_data()
    pays = sorted(df["country"].unique())

    # 2) Sidebar : presets + multiselect
    st.sidebar.header("Filtres")
    preset = st.sidebar.selectbox("Choisir un preset de région", list(REGION_PRESETS.keys()), index=0)
    preset_list = REGION_PRESETS[preset]
    default_countries = [c for c in preset_list if c in pays] if preset_list else []
    sel = st.sidebar.multiselect("Pays", pays, default=default_countries)
    df_filt = df[df["country"].isin(sel)]

    # 3) Sidebar : contrôles du bar chart
    st.sidebar.markdown("---")
    st.sidebar.header("Taille du bar chart")
    chart_width  = st.sidebar.slider("Largeur (px)", min_value=400, max_value=1600, value=800, step=50)
    chart_height = st.sidebar.slider("Hauteur (px)", min_value=300, max_value=1000, value=600, step=50)

    # 4) Bar chart
    st.markdown("### Ventes par pays")
    draw_bar_by_country(df_filt, width=chart_width, height=chart_height)

    # 5) Carte et tableau côte-à-côte
    st.markdown("### Carte interactive des ventes et Détails")
    col1, col2 = st.columns((2, 1))
    with col1:
        draw_interactive_country_map(df_filt)
    with col2:
        st.markdown("#### Détails des ventes sélectionnées")
        st.dataframe(
            df_filt[["purchaseDate", "quantity", "country"]]
            .sort_values("purchaseDate")
            .reset_index(drop=True),
            use_container_width=True
        )

    # 6) Télécharger
    st.markdown("---")
    st.download_button(
        "Télécharger CSV", df_filt.to_csv(index=False).encode("utf-8"),
        "sales_export.csv", "text/csv"
    )

if __name__ == "__main__":
    main()
