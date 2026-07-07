# -*- coding: utf-8 -*-
"""
==============================================================================
  SolarBridge v2 | منصة الطاقة الشمسية الذكية
  Bilingual (AR/EN) Solar Platform — Streamlit single-file app
------------------------------------------------------------------------------
  STRICT FLOW (as specified):
    Landing Page ──► [Customer] ──► Registration ──► Calculator
                │                    (address text ONLY → auto geocode
                │                     → simulated Google Solar API roof scan)
                ├──► [Installer Company] ──► Login ──► Full ERP
                └──► [Supplier]           ──► Login ──► Full ERP
  ERP sections: Overview · Inventory · Orders · Customers · Accounts
------------------------------------------------------------------------------
  NO manual inputs for: latitude, longitude, roof area, or obstacles.
  All of these are resolved automatically from the address string.
------------------------------------------------------------------------------
  requirements.txt : streamlit / pandas / plotly / requests
==============================================================================
"""

import math
import hashlib
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
    initial_sidebar_state="collapsed",
)

# =============================================================================
# 1) TRANSLATION LAYER — every UI string lives here
# =============================================================================
T = {
    "en": {
        "app_title": "☀️ SolarBridge — Smart Solar Platform",
        "tagline": "From your address to a full solar design — automatically.",
        "language": "🌐 Language",
        "back": "⬅️ Back",
        "home": "🏠 Home",
        # ---- Landing ----
        "landing_q": "Who are you?",
        "role_customer": "🏠 Customer",
        "role_customer_d": "Get a full solar system design for your home from just your address.",
        "role_installer": "🛠️ Energy & Installation Company",
        "role_installer_d": "Manage projects, orders, inventory and clients in one ERP.",
        "role_supplier": "📦 Supplier",
        "role_supplier_d": "Track stock, sales orders and accounts with installers.",
        "choose": "Select",
        # ---- Customer registration ----
        "reg_title": "📝 Create your account",
        "reg_sub": "One quick step before your free solar study.",
        "name": "👤 Full name",
        "phone": "📱 Phone number",
        "email": "✉️ Email",
        "reg_btn": "Continue to the calculator ➜",
        "reg_err": "Please fill in all fields correctly (valid phone & email).",
        "hello": "Hello",
        # ---- Calculator ----
        "calc_title": "⚡ Smart Solar Calculator",
        "calc_sub": "Type your address — we locate the building and scan the roof automatically.",
        "address": "📍 Your address",
        "address_ph": "e.g. 12 Tahrir St, Dokki, Giza, Egypt",
        "scan_btn": "🛰️ Locate & scan my roof",
        "scanning1": "Geocoding your address…",
        "scanning2": "Analyzing satellite imagery (Solar API)…",
        "scanning3": "Fetching NASA POWER irradiance…",
        "scan_ok": "✅ Roof analysis complete.",
        "geo_fail": "❌ Could not locate this address. Try adding city & country.",
        "found_at": "📌 Building located",
        "roof_gross": "Detected roof area",
        "roof_obst": "Obstacles deducted",
        "roof_net": "Net usable area",
        "confidence": "Detection confidence",
        "bill_head": "🔌 Your electricity consumption",
        "monthly_bill": "💵 Average monthly bill",
        "tariff": "⚡ Tariff (per kWh)",
        "currency": "💱 Currency",
        "sys_type": "🔋 System type",
        "on_grid": "On-Grid (no batteries)",
        "off_grid": "Off-Grid (with batteries)",
        "hybrid": "Hybrid (grid + batteries)",
        "autonomy": "🌙 Battery autonomy (days)",
        "calc_btn": "⚙️ Design my solar system",
        "nasa_fail": "⚠️ NASA API unreachable — using regional averages.",
        # ---- Results ----
        "results_title": "📊 Your Solar System — Engineering Report",
        "kpi_panels": "Solar Panels",
        "kpi_system": "System Size",
        "kpi_inverter": "Inverter",
        "kpi_batteries": "Batteries",
        "kpi_cost": "Estimated Cost",
        "kpi_saving": "Annual Savings",
        "kpi_payback": "Payback",
        "kpi_co2": "CO₂ Avoided / yr",
        "years": "years",
        "panel_unit": "panels",
        "battery_unit": "× 5 kWh",
        "no_batt": "Not required",
        "chart_prod": "🔆 Monthly Energy Production (kWh)",
        "chart_save": "💰 Cumulative Savings vs. System Cost (25 years)",
        "chart_irr": "☀️ Solar Irradiance at Your Location (kWh/m²/day)",
        "prod": "Production",
        "consumption": "Consumption",
        "cum_saving": "Cumulative savings",
        "sys_cost": "System cost",
        "month": "Month",
        "energy": "Energy (kWh)",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "coverage": "☑️ Your roof covers ~{pct}% of your annual consumption.",
        "eng_details": "🧮 Engineering details & equations used",
        "request_quote": "📨 Request quotes from certified installers",
        "quote_sent": "✅ Your request was sent! Installers will contact you at {phone}.",
        # ---- B2B / Login ----
        "login_title": "🔐 Company Login",
        "login_sub_installer": "Installation company portal",
        "login_sub_supplier": "Supplier portal",
        "password": "Password",
        "login_btn": "Sign in",
        "login_bad": "❌ Invalid credentials.",
        "demo_hint": "Demo — installer: installer@demo.com / solar123 · supplier: supplier@demo.com / solar123",
        "logout": "🚪 Logout",
        "welcome": "Welcome",
        # ---- ERP ----
        "erp_installer": "🛠️ Installer ERP",
        "erp_supplier": "📦 Supplier ERP",
        "tab_overview": "📈 Overview",
        "tab_inventory": "📦 Inventory",
        "tab_orders": "🧾 Orders",
        "tab_customers": "👥 Customers",
        "tab_accounts": "💰 Accounts",
        # overview
        "ov_revenue": "Revenue (YTD)",
        "ov_open": "Open Orders",
        "ov_stock_alerts": "Low-stock Alerts",
        "ov_receivable": "Receivables",
        "ov_rev_month": "Monthly Revenue",
        "ov_orders_status": "Orders by Status",
        # inventory
        "inv_title": "Inventory Management",
        "inv_add": "➕ Add / update item",
        "inv_item": "Item",
        "inv_cat": "Category",
        "inv_qty": "Qty",
        "inv_min": "Min. level",
        "inv_price": "Unit price (USD)",
        "inv_save": "Save item",
        "inv_saved": "✅ Item saved.",
        "inv_low": "⚠️ {n} item(s) below minimum stock level!",
        "cat_panel": "Panels", "cat_inv": "Inverters",
        "cat_batt": "Batteries", "cat_mount": "Mounting", "cat_cable": "Cables",
        # orders
        "ord_title": "Orders Management",
        "ord_new": "➕ New order",
        "ord_client": "Client",
        "ord_kwp": "System (kWp)",
        "ord_value": "Value (USD)",
        "ord_status": "Status",
        "ord_date": "Date",
        "ord_save": "Create order",
        "ord_saved": "✅ Order created.",
        "ord_update": "Update status of",
        "ord_apply": "Apply",
        "status_new": "New", "status_progress": "In progress",
        "status_done": "Installed", "status_cancel": "Cancelled",
        # customers
        "cust_title": "Customer Records (CRM)",
        "cust_note": "Leads registered from the customer calculator appear here automatically.",
        "cust_name": "Name", "cust_phone": "Phone", "cust_email": "Email",
        "cust_addr": "Address", "cust_kwp": "Est. kWp", "cust_date": "Registered",
        "cust_none": "No customer leads yet.",
        # accounts
        "acc_title": "Accounts & Finance",
        "acc_in": "Income", "acc_out": "Expenses", "acc_net": "Net profit",
        "acc_add": "➕ Record transaction",
        "acc_type": "Type", "acc_desc": "Description",
        "acc_amount": "Amount (USD)", "acc_save": "Record",
        "acc_saved": "✅ Transaction recorded.",
        "acc_ledger": "General Ledger",
        "disclaimer": "ℹ️ Estimates are indicative; a site survey is required for final quotation. Roof detection uses a simulated Solar API pending a production key.",
    },
    "ar": {
        "app_title": "☀️ سولار بريدج — منصة الطاقة الشمسية الذكية",
        "tagline": "من عنوانك إلى تصميم شمسي متكامل — أوتوماتيكياً.",
        "language": "🌐 اللغة",
        "back": "⬅️ رجوع",
        "home": "🏠 الرئيسية",
        # ---- Landing ----
        "landing_q": "من أنت؟",
        "role_customer": "🏠 عميل",
        "role_customer_d": "احصل على تصميم كامل لنظام شمسي لمنزلك من عنوانك فقط.",
        "role_installer": "🛠️ شركة طاقة وتركيب",
        "role_installer_d": "أدر المشاريع والطلبات والمخزون والعملاء في نظام ERP واحد.",
        "role_supplier": "📦 مورد",
        "role_supplier_d": "تابع المخزون وأوامر البيع والحسابات مع شركات التركيب.",
        "choose": "اختيار",
        # ---- Customer registration ----
        "reg_title": "📝 إنشاء حسابك",
        "reg_sub": "خطوة سريعة واحدة قبل دراستك الشمسية المجانية.",
        "name": "👤 الاسم الكامل",
        "phone": "📱 رقم الهاتف",
        "email": "✉️ البريد الإلكتروني",
        "reg_btn": "المتابعة إلى الحاسبة ➜",
        "reg_err": "يرجى تعبئة جميع الحقول بشكل صحيح (هاتف وبريد صالحين).",
        "hello": "مرحباً",
        # ---- Calculator ----
        "calc_title": "⚡ حاسبة الطاقة الشمسية الذكية",
        "calc_sub": "اكتب عنوانك — نحدد المبنى ونمسح السطح أوتوماتيكياً.",
        "address": "📍 عنوانك",
        "address_ph": "مثال: ١٢ شارع التحرير، الدقي، الجيزة، مصر",
        "scan_btn": "🛰️ حدد موقعي وامسح السطح",
        "scanning1": "جاري تحويل العنوان إلى إحداثيات…",
        "scanning2": "جاري تحليل صور الأقمار الصناعية (Solar API)…",
        "scanning3": "جاري جلب بيانات الإشعاع من ناسا…",
        "scan_ok": "✅ اكتمل تحليل السطح.",
        "geo_fail": "❌ تعذر تحديد هذا العنوان. جرّب إضافة المدينة والدولة.",
        "found_at": "📌 تم تحديد المبنى",
        "roof_gross": "مساحة السطح المكتشفة",
        "roof_obst": "العوائق المخصومة",
        "roof_net": "المساحة الصافية القابلة للاستخدام",
        "confidence": "دقة الاكتشاف",
        "bill_head": "🔌 استهلاكك من الكهرباء",
        "monthly_bill": "💵 متوسط الفاتورة الشهرية",
        "tariff": "⚡ التعريفة (لكل ك.و.س)",
        "currency": "💱 العملة",
        "sys_type": "🔋 نوع النظام",
        "on_grid": "متصل بالشبكة (بدون بطاريات)",
        "off_grid": "منفصل عن الشبكة (مع بطاريات)",
        "hybrid": "هجين (شبكة + بطاريات)",
        "autonomy": "🌙 أيام استقلالية البطاريات",
        "calc_btn": "⚙️ صمّم نظامي الشمسي",
        "nasa_fail": "⚠️ تعذر الوصول لواجهة ناسا — سيتم استخدام متوسطات إقليمية.",
        # ---- Results ----
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
        "battery_unit": "× 5 ك.و.س",
        "no_batt": "غير مطلوبة",
        "chart_prod": "🔆 الإنتاج الشهري للطاقة (ك.و.س)",
        "chart_save": "💰 التوفير التراكمي مقابل تكلفة النظام (25 سنة)",
        "chart_irr": "☀️ الإشعاع الشمسي في موقعك (ك.و.س/م²/يوم)",
        "prod": "الإنتاج",
        "consumption": "الاستهلاك",
        "cum_saving": "التوفير التراكمي",
        "sys_cost": "تكلفة النظام",
        "month": "الشهر",
        "energy": "الطاقة (ك.و.س)",
        "months": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                   "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
        "coverage": "☑️ سطحك يغطي حوالي {pct}% من استهلاكك السنوي.",
        "eng_details": "🧮 التفاصيل الهندسية والمعادلات المستخدمة",
        "request_quote": "📨 اطلب عروض أسعار من شركات معتمدة",
        "quote_sent": "✅ تم إرسال طلبك! ستتواصل معك الشركات على {phone}.",
        # ---- B2B / Login ----
        "login_title": "🔐 تسجيل دخول الشركات",
        "login_sub_installer": "بوابة شركات التركيب",
        "login_sub_supplier": "بوابة الموردين",
        "password": "كلمة المرور",
        "login_btn": "دخول",
        "login_bad": "❌ بيانات غير صحيحة.",
        "demo_hint": "تجريبي — شركة تركيب: installer@demo.com / solar123 · مورد: supplier@demo.com / solar123",
        "logout": "🚪 تسجيل الخروج",
        "welcome": "مرحباً",
        # ---- ERP ----
        "erp_installer": "🛠️ نظام ERP — شركة التركيب",
        "erp_supplier": "📦 نظام ERP — المورد",
        "tab_overview": "📈 نظرة عامة",
        "tab_inventory": "📦 إدارة المخزون",
        "tab_orders": "🧾 الطلبات",
        "tab_customers": "👥 بيانات العملاء",
        "tab_accounts": "💰 الحسابات",
        # overview
        "ov_revenue": "الإيرادات (منذ بداية السنة)",
        "ov_open": "طلبات مفتوحة",
        "ov_stock_alerts": "تنبيهات نقص المخزون",
        "ov_receivable": "مستحقات لدى الغير",
        "ov_rev_month": "الإيراد الشهري",
        "ov_orders_status": "الطلبات حسب الحالة",
        # inventory
        "inv_title": "إدارة المخزون",
        "inv_add": "➕ إضافة / تحديث صنف",
        "inv_item": "الصنف",
        "inv_cat": "الفئة",
        "inv_qty": "الكمية",
        "inv_min": "الحد الأدنى",
        "inv_price": "سعر الوحدة (دولار)",
        "inv_save": "حفظ الصنف",
        "inv_saved": "✅ تم حفظ الصنف.",
        "inv_low": "⚠️ يوجد {n} صنف/أصناف تحت الحد الأدنى للمخزون!",
        "cat_panel": "ألواح", "cat_inv": "إنفرترات",
        "cat_batt": "بطاريات", "cat_mount": "هياكل تثبيت", "cat_cable": "كابلات",
        # orders
        "ord_title": "إدارة الطلبات",
        "ord_new": "➕ طلب جديد",
        "ord_client": "العميل",
        "ord_kwp": "النظام (ك.و ذروة)",
        "ord_value": "القيمة (دولار)",
        "ord_status": "الحالة",
        "ord_date": "التاريخ",
        "ord_save": "إنشاء الطلب",
        "ord_saved": "✅ تم إنشاء الطلب.",
        "ord_update": "تحديث حالة",
        "ord_apply": "تطبيق",
        "status_new": "جديد", "status_progress": "قيد التنفيذ",
        "status_done": "تم التركيب", "status_cancel": "ملغي",
        # customers
        "cust_title": "سجل العملاء (CRM)",
        "cust_note": "العملاء المسجلون من حاسبة العميل يظهرون هنا تلقائياً.",
        "cust_name": "الاسم", "cust_phone": "الهاتف", "cust_email": "البريد",
        "cust_addr": "العنوان", "cust_kwp": "ك.و تقديري", "cust_date": "تاريخ التسجيل",
        "cust_none": "لا يوجد عملاء مسجلون بعد.",
        # accounts
        "acc_title": "الحسابات والمالية",
        "acc_in": "الإيرادات", "acc_out": "المصروفات", "acc_net": "صافي الربح",
        "acc_add": "➕ تسجيل حركة مالية",
        "acc_type": "النوع", "acc_desc": "الوصف",
        "acc_amount": "المبلغ (دولار)", "acc_save": "تسجيل",
        "acc_saved": "✅ تم تسجيل الحركة.",
        "acc_ledger": "دفتر الأستاذ العام",
        "disclaimer": "ℹ️ النتائج تقديرية والمعاينة الميدانية مطلوبة للعرض النهائي. اكتشاف السطح يستخدم محاكاة لـ Solar API لحين تفعيل مفتاح الإنتاج.",
    },
}

# =============================================================================
# 2) SESSION STATE / ROUTER
# =============================================================================
_defaults = {
    "lang": "ar",
    "page": "landing",        # landing | register | calculator | login | erp
    "role": None,             # customer | installer | supplier
    "customer": None,         # dict(name, phone, email)
    "roof": None,             # dict from simulated Solar API
    "result": None,           # engineering result
    "b2b_user": None,
    "leads": [],              # CRM leads pushed from the calculator
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)

def tr(key: str):
    """Translated string for the active language."""
    return T[st.session_state.lang].get(key, key)

def goto(page: str):
    st.session_state.page = page
    st.rerun()

# =============================================================================
# 3) MODERN UI — CSS (RTL for Arabic, card design)
# =============================================================================
IS_AR = st.session_state.lang == "ar"
st.markdown(
    f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&family=Inter:wght@400;600;800&display=swap');
      html, body, [class*="css"] {{ font-family: {"'Cairo'" if IS_AR else "'Inter'"}, sans-serif; }}
      .stApp {{ direction: {"rtl" if IS_AR else "ltr"}; }}
      div[data-testid="stMetric"] {{
          background: linear-gradient(145deg,#fffdf5,#fff7e0);
          border:1px solid #ffe1a8; border-radius:16px;
          padding:14px 16px; box-shadow:0 2px 8px rgba(255,170,0,.08);
      }}
      h1,h2,h3 {{ color:#1c3d5a; }}
      .stButton>button {{ border-radius:12px; font-weight:700; }}
      .solar-hero {{
          background:linear-gradient(120deg,#1c3d5a 0%,#2e6da4 60%,#f9a825 130%);
          color:#fff; padding:20px 26px; border-radius:18px; margin-bottom:14px;
      }}
      .solar-hero h1 {{ color:#fff; margin:0; font-size:1.5rem; }}
      .solar-hero p  {{ color:#ffe9b8; margin:4px 0 0; }}
      .role-card {{
          border:2px solid #ffe1a8; border-radius:18px; padding:22px;
          background:#fffdf5; min-height:150px; text-align:center;
      }}
      .role-card h3 {{ margin-top:0; }}
      .roof-card {{
          border:1px dashed #2e6da4; border-radius:14px;
          padding:12px 16px; background:#f2f8ff; margin:6px 0;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- Top bar: language toggle + home ----------------------------------------
top = st.columns([5, 2, 1])
with top[1]:
    lang_choice = st.radio("lang", ["العربية", "English"],
                           index=0 if IS_AR else 1,
                           horizontal=True, label_visibility="collapsed")
    new_lang = "ar" if lang_choice == "العربية" else "en"
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.rerun()
with top[2]:
    if st.session_state.page != "landing" and st.button(tr("home")):
        st.session_state.update(page="landing", role=None)
        st.rerun()

st.markdown(
    f"""<div class="solar-hero"><h1>{tr("app_title")}</h1>
        <p>{tr("tagline")}</p></div>""",
    unsafe_allow_html=True,
)

# =============================================================================
# 4) ENGINEERING CONSTANTS (standard industry assumptions)
# =============================================================================
PANEL_W              = 550     # W — standard commercial mono-PERC module
PANEL_AREA_M2        = 2.2     # m² per 550W module
AREA_UTILIZATION     = 0.70    # row spacing & walkways packing factor
TEMP_COEFF_P         = -0.0035 # γ : power temp. coefficient (per °C)
NOCT                 = 45.0    # Nominal Operating Cell Temperature (°C)
SOILING_LOSS         = 0.03
WIRING_LOSS          = 0.02
MISMATCH_LOSS        = 0.02
INVERTER_EFF         = 0.97
AVAILABILITY         = 0.99
DC_AC_RATIO          = 1.15    # inverter sizing: P_inv = kWp / 1.15
BATTERY_UNIT_KWH     = 5.0     # LiFePO4 48V/100Ah unit
DOD                  = 0.80    # Depth of Discharge (LiFePO4)
BATT_ROUNDTRIP_EFF   = 0.92
GRID_CO2_KG_PER_KWH  = 0.55    # grid emission factor (MENA ≈ 0.5–0.6)
COST_PER_WP          = 0.55    # USD/Wp installed (on-grid part)
COST_PER_KWH_BATT    = 250.0   # USD per stored kWh (LiFePO4)
DAYS_IN_MONTH        = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
FALLBACK_TEMPS       = [14, 16, 19, 24, 28, 30, 31, 31, 29, 26, 20, 16]
FALLBACK_GHI         = [5.0, 5.6, 6.4, 7.1, 7.5, 7.9,
                        7.7, 7.4, 6.9, 6.0, 5.2, 4.8]

# =============================================================================
# 5) LOCATION PIPELINE — address string ➜ coordinates ➜ roof geometry
#     (the customer NEVER types coordinates or areas)
# =============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def geocode_address(address: str):
    """
    Address string ➜ (lat, lon, display_name).
    1) Google Maps Geocoding API if GOOGLE_MAPS_API_KEY exists in st.secrets.
    2) Otherwise OpenStreetMap Nominatim (free, no key).
    Returns None on failure.
    """
    key = st.secrets.get("GOOGLE_MAPS_API_KEY", None) if hasattr(st, "secrets") else None
    if key:
        try:
            r = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": address, "key": key}, timeout=10)
            js = r.json()
            if js.get("status") == "OK":
                res = js["results"][0]
                loc = res["geometry"]["location"]
                return loc["lat"], loc["lng"], res["formatted_address"]
        except Exception:
            pass
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "SolarBridge/2.0"}, timeout=10)
        js = r.json()
        if js:
            return float(js[0]["lat"]), float(js[0]["lon"]), js[0]["display_name"]
    except Exception:
        pass
    return None


def solar_api_roof_scan(lat: float, lon: float):
    """
    *** Google Solar API simulation ***
    In production, replace the body of this function with a call to:
      GET https://solar.googleapis.com/v1/buildingInsights:findClosest
          ?location.latitude={lat}&location.longitude={lon}&key=API_KEY
    which returns `solarPotential.wholeRoofStats.areaMeters2` and per-segment
    stats from which net usable area is derived.

    The simulation below is DETERMINISTIC per location (seeded by coordinates)
    so the same address always yields the same roof — mimicking a real scan:
      - gross roof area:      80–320 m²  (typical urban residential range)
      - obstacle fraction:    10–28 %    (tanks, stairwells, HVAC, shading)
      - detection confidence: 88–99 %
    """
    seed = int(hashlib.sha256(f"{lat:.5f},{lon:.5f}".encode()).hexdigest(), 16)
    gross = 80 + (seed % 241)                       # 80..320 m²
    obst_frac = 0.10 + ((seed >> 8) % 19) / 100.0   # 0.10..0.28
    conf = 88 + ((seed >> 16) % 12)                 # 88..99 %
    obstacles = round(gross * obst_frac, 1)
    net = round(gross - obstacles, 1)
    return {"gross_m2": float(gross), "obstacles_m2": obstacles,
            "net_m2": net, "confidence": conf}


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_nasa_power(lat: float, lon: float):
    """
    NASA POWER climatology. ALLSKY_SFC_SW_DWN [kWh/m²/day] numerically equals
    the daily Peak Sun Hours (PSH) at the 1 kW/m² reference irradiance.
    """
    r = requests.get(
        "https://power.larc.nasa.gov/api/temporal/climatology/point",
        params={"parameters": "ALLSKY_SFC_SW_DWN,T2M", "community": "RE",
                "latitude": lat, "longitude": lon, "format": "JSON"},
        timeout=15)
    r.raise_for_status()
    p = r.json()["properties"]["parameter"]
    keys = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
    ghi = [p["ALLSKY_SFC_SW_DWN"][k] for k in keys]
    temps = [p.get("T2M", {}).get(k, FALLBACK_TEMPS[i]) for i, k in enumerate(keys)]
    return ghi, temps

# =============================================================================
# 6) PV ENGINEERING MODEL — standard equations (fully commented)
# =============================================================================
def design_pv_system(net_roof_m2, monthly_bill, tariff,
                     ghi_monthly, temp_monthly, sys_type, autonomy_days):
    """
    (1) Usable area:      A_use = A_net × 0.70            (row-spacing factor)
    (2) Daily load:       E_day = (Bill / tariff) / 30.4
    (3) Cell temperature: T_cell = T_amb + (NOCT−20)/800 × G   (G = 1000 W/m²)
    (4) Thermal derate:   f_T = 1 + γ (T_cell − 25)
    (5) Performance Ratio PR = f_T·(1−L_soil)(1−L_wire)(1−L_mism)·η_inv·A_avail
    (6) Sizing (worst month): kWp = E_day / (PSH_min × PR_min), capped by area
    (7) Monthly energy:   E_m = kWp × PSH_m × PR_m × N_days
    (8) Battery bank:     C = (E_day × N_autonomy) / (DoD × η_roundtrip)
    (9) Inverter:         P_inv = kWp / 1.15  → next commercial size
    """
    a_use = net_roof_m2 * AREA_UTILIZATION                      # (1)
    max_panels = int(a_use // PANEL_AREA_M2)
    kwp_area_max = max_panels * PANEL_W / 1000.0

    daily_load = (monthly_bill / max(tariff, 1e-6)) / 30.4      # (2)

    pr_m = []
    for m in range(12):
        t_cell = temp_monthly[m] + (NOCT - 20.0) / 800.0 * 1000.0   # (3)
        f_t = 1 + TEMP_COEFF_P * (t_cell - 25.0)                    # (4)
        pr_m.append(f_t * (1 - SOILING_LOSS) * (1 - WIRING_LOSS)    # (5)
                    * (1 - MISMATCH_LOSS) * INVERTER_EFF * AVAILABILITY)

    w = ghi_monthly.index(min(ghi_monthly))                     # worst month
    kwp_req = daily_load / (ghi_monthly[w] * pr_m[w])           # (6)
    n_panels = max(1, min(math.ceil(kwp_req * 1000 / PANEL_W), max_panels))
    kwp = n_panels * PANEL_W / 1000.0

    e_m = [kwp * ghi_monthly[m] * pr_m[m] * DAYS_IN_MONTH[m]    # (7)
           for m in range(12)]
    e_year = sum(e_m)

    if sys_type in ("off_grid", "hybrid"):                      # (8)
        batt_kwh = (daily_load * autonomy_days) / (DOD * BATT_ROUNDTRIP_EFF)
        n_batt = math.ceil(batt_kwh / BATTERY_UNIT_KWH)
    else:
        batt_kwh, n_batt = 0.0, 0

    inv_raw = kwp / DC_AC_RATIO                                 # (9)
    sizes = [1.5, 2, 3, 3.6, 5, 6, 8, 10, 12, 15, 20, 25, 30, 50, 100]
    inv_kw = next((s for s in sizes if s >= inv_raw), math.ceil(inv_raw))

    capex = kwp * 1000 * COST_PER_WP + batt_kwh * COST_PER_KWH_BATT
    annual_cons = daily_load * 365
    saving = min(e_year, annual_cons) * tariff       # self-consumption cap
    payback = capex / saving if saving > 0 else float("inf")
    co2 = e_year * GRID_CO2_KG_PER_KWH / 1000.0
    coverage = min(100.0, 100.0 * e_year / annual_cons) if annual_cons else 0

    return dict(kwp=kwp, n_panels=n_panels, inv_kw=inv_kw,
                n_batteries=n_batt, batt_kwh=batt_kwh, capex=capex,
                annual_saving=saving, payback=payback, co2_tons=co2,
                e_monthly=e_m, e_annual=e_year, pr_monthly=pr_m,
                daily_load=daily_load, coverage=coverage)

# =============================================================================
# 7) DEMO DATA STORES for the ERP (replace with a DB in production)
# =============================================================================
def init_erp_data():
    if "inventory" not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            ["Jinko Tiger 550W",  "cat_panel", 120, 40, 95.0],
            ["Huawei SUN2000 10kW","cat_inv",    8,  5, 1150.0],
            ["Pylontech US5000",  "cat_batt",   14, 10, 1250.0],
            ["Alu Rail 4.2m",     "cat_mount", 300, 100, 18.0],
            ["DC Cable 6mm² (m)", "cat_cable",  60, 200, 1.2],
        ], columns=["item", "cat", "qty", "min", "price"])
    if "orders" not in st.session_state:
        st.session_state.orders = pd.DataFrame([
            ["SO-1001", "Ahmed M.",   8.25,  4900, "status_new",      "2026-07-02"],
            ["SO-1002", "Mona K.",   12.10,  7300, "status_progress", "2026-06-24"],
            ["SO-1003", "Delta Co.", 55.00, 31000, "status_progress", "2026-06-18"],
            ["SO-1004", "Omar S.",    5.50,  3200, "status_done",     "2026-06-02"],
            ["SO-1005", "Nile Farms",90.00, 49500, "status_done",     "2026-05-11"],
        ], columns=["id", "client", "kwp", "value", "status", "date"])
    if "ledger" not in st.session_state:
        st.session_state.ledger = pd.DataFrame([
            ["2026-05-15", "in",  "Payment SO-1005", 49500.0],
            ["2026-06-05", "in",  "Payment SO-1004",  3200.0],
            ["2026-06-10", "out", "Panels purchase", 11400.0],
            ["2026-06-20", "out", "Salaries",         6500.0],
            ["2026-07-01", "in",  "Deposit SO-1001",  2450.0],
        ], columns=["date", "type", "desc", "amount"])

# =============================================================================
# 8) PAGE: LANDING — the 3 role buttons ONLY
# =============================================================================
def page_landing():
    st.markdown(f"## {tr('landing_q')}")
    c1, c2, c3 = st.columns(3)
    roles = [
        (c1, "customer",  "role_customer",  "role_customer_d"),
        (c2, "installer", "role_installer", "role_installer_d"),
        (c3, "supplier",  "role_supplier",  "role_supplier_d"),
    ]
    for col, role, title_k, desc_k in roles:
        with col:
            st.markdown(
                f"""<div class="role-card"><h3>{tr(title_k)}</h3>
                    <p>{tr(desc_k)}</p></div>""",
                unsafe_allow_html=True)
            if st.button(f"{tr('choose')} — {tr(title_k)}",
                         key=f"role_{role}", use_container_width=True):
                st.session_state.role = role
                goto("register" if role == "customer" else "login")
    st.caption(tr("disclaimer"))

# =============================================================================
# 9) PAGE: CUSTOMER REGISTRATION (name / phone / email)
# =============================================================================
def page_register():
    st.markdown(f"## {tr('reg_title')}")
    st.caption(tr("reg_sub"))
    with st.form("reg"):
        name = st.text_input(tr("name"))
        phone = st.text_input(tr("phone"))
        email = st.text_input(tr("email"))
        ok = st.form_submit_button(tr("reg_btn"), use_container_width=True,
                                   type="primary")
    if ok:
        valid = (len(name.strip()) >= 3
                 and sum(ch.isdigit() for ch in phone) >= 8
                 and "@" in email and "." in email.split("@")[-1])
        if valid:
            st.session_state.customer = dict(
                name=name.strip(), phone=phone.strip(), email=email.strip())
            goto("calculator")
        else:
            st.error(tr("reg_err"))
    if st.button(tr("back")):
        goto("landing")

# =============================================================================
# 10) PAGE: CALCULATOR — address text box ONLY (everything else automatic)
# =============================================================================
def page_calculator():
    cust = st.session_state.customer or {"name": "?", "phone": "?"}
    st.markdown(f"## {tr('calc_title')}")
    st.caption(f"{tr('hello')} **{cust['name']}** 👋 — {tr('calc_sub')}")

    # ---- (A) The ONLY location input: a single address search box ----------
    address = st.text_input(tr("address"), placeholder=tr("address_ph"),
                            key="addr_input")
    if st.button(tr("scan_btn"), type="primary", use_container_width=True):
        if not address.strip():
            st.error(tr("geo_fail"))
        else:
            with st.status(tr("scanning1"), expanded=False) as status:
                geo = geocode_address(address.strip())
                if geo is None:
                    status.update(label=tr("geo_fail"), state="error")
                else:
                    lat, lon, display = geo
                    status.update(label=tr("scanning2"))
                    roof = solar_api_roof_scan(lat, lon)   # auto roof geometry
                    status.update(label=tr("scanning3"))
                    try:
                        ghi, temps = fetch_nasa_power(lat, lon)
                    except Exception:
                        ghi, temps = FALLBACK_GHI, FALLBACK_TEMPS
                        st.warning(tr("nasa_fail"))
                    st.session_state.roof = dict(
                        lat=lat, lon=lon, display=display,
                        ghi=ghi, temps=temps, **roof)
                    st.session_state.result = None
                    status.update(label=tr("scan_ok"), state="complete")

    # ---- (B) Auto-detected roof summary (read-only — never typed by user) --
    roof = st.session_state.roof
    if roof:
        st.markdown(
            f"""<div class="roof-card">
                 <b>{tr('found_at')}:</b> {roof['display'][:120]}<br>
                 🛰️ <b>{tr('roof_gross')}:</b> {roof['gross_m2']:,.0f} m² &nbsp;·&nbsp;
                 🚧 <b>{tr('roof_obst')}:</b> −{roof['obstacles_m2']:,.1f} m² &nbsp;·&nbsp;
                 ✅ <b>{tr('roof_net')}:</b> <b>{roof['net_m2']:,.1f} m²</b> &nbsp;·&nbsp;
                 🎯 <b>{tr('confidence')}:</b> {roof['confidence']}%
               </div>""",
            unsafe_allow_html=True)
        st.map(pd.DataFrame({"lat": [roof["lat"]], "lon": [roof["lon"]]}),
               size=30, zoom=16)

        # ---- (C) Consumption inputs (billing only — not geometry) ----------
        st.markdown(f"### {tr('bill_head')}")
        c1, c2, c3 = st.columns(3)
        with c1:
            currency = st.selectbox(tr("currency"), ["EGP", "SAR", "AED", "USD"])
            bill = st.number_input(tr("monthly_bill"), 50.0, 1e7, 1500.0, 50.0)
        with c2:
            tariff = st.number_input(tr("tariff"), 0.05, 50.0, 2.2, 0.05)
        with c3:
            sys_label = st.selectbox(
                tr("sys_type"), [tr("on_grid"), tr("hybrid"), tr("off_grid")])
            sys_type = {tr("on_grid"): "on_grid", tr("hybrid"): "hybrid",
                        tr("off_grid"): "off_grid"}[sys_label]
            autonomy = (st.slider(tr("autonomy"), 0.5, 3.0, 1.0, 0.5)
                        if sys_type != "on_grid" else 0.0)

        if st.button(tr("calc_btn"), type="primary", use_container_width=True):
            st.session_state.result = design_pv_system(
                roof["net_m2"], bill, tariff,
                roof["ghi"], roof["temps"], sys_type, autonomy)
            st.session_state.result_meta = dict(currency=currency)
            # push a CRM lead to the B2B side automatically
            st.session_state.leads.append(dict(
                name=cust["name"], phone=cust["phone"],
                email=cust.get("email", ""),
                addr=roof["display"][:80],
                kwp=round(st.session_state.result["kwp"], 2),
                date=dt.date.today().isoformat()))

    # ---- (D) Results dashboard ---------------------------------------------
    res = st.session_state.result
    if res and roof:
        cur = st.session_state.result_meta["currency"]
        months = tr("months")
        st.markdown(f"## {tr('results_title')}")

        k1, k2, k3, k4 = st.columns(4)
        k1.metric(tr("kpi_panels"), f"{res['n_panels']} {tr('panel_unit')}",
                  f"{PANEL_W} W")
        k2.metric(tr("kpi_system"), f"{res['kwp']:.2f} kWp")
        k3.metric(tr("kpi_inverter"), f"{res['inv_kw']} kW")
        k4.metric(tr("kpi_batteries"),
                  f"{res['n_batteries']} {tr('battery_unit')}"
                  if res["n_batteries"] else tr("no_batt"),
                  f"{res['batt_kwh']:.1f} kWh" if res["batt_kwh"] else None)

        k5, k6, k7, k8 = st.columns(4)
        k5.metric(tr("kpi_cost"), f"{res['capex']:,.0f} USD")
        k6.metric(tr("kpi_saving"), f"{res['annual_saving']:,.0f} {cur}")
        k7.metric(tr("kpi_payback"),
                  f"{res['payback']:.1f} {tr('years')}"
                  if res["payback"] != float("inf") else "—")
        k8.metric(tr("kpi_co2"), f"{res['co2_tons']:.2f} t")

        st.success(tr("coverage").format(pct=f"{res['coverage']:.0f}"))

        # Chart 1 — monthly production vs consumption
        fig1 = go.Figure()
        fig1.add_bar(x=months, y=[round(e) for e in res["e_monthly"]],
                     name=tr("prod"), marker_color="#f9a825")
        fig1.add_scatter(x=months,
                         y=[round(res["daily_load"] * d) for d in DAYS_IN_MONTH],
                         name=tr("consumption"), mode="lines+markers",
                         line=dict(color="#1c3d5a", width=3))
        fig1.update_layout(title=tr("chart_prod"), yaxis_title=tr("energy"),
                           legend=dict(orientation="h"), height=380)
        st.plotly_chart(fig1, use_container_width=True)

        # Chart 2 — cumulative savings vs capex over 25 years
        DEGRADATION = 0.005            # 0.5 %/yr module degradation
        yrs, cum, total = list(range(26)), [], 0.0
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

        # Chart 3 — irradiance profile
        fig3 = px.area(x=months, y=roof["ghi"], title=tr("chart_irr"),
                       color_discrete_sequence=["#f9a825"])
        fig3.update_layout(height=320, xaxis_title=tr("month"),
                           yaxis_title="kWh/m²/day")
        st.plotly_chart(fig3, use_container_width=True)

        with st.expander(tr("eng_details")):
            st.latex(r"E_{month} = kWp \times PSH \times PR \times N_{days}")
            st.latex(r"PR = f_{T}\,(1-L_{soil})(1-L_{wire})(1-L_{mism})\,\eta_{inv}\,A_{avail}")
            st.latex(r"f_{T} = 1 + \gamma\,(T_{cell}-25),\quad T_{cell}=T_{amb}+\tfrac{NOCT-20}{800}\,G")
            st.latex(r"C_{batt} = \frac{E_{daily}\times N_{autonomy}}{DoD\times\eta_{rt}}")
            st.latex(r"P_{inverter} = kWp / 1.15")
            st.dataframe(pd.DataFrame({
                tr("month"): months,
                "PSH": [round(g, 2) for g in roof["ghi"]],
                "PR": [round(p, 3) for p in res["pr_monthly"]],
                tr("prod"): [round(e) for e in res["e_monthly"]],
            }), use_container_width=True, hide_index=True)

        if st.button(tr("request_quote"), use_container_width=True):
            st.balloons()
            st.success(tr("quote_sent").format(phone=cust["phone"]))

# =============================================================================
# 11) PAGE: B2B LOGIN (installer / supplier)
# =============================================================================
DEMO_USERS = {   # replace with hashed-password DB in production
    "installer@demo.com": ("solar123", "installer"),
    "supplier@demo.com":  ("solar123", "supplier"),
}

def page_login():
    role = st.session_state.role or "installer"
    st.markdown(f"## {tr('login_title')}")
    st.caption(tr("login_sub_installer") if role == "installer"
               else tr("login_sub_supplier"))
    with st.form("login"):
        email = st.text_input(tr("email") if "email" in T[st.session_state.lang]
                              else "Email", key="login_email")
        pwd = st.text_input(tr("password"), type="password")
        ok = st.form_submit_button(tr("login_btn"), use_container_width=True,
                                   type="primary")
    st.caption(tr("demo_hint"))
    if ok:
        rec = DEMO_USERS.get(email.strip().lower())
        if rec and rec[0] == pwd:
            st.session_state.b2b_user = email.strip().lower()
            st.session_state.role = rec[1]      # trust role from account
            goto("erp")
        else:
            st.error(tr("login_bad"))
    if st.button(tr("back")):
        goto("landing")

# =============================================================================
# 12) PAGE: FULL ERP — Overview · Inventory · Orders · Customers · Accounts
# =============================================================================
def page_erp():
    init_erp_data()
    role = st.session_state.role
    head = st.columns([4, 1])
    head[0].markdown(f"## {tr('erp_installer') if role == 'installer' else tr('erp_supplier')}")
    head[0].caption(f"{tr('welcome')} `{st.session_state.b2b_user}`")
    if head[1].button(tr("logout"), use_container_width=True):
        st.session_state.update(b2b_user=None, page="landing", role=None)
        st.rerun()

    tabs = st.tabs([tr("tab_overview"), tr("tab_inventory"),
                    tr("tab_orders"), tr("tab_customers"), tr("tab_accounts")])

    inv, orders, ledger = (st.session_state.inventory,
                           st.session_state.orders,
                           st.session_state.ledger)

    # ---------------- Overview ----------------
    with tabs[0]:
        income = ledger.loc[ledger["type"] == "in", "amount"].sum()
        low_stock = int((inv["qty"] < inv["min"]).sum())
        open_orders = int((~orders["status"].isin(["status_done",
                                                   "status_cancel"])).sum())
        receiv = orders.loc[~orders["status"].isin(
            ["status_done", "status_cancel"]), "value"].sum()
        m = st.columns(4)
        m[0].metric(tr("ov_revenue"), f"{income:,.0f} USD")
        m[1].metric(tr("ov_open"), open_orders)
        m[2].metric(tr("ov_stock_alerts"), low_stock)
        m[3].metric(tr("ov_receivable"), f"{receiv:,.0f} USD")

        c1, c2 = st.columns(2)
        with c1:  # monthly revenue bar
            led = ledger[ledger["type"] == "in"].copy()
            led["month"] = pd.to_datetime(led["date"]).dt.strftime("%Y-%m")
            rev = led.groupby("month", as_index=False)["amount"].sum()
            st.plotly_chart(px.bar(rev, x="month", y="amount",
                                   title=tr("ov_rev_month"),
                                   color_discrete_sequence=["#f9a825"])
                            .update_layout(height=320),
                            use_container_width=True)
        with c2:  # orders by status donut
            pie = orders.copy()
            pie["s"] = pie["status"].map(lambda s: tr(s))
            st.plotly_chart(px.pie(pie, names="s", values="value", hole=0.5,
                                   title=tr("ov_orders_status"),
                                   color_discrete_sequence=px.colors.sequential.YlOrBr)
                            .update_layout(height=320),
                            use_container_width=True)

    # ---------------- Inventory ----------------
    with tabs[1]:
        st.markdown(f"### {tr('inv_title')}")
        low = inv[inv["qty"] < inv["min"]]
        if len(low):
            st.warning(tr("inv_low").format(n=len(low)))
        view = inv.copy()
        view["cat"] = view["cat"].map(lambda c: tr(c))
        view.columns = [tr("inv_item"), tr("inv_cat"), tr("inv_qty"),
                        tr("inv_min"), tr("inv_price")]
        st.dataframe(view, use_container_width=True, hide_index=True)

        with st.expander(tr("inv_add")):
            with st.form("inv_form"):
                c = st.columns(5)
                item = c[0].text_input(tr("inv_item"))
                cat = c[1].selectbox(tr("inv_cat"),
                                     ["cat_panel", "cat_inv", "cat_batt",
                                      "cat_mount", "cat_cable"],
                                     format_func=tr)
                qty = c[2].number_input(tr("inv_qty"), 0, 100000, 10)
                mn = c[3].number_input(tr("inv_min"), 0, 100000, 5)
                pr = c[4].number_input(tr("inv_price"), 0.0, 1e6, 100.0)
                if st.form_submit_button(tr("inv_save")) and item.strip():
                    df = st.session_state.inventory
                    mask = df["item"].str.lower() == item.strip().lower()
                    if mask.any():          # update existing
                        df.loc[mask, ["cat", "qty", "min", "price"]] = \
                            [cat, qty, mn, pr]
                    else:                   # insert new
                        df.loc[len(df)] = [item.strip(), cat, qty, mn, pr]
                    st.success(tr("inv_saved"))
                    st.rerun()

    # ---------------- Orders ----------------
    with tabs[2]:
        st.markdown(f"### {tr('ord_title')}")
        view = orders.copy()
        view["status"] = view["status"].map(lambda s: tr(s))
        view.columns = ["ID", tr("ord_client"), tr("ord_kwp"),
                        tr("ord_value"), tr("ord_status"), tr("ord_date")]
        st.dataframe(view, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1, st.expander(tr("ord_new"), expanded=False):
            with st.form("ord_form"):
                client = st.text_input(tr("ord_client"))
                kwp = st.number_input(tr("ord_kwp"), 0.5, 5000.0, 10.0)
                val = st.number_input(tr("ord_value"), 100.0, 1e7, 6000.0)
                if st.form_submit_button(tr("ord_save")) and client.strip():
                    df = st.session_state.orders
                    new_id = f"SO-{1000 + len(df) + 1}"
                    df.loc[len(df)] = [new_id, client.strip(), kwp, val,
                                       "status_new",
                                       dt.date.today().isoformat()]
                    st.success(tr("ord_saved"))
                    st.rerun()
        with c2:
            oid = st.selectbox(tr("ord_update"), orders["id"].tolist())
            new_s = st.selectbox(tr("ord_status"),
                                 ["status_new", "status_progress",
                                  "status_done", "status_cancel"],
                                 format_func=tr)
            if st.button(tr("ord_apply")):
                st.session_state.orders.loc[
                    st.session_state.orders["id"] == oid, "status"] = new_s
                st.rerun()

    # ---------------- Customers (CRM) ----------------
    with tabs[3]:
        st.markdown(f"### {tr('cust_title')}")
        st.caption(tr("cust_note"))
        leads = st.session_state.leads
        if leads:
            df_l = pd.DataFrame(leads)
            df_l.columns = [tr("cust_name"), tr("cust_phone"), tr("cust_email"),
                            tr("cust_addr"), tr("cust_kwp"), tr("cust_date")]
            st.dataframe(df_l, use_container_width=True, hide_index=True)
        else:
            st.info(tr("cust_none"))

    # ---------------- Accounts ----------------
    with tabs[4]:
        st.markdown(f"### {tr('acc_title')}")
        income = ledger.loc[ledger["type"] == "in", "amount"].sum()
        expense = ledger.loc[ledger["type"] == "out", "amount"].sum()
        a = st.columns(3)
        a[0].metric(tr("acc_in"), f"{income:,.0f} USD")
        a[1].metric(tr("acc_out"), f"{expense:,.0f} USD")
        a[2].metric(tr("acc_net"), f"{income - expense:,.0f} USD")

        with st.expander(tr("acc_add")):
            with st.form("acc_form"):
                c = st.columns(3)
                ttype = c[0].selectbox(tr("acc_type"), ["in", "out"],
                                       format_func=lambda x:
                                       tr("acc_in") if x == "in" else tr("acc_out"))
                desc = c[1].text_input(tr("acc_desc"))
                amt = c[2].number_input(tr("acc_amount"), 0.0, 1e7, 1000.0)
                if st.form_submit_button(tr("acc_save")) and desc.strip():
                    st.session_state.ledger.loc[len(ledger)] = \
                        [dt.date.today().isoformat(), ttype, desc.strip(), amt]
                    st.success(tr("acc_saved"))
                    st.rerun()

        st.markdown(f"#### {tr('acc_ledger')}")
        led_view = ledger.copy().sort_values("date", ascending=False)
        led_view["type"] = led_view["type"].map(
            lambda x: tr("acc_in") if x == "in" else tr("acc_out"))
        led_view.columns = [tr("ord_date"), tr("acc_type"),
                            tr("acc_desc"), tr("acc_amount")]
        st.dataframe(led_view, use_container_width=True, hide_index=True)

# =============================================================================
# 13) ROUTER
# =============================================================================
PAGES = {
    "landing": page_landing,
    "register": page_register,
    "calculator": page_calculator,
    "login": page_login,
    "erp": page_erp,
}
# Guard: ERP requires auth; calculator requires registration
if st.session_state.page == "erp" and not st.session_state.b2b_user:
    st.session_state.page = "login"
if st.session_state.page == "calculator" and not st.session_state.customer:
    st.session_state.page = "register"

PAGES[st.session_state.page]()
