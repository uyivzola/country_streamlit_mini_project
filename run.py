import sqlite3

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from folium.plugins import Geocoder, MiniMap, Fullscreen, Draw
from streamlit_folium import st_folium

st.set_page_config(page_title="🌍 World Countries App", layout="wide")


@st.cache_data
def load_data():
    with sqlite3.connect("countries.db") as conn:
        df = pd.read_sql_query("SELECT * FROM countries", conn)
    # safety: ensure columns exist
    for c in ["capital", "population", "area", "language_count", "cca3", "cca2", "name_common", "region", "subregion"]:
        if c not in df.columns:
            df[c] = None

    df['capital_length'] = df['capital'].apply(lambda x: len(
        x) if isinstance(x, str) else (len(x) if isinstance(x, list) else 0))
    df['capital_length_cat'] = pd.cut(df['capital_length'], bins=[-1, 5, 10, 15, 20, 100],
                                      labels=['0-5', '6-10', '11-15', '16-20', '20+'])
    # avoid division by zero
    df['area'] = df['area'].replace({0: pd.NA}).astype(float)
    df['population'] = df['population'].astype(float)
    df['density'] = df['population'] / df['area']
    return df


@st.cache_data
def load_geojson():
    try:
        return gpd.read_file("world.geojson")
    except Exception:
        return gpd.GeoDataFrame()


@st.cache_data
def get_country_data_by_cca3(cca3):
    try:
        response = requests.get(
            f"https://restcountries.com/v3.1/alpha/{cca3}", timeout=10)
        if response.status_code == 200:
            return response.json()[0]
    except Exception:
        return None
    return None


@st.cache_data
def load_worldbank_from_db(cca2):
    try:
        with sqlite3.connect("countries.db") as conn:
            df = pd.read_sql_query(
                f"SELECT * FROM indicators WHERE country_code = '{cca2}'", conn)
        return df
    except Exception:
        return pd.DataFrame()


# ---------------------- load static datasets ----------------------

df = load_data()
geo_data = load_geojson()

# helper maps
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

# Top navigation using tabs (appears at the top)
tabs = st.tabs(["Compare Countries", "Country Details", "Dashboard"])

# small header row with DM link
st.markdown("[DM me on Telegram](https://t.me/Hopxol)")

# ---------------------------- Dashboard (original) ----------------------------
with tabs[2]:
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

    # Multiple charts (kept from your original layout)
    charts = []

    subregions = df['subregion'].value_counts().nlargest(10).reset_index()
    subregions.columns = ['Субрегион', 'Количество стран']
    fig1 = px.bar(subregions, x='Количество стран',
                  y='Субрегион', orientation='h', color='Субрегион')
    charts.append(("🌍 Топ-10 субрегионов", fig1))

    fig2 = px.scatter(df, x='area', y='population',
                      log_x=True, log_y=True, color='region')
    charts.append(("📏 Площадь vs Население", fig2))

    top_lang = df.sort_values(by='language_count', ascending=False).head(15)
    fig3 = px.bar(top_lang, x='language_count', y='name_common',
                  orientation='h', color='name_common')
    charts.append(("🗣️ Топ-15 по языкам", fig3))

    region_counts = df['region'].value_counts().reset_index()
    region_counts.columns = ['Регион', 'Количество стран']
    fig5 = px.bar(region_counts, x='Количество стран',
                  y='Регион', orientation='h', color='Регион')
    charts.append(("🗺️ Страны по регионам", fig5))

    top20 = df.sort_values(by='population', ascending=False).head(20)
    fig6 = px.bar(top20, x='population', y='name_common',
                  orientation='h', color='name_common')
    charts.append(("🏙️ Топ-20 по населению", fig6))

    fig7 = px.pie(region_counts, names='Регион',
                  values='Количество стран', hole=0.3)
    charts.append(("🌐 Доля регионов", fig7))

    avg_lang = df.groupby('region')['language_count'].mean().reset_index()
    avg_lang['language_count'] = avg_lang['language_count'].round(1)
    fig8 = px.bar(avg_lang, x='language_count', y='region',
                  orientation='h', color='region')
    charts.append(("🗣️ Среднее языков по регионам", fig8))

    cap_len = df['capital_length_cat'].value_counts(
    ).sort_index().reset_index()
    cap_len.columns = ['Категория длины столицы', 'Количество стран']
    fig9 = px.bar(cap_len, x='Категория длины столицы',
                  y='Количество стран', color='Категория длины столицы')
    charts.append(("🏛️ Длина названий столиц", fig9))

    for i in range(0, len(charts), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(charts):
                with cols[j]:
                    st.subheader(charts[i + j][0])
                    st.plotly_chart(charts[i + j][1], use_container_width=True)

    st.markdown("---")
    st.markdown("with love 💘 by Behzod Khidirov.")

# ---------------------------- Country Details (updated) ----------------------------
with tabs[1]:
    st.title("📊 Дашборд по странам мира | 🌐 Детали по стране")
    
    df_sorted = df.sort_values(by='name_common')
    country_options = df_sorted[['name_common', 'cca3']].dropna()

    default_country = 'Netherlands' if 'Netherlands' in country_options[
        'name_common'].values else country_options['name_common'].iloc[0]
    selected_country_name = st.selectbox("Выберите страну", country_options['name_common'].tolist(),
                                         index=country_options['name_common'].tolist().index(default_country))

    selected_cca3 = country_options[country_options['name_common']
                                    == selected_country_name]['cca3'].values[0]
    selected_cca2 = df[df['cca3'] == selected_cca3]['cca2'].values[0]
    country = get_country_data_by_cca3(selected_cca3)

    if not country:
        st.error("❌ Страна не найдена.")
        st.stop()

    wb_data = load_worldbank_from_db(selected_cca2)

    # Cards (same layout as your original single-country page)
    if not wb_data.empty:
        card_cols = st.columns(4)
        for i, indicator in enumerate(card_indicators):
            latest = wb_data[(wb_data['indicator'] == indicator)
                             ].sort_values('year')
            value = latest.iloc[-1]['value'] if not latest.empty else None
            label = card_titles.get(indicator, indicator)
            if value is not None:
                with card_cols[i % 4]:
                    st.metric(label=label, value=f"{int(value):,}")
            if (i + 1) % 4 == 0 and i + 1 < len(card_indicators):
                card_cols = st.columns(4)

    # Old-style country header: big text + images + details (keeps look from your original first code)
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(
            f"## {country['name']['official']} ({country['name']['common']})")
        st.markdown(
            f"**Регион:** {country.get('region', '—')} &nbsp;&nbsp;|&nbsp;&nbsp; **Субрегион:** {country.get('subregion', '—')}")
        st.markdown(
            f"**Площадь:** {int(country.get('area', 0)):,} км² &nbsp;&nbsp;|&nbsp;&nbsp; **Континент:** {', '.join(country.get('continents', []))}")
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
    # Add mixed GDP + % growth chart for the single country
    st.subheader('💰 ВВП и % прироста (страна)')

    # single-country GDP + pct change
    try:
        gdp_df = wb_data[wb_data['indicator'] == 'gdp_current_usd'][[
            'year', 'value']].sort_values('year')
        if not gdp_df.empty:
            gdp_df = gdp_df.set_index('year')
            gdp = gdp_df['value']
            gdp_pct = gdp.pct_change() * 100

            fig = go.Figure()
            fig.add_trace(go.Bar(x=gdp.index, y=gdp.values, name='ВВП (USD)',
                          yaxis='y1', hovertemplate='%{x}: %{y:,.0f}<extra></extra>'))
            fig.add_trace(go.Scatter(x=gdp_pct.index, y=gdp_pct.values, name='% прироста',
                          yaxis='y2', mode='lines+markers', hovertemplate='%{x}: %{y:.2f}%<extra></extra>'))

            fig.update_layout(
                xaxis=dict(title='Год'),
                yaxis=dict(title='ВВП (USD)', side='left', showgrid=False),
                yaxis2=dict(title='% прироста', overlaying='y',
                            side='right', showgrid=False),
                legend=dict(orientation='h', yanchor='bottom',
                            y=1.02, xanchor='right', x=1),
                hovermode='x unified',
                height=420
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info('Нет данных ВВП для этой страны.')
    except Exception:
        st.info('Ошибка при построении ВВП графика для этой страны.')
    st.markdown("---")
    if not wb_data.empty:
        indicators_list = wb_data['indicator'].unique()
        for i in range(0, len(indicators_list), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(indicators_list):
                    indicator = indicators_list[i + j]
                    chart_df = wb_data[wb_data['indicator']
                                       == indicator].sort_values('year')
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
                        title = title_map.get(
                            indicator, indicator.replace('_', ' ').capitalize())
                        with cols[j]:
                            st.subheader(title)
                            # choose visual type per indicator
                            if indicator in ['gdp_growth_percent', 'inflation_percent', 'unemployment_percent']:
                                fig = px.bar(
                                    chart_df, x="year", y="value", text="value", title=title)
                            elif indicator in ['population_total']:
                                fig = px.area(chart_df, x="year",
                                              y="value", title=title)
                            elif indicator in ['exports_pct_gdp', 'imports_pct_gdp']:
                                fig = px.scatter(
                                    chart_df, x="year", y="value", title=title)
                            else:
                                fig = px.line(
                                    chart_df, x="year", y="value", markers=True, title=title)

                            try:
                                fig.update_traces(
                                    texttemplate='%{text:.2s}', textposition='top center')
                            except Exception:
                                pass

                            fig.update_layout(yaxis_title="Значение", xaxis_title="Год", height=350, margin=dict(
                                t=10), hovermode='x unified')
                            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Нет доступных данных для выбранной страны.")
    st.markdown("---")

    # Single-country map (similar to compare map)
    st.subheader('🗺️ Карта — границы и столица')
    geo_match = geo_data[geo_data["iso_a3"] == selected_cca3]
    if not geo_match.empty:
        geo_match_projected = geo_match.to_crs(epsg=3857)
        centroid_projected = geo_match_projected.geometry.centroid.iloc[0]
        
        # Convert the Point to a GeoSeries to use to_crs
        centroid_geo = gpd.GeoSeries([centroid_projected], crs="EPSG:3857").to_crs(epsg=4326).iloc[0]
        
        # Use the re-projected centroid coordinates for the map
        fmap = folium.Map(location=[centroid_geo.y, centroid_geo.x], zoom_start=5)
        
        # Use the original geometry in EPSG:4326 for GeoJson
        geo_match = geo_match.to_crs(epsg=4326)
        folium.GeoJson(geo_match, name="Границы страны").add_to(fmap)
        
        capital_coord = country.get("capitalInfo", {}).get("latlng", None)
        capital_name = ", ".join(country.get(
            "capital", [])) if country.get("capital") else '—'
        if capital_coord:
            folium.Marker(location=capital_coord, popup=f"Capital: {capital_name}", icon=folium.Icon(
                color="green", icon="flag")).add_to(fmap)
        else:
            folium.Marker(location=[centroid.y, centroid.x], popup=f"Capital (approx.): {capital_name}", icon=folium.Icon(
                color="gray", icon="question-sign")).add_to(fmap)

        Geocoder().add_to(fmap)
        Fullscreen().add_to(fmap)
        Draw(export=False).add_to(fmap)
        MiniMap(position="bottomright").add_to(fmap)

        st_folium(fmap, width='100%', height=500)
    else:
        st.warning("Геометрии для страны не найдены в GeoJSON.")

    st.markdown("with love 💘 by Behzod Khidirov.")

# ---------------------------- Compare Countries (REDESIGN) ----------------------------
with tabs[0]:
    
    st.title("🌐 Детали по стране: 🔁 Compare Countries — Сравнение нескольких стран")
    st.markdown(
        "Выберите несколько стран, и для каждой страны будут показаны те же карточки и графики, что и в деталях.")

    # selection controls
    df_sorted = df.sort_values(by='name_common')
    country_map = dict(zip(df_sorted['name_common'], df_sorted['cca3']))
    country_names = df_sorted['name_common'].tolist()

    default = [c for c in ['Netherlands', 'United Kingdom',
                           'Germany'] if c in country_names]
    if not default:
        default = country_names[:3]
    selected_names = st.multiselect(
        "Выберите страны (несколько)", country_names, default=default)

    if not selected_names:
        st.warning("Пожалуйста, выберите как минимум одну страну для сравнения.")
        st.stop()

    # limit to reasonable number to avoid UI break
    MAX_COUNTRIES = 8
    if len(selected_names) > MAX_COUNTRIES:
        st.warning(
            f"Слишком много стран для одновременного показа — пожалуйста, выберите не более {MAX_COUNTRIES} стран.")
        selected_names = selected_names[:MAX_COUNTRIES]

    selected_cca3_list = [country_map[n] for n in selected_names]
    selected_df = df[df['cca3'].isin(selected_cca3_list)]

    # load restcountries data and worldbank data for each selected
    restcountries = {}
    wb_by_country = {}
    for cca3 in selected_cca3_list:
        restcountries[cca3] = get_country_data_by_cca3(cca3) or {}
        cca2 = df[df['cca3'] == cca3]['cca2'].values[0]
        wb_by_country[cca3] = load_worldbank_from_db(
            cca2) if cca2 is not None else pd.DataFrame()

    st.markdown("---")

    # show flags and coats of arms for selected countries (compact row)
    st.subheader("Флаги и гербы выбранных стран")
    cols = st.columns(len(selected_names))
    for i, name in enumerate(selected_names):
        cca3 = country_map[name]
        rc = restcountries.get(cca3, {})
        with cols[i]:
            flag = rc.get('flags', {}).get('png')
            coa = None
            if 'coatOfArms' in rc:
                coa = rc['coatOfArms'].get(
                    'png') or rc['coatOfArms'].get('svg')
            st.markdown(f"**{name}**")
            if flag:
                st.image(flag, width=160)
            if coa:
                st.image(coa, width=100)

    st.markdown("---")

    # ------------------- Side-by-side latest indicators table (expanded) -------------------
    st.subheader(
        "Последние значения ключевых индикаторов и базовая информация")

    # Prepare table rows: indicators + extra info
    table_rows = [card_titles.get(i, i) for i in card_indicators]
    extra_rows = ['🌍Соседние страны', '🕒Временные зоны', '💬Языки',
                  '💻TLD', '💱Валюта', '🏞️Площадь', '🗺️Континент', '🏙️Столица']
    table_index = table_rows + extra_rows

    latest_table = pd.DataFrame(index=table_index)

    for cca3 in selected_cca3_list:
        name = df[df['cca3'] == cca3]['name_common'].values[0]
        wb = wb_by_country.get(cca3, pd.DataFrame())
        col_vals = []
        # indicators
        for ind in card_indicators:
            val = None
            if not wb.empty and 'indicator' in wb.columns:
                t = wb[wb['indicator'] == ind].sort_values('year')
                if not t.empty:
                    val = t.iloc[-1]['value']
            col_vals.append(val)
        # extra info from restcountries / df
        rc = restcountries.get(cca3, {})
        borders = ', '.join(rc.get('borders', [])
                            ) if rc.get('borders') else '—'
        timezones = ', '.join(rc.get('timezones', [])
                              ) if rc.get('timezones') else '—'
        languages = ', '.join(rc.get('languages', {}).values()
                              ) if rc.get('languages') else '—'
        tld = ', '.join(rc.get('tld', [])) if rc.get('tld') else '—'
        currency = '—'
        if rc.get('currencies'):
            first = list(rc.get('currencies').items())[0]
            currency = f"{first[0]} — {first[1].get('name', '')} ({first[1].get('symbol', '')})"
        area = f"{int(rc.get('area')):,}" if rc.get('area') else (
            f"{int(df[df['cca3'] == cca3]['area'].values[0]):,}" if not pd.isna(df[df['cca3'] == cca3]['area'].values[0]) else '—')
        continents = ', '.join(rc.get('continents', [])
                               ) if rc.get('continents') else '—'
        capital = ', '.join(rc.get('capital', [])
                            ) if rc.get('capital') else '—'

        col_vals.extend([borders, timezones, languages, tld,
                        currency, area, continents, capital])
        latest_table[name] = col_vals

    # format numbers and display
    def fmt_cell(x):
        if pd.isna(x) or x is None:
            return '—'
        try:
            return f"{int(x):,}"
        except Exception:
            return x

    display_table = latest_table.copy()
    display_table = display_table.map(lambda x: fmt_cell(x))
    st.table(display_table)
    st.markdown("---")

    # ------------------- Time series charts for each key indicator (mixed visuals + unified hover) -------------------
    st.subheader("📈 Сравнение ключевых индикаторов по годам")
    combined = []
    for cca3 in selected_cca3_list:
        wb = wb_by_country.get(cca3, pd.DataFrame())
        name = df[df['cca3'] == cca3]['name_common'].values[0]
        if not wb.empty:
            tmp = wb.copy()
            tmp['country_name'] = name
            combined.append(tmp)

    if combined:
        combined_df = pd.concat(combined, ignore_index=True)
        indicators_list = combined_df['indicator'].unique().tolist()
        ordered = [i for i in card_indicators if i in indicators_list] + \
            [i for i in indicators_list if i not in card_indicators]

        for i in range(0, len(ordered), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(ordered):
                    ind = ordered[i + j]
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
                    title = title_map.get(
                        ind, ind.replace('_', ' ').capitalize())
                    chart_df = combined_df[combined_df['indicator'] == ind]
                    with cols[j]:
                        st.subheader(title)
                        if chart_df.empty:
                            st.info('Нет данных для этого индикатора.')
                        else:
                            # choose visual type per indicator
                            if ind in ['gdp_growth_percent', 'inflation_percent', 'unemployment_percent']:
                                fig = px.bar(
                                    chart_df, x='year', y='value', color='country_name', barmode='group')
                            elif ind in ['population_total']:
                                fig = px.area(chart_df, x='year',
                                              y='value', color='country_name')
                            elif ind in ['gdp_current_usd', 'imports_usd', 'exports_usd']:
                                fig = px.bar(
                                    chart_df, x='year', y='value', color='country_name', barmode='group')
                            else:
                                fig = px.line(
                                    chart_df, x='year', y='value', color='country_name', markers=True)

                            # unified hover so the vertical hover line shows all countries' values at a year
                            fig.update_layout(height=380, margin=dict(
                                t=10), hovermode='x unified')
                            # make traces show markers (for lines) and make hover label complete
                            try:
                                fig.update_traces(marker=dict(
                                    size=6), hovertemplate=None)
                            except Exception:
                                pass

                            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('Нет данных World Bank для выбранных стран.')

    st.markdown('---')

    # ------------------- Compare GDP + % growth mixed chart (per-country) -------------------
    st.subheader('💰 ВВП и % прироста (сравнение стран)')
    # prepare per-country GDP by year and pct change per country
    gdp_list = []
    for cca3 in selected_cca3_list:
        wb = wb_by_country.get(cca3, pd.DataFrame())
        name = df[df['cca3'] == cca3]['name_common'].values[0]
        if not wb.empty and 'indicator' in wb.columns:
            tmp = wb[wb['indicator'] == 'gdp_current_usd'][[
                'year', 'value']].copy()
            if not tmp.empty:
                tmp['country_name'] = name
                gdp_list.append(tmp)

    if gdp_list:
        gdp_df = pd.concat(gdp_list, ignore_index=True)
        # compute pct change per country
        gdp_df = gdp_df.sort_values(['country_name', 'year'])
        gdp_df['pct_change'] = gdp_df.groupby(
            'country_name')['value'].pct_change() * 100

        years = sorted(gdp_df['year'].unique())
        fig = go.Figure()

        # add GDP bars per country (grouped by year)
        for name in gdp_df['country_name'].unique():
            sub = gdp_df[gdp_df['country_name'] == name]
            fig.add_trace(go.Bar(
                x=sub['year'], y=sub['value'], name=f'{name} — ВВП (USD)', hovertemplate='%{x}: %{y:,.0f}<extra></extra>'))

        # add pct change lines per country on secondary axis
        for name in gdp_df['country_name'].unique():
            sub = gdp_df[gdp_df['country_name'] == name]
            fig.add_trace(go.Scatter(x=sub['year'], y=sub['pct_change'],
                          name=f'{name} — % прироста', yaxis='y2', mode='lines+markers', hovertemplate='%{x}: %{y:.2f}%<extra></extra>'))

        fig.update_layout(
            barmode='group',
            xaxis=dict(title='Год'),
            yaxis=dict(title='ВВП (USD)', side='left', showgrid=False),
            yaxis2=dict(title='% прироста', overlaying='y',
                        side='right', showgrid=False),
            legend=dict(orientation='h', yanchor='bottom',
                        y=1.02, xanchor='right', x=1),
            hovermode='x unified',
            height=520
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('Нет данных ВВП для выбранных стран.')

    st.markdown('---')

    # ------------------- Map -------------------
    st.subheader('🗺️ Карта — выбранные страны')
    geo_sel = geo_data[geo_data['iso_a3'].isin(selected_cca3_list)]
    if not geo_sel.empty:
        geo_sel = geo_sel.to_crs(epsg=4326)
        bounds = geo_sel.total_bounds
        minx, miny, maxx, maxy = bounds[0], bounds[1], bounds[2], bounds[3]
        center_lat = (miny + maxy) / 2
        center_lon = (minx + maxx) / 2

        fmap = folium.Map(location=[center_lat, center_lon], zoom_start=3)
        folium.GeoJson(geo_sel, name='Selected countries', tooltip=folium.GeoJsonTooltip(
            fields=['name'] if 'name' in geo_sel.columns else [])).add_to(fmap)

        # capitals
        for cca3 in selected_cca3_list:
            rc = restcountries.get(cca3, {})
            capital_coord = rc.get('capitalInfo', {}).get('latlng')
            cap_name = ', '.join(rc.get('capital', [])) if rc.get(
                'capital') else None
            country_name = df[df['cca3'] == cca3]['name_common'].values[0]
            if capital_coord:
                folium.Marker(location=capital_coord, popup=f"{country_name} — {cap_name}", icon=folium.Icon(
                    icon='flag')).add_to(fmap)

        fmap.fit_bounds([[miny, minx], [maxy, maxx]])
        Geocoder().add_to(fmap)
        Fullscreen().add_to(fmap)
        Draw(export=False).add_to(fmap)
        MiniMap(position='bottomright').add_to(fmap)

        st_folium(fmap, width="100%", height=600)
    else:
        st.warning('Геометрии для выбранных стран не найдены в GeoJSON.')

    st.markdown('\n---\nwith love 💘 by Behzod Khidirov.')
