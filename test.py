import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
import json
from pymongo import MongoClient
from streamlit_folium import st_folium
from folium import Choropleth

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
    df = pd.DataFrame(list(client[DB_NAME][COLLECTION_NAME].find({})))
    df = df.dropna(subset=["purchaseDate", "quantity", "country"])
    df["ISO_A3"] = df["country"].map(ISO_MAP)
    return df

@st.cache_data(ttl=600)
def load_geojson(path="countriesgeo.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# ─── FONCTIONS DE VISUALISATION ─────────────────────────────────────────────────
def draw_bar_by_country(df: pd.DataFrame, width: int, height: int):
    agg = df.groupby("country", as_index=False)["quantity"].sum()
    fig = px.bar(agg, x="country", y="quantity",
                 title="Ventes totales de pommes par pays",
                 labels={"quantity": "Quantité vendue", "country": "Pays"},
                 width=width, height=height)
    st.plotly_chart(fig, use_container_width=False)


def draw_region_bar(df: pd.DataFrame):
    dfr = df.copy()
    dfr["region"] = dfr["country"].map(
        {c: r for r, lst in REGION_PRESETS.items() for c in lst}
    ).fillna("Autres")
    agg = dfr.groupby("region", as_index=False)["quantity"].sum()
    fig = px.bar(agg, x="region", y="quantity",
                 title="Comparaison des ventes par région",
                 color="region",
                 color_discrete_map={"Nordiques": "crimson", "Europe de l'Ouest": "gray", "Autres": "lightgray"})
    st.plotly_chart(fig, use_container_width=True)


def draw_radar_chart(df: pd.DataFrame, countries: list):
    if not countries:
        st.info("Sélectionnez des pays pour afficher le radar chart.")
        return
    agg = df[df.country.isin(countries)].groupby("country")["quantity"].sum().reindex(countries)
    r = agg.tolist() + [agg.tolist()[0]]
    theta = countries + [countries[0]]
    fig = go.Figure(data=go.Scatterpolar(r=r, theta=theta, fill="toself", marker=dict(color="firebrick")))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True)),
                      title="Radar chart des ventes (sélection)")
    st.plotly_chart(fig, use_container_width=True)


def draw_interactive_country_map(df: pd.DataFrame, map_height=800):
    # Agrégation par ISO
    stats = df.groupby("ISO_A3").quantity.agg(total="sum", transactions="count").reset_index()
    extras = df.groupby("ISO_A3").quantity.agg(average="mean", maximum="max").reset_index()
    stats = stats.merge(extras, on="ISO_A3")

    # Charger GeoJSON
    geojson_data = load_geojson()

    # Construire la carte avec style clair
    m = folium.Map(location=[54, 15], zoom_start=4, tiles="CartoDB positron")

    # Ajouter choropleth pour les couleurs
    Choropleth(
        geo_data=geojson_data,
        name="Ventes",
        data=stats,
        columns=["ISO_A3", "total"],
        key_on="feature.id",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Total de pommes vendues",
        highlight=True
    ).add_to(m)

    # Préparer un GeoJson layer pour les tooltips
    # On enrichit chaque feature avec les propriétés
    iso_to_props = stats.set_index("ISO_A3")[['total','transactions','average','maximum']].to_dict(orient='index')
    def lookup_props(feature):
        iso = feature.get('id')
        props = iso_to_props.get(iso, {'total':0,'transactions':0,'average':0,'maximum':0})
        return {
            'name': iso,
            'total': int(props['total']),
            'transactions': int(props['transactions']),
            'average': round(props['average'],1),
            'maximum': int(props['maximum'])
        }

    def add_properties(feature):
        feature['properties'].update(lookup_props(feature))
        return feature

    # Appliquer l'enrichissement
    geojson_data['features'] = [add_properties(f) for f in geojson_data['features']]

    # Ajouter le GeoJson avec tooltip
    folium.GeoJson(
        geojson_data,
        name="Info",
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "total", "transactions", "average", "maximum"],
            aliases=["Pays :", "Total :", "Transactions :", "Moyenne :", "Max :"],
            localize=True,
            sticky=True
        )
    ).add_to(m)

    folium.LayerControl().add_to(m)
    # Afficher la carte
    st_folium(m, width=1000, height=map_height)


# ─── APP STREAMLIT ───────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Dashboard ventes pommes", layout="wide")
    st.title("📊 Dashboard des ventes de pommes")

    df = load_data()
    pays = sorted(df["country"].unique())

    # Sidebar
    st.sidebar.header("Filtres")
    preset = st.sidebar.selectbox("Choisir un preset de région", list(REGION_PRESETS.keys()), index=0)
    preset_list = REGION_PRESETS[preset]
    default_countries = [c for c in preset_list if c in pays] if preset_list else []
    sel = st.sidebar.multiselect("Pays", pays, default=default_countries)
    df_filt = df[df["country"].isin(sel)]

    # Carte + tableau détails
    st.markdown("### Carte interactive des ventes et Détails")
    col1, col2 = st.columns((2, 1))
    with col1:
        draw_interactive_country_map(df_filt)
    with col2:
        st.markdown("#### Détails des ventes sélectionnées")
        st.dataframe(df_filt[["purchaseDate", "quantity", "country"]]
                     .sort_values("purchaseDate").reset_index(drop=True), use_container_width=True)

    # Comparaison par région
    st.markdown("### Comparaison des ventes par région")
    draw_region_bar(df)

    # Radar chart dynamique
    st.markdown("### Radar chart des ventes sélectionnées")
    draw_radar_chart(df, sel)

    # Télécharger
    st.markdown("---")
    st.download_button("Télécharger CSV", df_filt.to_csv(index=False).encode("utf-8"),
                       "sales_export.csv", "text/csv")

if __name__ == "__main__":
    main()