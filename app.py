# -*- coding: utf-8 -*-
"""
==============================================================================
  SolarBridge | منصة الطاقة الشمسية الذكية
  Bilingual (AR/EN) Solar Energy Platform — Streamlit single-file app
------------------------------------------------------------------------------
  Module 1 (this version):  Customer Module
    - Address input + Google Maps API hook (geocoding / roof area)
    - NASA POWER API integration (solar irradiance climatology)
    - Full standard PV engineering equations (commented below)
    - Interactive results dashboard (Plotly)
  Module 2 (skeleton, to be expanded next step): B2B / ERP Dashboard
------------------------------------------------------------------------------
  Requirements (requirements.txt for Streamlit Cloud):
      streamlit
      pandas
      plotly
      requests
==============================================================================
"""

import math
import datetime as dt

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# =============================================================================
# 0) PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="SolarBridge ☀️",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# 1) TRANSLATION LAYER (all UI strings live here → easy to extend/translate)
# =============================================================================
T = {
    "en": {
        "app_title": "☀️ SolarBridge — Smart Solar Platform",
        "tagline": "Design your solar system in minutes, powered by NASA data.",
        "nav_customer": "🏠 Customer",
        "nav_b2b": "🏢 Companies (B2B)",
        "language": "🌐 Language",
        "step1": "1️⃣ Location & Roof",
        "step2": "2️⃣ Consumption & System",
        "step3": "3️⃣ Results Dashboard",
        "address": "📍 Property address",
        "address_ph": "e.g. 12 Tahrir St, Cairo, Egypt",
        "locate_btn": "🛰️ Locate & fetch solar data",
        "roof_area": "🏗️ Gross roof area (m²)",
        "obstacles": "🚧 Obstacles area — tanks, stairs, shading (m²)",
        "net_area_info": "Net usable roof area",
        "monthly_bill": "💵 Average monthly electricity bill",
        "tariff": "⚡ Electricity tariff (currency / kWh)",
        "currency": "💱 Currency",
        "sys_type": "🔋 System type",
        "on_grid": "On-Grid (no batteries)",
        "off_grid": "Off-Grid (with batteries)",
        "hybrid": "Hybrid (grid + batteries)",
        "autonomy": "🌙 Battery autonomy (days)",
        "panel_w": "🔆 Panel rated power (W)",
        "calc_btn": "⚙️ Calculate my solar system",
        "fetching": "Contacting NASA POWER API…",
        "nasa_ok": "✅ NASA POWER data loaded for your location.",
        "nasa_fail": "⚠️ NASA API unreachable — using regional average irradiance (5.8 kWh/m²/day).",
        "geo_fail": "⚠️ Geocoding unavailable — enter coordinates manually below.",
        "lat": "Latitude",
        "lon": "Longitude",
        "results_title": "📊 Your Solar System — Engineering Report",
        "kpi_panels": "Solar Panels",
        "kpi_system": "System Size",
        "kpi_inverter": "Inverter",
        "kpi_batteries": "Batteries",
        "kpi_cost": "Estimated Cost",
        "kpi_saving": "Annual Savings",
        "kpi_payback": "Payback Period",
        "kpi_co2": "CO₂ Avoided / yr",
        "years": "years",
        "panel_unit": "panel",
        "battery_unit": "× 5 kWh unit",
        "no_batt": "Not required (On-Grid)",
        "chart_prod": "🔆 Monthly Energy Production (kWh)",
        "chart_save": "💰 Cumulative Savings vs. System Cost",
        "chart_irr": "☀️ Solar Irradiance at Your Location (kWh/m²/day)",
        "prod": "Production",
        "consumption": "Consumption",
        "cum_saving": "Cumulative savings",
        "sys_cost": "System cost",
        "month": "Month",
        "energy": "Energy (kWh)",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "coverage": "☑️ Your system covers ~{pct}% of your annual consumption.",
        "eng_details": "🧮 Engineering details & equations used",
        "b2b_title": "🏢 Supplier & Company Portal",
        "login": "🔐 Login",
        "email": "Email",
        "password": "Password",
        "login_btn": "Sign in",
        "login_bad": "❌ Invalid credentials. (demo: supplier@demo.com / solar123)",
        "logout": "Logout",
        "erp_title": "📦 Orders Dashboard (ERP — basic)",
        "erp_note": "Full ERP module will be expanded in the next step.",
        "orders_open": "Open Orders",
        "orders_value": "Pipeline Value",
        "orders_month": "Orders this month",
        "tbl_id": "Order ID", "tbl_client": "Client", "tbl_kwp": "kWp",
        "tbl_value": "Value", "tbl_status": "Status", "tbl_date": "Date",
        "status_new": "New", "status_progress": "In progress", "status_done": "Installed",
        "welcome": "Welcome",
        "disclaimer": "ℹ️ Estimates are indicative and based on standard engineering assumptions; a site survey is required for a final quotation.",
    },
    "ar": {
        "app_title": "☀️ سولار بريدج — منصة الطاقة الشمسية الذكية",
        "tagline": "صمّم نظامك الشمسي في دقائق، بالاعتماد على بيانات ناسا.",
        "nav_customer": "🏠 العميل",
        "nav_b2b": "🏢 الشركات والموردون (B2B)",
        "language": "🌐 اللغة",
        "step1": "1️⃣ الموقع والسطح",
        "step2": "2️⃣ الاستهلاك والنظام",
        "step3": "3️⃣ لوحة النتائج",
        "address": "📍 عنوان العقار",
        "address_ph": "مثال: ١٢ شارع التحرير، القاهرة، مصر",
        "locate_btn": "🛰️ تحديد الموقع وجلب بيانات الشمس",
        "roof_area": "🏗️ المساحة الإجمالية للسطح (م²)",
        "obstacles": "🚧 مساحة العوائق — خزانات، سلالم، ظلال (م²)",
        "net_area_info": "المساحة الصافية القابلة للاستخدام",
        "monthly_bill": "💵 متوسط فاتورة الكهرباء الشهرية",
        "tariff": "⚡ تعريفة الكهرباء (عملة / ك.و.س)",
        "currency": "💱 العملة",
        "sys_type": "🔋 نوع النظام",
        "on_grid": "متصل بالشبكة (بدون بطاريات)",
        "off_grid": "منفصل عن الشبكة (مع بطاريات)",
        "hybrid": "هجين (شبكة + بطاريات)",
        "autonomy": "🌙 أيام الاستقلالية للبطاريات",
        "panel_w": "🔆 قدرة اللوح الواحد (واط)",
        "calc_btn": "⚙️ احسب نظامي الشمسي",
        "fetching": "جاري الاتصال بـ NASA POWER API…",
        "nasa_ok": "✅ تم تحميل بيانات ناسا لموقعك بنجاح.",
        "nasa_fail": "⚠️ تعذّر الوصول لواجهة ناسا — سيتم استخدام متوسط إقليمي (5.8 ك.و.س/م²/يوم).",
        "geo_fail": "⚠️ خدمة تحديد الموقع غير متاحة — أدخل الإحداثيات يدوياً أدناه.",
        "lat": "خط العرض",
        "lon": "خط الطول",
        "results_title": "📊 نظامك الشمسي — التقرير الهندسي",
        "kpi_panels": "الألواح الشمسية",
        "kpi_system": "حجم النظام",
        "kpi_inverter": "الإنفرتر",
        "kpi_batteries": "البطاريات",
        "kpi_cost": "التكلفة التقديرية",
        "kpi_saving": "التوفير السنوي",
        "kpi_payback": "فترة الاسترداد",
        "kpi_co2": "كربون مُجنَّب / سنة",
        "years": "سنة",
        "panel_unit": "لوح",
        "battery_unit": "× وحدة 5 ك.و.س",
        "no_batt": "غير مطلوبة (متصل بالشبكة)",
        "chart_prod": "🔆 الإنتاج الشهري للطاقة (ك.و.س)",
        "chart_save": "💰 التوفير التراكمي مقابل تكلفة النظام",
        "chart_irr": "☀️ الإشعاع الشمسي في موقعك (ك.و.س/م²/يوم)",
        "prod": "الإنتاج",
        "consumption": "الاستهلاك",
        "cum_saving": "التوفير التراكمي",
        "sys_cost": "تكلفة النظام",
        "month": "الشهر",
        "energy": "الطاقة (ك.و.س)",
        "months": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                   "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
        "coverage": "☑️ يغطي نظامك حوالي {pct}% من استهلاكك السنوي.",
        "eng_details": "🧮 التفاصيل الهندسية والمعادلات المستخدمة",
        "b2b_title": "🏢 بوابة الشركات والموردين",
        "login": "🔐 تسجيل الدخول",
        "email": "البريد الإلكتروني",
        "password": "كلمة المرور",
        "login_btn": "دخول",
        "login_bad": "❌ بيانات غير صحيحة. (تجريبي: supplier@demo.com / solar123)",
        "logout": "تسجيل الخروج",
        "erp_title": "📦 لوحة إدارة الطلبات (ERP — أساسية)",
        "erp_note": "سيتم توسعة وحدة الـ ERP الكاملة في الخطوة التالية.",
        "orders_open": "طلبات مفتوحة",
        "orders_value": "قيمة الطلبات",
        "orders_month": "طلبات هذا الشهر",
        "tbl_id": "رقم الطلب", "tbl_client": "العميل", "tbl_kwp": "ك.و ذروة",
        "tbl_value": "القيمة", "tbl_status": "الحالة", "tbl_date": "التاريخ",
        "status_new": "جديد", "status_progress": "قيد التنفيذ", "status_done": "تم التركيب",
        "welcome": "مرحباً",
        "disclaimer": "ℹ️ النتائج تقديرية ومبنية على افتراضات هندسية قياسية؛ المعاينة الميدانية مطلوبة للعرض النهائي.",
    },
}

# ---- Language toggle (session state) ----------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "ar"

def tr(key: str):
    """Fetch a translated string for the active language."""
    return T[st.session_state.lang].get(key, key)

# =============================================================================
# 2) MODERN UI — CSS (RTL support for Arabic + soft card design)
# =============================================================================
IS_AR = st.session_state.lang == "ar"
st.markdown(
    f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&family=Inter:wght@400;600;800&display=swap');
      html, body, [class*="css"] {{
          font-family: {"'Cairo'" if IS_AR else "'Inter'"}, sans-serif;
      }}
      .stApp {{ direction: {"rtl" if IS_AR else "ltr"}; }}
      section[data-testid="stSidebar"] {{ direction: {"rtl" if IS_AR else "ltr"}; }}
      /* KPI cards */
      div[data-testid="stMetric"] {{
          background: linear-gradient(145deg, #fffdf5, #fff7e0);
          border: 1px solid #ffe1a8;
          border-radius: 16px;
          padding: 14px 16px;
          box-shadow: 0 2px 8px rgba(255,170,0,.08);
      }}
      h1, h2, h3 {{ color: #1c3d5a; }}
      .stButton>button {{
          border-radius: 12px;
          font-weight: 700;
      }}
      .solar-hero {{
          background: linear-gradient(120deg, #1c3d5a 0%, #2e6da4 60%, #f9a825 130%);
          color: #fff; padding: 22px 28px; border-radius: 18px; margin-bottom: 14px;
      }}
      .solar-hero h1 {{ color:#fff; margin:0; font-size: 1.6rem; }}
      .solar-hero p  {{ color:#ffe9b8; margin:4px 0 0; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# 3) ENGINEERING CONSTANTS (standard industry assumptions — editable)
# =============================================================================
PANEL_AREA_M2        = 2.0    # Typical 550W mono panel ≈ 2.28×0.95 m ≈ 2.0–2.2 m²
AREA_UTILIZATION     = 0.70   # Packing factor: spacing between rows to avoid
                              # self-shading + walkways (30% of net area lost)
PANEL_EFF_STC        = 0.21   # Module efficiency at Standard Test Conditions
TEMP_COEFF_P         = -0.0035  # γ: power temperature coefficient (%/°C → per °C)
NOCT                 = 45.0   # Nominal Operating Cell Temperature (°C)
SOILING_LOSS         = 0.03   # Dust/soiling (high in MENA region)
WIRING_LOSS          = 0.02   # DC + AC cable ohmic losses
MISMATCH_LOSS        = 0.02   # Module mismatch + connections
INVERTER_EFF         = 0.97   # Modern string inverter efficiency
AVAILABILITY         = 0.99   # Downtime allowance
DC_AC_RATIO          = 1.15   # Standard inverter sizing: P_inv = kWp / 1.15
BATTERY_UNIT_KWH     = 5.0    # Commercial LiFePO4 unit size (e.g. 48V/100Ah ≈ 5kWh)
DOD                  = 0.80   # Depth of Discharge for LiFePO4 (80%)
BATT_ROUNDTRIP_EFF   = 0.92   # Battery round-trip efficiency
GRID_CO2_KG_PER_KWH  = 0.55   # Grid emission factor (Egypt ≈ 0.5–0.6 kg CO₂/kWh)
COST_PER_WP_ONGRID   = 0.55   # USD/Wp installed (regional market, on-grid)
COST_PER_KWH_BATT    = 250.0  # USD per kWh of LiFePO4 storage installed
AMBIENT_TEMP_C       = {      # Monthly avg ambient temp (Cairo-like default, °C)
    1: 14, 2: 16, 3: 19, 4: 24, 5: 28, 6: 30,
    7: 31, 8: 31, 9: 29, 10: 26, 11: 20, 12: 16,
}
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# =============================================================================
# 4) EXTERNAL APIs
# =============================================================================
def geocode_address(address: str, api_key: str | None = None):
    """
    Google Maps Geocoding hook.
    - If a GOOGLE_MAPS_API_KEY is provided (st.secrets), use Google Geocoding API.
    - Roof area extraction from satellite imagery (Solar API / building footprint)
      can be wired here later via Google Solar API `buildingInsights` endpoint.
    Returns (lat, lon) or None.
    """
    api_key = api_key or st.secrets.get("GOOGLE_MAPS_API_KEY", None)
    if api_key:
        try:
            r = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": address, "key": api_key},
                timeout=10,
            )
            data = r.json()
            if data.get("status") == "OK":
                loc = data["results"][0]["geometry"]["location"]
                return loc["lat"], loc["lng"]
        except Exception:
            return None
    # Fallback: free OpenStreetMap Nominatim geocoder (no key required)
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "SolarBridge/1.0"},
            timeout=10,
        )
        js = r.json()
        if js:
            return float(js[0]["lat"]), float(js[0]["lon"])
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_nasa_power(lat: float, lon: float):
    """
    NASA POWER API — monthly climatology of Global Horizontal Irradiance (GHI).
    Parameter ALLSKY_SFC_SW_DWN is returned in kWh/m²/day, which numerically
    equals the daily Peak Sun Hours (PSH) at 1 kW/m² reference irradiance.
    """
    url = "https://power.larc.nasa.gov/api/temporal/climatology/point"
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,T2M",
        "community": "RE",
        "latitude": lat,
        "longitude": lon,
        "format": "JSON",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    p = r.json()["properties"]["parameter"]
    keys = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
            "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    ghi = [p["ALLSKY_SFC_SW_DWN"][k] for k in keys]          # kWh/m²/day = PSH
    temps = [p.get("T2M", {}).get(k, AMBIENT_TEMP_C[i + 1])  # °C
             for i, k in enumerate(keys)]
    return ghi, temps

# =============================================================================
# 5) PV ENGINEERING MODEL  —  all standard equations, fully commented
# =============================================================================
def design_pv_system(net_roof_m2, monthly_bill, tariff, panel_w,
                     ghi_monthly, temp_monthly, sys_type, autonomy_days):
    """
    Full PV sizing chain. Equations:

    (1) Usable area:
        A_usable = A_net × f_util            (f_util = 0.70 row-spacing factor)

    (2) Load estimation from the bill:
        E_daily_load [kWh] = (Bill / tariff) / 30.4

    (3) Array size (energy-driven), using worst-month PSH:
        kWp_required = E_daily_load / (PSH_min × PR)
        …capped by area: kWp_area_max = A_usable / A_panel × P_panel/1000

    (4) Cell temperature (NOCT model):
        T_cell = T_amb + (NOCT − 20)/800 × G      with G = 1000 W/m² at peak

    (5) Thermal derating:
        f_temp = 1 + γ × (T_cell − 25)            γ = −0.35 %/°C

    (6) Performance Ratio (PR): product of all loss factors
        PR = f_temp × (1−soiling) × (1−wiring) × (1−mismatch)
                    × η_inverter × availability

    (7) Monthly energy:
        E_month [kWh] = kWp × PSH_month × PR_month × N_days

    (8) Battery bank (off-grid / hybrid):
        C_bank [kWh] = (E_daily_load × N_autonomy) / (DoD × η_roundtrip)

    (9) Inverter sizing (DC/AC ratio):
        P_inv [kW] = kWp / 1.15   → rounded up to commercial size
    """
    # --- (1) usable area & area-limited capacity -----------------------------
    a_usable = net_roof_m2 * AREA_UTILIZATION
    max_panels_by_area = int(a_usable // PANEL_AREA_M2)
    kwp_area_max = max_panels_by_area * panel_w / 1000.0

    # --- (2) daily load from the electricity bill -----------------------------
    daily_load_kwh = (monthly_bill / max(tariff, 1e-6)) / 30.4

    # --- (4)+(5)+(6) monthly Performance Ratio --------------------------------
    pr_monthly = []
    for m in range(12):
        t_amb = temp_monthly[m]
        # NOCT model at reference irradiance 1000 W/m² (peak-hour condition)
        t_cell = t_amb + (NOCT - 20.0) / 800.0 * 1000.0
        f_temp = 1 + TEMP_COEFF_P * (t_cell - 25.0)          # thermal derate
        pr = (f_temp
              * (1 - SOILING_LOSS)
              * (1 - WIRING_LOSS)
              * (1 - MISMATCH_LOSS)
              * INVERTER_EFF
              * AVAILABILITY)
        pr_monthly.append(pr)

    # --- (3) required capacity using worst month (conservative sizing) --------
    worst_idx = ghi_monthly.index(min(ghi_monthly))
    psh_min, pr_min = ghi_monthly[worst_idx], pr_monthly[worst_idx]
    kwp_required = daily_load_kwh / (psh_min * pr_min)

    kwp = min(kwp_required, kwp_area_max)          # area is the hard limit
    n_panels = max(1, math.ceil(kwp * 1000 / panel_w))
    kwp = n_panels * panel_w / 1000.0              # snap to whole panels
    if n_panels > max_panels_by_area:              # never exceed the roof
        n_panels = max_panels_by_area
        kwp = n_panels * panel_w / 1000.0

    # --- (7) monthly & annual production ---------------------------------------
    e_monthly = [kwp * ghi_monthly[m] * pr_monthly[m] * DAYS_IN_MONTH[m]
                 for m in range(12)]
    e_annual = sum(e_monthly)

    # --- (8) battery bank -------------------------------------------------------
    if sys_type in ("off_grid", "hybrid"):
        c_bank_kwh = (daily_load_kwh * autonomy_days) / (DOD * BATT_ROUNDTRIP_EFF)
        n_batteries = math.ceil(c_bank_kwh / BATTERY_UNIT_KWH)
    else:
        c_bank_kwh, n_batteries = 0.0, 0

    # --- (9) inverter ------------------------------------------------------------
    inv_kw_raw = kwp / DC_AC_RATIO
    commercial_sizes = [1.5, 2, 3, 3.6, 5, 6, 8, 10, 12, 15, 20, 25, 30, 50, 100]
    inv_kw = next((s for s in commercial_sizes if s >= inv_kw_raw),
                  math.ceil(inv_kw_raw))

    # --- Economics ---------------------------------------------------------------
    capex = kwp * 1000 * COST_PER_WP_ONGRID + c_bank_kwh * COST_PER_KWH_BATT
    annual_consumption = daily_load_kwh * 365
    # Savings limited by what the customer actually consumes (self-consumption)
    annual_saving = min(e_annual, annual_consumption) * tariff
    payback_years = capex / annual_saving if annual_saving > 0 else float("inf")
    co2_tons = e_annual * GRID_CO2_KG_PER_KWH / 1000.0
    coverage = min(100.0, 100.0 * e_annual / annual_consumption) if annual_consumption else 0

    return {
        "kwp": kwp, "n_panels": n_panels, "inv_kw": inv_kw,
        "n_batteries": n_batteries, "batt_kwh": c_bank_kwh,
        "capex": capex, "annual_saving": annual_saving,
        "payback": payback_years, "co2_tons": co2_tons,
        "e_monthly": e_monthly, "e_annual": e_annual,
        "pr_monthly": pr_monthly, "daily_load": daily_load_kwh,
        "coverage": coverage, "a_usable": a_usable,
    }

# =============================================================================
# 6) SIDEBAR — language toggle + navigation
# =============================================================================
with st.sidebar:
    st.markdown("## ☀️ SolarBridge")
    lang_choice = st.radio(
        T["ar"]["language"] + " / " + T["en"]["language"],
        options=["العربية", "English"],
        index=0 if st.session_state.lang == "ar" else 1,
        horizontal=True,
    )
    new_lang = "ar" if lang_choice == "العربية" else "en"
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.rerun()

    page = st.radio(
        "📌", [tr("nav_customer"), tr("nav_b2b")], label_visibility="collapsed"
    )
    st.divider()
    st.caption(tr("disclaimer"))

# =============================================================================
# 7) HERO HEADER
# =============================================================================
st.markdown(
    f"""<div class="solar-hero">
          <h1>{tr("app_title")}</h1>
          <p>{tr("tagline")}</p>
        </div>""",
    unsafe_allow_html=True,
)

# =============================================================================
# 8) CUSTOMER MODULE
# =============================================================================
if page == tr("nav_customer"):

    # ---- STEP 1 : location & roof -------------------------------------------
    st.subheader(tr("step1"))
    c1, c2 = st.columns([2, 1])
    with c1:
        address = st.text_input(tr("address"), placeholder=tr("address_ph"))
        if st.button(tr("locate_btn"), use_container_width=True) and address:
            coords = geocode_address(address)
            if coords:
                st.session_state["lat"], st.session_state["lon"] = coords
            else:
                st.warning(tr("geo_fail"))
    with c2:
        lat = st.number_input(tr("lat"), value=float(st.session_state.get("lat", 30.04)), format="%.4f")
        lon = st.number_input(tr("lon"), value=float(st.session_state.get("lon", 31.24)), format="%.4f")

    c3, c4 = st.columns(2)
    with c3:
        roof_area = st.number_input(tr("roof_area"), 10.0, 100000.0, 120.0, 10.0)
    with c4:
        obstacles = st.number_input(tr("obstacles"), 0.0, roof_area, 20.0, 5.0)
    net_area = roof_area - obstacles
    st.info(f"**{tr('net_area_info')}: {net_area:,.0f} m²**")

    # ---- STEP 2 : consumption & system ---------------------------------------
    st.subheader(tr("step2"))
    c5, c6, c7 = st.columns(3)
    with c5:
        currency = st.selectbox(tr("currency"), ["EGP", "SAR", "AED", "USD"])
        monthly_bill = st.number_input(tr("monthly_bill"), 50.0, 1e7, 1500.0, 50.0)
    with c6:
        tariff = st.number_input(tr("tariff"), 0.05, 50.0, 2.2, 0.05)
        panel_w = st.selectbox(tr("panel_w"), [450, 500, 550, 600, 650], index=2)
    with c7:
        sys_label = st.selectbox(
            tr("sys_type"), [tr("on_grid"), tr("hybrid"), tr("off_grid")]
        )
        sys_type = {tr("on_grid"): "on_grid", tr("hybrid"): "hybrid",
                    tr("off_grid"): "off_grid"}[sys_label]
        autonomy = st.slider(tr("autonomy"), 0.5, 3.0, 1.0, 0.5) \
            if sys_type != "on_grid" else 0.0

    # ---- CALCULATE -------------------------------------------------------------
    if st.button(tr("calc_btn"), type="primary", use_container_width=True):
        with st.spinner(tr("fetching")):
            try:
                ghi, temps = fetch_nasa_power(lat, lon)
                st.success(tr("nasa_ok"))
            except Exception:
                ghi = [5.0, 5.6, 6.4, 7.1, 7.5, 7.9,
                       7.7, 7.4, 6.9, 6.0, 5.2, 4.8]   # regional fallback
                temps = [AMBIENT_TEMP_C[m] for m in range(1, 13)]
                st.warning(tr("nasa_fail"))

        res = design_pv_system(net_area, monthly_bill, tariff, panel_w,
                               ghi, temps, sys_type, autonomy)
        st.session_state["result"] = res
        st.session_state["ghi"] = ghi
        st.session_state["inputs"] = dict(currency=currency, tariff=tariff,
                                          bill=monthly_bill)

    # ---- STEP 3 : results dashboard ---------------------------------------------
    if "result" in st.session_state:
        res, ghi = st.session_state["result"], st.session_state["ghi"]
        cur = st.session_state["inputs"]["currency"]
        months = tr("months")

        st.subheader(tr("results_title"))
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(tr("kpi_panels"), f"{res['n_panels']} {tr('panel_unit')}",
                  f"{res['kwp']:.1f} kWp")
        k2.metric(tr("kpi_inverter"), f"{res['inv_kw']} kW")
        k3.metric(tr("kpi_batteries"),
                  f"{res['n_batteries']} {tr('battery_unit')}"
                  if res["n_batteries"] else tr("no_batt"),
                  f"{res['batt_kwh']:.1f} kWh" if res["batt_kwh"] else None)
        k4.metric(tr("kpi_cost"), f"{res['capex']:,.0f} USD")

        k5, k6, k7, k8 = st.columns(4)
        k5.metric(tr("kpi_saving"), f"{res['annual_saving']:,.0f} {cur}")
        k6.metric(tr("kpi_payback"),
                  f"{res['payback']:.1f} {tr('years')}"
                  if res["payback"] != float("inf") else "—")
        k7.metric(tr("kpi_co2"), f"{res['co2_tons']:.2f} t CO₂")
        k8.metric(tr("kpi_system"), f"{res['kwp']:.2f} kWp")

        st.success(tr("coverage").format(pct=f"{res['coverage']:.0f}"))

        # ---- Chart 1: monthly production vs consumption ----------------------
        df = pd.DataFrame({
            tr("month"): months,
            tr("prod"): [round(e) for e in res["e_monthly"]],
            tr("consumption"): [round(res["daily_load"] * d) for d in DAYS_IN_MONTH],
        })
        fig1 = go.Figure()
        fig1.add_bar(x=df[tr("month")], y=df[tr("prod")],
                     name=tr("prod"), marker_color="#f9a825")
        fig1.add_scatter(x=df[tr("month")], y=df[tr("consumption")],
                         name=tr("consumption"), mode="lines+markers",
                         line=dict(color="#1c3d5a", width=3))
        fig1.update_layout(title=tr("chart_prod"), yaxis_title=tr("energy"),
                           legend=dict(orientation="h"), height=380)
        st.plotly_chart(fig1, use_container_width=True)

        # ---- Chart 2: cumulative savings vs capex (25-year view) --------------
        yrs = list(range(0, 26))
        DEGRADATION = 0.005          # 0.5%/yr module degradation (linear warranty)
        cum = []
        total = 0.0
        for y in yrs:
            total += res["annual_saving"] * (1 - DEGRADATION) ** y if y else 0
            cum.append(total)
        fig2 = go.Figure()
        fig2.add_scatter(x=yrs, y=cum, name=tr("cum_saving"), fill="tozeroy",
                         line=dict(color="#2e7d32", width=3))
        fig2.add_hline(y=res["capex"], line_dash="dash", line_color="#c62828",
                       annotation_text=tr("sys_cost"))
        fig2.update_layout(title=tr("chart_save"), height=380,
                           xaxis_title=tr("years"), yaxis_title=cur)
        st.plotly_chart(fig2, use_container_width=True)

        # ---- Chart 3: irradiance profile ---------------------------------------
        fig3 = px.area(x=months, y=ghi, title=tr("chart_irr"),
                       color_discrete_sequence=["#f9a825"])
        fig3.update_layout(height=320, xaxis_title=tr("month"),
                           yaxis_title="kWh/m²/day")
        st.plotly_chart(fig3, use_container_width=True)

        # ---- Engineering transparency -------------------------------------------
        with st.expander(tr("eng_details")):
            st.latex(r"E_{month} = kWp \times PSH \times PR \times N_{days}")
            st.latex(r"PR = f_{temp}\,(1-L_{soil})(1-L_{wire})(1-L_{mism})\,\eta_{inv}\,A_{avail}")
            st.latex(r"f_{temp} = 1 + \gamma\,(T_{cell} - 25),\quad T_{cell}=T_{amb}+\frac{NOCT-20}{800}G")
            st.latex(r"C_{batt} = \frac{E_{daily}\times N_{autonomy}}{DoD \times \eta_{rt}}")
            st.latex(r"P_{inverter} = \frac{kWp}{1.15}")
            st.dataframe(pd.DataFrame({
                tr("month"): months,
                "PSH (kWh/m²/day)": [round(g, 2) for g in ghi],
                "PR": [round(p, 3) for p in res["pr_monthly"]],
                tr("prod"): [round(e) for e in res["e_monthly"]],
            }), use_container_width=True, hide_index=True)

# =============================================================================
# 9) B2B MODULE (skeleton — expanded next step)
# =============================================================================
else:
    st.subheader(tr("b2b_title"))

    if "b2b_user" not in st.session_state:
        st.session_state.b2b_user = None

    if st.session_state.b2b_user is None:
        with st.form("login_form"):
            st.markdown(f"### {tr('login')}")
            email = st.text_input(tr("email"))
            pwd = st.text_input(tr("password"), type="password")
            ok = st.form_submit_button(tr("login_btn"), use_container_width=True)
        if ok:
            # Demo auth — replace with hashed DB lookup in production
            if email.strip().lower() == "supplier@demo.com" and pwd == "solar123":
                st.session_state.b2b_user = email
                st.rerun()
            else:
                st.error(tr("login_bad"))
    else:
        top = st.columns([4, 1])
        top[0].markdown(f"### {tr('welcome')}, `{st.session_state.b2b_user}` 👋")
        if top[1].button(tr("logout")):
            st.session_state.b2b_user = None
            st.rerun()

        st.markdown(f"#### {tr('erp_title')}")
        st.caption(tr("erp_note"))

        # Demo orders data (session-persisted) — DB layer comes in next step
        if "orders" not in st.session_state:
            st.session_state.orders = pd.DataFrame([
                ["SO-1001", "Ahmed M.",  8.25, 4900, "status_new",      "2026-07-01"],
                ["SO-1002", "Mona K.",  12.10, 7300, "status_progress", "2026-06-24"],
                ["SO-1003", "Delta Co.", 55.0, 31000, "status_progress","2026-06-18"],
                ["SO-1004", "Omar S.",   5.50, 3200, "status_done",     "2026-06-02"],
            ], columns=["id", "client", "kwp", "value", "status", "date"])

        df_o = st.session_state.orders.copy()
        m1, m2, m3 = st.columns(3)
        m1.metric(tr("orders_open"), int((df_o["status"] != "status_done").sum()))
        m2.metric(tr("orders_value"), f"{df_o['value'].sum():,.0f} USD")
        m3.metric(tr("orders_month"),
                  int(df_o["date"].str.startswith("2026-07").sum()))

        df_view = df_o.rename(columns={
            "id": tr("tbl_id"), "client": tr("tbl_client"), "kwp": tr("tbl_kwp"),
            "value": tr("tbl_value"), "status": tr("tbl_status"), "date": tr("tbl_date"),
        })
        df_view[tr("tbl_status")] = df_o["status"].map(lambda s: tr(s))
        st.dataframe(df_view, use_container_width=True, hide_index=True)

        fig = px.pie(df_o, names=df_o["status"].map(lambda s: tr(s)),
                     values="value", hole=0.5,
                     color_discrete_sequence=px.colors.sequential.YlOrBr)
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)
