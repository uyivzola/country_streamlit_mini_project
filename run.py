import sqlite3

import folium
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
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

df = load_data()

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

# Define chart blocks
charts = []


def fmt(val): return f"{val:.1f}" if isinstance(val, float) else val


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

# ---------------------------- 🌐 Country Details ----------------------------
st.title("🌐 Детали по стране")

country_name = st.text_input("Введите название страны", "Uzbekistan")


@st.cache_data
def get_country_data(name):
    response = requests.get(f"https://restcountries.com/v3.1/name/{name}")
    if response.status_code == 200:
        return response.json()[0]
    return None


country = get_country_data(country_name)

if not country:
    st.error("❌ Страна не найдена. Проверьте правильность написания.")
    st.stop()

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
    st.subheader("📌 Прочее")
    st.write("**Код страны (ISO):**", country.get("cca3", "—"))
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

st.subheader("🗺️ Карта расположения страны")
latlng = country.get("latlng", [0, 0])
m = folium.Map(location=latlng, zoom_start=5)
folium.Marker(location=latlng, popup=country['name']['common']).add_to(m)
st_folium(m, width=1920, height=600)
st.markdown("---")

st.markdown("with love 💘 by Behzod Khidirov.")
st.link_button('DM me on Telegram', 'https://t.me/Hopxol')
