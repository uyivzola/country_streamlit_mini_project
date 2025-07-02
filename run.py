import sqlite3

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from folium.plugins import Geocoder, MiniMap, Fullscreen, Draw
from streamlit_folium import st_folium

st.set_page_config(page_title="🌍 World Countries App", layout="wide")


@st.cache_data
def load_data():
    with sqlite3.connect("countries.db") as conn:
        df = pd.read_sql_query("SELECT * FROM countries", conn)
    df['capital_length'] = df['capital'].apply(lambda x: len(x) if x else 0)
    df['capital_length_cat'] = pd.cut(df['capital_length'], bins=[0, 5, 10, 15, 20, 100],
                                      labels=['0-5', '6-10', '11-15', '16-20', '20+'])
    df['density'] = df['population'] / df['area']
    return df


@st.cache_data
def load_geojson():
    return gpd.read_file("world.geojson")


@st.cache_data
def get_country_data_by_cca3(cca3):
    response = requests.get(f"https://restcountries.com/v3.1/alpha/{cca3}")
    if response.status_code == 200:
        return response.json()[0]
    return None


@st.cache_data
def load_worldbank_from_db(cca2):
    with sqlite3.connect("countries.db") as conn:
        df = pd.read_sql_query(f"SELECT * FROM indicators WHERE country_code = '{cca2}'", conn)
    return df


df = load_data()
geo_data = load_geojson()

# ---------------------------- 📊 Dashboard ----------------------------
st.link_button('DM me on Telegram', 'https://t.me/Hopxol')
st.title("📊 Дашборд по странам мира")
st.markdown("""
Этот дашборд использует данные из REST Countries API и визуализирует различные метрики:
- 📌 Население
- 🗺️ География
- 🗣️ Языки
- 🌐 Регионы и субрегионы
""")

map_fig = px.choropleth(
    df,
    locations="cca3",
    color="population",
    hover_name="name_common",
    color_continuous_scale="viridis",
    title="🗺️ Население по странам",
    labels={"population": "Население"}
)
st.plotly_chart(map_fig, use_container_width=True)
st.markdown("---")

# ------------------------- Multiple Charts --------------------------
charts = []

subregions = df['subregion'].value_counts().nlargest(10).reset_index()
subregions.columns = ['Субрегион', 'Количество стран']
fig1 = px.bar(subregions, x='Количество стран', y='Субрегион', orientation='h', color='Субрегион')
charts.append(("🌍 Топ-10 субрегионов", fig1))

fig2 = px.scatter(df, x='area', y='population', log_x=True, log_y=True, color='region')
charts.append(("📏 Площадь vs Население", fig2))

top_lang = df.sort_values(by='language_count', ascending=False).head(15)
fig3 = px.bar(top_lang, x='language_count', y='name_common', orientation='h', color='name_common')
charts.append(("🗣️ Топ-15 по языкам", fig3))

region_counts = df['region'].value_counts().reset_index()
region_counts.columns = ['Регион', 'Количество стран']
fig5 = px.bar(region_counts, x='Количество стран', y='Регион', orientation='h', color='Регион')
charts.append(("🗺️ Страны по регионам", fig5))

top20 = df.sort_values(by='population', ascending=False).head(20)
fig6 = px.bar(top20, x='population', y='name_common', orientation='h', color='name_common')
charts.append(("🏙️ Топ-20 по населению", fig6))

fig7 = px.pie(region_counts, names='Регион', values='Количество стран', hole=0.3)
charts.append(("🌐 Доля регионов", fig7))

avg_lang = df.groupby('region')['language_count'].mean().reset_index()
avg_lang['language_count'] = avg_lang['language_count'].round(1)
fig8 = px.bar(avg_lang, x='language_count', y='region', orientation='h', color='region')
charts.append(("🗣️ Среднее языков по регионам", fig8))

cap_len = df['capital_length_cat'].value_counts().sort_index().reset_index()
cap_len.columns = ['Категория длины столицы', 'Количество стран']
fig9 = px.bar(cap_len, x='Категория длины столицы', y='Количество стран', color='Категория длины столицы')
charts.append(("🏛️ Длина названий столиц", fig9))

for i in range(0, len(charts), 2):
    cols = st.columns(2)
    for j in range(2):
        if i + j < len(charts):
            with cols[j]:
                st.subheader(charts[i + j][0])
                st.plotly_chart(charts[i + j][1], use_container_width=True)

st.markdown("---")

# Use country list from df with name_common and cca3
df_sorted = df.sort_values(by='name_common')
country_options = df_sorted[['name_common', 'cca3']].dropna()

# Set Uzbekistan as default if available
default_country = 'Uzbekistan' if 'Uzbekistan' in country_options['name_common'].values else \
country_options['name_common'].iloc[0]
selected_country_name = st.selectbox("Выберите страну", country_options['name_common'].tolist(),
                                     index=country_options['name_common'].tolist().index(default_country))

selected_cca3 = country_options[country_options['name_common'] == selected_country_name]['cca3'].values[0]
selected_cca2 = df[df['cca3'] == selected_cca3]['cca2'].values[0]
country = get_country_data_by_cca3(selected_cca3)

# ---------------------------- 🌐 Country Details ----------------------------
st.title("🌐 Детали по стране")

if not country:
    st.error("❌ Страна не найдена.")
    st.stop()
# Load World Bank data for cards
wb_data = load_worldbank_from_db(selected_cca2)

# Define key indicators for cards
card_indicators = [
    "gdp_current_usd", "gdp_per_capita", "gdp_growth_percent", "inflation_percent",
    "unemployment_percent", "population_total", "imports_usd", "exports_usd"
]

card_titles = {
    'gdp_current_usd': '💰 ВВП (USD)',
    'population_total': '👥 Население',
    'gdp_per_capita': '👤 ВВП на душу',
    'gdp_growth_percent': '📈 Рост ВВП (%)',
    'inflation_percent': '🔥 Инфляция (%)',
    'unemployment_percent': '📉 Безработица (%)',
    'imports_usd': '📦 Импорт (USD)',
    'exports_usd': '🚢 Экспорт (USD)'
}
if not wb_data.empty:
    card_cols = st.columns(4)
    for i, indicator in enumerate(card_indicators):
        latest = wb_data[(wb_data['indicator'] == indicator) & (wb_data['year'] == 2023)]
        value = latest['value'].values[0] if not latest.empty else None
        label = card_titles.get(indicator, indicator)
        if value is not None:
            with card_cols[i % 4]:
                st.metric(label=label, value=f"{value:,.0f}")
        if (i + 1) % 4 == 0 and i + 1 < len(card_indicators):
            card_cols = st.columns(4)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown(f"## {country['name']['official']} ({country['name']['common']})")
    st.markdown(
        f"**Регион:** {country.get('region', '—')} &nbsp;&nbsp;|&nbsp;&nbsp; **Субрегион:** {country.get('subregion', '—')}")
    st.markdown(
        f"**Столица:** {', '.join(country.get('capital', []))} &nbsp;&nbsp;|&nbsp;&nbsp; **Население:** {country['population']:,}")
    st.markdown(
        f"**Площадь:** {country['area']:,} км² &nbsp;&nbsp;|&nbsp;&nbsp; **Континент:** {', '.join(country.get('continents', []))}")
with col2:
    st.image(country["flags"]["png"], caption="Флаг", width=350)
with col3:
    if "coatOfArms" in country and country["coatOfArms"].get("png"):
        st.image(country["coatOfArms"]["png"], caption="Герб", width=170)

colA, colB = st.columns(2)
with colA:
    st.subheader("💱 Валюта и Языки")
    currencies = country.get("currencies", {})
    if currencies:
        currency_data = [
            {"Код": code, "Название": val["name"], "Символ": val.get("symbol", "")}
            for code, val in currencies.items()
        ]
        st.table(pd.DataFrame(currency_data))
    languages = country.get("languages", {})
    if languages:
        st.write("**Языки:**", ", ".join(languages.values()))
    st.write("**Временные зоны:**", ", ".join(country.get("timezones", [])))
    st.write("**TLD:**", ", ".join(country.get("tld", [])))
    st.write("**FIFA код:**", country.get("fifa", "—"))
with colB:
    st.subheader("Прочее")
    st.write("**Код страны (ISO):**", selected_cca3)
    st.write("**Независимая:**", "Да" if country.get("independent") else "Нет")
    st.write("**Член ООН:**", "Да" if country.get("unMember") else "Нет")
    st.write("**Начало недели:**", country.get("startOfWeek", "—").capitalize())
    borders = country.get("borders", [])
    st.write("**Соседние страны:**", ", ".join(borders) if borders else "—")
    gini = country.get("gini", {})
    if gini:
        gini_year = list(gini.keys())[0]
        st.write(f"**Индекс Джини ({gini_year}):** {gini[gini_year]}")

st.markdown("---")

st.subheader("📈 Экономические показатели (World Bank)")
wb_data = load_worldbank_from_db(selected_cca2)
if not wb_data.empty:
    indicators_list = wb_data['indicator'].unique()
    for i in range(0, len(indicators_list), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(indicators_list):
                indicator = indicators_list[i + j]
                chart_df = wb_data[wb_data['indicator'] == indicator].sort_values('year')
                if not chart_df.empty:
                    title_map = {
                        'gdp_current_usd': '💰 ВВП (текущий, USD)',
                        'gdp_per_capita': '👤 ВВП на душу населения',
                        'gdp_growth_percent': '📈 Рост ВВП (%)',
                        'inflation_percent': '🔥 Инфляция (%)',
                        'unemployment_percent': '📉 Безработица (%)',
                        'population_total': '👥 Население',
                        'imports_usd': '📦 Импорт (USD)',
                        'exports_usd': '🚢 Экспорт (USD)',
                        'exports_pct_gdp': '📊 Экспорт (% ВВП)',
                        'imports_pct_gdp': '📊 Импорт (% ВВП)',
                        'current_account_pct_gdp': '💼 Текущий счёт (% ВВП)',
                        'capital_formation_pct_gdp': '🏗️ Капитальные вложения (% ВВП)',
                        'govt_expenditure_pct_gdp': '🏛️ Госрасходы (% ВВП)'
                    }
                    title = title_map.get(indicator, indicator.replace('_', ' ').capitalize())
                    with cols[j]:
                        st.subheader(title)
                        if indicator in ['gdp_growth_percent', 'inflation_percent', 'unemployment_percent']:
                            fig = px.bar(chart_df, x="year", y="value", text="value")
                        elif indicator in ['population_total']:
                            fig = px.area(chart_df, x="year", y="value")
                        elif indicator in ['exports_pct_gdp', 'imports_pct_gdp']:
                            fig = px.scatter(chart_df, x="year", y="value", color_discrete_sequence=['#00CC96'])
                        else:
                            fig = px.line(chart_df, x="year", y="value", markers=True)

                        # Safely apply text labels if supported
                        try:
                            fig.update_traces(
                                texttemplate='%{text:.2s}',
                                textposition='top center'
                            )
                        except:
                            pass

                        fig.update_layout(
                            yaxis_title="Значение",
                            xaxis_title="Год",
                            height=350,
                            margin=dict(t=10)
                        )
                        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Нет доступных данных для выбранной страны.")


st.markdown("with love 💘 by Behzod Khidirov.")
st.link_button('DM me on Telegram', 'https://t.me/Hopxol')

st.subheader("🗺️ Расширенная карта с границами страны")

geo_match = geo_data[geo_data["iso_a3"] == selected_cca3]

if not geo_match.empty:
    geo_match = geo_match.to_crs(epsg=3857)
    centroid = geo_match.geometry.centroid.to_crs(epsg=4326).iloc[0]

    folium_map = folium.Map(location=[centroid.y, centroid.x], zoom_start=5)

    folium.GeoJson(geo_match.to_crs(epsg=4326), name="Границы страны").add_to(folium_map)

    capital_name = ", ".join(country.get("capital", []))
    capital_coord = country.get("capitalInfo", {}).get("latlng", None)

    if capital_coord:
        folium.Marker(
            location=capital_coord,
            popup=f"Capital: {capital_name}",
            icon=folium.Icon(color="green", icon="flag")
        ).add_to(folium_map)
    else:
        folium.Marker(
            location=[centroid.y, centroid.x],
            popup=f"Capital (approx.): {capital_name}",
            icon=folium.Icon(color="gray", icon="question-sign")
        ).add_to(folium_map)

    Geocoder().add_to(folium_map)
    Fullscreen().add_to(folium_map)
    Draw(export=False).add_to(folium_map)
    MiniMap(position="bottomright").add_to(folium_map)

    st_folium(folium_map, width=1920, height=600)
else:
    st.warning("🌐 Границы страны не найдены в GeoJSON.")

