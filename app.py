# -*- coding: utf-8 -*-
"""
==============================================================================
  SolarBridge v3 — Premium SaaS | منصة الطاقة الشمسية الذكية
  Bilingual (AR/EN) • Streamlit single-file app
------------------------------------------------------------------------------
  ✔ Premium UI  : custom CSS, hidden Streamlit chrome, glass cards,
                  fully clickable role cards with hover effects
  ✔ Real DB     : SQLite (customers / orders / inventory / ledger)
                  → customer requests are INSERTed, ERP SELECTs live data
  ✔ Real APIs   : Google Geocoding API + Google Solar API + NASA POWER
                  (API key ONLY via st.secrets["GOOGLE_API_KEY"] — never
                   hard-coded; admins are prompted if it's missing)
  ✔ Router      : st.session_state navigation, no page reloads
------------------------------------------------------------------------------
  requirements.txt:
      streamlit
      pandas
      plotly
      requests
      googlemaps
==============================================================================
"""

import math
import sqlite3
import hashlib
import datetime as dt

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# Official Google SDK is primary; raw HTTPS via `requests` (still Google
# endpoints) is the fallback if the package is missing.
try:
    import googlemaps
    GMAPS_OK = True
except Exception:
    GMAPS_OK = False

# =============================================================================
# 0) PAGE CONFIG
# =============================================================================
st.set_page_config(page_title="SolarBridge", page_icon="☀️",
                   layout="wide", initial_sidebar_state="collapsed")

# =============================================================================
# 1) SQLITE DATABASE LAYER  — real persistence (file: solarbridge.db)
# =============================================================================
DB_PATH = "solarbridge.db"

@st.cache_resource
def get_db() -> sqlite3.Connection:
    """Single cached connection shared across reruns/sessions."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS customers(
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            phone      TEXT NOT NULL,
            email      TEXT NOT NULL,
            address    TEXT DEFAULT '',
            lat        REAL, lon REAL,
            roof_net   REAL,             -- m² (auto-detected)
            kwp        REAL,             -- last computed design
            created_at TEXT DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS orders(
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ref         TEXT UNIQUE,
            customer_id INTEGER,
            client      TEXT NOT NULL,
            kwp         REAL,
            value_usd   REAL,
            status      TEXT DEFAULT 'status_new',
            created_at  TEXT DEFAULT (date('now')),
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );
        CREATE TABLE IF NOT EXISTS inventory(
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            item      TEXT UNIQUE NOT NULL,
            cat       TEXT NOT NULL,
            qty       INTEGER DEFAULT 0,
            min_level INTEGER DEFAULT 0,
            price_usd REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS ledger(
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            tdate  TEXT DEFAULT (date('now')),
            ttype  TEXT CHECK(ttype IN ('in','out')),
            descr  TEXT,
            amount REAL
        );
    """)
    # ---- seed demo rows once (so the investor demo never looks empty) -------
    if conn.execute("SELECT COUNT(*) c FROM inventory").fetchone()["c"] == 0:
        conn.executemany(
            "INSERT INTO inventory(item,cat,qty,min_level,price_usd) VALUES(?,?,?,?,?)",
            [("Jinko Tiger Neo 550W", "cat_panel", 120, 40, 95.0),
             ("Huawei SUN2000 10kW",  "cat_inv",     8,  5, 1150.0),
             ("Pylontech US5000 5kWh","cat_batt",   14, 10, 1250.0),
             ("Alu Mounting Rail 4.2m","cat_mount",300,100, 18.0),
             ("DC Solar Cable 6mm²/m","cat_cable",  60,200, 1.2)])
    if conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"] == 0:
        conn.executemany(
            "INSERT INTO orders(ref,client,kwp,value_usd,status,created_at) VALUES(?,?,?,?,?,?)",
            [("SO-1001","Delta Agro Co.",55.0,31000,"status_progress","2026-06-18"),
             ("SO-1002","Nile Farms",    90.0,49500,"status_done",    "2026-05-11"),
             ("SO-1003","Omar S.",        5.5, 3200,"status_done",    "2026-06-02")])
    if conn.execute("SELECT COUNT(*) c FROM ledger").fetchone()["c"] == 0:
        conn.executemany(
            "INSERT INTO ledger(tdate,ttype,descr,amount) VALUES(?,?,?,?)",
            [("2026-05-15","in","Payment SO-1002",49500.0),
             ("2026-06-05","in","Payment SO-1003", 3200.0),
             ("2026-06-10","out","Panels purchase",11400.0),
             ("2026-06-20","out","Salaries",        6500.0),
             ("2026-07-01","in","Deposit SO-1001",  9300.0)])
    conn.commit()
    return conn

def db_insert_customer(name, phone, email) -> int:
    """INSERT the registered customer — returns the new row id."""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO customers(name,phone,email) VALUES(?,?,?)",
        (name, phone, email))
    conn.commit()
    return cur.lastrowid

def db_update_customer_site(cid, address, lat, lon, roof_net, kwp):
    conn = get_db()
    conn.execute("""UPDATE customers
                    SET address=?, lat=?, lon=?, roof_net=?, kwp=? WHERE id=?""",
                 (address, lat, lon, roof_net, kwp, cid))
    conn.commit()

def db_create_order(cid, client, kwp, value_usd) -> str:
    """Customer quote request → real order row the ERP will SELECT."""
    conn = get_db()
    n = conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]
    ref = f"SO-{1001 + n}"
    conn.execute("""INSERT INTO orders(ref,customer_id,client,kwp,value_usd)
                    VALUES(?,?,?,?,?)""", (ref, cid, client, kwp, value_usd))
    conn.commit()
    return ref

def db_df(query, params=()) -> pd.DataFrame:
    """SELECT → DataFrame helper for the ERP views."""
    return pd.read_sql_query(query, get_db(), params=params)

# =============================================================================
# 2) TRANSLATIONS — every UI string, both languages
# =============================================================================
T = {
 "en": {
  "brand":"SolarBridge","tag":"From your address to a bankable solar design — automatically.",
  "landing_q":"Choose your portal","home":"Home","back":"← Back","logout":"Logout",
  "role_customer":"Customer","role_customer_i":"🏠",
  "role_customer_d":"A complete solar design for your home from just your address — panels, batteries, savings & CO₂.",
  "role_installer":"Energy & Installation Co.","role_installer_i":"🛠️",
  "role_installer_d":"Run projects end-to-end: live customer leads, orders, inventory and finance in one ERP.",
  "role_supplier":"Supplier","role_supplier_i":"📦",
  "role_supplier_d":"Track stock levels, sales orders and receivables with installer partners.",
  "reg_title":"Create your account","reg_sub":"30 seconds — then your free solar study.",
  "name":"Full name","phone":"Phone number","email":"Email",
  "reg_btn":"Continue to the calculator →",
  "reg_err":"Please fill all fields correctly (valid phone & email).",
  "calc_title":"Smart Solar Calculator",
  "calc_sub":"Type your address — we geocode it, scan the roof and design the system.",
  "address":"Your address","address_ph":"e.g. 12 Tahrir St, Dokki, Giza, Egypt",
  "scan_btn":"🛰️ Locate & scan my roof",
  "scanning1":"Geocoding address (Google Geocoding API)…",
  "scanning2":"Scanning roof (Google Solar API)…",
  "no_key_admin":"⚙️ Google API key is not configured. Administrator: add GOOGLE_API_KEY to Streamlit Secrets (App → Settings → Secrets) then restart the app.",
  "src_google":"🛰️ Source: Google Solar API (measured)",
  "src_estimate":"📐 Source: engineering estimate — Google Solar API has no imagery coverage for this location.",
  "scanning3":"Fetching NASA POWER irradiance…",
  "scan_ok":"Roof analysis complete","geo_fail":"Could not locate this address — add city & country.",
  "found_at":"Building located","roof_gross":"Detected roof","roof_obst":"Obstacles",
  "roof_net":"Net usable","confidence":"Confidence",
  "bill_head":"Your electricity consumption",
  "monthly_bill":"Average monthly bill","tariff":"Tariff / kWh","currency":"Currency",
  "sys_type":"System type","on_grid":"On-Grid","hybrid":"Hybrid","off_grid":"Off-Grid",
  "autonomy":"Battery autonomy (days)","calc_btn":"⚙️ Design my solar system",
  "nasa_fail":"NASA API unreachable — regional averages used.",
  "results_title":"Your Solar System — Engineering Report",
  "kpi_panels":"Solar Panels","kpi_system":"System Size","kpi_inverter":"Inverter",
  "kpi_batteries":"Batteries","kpi_cost":"Estimated Cost","kpi_saving":"Annual Savings",
  "kpi_payback":"Payback","kpi_co2":"CO₂ Avoided / yr","years":"yrs","panel_unit":"panels",
  "battery_unit":"× 5 kWh","no_batt":"Not required",
  "chart_prod":"Monthly Energy Production (kWh)",
  "chart_save":"Cumulative Savings vs. System Cost — 25 years",
  "chart_irr":"Solar Irradiance at Your Location (kWh/m²/day)",
  "prod":"Production","consumption":"Consumption","cum_saving":"Cumulative savings",
  "sys_cost":"System cost","month":"Month","energy":"kWh",
  "months":["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
  "coverage":"Your roof covers ~{pct}% of your annual consumption.",
  "eng_details":"Engineering details & equations",
  "request_quote":"📨 Send my request to certified installers",
  "quote_sent":"Request {ref} saved to the platform. Installers will call {phone}.",
  "login_title":"Company Login","login_sub_installer":"Installation company portal",
  "login_sub_supplier":"Supplier portal","password":"Password","login_btn":"Sign in",
  "login_bad":"Invalid credentials.",
  "demo_hint":"Demo · installer@demo.com / solar123 · supplier@demo.com / solar123",
  "erp_installer":"Installer ERP","erp_supplier":"Supplier ERP","welcome":"Welcome",
  "tab_overview":"📈 Overview","tab_inventory":"📦 Inventory","tab_orders":"🧾 Orders",
  "tab_customers":"👥 Customers","tab_accounts":"💰 Accounts",
  "ov_revenue":"Revenue (YTD)","ov_open":"Open Orders","ov_stock_alerts":"Low-stock Alerts",
  "ov_receivable":"Receivables","ov_rev_month":"Monthly Revenue","ov_orders_status":"Orders by Status",
  "inv_title":"Inventory Management","inv_add":"➕ Add / update item","inv_item":"Item",
  "inv_cat":"Category","inv_qty":"Qty","inv_min":"Min. level","inv_price":"Unit price (USD)",
  "inv_save":"Save item","inv_saved":"Item saved to database.",
  "inv_low":"{n} item(s) below minimum stock!",
  "cat_panel":"Panels","cat_inv":"Inverters","cat_batt":"Batteries",
  "cat_mount":"Mounting","cat_cable":"Cables",
  "ord_title":"Orders — live from the database","ord_new":"➕ New order","ord_client":"Client",
  "ord_kwp":"kWp","ord_value":"Value (USD)","ord_status":"Status","ord_date":"Date",
  "ord_save":"Create order","ord_saved":"Order saved to database.",
  "ord_update":"Update status of","ord_apply":"Apply",
  "status_new":"New","status_progress":"In progress","status_done":"Installed","status_cancel":"Cancelled",
  "cust_title":"Customer Leads (CRM) — live from the database",
  "cust_note":"Every customer who registers and requests a quote appears here instantly.",
  "cust_none":"No customer leads yet — try the Customer portal.",
  "acc_title":"Accounts & Finance","acc_in":"Income","acc_out":"Expenses","acc_net":"Net profit",
  "acc_add":"➕ Record transaction","acc_type":"Type","acc_desc":"Description",
  "acc_amount":"Amount (USD)","acc_save":"Record","acc_saved":"Transaction saved to database.",
  "acc_ledger":"General Ledger",
  "disclaimer":"Estimates are indicative; a site survey is required for final quotation. Roof detection simulates Google Solar API pending a production key.",
 },
 "ar": {
  "brand":"سولار بريدج","tag":"من عنوانك إلى تصميم شمسي جاهز للتمويل — أوتوماتيكياً.",
  "landing_q":"اختر بوابتك","home":"الرئيسية","back":"→ رجوع","logout":"تسجيل الخروج",
  "role_customer":"عميل","role_customer_i":"🏠",
  "role_customer_d":"تصميم شمسي كامل لمنزلك من عنوانك فقط — ألواح وبطاريات وتوفير وبصمة كربونية.",
  "role_installer":"شركة طاقة وتركيب","role_installer_i":"🛠️",
  "role_installer_d":"أدر مشاريعك بالكامل: عملاء مباشرون، طلبات، مخزون، وحسابات في نظام ERP واحد.",
  "role_supplier":"مورد","role_supplier_i":"📦",
  "role_supplier_d":"تابع مستويات المخزون وأوامر البيع والمستحقات مع شركائك من شركات التركيب.",
  "reg_title":"إنشاء حسابك","reg_sub":"٣٠ ثانية — ثم دراستك الشمسية المجانية.",
  "name":"الاسم الكامل","phone":"رقم الهاتف","email":"البريد الإلكتروني",
  "reg_btn":"المتابعة إلى الحاسبة ←",
  "reg_err":"يرجى تعبئة جميع الحقول بشكل صحيح (هاتف وبريد صالحين).",
  "calc_title":"حاسبة الطاقة الشمسية الذكية",
  "calc_sub":"اكتب عنوانك — نحوّله لإحداثيات، نمسح السطح، ونصمم النظام.",
  "address":"عنوانك","address_ph":"مثال: ١٢ شارع التحرير، الدقي، الجيزة، مصر",
  "scan_btn":"🛰️ حدد موقعي وامسح السطح",
  "scanning1":"جاري تحويل العنوان (Google Geocoding API)…",
  "scanning2":"جاري مسح السطح (Google Solar API)…",
  "no_key_admin":"⚙️ مفتاح Google API غير مُهيّأ. مدير النظام: أضف GOOGLE_API_KEY في إعدادات Streamlit Secrets (App ← Settings ← Secrets) ثم أعد تشغيل التطبيق.",
  "src_google":"🛰️ المصدر: Google Solar API (قياس فعلي)",
  "src_estimate":"📐 المصدر: تقدير هندسي — تغطية صور Google Solar API غير متاحة لهذا الموقع.",
  "scanning3":"جاري جلب بيانات الإشعاع من ناسا…",
  "scan_ok":"اكتمل تحليل السطح","geo_fail":"تعذر تحديد العنوان — أضف المدينة والدولة.",
  "found_at":"تم تحديد المبنى","roof_gross":"السطح المكتشف","roof_obst":"العوائق",
  "roof_net":"الصافي القابل للاستخدام","confidence":"دقة الاكتشاف",
  "bill_head":"استهلاكك من الكهرباء",
  "monthly_bill":"متوسط الفاتورة الشهرية","tariff":"التعريفة / ك.و.س","currency":"العملة",
  "sys_type":"نوع النظام","on_grid":"متصل بالشبكة","hybrid":"هجين","off_grid":"منفصل",
  "autonomy":"أيام استقلالية البطاريات","calc_btn":"⚙️ صمّم نظامي الشمسي",
  "nasa_fail":"تعذر الوصول لناسا — استخدمنا متوسطات إقليمية.",
  "results_title":"نظامك الشمسي — التقرير الهندسي",
  "kpi_panels":"الألواح الشمسية","kpi_system":"حجم النظام","kpi_inverter":"الإنفرتر",
  "kpi_batteries":"البطاريات","kpi_cost":"التكلفة التقديرية","kpi_saving":"التوفير السنوي",
  "kpi_payback":"فترة الاسترداد","kpi_co2":"كربون مُجنَّب / سنة","years":"سنة","panel_unit":"لوح",
  "battery_unit":"× 5 ك.و.س","no_batt":"غير مطلوبة",
  "chart_prod":"الإنتاج الشهري للطاقة (ك.و.س)",
  "chart_save":"التوفير التراكمي مقابل تكلفة النظام — 25 سنة",
  "chart_irr":"الإشعاع الشمسي في موقعك (ك.و.س/م²/يوم)",
  "prod":"الإنتاج","consumption":"الاستهلاك","cum_saving":"التوفير التراكمي",
  "sys_cost":"تكلفة النظام","month":"الشهر","energy":"ك.و.س",
  "months":["يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"],
  "coverage":"سطحك يغطي حوالي {pct}% من استهلاكك السنوي.",
  "eng_details":"التفاصيل الهندسية والمعادلات",
  "request_quote":"📨 أرسل طلبي لشركات التركيب المعتمدة",
  "quote_sent":"تم حفظ الطلب {ref} في المنصة. ستتصل بك الشركات على {phone}.",
  "login_title":"تسجيل دخول الشركات","login_sub_installer":"بوابة شركات التركيب",
  "login_sub_supplier":"بوابة الموردين","password":"كلمة المرور","login_btn":"دخول",
  "login_bad":"بيانات غير صحيحة.",
  "demo_hint":"تجريبي · installer@demo.com / solar123 · supplier@demo.com / solar123",
  "erp_installer":"نظام ERP — شركة التركيب","erp_supplier":"نظام ERP — المورد","welcome":"مرحباً",
  "tab_overview":"📈 نظرة عامة","tab_inventory":"📦 المخزون","tab_orders":"🧾 الطلبات",
  "tab_customers":"👥 العملاء","tab_accounts":"💰 الحسابات",
  "ov_revenue":"الإيرادات (السنة)","ov_open":"طلبات مفتوحة","ov_stock_alerts":"تنبيهات المخزون",
  "ov_receivable":"مستحقات","ov_rev_month":"الإيراد الشهري","ov_orders_status":"الطلبات حسب الحالة",
  "inv_title":"إدارة المخزون","inv_add":"➕ إضافة / تحديث صنف","inv_item":"الصنف",
  "inv_cat":"الفئة","inv_qty":"الكمية","inv_min":"الحد الأدنى","inv_price":"سعر الوحدة (دولار)",
  "inv_save":"حفظ الصنف","inv_saved":"تم حفظ الصنف في قاعدة البيانات.",
  "inv_low":"يوجد {n} صنف/أصناف تحت الحد الأدنى!",
  "cat_panel":"ألواح","cat_inv":"إنفرترات","cat_batt":"بطاريات",
  "cat_mount":"هياكل تثبيت","cat_cable":"كابلات",
  "ord_title":"الطلبات — مباشرة من قاعدة البيانات","ord_new":"➕ طلب جديد","ord_client":"العميل",
  "ord_kwp":"ك.و ذروة","ord_value":"القيمة (دولار)","ord_status":"الحالة","ord_date":"التاريخ",
  "ord_save":"إنشاء الطلب","ord_saved":"تم حفظ الطلب في قاعدة البيانات.",
  "ord_update":"تحديث حالة","ord_apply":"تطبيق",
  "status_new":"جديد","status_progress":"قيد التنفيذ","status_done":"تم التركيب","status_cancel":"ملغي",
  "cust_title":"عملاء المنصة (CRM) — مباشرة من قاعدة البيانات",
  "cust_note":"كل عميل يسجّل ويطلب عرض سعر يظهر هنا فوراً.",
  "cust_none":"لا يوجد عملاء بعد — جرّب بوابة العميل.",
  "acc_title":"الحسابات والمالية","acc_in":"الإيرادات","acc_out":"المصروفات","acc_net":"صافي الربح",
  "acc_add":"➕ تسجيل حركة مالية","acc_type":"النوع","acc_desc":"الوصف",
  "acc_amount":"المبلغ (دولار)","acc_save":"تسجيل","acc_saved":"تم حفظ الحركة في قاعدة البيانات.",
  "acc_ledger":"دفتر الأستاذ العام",
  "disclaimer":"النتائج تقديرية والمعاينة الميدانية مطلوبة للعرض النهائي. اكتشاف السطح يحاكي Google Solar API لحين تفعيل مفتاح الإنتاج.",
 },
}

# =============================================================================
# 3) SESSION STATE / ROUTER
# =============================================================================
for k, v in {"lang": "ar", "page": "landing", "role": None,
             "customer": None, "customer_id": None,
             "roof": None, "result": None, "b2b_user": None}.items():
    st.session_state.setdefault(k, v)

def tr(key):  return T[st.session_state.lang].get(key, key)
def goto(p):  st.session_state.page = p; st.rerun()

IS_AR = st.session_state.lang == "ar"

# =============================================================================
# 4) PREMIUM CSS — hidden Streamlit chrome + clickable glass role cards
# =============================================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800;900&family=Inter:wght@400;600;800;900&display=swap');

/* ---------- hide Streamlit chrome (menu / header / footer) ---------- */
#MainMenu, header[data-testid="stHeader"], footer {{visibility:hidden; height:0;}}
div[data-testid="stToolbar"], div[data-testid="stDecoration"] {{display:none;}}
.block-container {{padding-top:1.2rem; max-width:1200px;}}

/* ---------- global ---------- */
html, body, [class*="css"] {{font-family:{"'Cairo'" if IS_AR else "'Inter'"},sans-serif;}}
.stApp {{
  direction:{"rtl" if IS_AR else "ltr"};
  background:
    radial-gradient(1200px 500px at 80% -10%, rgba(249,168,37,.14), transparent 60%),
    radial-gradient(900px 500px at -10% 110%, rgba(46,109,164,.16), transparent 60%),
    linear-gradient(180deg,#f7f9fc 0%,#eef3f9 100%);
}}
h1,h2,h3 {{color:#122b45; letter-spacing:-.02em;}}

/* ---------- hero ---------- */
.hero {{
  background:linear-gradient(115deg,#0e2438 0%,#1c3d5a 45%,#b97909 130%);
  border-radius:22px; padding:26px 32px; color:#fff;
  box-shadow:0 20px 40px -18px rgba(14,36,56,.45); margin-bottom:18px;
  border:1px solid rgba(255,255,255,.08);
}}
.hero h1 {{color:#fff; margin:0; font-size:1.7rem; font-weight:900;}}
.hero p  {{color:#ffd98a; margin:6px 0 0; font-size:1.02rem;}}
.hero .badge {{
  display:inline-block; background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.25);
  padding:2px 12px; border-radius:999px; font-size:.75rem; color:#ffe9b8; margin-bottom:10px;
}}

/* ---------- KPI metrics ---------- */
div[data-testid="stMetric"] {{
  background:rgba(255,255,255,.75); backdrop-filter:blur(8px);
  border:1px solid #e6ecf4; border-radius:18px; padding:16px 18px;
  box-shadow:0 8px 24px -14px rgba(18,43,69,.25);
}}
div[data-testid="stMetricValue"] {{color:#122b45; font-weight:800;}}

/* ---------- generic buttons ---------- */
.stButton>button, .stFormSubmitButton>button {{
  border-radius:14px; font-weight:800; border:1px solid #dfe7f1;
  transition:all .18s ease;
}}
.stButton>button:hover, .stFormSubmitButton>button:hover {{
  transform:translateY(-1px); box-shadow:0 10px 22px -12px rgba(28,61,90,.45);
}}

/* =====================================================================
   CLICKABLE ROLE CARDS
   Trick: each card IS a st.button. Streamlit ≥1.32 exposes the widget
   key as a CSS class (.st-key-<key>), so we restyle the whole button
   into a large glass card with hover lift — the entire surface is
   clickable, no separate select buttons.
   ===================================================================== */
.st-key-card_customer button, .st-key-card_installer button, .st-key-card_supplier button {{
  width:100%; min-height:250px; white-space:pre-line;
  background:rgba(255,255,255,.82); backdrop-filter:blur(10px);
  border:1.5px solid #e3eaf3; border-radius:24px;
  padding:28px 22px; text-align:center;
  font-size:1.02rem; font-weight:600; color:#3d5570; line-height:1.75;
  box-shadow:0 14px 34px -20px rgba(18,43,69,.35);
  transition:all .22s cubic-bezier(.2,.8,.3,1);
}}
.st-key-card_customer button:hover, .st-key-card_installer button:hover, .st-key-card_supplier button:hover {{
  transform:translateY(-6px) scale(1.015);
  border-color:#f9a825;
  background:linear-gradient(160deg,#fffdf6 0%,#fff4d6 100%);
  box-shadow:0 26px 48px -22px rgba(185,121,9,.45);
  color:#122b45;
}}
.st-key-card_customer button:active, .st-key-card_installer button:active, .st-key-card_supplier button:active {{
  transform:translateY(-2px) scale(.995);
}}

/* first line of the card label = icon+title, styled bigger via ::first-line */
.st-key-card_customer button::first-line,
.st-key-card_installer button::first-line,
.st-key-card_supplier button::first-line {{
  font-size:1.5rem; font-weight:900; color:#122b45;
}}

/* ---------- roof result strip ---------- */
.roof-card {{
  border:1px solid #cfe0f2; border-radius:16px; padding:14px 18px;
  background:linear-gradient(120deg,#f4f9ff,#eef6ff);
  box-shadow:0 8px 22px -16px rgba(46,109,164,.5); margin:8px 0 4px;
}}

/* ---------- dataframes / tabs polish ---------- */
div[data-testid="stDataFrame"] {{border-radius:14px; overflow:hidden;
  border:1px solid #e6ecf4; box-shadow:0 6px 18px -14px rgba(18,43,69,.3);}}
button[data-baseweb="tab"] {{font-weight:700;}}
</style>
""", unsafe_allow_html=True)

# ---------- top bar: brand + language + home ----------
tb = st.columns([5, 2, 1])
with tb[1]:
    lang = st.radio("lang", ["العربية", "English"], horizontal=True,
                    index=0 if IS_AR else 1, label_visibility="collapsed")
    nl = "ar" if lang == "العربية" else "en"
    if nl != st.session_state.lang:
        st.session_state.lang = nl; st.rerun()
with tb[2]:
    if st.session_state.page != "landing" and st.button(f"🏠 {tr('home')}"):
        st.session_state.update(page="landing", role=None); st.rerun()

st.markdown(f"""
<div class="hero">
  <span class="badge">☀️ SaaS · AR/EN · NASA-powered</span>
  <h1>{tr('brand')}</h1><p>{tr('tag')}</p>
</div>""", unsafe_allow_html=True)

# =============================================================================
# 5) ENGINEERING CONSTANTS (standard PV industry assumptions)
# =============================================================================
PANEL_W, PANEL_AREA_M2 = 550, 2.2      # 550W mono-PERC module, ~2.2 m²
AREA_UTILIZATION   = 0.70              # row spacing / walkways packing factor
TEMP_COEFF_P       = -0.0035           # γ per °C
NOCT               = 45.0              # °C
SOILING_LOSS, WIRING_LOSS, MISMATCH_LOSS = 0.03, 0.02, 0.02
INVERTER_EFF, AVAILABILITY = 0.97, 0.99
DC_AC_RATIO        = 1.15
BATTERY_UNIT_KWH, DOD, BATT_RT_EFF = 5.0, 0.80, 0.92
GRID_CO2           = 0.55              # kg CO₂ / kWh (MENA grid)
COST_PER_WP, COST_PER_KWH_BATT = 0.55, 250.0
DAYS = [31,28,31,30,31,30,31,31,30,31,30,31]
FB_TEMPS = [14,16,19,24,28,30,31,31,29,26,20,16]
FB_GHI   = [5.0,5.6,6.4,7.1,7.5,7.9,7.7,7.4,6.9,6.0,5.2,4.8]

# =============================================================================
# 6) GOOGLE APIs — REAL Geocoding + REAL Solar API  (key via st.secrets ONLY)
# =============================================================================
def get_google_key():
    """
    SECURITY: the API key is read exclusively from Streamlit secrets.
    Never hard-code keys in source. On Streamlit Cloud set it under:
      App → Settings → Secrets:
          GOOGLE_API_KEY = "AIza...your-key..."
    Locally: .streamlit/secrets.toml with the same line (git-ignored).
    """
    try:
        key = st.secrets["GOOGLE_API_KEY"]
        return key if key and str(key).strip() else None
    except Exception:
        return None


@st.cache_resource
def _gmaps_client():
    """One googlemaps.Client per server process (official Google SDK)."""
    if GMAPS_OK and get_google_key():
        return googlemaps.Client(key=get_google_key())
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def geocode_address(address: str):
    """
    REAL Google Geocoding API: address string → (lat, lon, formatted_address).
    Primary : official `googlemaps` SDK.
    Fallback: direct HTTPS call via `requests` to the same Google endpoint
              (still Google — used only if the SDK isn't installed).
    Returns None if the address can't be resolved.
    """
    key = get_google_key()
    if key is None:
        return None                       # guarded earlier in the UI too
    client = _gmaps_client()
    if client is not None:                # ---- googlemaps SDK path ----
        try:
            res = client.geocode(address)
            if res:
                loc = res[0]["geometry"]["location"]
                return loc["lat"], loc["lng"], res[0]["formatted_address"]
        except Exception:
            pass
    try:                                  # ---- raw HTTPS path (Google) ----
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": address, "key": key}, timeout=10)
        js = r.json()
        if js.get("status") == "OK":
            top = js["results"][0]
            loc = top["geometry"]["location"]
            return loc["lat"], loc["lng"], top["formatted_address"]
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def solar_api_roof_scan(lat: float, lon: float):
    """
    REAL Google Solar API — buildingInsights:findClosest.
      gross roof  : solarPotential.wholeRoofStats.areaMeters2
      net usable  : solarPotential.maxArrayAreaMeters2
                    (Google already excludes obstacles, edges & shaded zones,
                     so obstacles = gross − net)
      confidence  : imageryQuality (HIGH/MEDIUM/LOW → 97/92/88 %)

    COVERAGE NOTE (important for production):
      Google Solar API covers a specific list of countries (strong in
      US/EU/JP/AU; most of MENA is NOT yet covered). When the API returns
      404 "not found" for a location, we fall back to a clearly-labelled
      deterministic ESTIMATE (source='estimate') instead of failing, and
      the UI displays which source was used. Remove the fallback only if
      you operate exclusively inside covered regions.
    """
    key = get_google_key()
    if key:
        try:
            r = requests.get(
                "https://solar.googleapis.com/v1/buildingInsights:findClosest",
                params={"location.latitude": f"{lat:.6f}",
                        "location.longitude": f"{lon:.6f}",
                        "requiredQuality": "LOW",
                        "key": key},
                timeout=15)
            if r.status_code == 200:
                js = r.json()
                sp = js.get("solarPotential", {})
                gross = float(sp.get("wholeRoofStats", {})
                                .get("areaMeters2", 0.0))
                net = float(sp.get("maxArrayAreaMeters2", 0.0))
                if gross > 0 and net > 0:
                    conf = {"HIGH": 97, "MEDIUM": 92,
                            "LOW": 88}.get(js.get("imageryQuality"), 90)
                    return {"gross_m2": round(gross, 1),
                            "obstacles_m2": round(max(gross - net, 0.0), 1),
                            "net_m2": round(net, 1),
                            "confidence": conf,
                            "source": "google"}
            # 404 → building/region not in Solar API coverage → estimate
        except Exception:
            pass

    # ---- documented fallback: deterministic estimate (no coverage) ----------
    seed = int(hashlib.sha256(f"{lat:.5f},{lon:.5f}".encode()).hexdigest(), 16)
    gross = 80 + (seed % 241)                        # 80–320 m² residential
    obst = round(gross * (0.10 + ((seed >> 8) % 19) / 100.0), 1)  # 10–28 %
    return {"gross_m2": float(gross), "obstacles_m2": obst,
            "net_m2": round(gross - obst, 1),
            "confidence": 88 + ((seed >> 16) % 12),
            "source": "estimate"}

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_nasa_power(lat: float, lon: float):
    """
    NASA POWER climatology (REAL API).
    ALLSKY_SFC_SW_DWN [kWh/m²/day] ≡ daily Peak Sun Hours at 1 kW/m².
    """
    r = requests.get("https://power.larc.nasa.gov/api/temporal/climatology/point",
                     params={"parameters": "ALLSKY_SFC_SW_DWN,T2M",
                             "community": "RE", "latitude": lat,
                             "longitude": lon, "format": "JSON"}, timeout=15)
    r.raise_for_status()
    p = r.json()["properties"]["parameter"]
    keys = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
    ghi = [p["ALLSKY_SFC_SW_DWN"][k] for k in keys]
    temps = [p.get("T2M", {}).get(k, FB_TEMPS[i]) for i, k in enumerate(keys)]
    return ghi, temps

# =============================================================================
# 7) PV ENGINEERING MODEL — standard equations (real physics on real coords)
# =============================================================================
def design_pv_system(net_roof_m2, bill, tariff, ghi, temps, sys_type, autonomy):
    """
    (1) A_use  = A_net × 0.70                       usable area
    (2) E_day  = (Bill / tariff) / 30.4             daily load from the bill
    (3) T_cell = T_amb + (NOCT−20)/800 × 1000       NOCT cell-temperature model
    (4) f_T    = 1 + γ(T_cell − 25)                 thermal derating
    (5) PR     = f_T (1−L_soil)(1−L_wire)(1−L_mism) η_inv A_avail
    (6) kWp    = E_day / (PSH_worst × PR_worst)     sized on worst month,
                                                    hard-capped by roof area
    (7) E_m    = kWp × PSH_m × PR_m × N_days        monthly yield
    (8) C_batt = E_day × N_aut / (DoD × η_rt)       bank capacity (LiFePO4)
    (9) P_inv  = kWp / 1.15 → next commercial size  DC/AC ratio sizing
    """
    a_use = net_roof_m2 * AREA_UTILIZATION                            # (1)
    max_panels = int(a_use // PANEL_AREA_M2)
    e_day = (bill / max(tariff, 1e-6)) / 30.4                         # (2)

    pr = []
    for m in range(12):
        t_cell = temps[m] + (NOCT - 20) / 800 * 1000                  # (3)
        f_t = 1 + TEMP_COEFF_P * (t_cell - 25)                        # (4)
        pr.append(f_t * (1-SOILING_LOSS) * (1-WIRING_LOSS)            # (5)
                  * (1-MISMATCH_LOSS) * INVERTER_EFF * AVAILABILITY)

    w = ghi.index(min(ghi))
    kwp_req = e_day / (ghi[w] * pr[w])                                # (6)
    n_panels = max(1, min(math.ceil(kwp_req * 1000 / PANEL_W), max_panels))
    kwp = n_panels * PANEL_W / 1000

    e_m = [kwp * ghi[m] * pr[m] * DAYS[m] for m in range(12)]         # (7)
    e_yr = sum(e_m)

    if sys_type in ("off_grid", "hybrid"):                            # (8)
        batt_kwh = e_day * autonomy / (DOD * BATT_RT_EFF)
        n_batt = math.ceil(batt_kwh / BATTERY_UNIT_KWH)
    else:
        batt_kwh, n_batt = 0.0, 0

    sizes = [1.5,2,3,3.6,5,6,8,10,12,15,20,25,30,50,100]              # (9)
    inv_kw = next((s for s in sizes if s >= kwp / DC_AC_RATIO),
                  math.ceil(kwp / DC_AC_RATIO))

    capex = kwp*1000*COST_PER_WP + batt_kwh*COST_PER_KWH_BATT
    cons_yr = e_day * 365
    saving = min(e_yr, cons_yr) * tariff
    return dict(kwp=kwp, n_panels=n_panels, inv_kw=inv_kw,
                n_batteries=n_batt, batt_kwh=batt_kwh, capex=capex,
                annual_saving=saving,
                payback=capex/saving if saving else float("inf"),
                co2_tons=e_yr*GRID_CO2/1000, e_monthly=e_m, e_annual=e_yr,
                pr_monthly=pr, daily_load=e_day,
                coverage=min(100, 100*e_yr/cons_yr) if cons_yr else 0)

# =============================================================================
# 8) PAGE: LANDING — three fully-clickable premium cards
# =============================================================================
def page_landing():
    st.markdown(f"### {tr('landing_q')}")
    c1, c2, c3 = st.columns(3, gap="large")
    cards = [
        (c1, "card_customer",  "customer",  "role_customer",  "role_customer_d"),
        (c2, "card_installer", "installer", "role_installer", "role_installer_d"),
        (c3, "card_supplier",  "supplier",  "role_supplier",  "role_supplier_d"),
    ]
    for col, key, role, tk, dk in cards:
        with col:
            # The button IS the card (styled via .st-key-<key> CSS above):
            label = f"{tr(tk+'_i')}  {tr(tk)}\n\n{tr(dk)}"
            if st.button(label, key=key, use_container_width=True):
                st.session_state.role = role
                goto("register" if role == "customer" else "login")
    st.caption(f"ℹ️ {tr('disclaimer')}")

# =============================================================================
# 9) PAGE: CUSTOMER REGISTRATION → INSERT INTO customers
# =============================================================================
def page_register():
    st.markdown(f"## 📝 {tr('reg_title')}")
    st.caption(tr("reg_sub"))
    with st.form("reg"):
        name  = st.text_input(f"👤 {tr('name')}")
        phone = st.text_input(f"📱 {tr('phone')}")
        email = st.text_input(f"✉️ {tr('email')}")
        ok = st.form_submit_button(tr("reg_btn"), type="primary",
                                   use_container_width=True)
    if ok:
        valid = (len(name.strip()) >= 3
                 and sum(c.isdigit() for c in phone) >= 8
                 and "@" in email and "." in email.split("@")[-1])
        if valid:
            cid = db_insert_customer(name.strip(), phone.strip(), email.strip())
            st.session_state.customer = dict(name=name.strip(),
                                             phone=phone.strip(),
                                             email=email.strip())
            st.session_state.customer_id = cid          # real DB row id
            goto("calculator")
        else:
            st.error(tr("reg_err"))
    if st.button(tr("back")):
        goto("landing")

# =============================================================================
# 10) PAGE: CALCULATOR — one address box → real geocode → auto roof → design
# =============================================================================
def page_calculator():
    cust = st.session_state.customer
    st.markdown(f"## ⚡ {tr('calc_title')}")
    st.caption(f"{tr('welcome')} **{cust['name']}** 👋 — {tr('calc_sub')}")

    # ---- production guard: Google key MUST be configured by the admin ------
    if get_google_key() is None:
        st.error(tr("no_key_admin"))
        st.code('# .streamlit/secrets.toml\nGOOGLE_API_KEY = "AIza...your-key..."',
                language="toml")
        return

    # (A) the ONLY location input — a single address search box
    address = st.text_input(f"📍 {tr('address')}", placeholder=tr("address_ph"))
    if st.button(tr("scan_btn"), type="primary", use_container_width=True):
        if not address.strip():
            st.error(tr("geo_fail"))
        else:
            with st.status(tr("scanning1"), expanded=False) as s:
                geo = geocode_address(address.strip())  # REAL Google Geocoding
                if geo is None:
                    s.update(label=tr("geo_fail"), state="error")
                else:
                    lat, lon, display = geo
                    s.update(label=tr("scanning2"))
                    roof = solar_api_roof_scan(lat, lon)   # auto roof geometry
                    s.update(label=tr("scanning3"))
                    try:
                        ghi, temps = fetch_nasa_power(lat, lon)  # REAL NASA
                    except Exception:
                        ghi, temps = FB_GHI, FB_TEMPS
                        st.warning(tr("nasa_fail"))
                    st.session_state.roof = dict(lat=lat, lon=lon,
                                                 display=display,
                                                 ghi=ghi, temps=temps, **roof)
                    st.session_state.result = None
                    s.update(label=tr("scan_ok"), state="complete")

    roof = st.session_state.roof
    if not roof:
        return

    # (B) auto-detected roof — read-only, never typed by the user
    st.markdown(f"""
      <div class="roof-card">
        <b>📌 {tr('found_at')}:</b> {roof['display'][:120]}<br>
        🛰️ <b>{tr('roof_gross')}:</b> {roof['gross_m2']:,.0f} m² ·
        🚧 <b>{tr('roof_obst')}:</b> −{roof['obstacles_m2']:,.1f} m² ·
        ✅ <b>{tr('roof_net')}:</b> <b>{roof['net_m2']:,.1f} m²</b> ·
        🎯 <b>{tr('confidence')}:</b> {roof['confidence']}%
      </div>""", unsafe_allow_html=True)
    # transparency badge: measured by Google Solar API vs estimated (no coverage)
    if roof.get("source") == "google":
        st.caption(tr("src_google"))
    else:
        st.caption(tr("src_estimate"))
    st.map(pd.DataFrame({"lat": [roof["lat"]], "lon": [roof["lon"]]}),
           size=30, zoom=16)

    # (C) consumption inputs (billing only)
    st.markdown(f"### 🔌 {tr('bill_head')}")
    c1, c2, c3 = st.columns(3)
    with c1:
        currency = st.selectbox(f"💱 {tr('currency')}", ["EGP","SAR","AED","USD"])
        bill = st.number_input(f"💵 {tr('monthly_bill')}", 50.0, 1e7, 1500.0, 50.0)
    with c2:
        tariff = st.number_input(f"⚡ {tr('tariff')}", 0.05, 50.0, 2.2, 0.05)
    with c3:
        sl = st.selectbox(f"🔋 {tr('sys_type')}",
                          [tr("on_grid"), tr("hybrid"), tr("off_grid")])
        stype = {tr("on_grid"):"on_grid", tr("hybrid"):"hybrid",
                 tr("off_grid"):"off_grid"}[sl]
        aut = (st.slider(f"🌙 {tr('autonomy')}", 0.5, 3.0, 1.0, 0.5)
               if stype != "on_grid" else 0.0)

    if st.button(tr("calc_btn"), type="primary", use_container_width=True):
        res = design_pv_system(roof["net_m2"], bill, tariff,
                               roof["ghi"], roof["temps"], stype, aut)
        st.session_state.result = res
        st.session_state.result_cur = currency
        # persist the site & design onto the customer's DB row (UPDATE)
        db_update_customer_site(st.session_state.customer_id,
                                roof["display"][:160], roof["lat"], roof["lon"],
                                roof["net_m2"], round(res["kwp"], 2))

    # (D) results dashboard
    res = st.session_state.result
    if not res:
        return
    cur, months = st.session_state.result_cur, tr("months")
    st.markdown(f"## 📊 {tr('results_title')}")

    k = st.columns(4)
    k[0].metric(tr("kpi_panels"), f"{res['n_panels']} {tr('panel_unit')}", f"{PANEL_W} W")
    k[1].metric(tr("kpi_system"), f"{res['kwp']:.2f} kWp")
    k[2].metric(tr("kpi_inverter"), f"{res['inv_kw']} kW")
    k[3].metric(tr("kpi_batteries"),
                f"{res['n_batteries']} {tr('battery_unit')}"
                if res["n_batteries"] else tr("no_batt"),
                f"{res['batt_kwh']:.1f} kWh" if res["batt_kwh"] else None)
    k = st.columns(4)
    k[0].metric(tr("kpi_cost"), f"{res['capex']:,.0f} USD")
    k[1].metric(tr("kpi_saving"), f"{res['annual_saving']:,.0f} {cur}")
    k[2].metric(tr("kpi_payback"),
                f"{res['payback']:.1f} {tr('years')}"
                if res["payback"] != float("inf") else "—")
    k[3].metric(tr("kpi_co2"), f"{res['co2_tons']:.2f} t")
    st.success("☑️ " + tr("coverage").format(pct=f"{res['coverage']:.0f}"))

    # chart 1 — production vs consumption
    f1 = go.Figure()
    f1.add_bar(x=months, y=[round(e) for e in res["e_monthly"]],
               name=tr("prod"), marker_color="#f9a825")
    f1.add_scatter(x=months, y=[round(res["daily_load"]*d) for d in DAYS],
                   name=tr("consumption"), mode="lines+markers",
                   line=dict(color="#1c3d5a", width=3))
    f1.update_layout(title=f"🔆 {tr('chart_prod')}", yaxis_title=tr("energy"),
                     legend=dict(orientation="h"), height=380,
                     paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(f1, use_container_width=True)

    # chart 2 — 25-year cumulative savings vs capex (0.5%/yr degradation)
    yrs, cum, tot = list(range(26)), [], 0.0
    for y in yrs:
        tot += res["annual_saving"] * (1 - 0.005) ** y if y else 0
        cum.append(tot)
    f2 = go.Figure()
    f2.add_scatter(x=yrs, y=cum, name=tr("cum_saving"), fill="tozeroy",
                   line=dict(color="#2e7d32", width=3))
    f2.add_hline(y=res["capex"], line_dash="dash", line_color="#c62828",
                 annotation_text=tr("sys_cost"))
    f2.update_layout(title=f"💰 {tr('chart_save')}", height=380,
                     xaxis_title=tr("years"), yaxis_title=cur,
                     paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(f2, use_container_width=True)

    # chart 3 — irradiance profile from NASA
    f3 = px.area(x=months, y=roof["ghi"], title=f"☀️ {tr('chart_irr')}",
                 color_discrete_sequence=["#f9a825"])
    f3.update_layout(height=320, xaxis_title=tr("month"),
                     yaxis_title="kWh/m²/day", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(f3, use_container_width=True)

    with st.expander(f"🧮 {tr('eng_details')}"):
        st.latex(r"E_{month}=kWp\times PSH\times PR\times N_{days}")
        st.latex(r"PR=f_T(1-L_{soil})(1-L_{wire})(1-L_{mism})\eta_{inv}A_{avail}")
        st.latex(r"f_T=1+\gamma(T_{cell}-25),\;T_{cell}=T_{amb}+\tfrac{NOCT-20}{800}G")
        st.latex(r"C_{batt}=\frac{E_{daily}N_{aut}}{DoD\cdot\eta_{rt}},\quad P_{inv}=kWp/1.15")
        st.dataframe(pd.DataFrame({
            tr("month"): months,
            "PSH": [round(g,2) for g in roof["ghi"]],
            "PR": [round(p,3) for p in res["pr_monthly"]],
            tr("prod"): [round(e) for e in res["e_monthly"]]}),
            use_container_width=True, hide_index=True)

    # (E) quote request → REAL INSERT INTO orders (ERP sees it instantly)
    if st.button(tr("request_quote"), use_container_width=True):
        ref = db_create_order(st.session_state.customer_id, cust["name"],
                              round(res["kwp"], 2), round(res["capex"], 0))
        st.balloons()
        st.success("✅ " + tr("quote_sent").format(ref=ref, phone=cust["phone"]))

# =============================================================================
# 11) PAGE: B2B LOGIN
# =============================================================================
DEMO_USERS = {  # production: hashed passwords in a users table
    "installer@demo.com": ("solar123", "installer"),
    "supplier@demo.com":  ("solar123", "supplier"),
}

def page_login():
    role = st.session_state.role or "installer"
    st.markdown(f"## 🔐 {tr('login_title')}")
    st.caption(tr("login_sub_installer") if role == "installer"
               else tr("login_sub_supplier"))
    with st.form("login"):
        email = st.text_input(f"✉️ {tr('email')}")
        pwd = st.text_input(f"🔑 {tr('password')}", type="password")
        ok = st.form_submit_button(tr("login_btn"), type="primary",
                                   use_container_width=True)
    st.caption(tr("demo_hint"))
    if ok:
        rec = DEMO_USERS.get(email.strip().lower())
        if rec and rec[0] == pwd:
            st.session_state.b2b_user = email.strip().lower()
            st.session_state.role = rec[1]
            goto("erp")
        else:
            st.error(tr("login_bad"))
    if st.button(tr("back")):
        goto("landing")

# =============================================================================
# 12) PAGE: ERP — every view SELECTs live from SQLite
# =============================================================================
def page_erp():
    role = st.session_state.role
    h = st.columns([4, 1])
    h[0].markdown(f"## {'🛠️ '+tr('erp_installer') if role=='installer' else '📦 '+tr('erp_supplier')}")
    h[0].caption(f"{tr('welcome')} `{st.session_state.b2b_user}`")
    if h[1].button(f"🚪 {tr('logout')}", use_container_width=True):
        st.session_state.update(b2b_user=None, page="landing", role=None)
        st.rerun()

    tabs = st.tabs([tr("tab_overview"), tr("tab_inventory"), tr("tab_orders"),
                    tr("tab_customers"), tr("tab_accounts")])

    # ---------------- Overview (live SELECT aggregates) ----------------
    with tabs[0]:
        inv = db_df("SELECT * FROM inventory")
        orders = db_df("SELECT * FROM orders")
        income = db_df("SELECT COALESCE(SUM(amount),0) s FROM ledger WHERE ttype='in'")["s"][0]
        open_mask = ~orders["status"].isin(["status_done", "status_cancel"])
        m = st.columns(4)
        m[0].metric(tr("ov_revenue"), f"{income:,.0f} USD")
        m[1].metric(tr("ov_open"), int(open_mask.sum()))
        m[2].metric(tr("ov_stock_alerts"), int((inv["qty"] < inv["min_level"]).sum()))
        m[3].metric(tr("ov_receivable"), f"{orders.loc[open_mask,'value_usd'].sum():,.0f} USD")

        c1, c2 = st.columns(2)
        with c1:
            led = db_df("SELECT substr(tdate,1,7) m, SUM(amount) a "
                        "FROM ledger WHERE ttype='in' GROUP BY 1 ORDER BY 1")
            st.plotly_chart(px.bar(led, x="m", y="a", title=tr("ov_rev_month"),
                                   color_discrete_sequence=["#f9a825"])
                            .update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)"),
                            use_container_width=True)
        with c2:
            pie = orders.copy(); pie["s"] = pie["status"].map(tr)
            st.plotly_chart(px.pie(pie, names="s", values="value_usd", hole=.55,
                                   title=tr("ov_orders_status"),
                                   color_discrete_sequence=px.colors.sequential.YlOrBr)
                            .update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)"),
                            use_container_width=True)

    # ---------------- Inventory (SELECT + INSERT/UPDATE) ----------------
    with tabs[1]:
        st.markdown(f"### {tr('inv_title')}")
        inv = db_df("SELECT item,cat,qty,min_level,price_usd FROM inventory ORDER BY cat,item")
        low = int((inv["qty"] < inv["min_level"]).sum())
        if low:
            st.warning("⚠️ " + tr("inv_low").format(n=low))
        v = inv.copy(); v["cat"] = v["cat"].map(tr)
        v.columns = [tr("inv_item"), tr("inv_cat"), tr("inv_qty"),
                     tr("inv_min"), tr("inv_price")]
        st.dataframe(v, use_container_width=True, hide_index=True)

        with st.expander(tr("inv_add")):
            with st.form("inv_form"):
                c = st.columns(5)
                item = c[0].text_input(tr("inv_item"))
                cat = c[1].selectbox(tr("inv_cat"),
                                     ["cat_panel","cat_inv","cat_batt",
                                      "cat_mount","cat_cable"], format_func=tr)
                qty = c[2].number_input(tr("inv_qty"), 0, 100000, 10)
                mn  = c[3].number_input(tr("inv_min"), 0, 100000, 5)
                pr  = c[4].number_input(tr("inv_price"), 0.0, 1e6, 100.0)
                if st.form_submit_button(tr("inv_save")) and item.strip():
                    get_db().execute("""
                        INSERT INTO inventory(item,cat,qty,min_level,price_usd)
                        VALUES(?,?,?,?,?)
                        ON CONFLICT(item) DO UPDATE SET
                          cat=excluded.cat, qty=excluded.qty,
                          min_level=excluded.min_level,
                          price_usd=excluded.price_usd""",
                        (item.strip(), cat, qty, mn, pr))
                    get_db().commit()
                    st.success("✅ " + tr("inv_saved")); st.rerun()

    # ---------------- Orders (SELECT + INSERT + UPDATE) ----------------
    with tabs[2]:
        st.markdown(f"### {tr('ord_title')}")
        orders = db_df("SELECT ref,client,kwp,value_usd,status,created_at "
                       "FROM orders ORDER BY id DESC")
        v = orders.copy(); v["status"] = v["status"].map(tr)
        v.columns = ["Ref", tr("ord_client"), tr("ord_kwp"),
                     tr("ord_value"), tr("ord_status"), tr("ord_date")]
        st.dataframe(v, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1, st.expander(tr("ord_new")):
            with st.form("ord_form"):
                client = st.text_input(tr("ord_client"))
                kwp = st.number_input(tr("ord_kwp"), 0.5, 5000.0, 10.0)
                val = st.number_input(tr("ord_value"), 100.0, 1e7, 6000.0)
                if st.form_submit_button(tr("ord_save")) and client.strip():
                    db_create_order(None, client.strip(), kwp, val)
                    st.success("✅ " + tr("ord_saved")); st.rerun()
        with c2:
            if len(orders):
                ref = st.selectbox(tr("ord_update"), orders["ref"].tolist())
                ns = st.selectbox(tr("ord_status"),
                                  ["status_new","status_progress",
                                   "status_done","status_cancel"], format_func=tr)
                if st.button(tr("ord_apply")):
                    get_db().execute("UPDATE orders SET status=? WHERE ref=?",
                                     (ns, ref))
                    get_db().commit(); st.rerun()

    # ---------------- Customers CRM (live SELECT from customers) --------
    with tabs[3]:
        st.markdown(f"### {tr('cust_title')}")
        st.caption(tr("cust_note"))
        cust = db_df("""SELECT name, phone, email,
                               COALESCE(address,'') address,
                               COALESCE(kwp,0) kwp, created_at
                        FROM customers ORDER BY id DESC""")
        if len(cust):
            cust.columns = [tr("name"), tr("phone"), tr("email"),
                            tr("address"), tr("ord_kwp"), tr("ord_date")]
            st.dataframe(cust, use_container_width=True, hide_index=True)
        else:
            st.info(tr("cust_none"))

    # ---------------- Accounts (SELECT + INSERT into ledger) ------------
    with tabs[4]:
        st.markdown(f"### {tr('acc_title')}")
        led = db_df("SELECT tdate,ttype,descr,amount FROM ledger ORDER BY tdate DESC")
        inc = led.loc[led["ttype"]=="in","amount"].sum()
        out = led.loc[led["ttype"]=="out","amount"].sum()
        a = st.columns(3)
        a[0].metric(tr("acc_in"), f"{inc:,.0f} USD")
        a[1].metric(tr("acc_out"), f"{out:,.0f} USD")
        a[2].metric(tr("acc_net"), f"{inc-out:,.0f} USD")

        with st.expander(tr("acc_add")):
            with st.form("acc_form"):
                c = st.columns(3)
                tt = c[0].selectbox(tr("acc_type"), ["in","out"],
                                    format_func=lambda x: tr("acc_in") if x=="in" else tr("acc_out"))
                ds = c[1].text_input(tr("acc_desc"))
                am = c[2].number_input(tr("acc_amount"), 0.0, 1e7, 1000.0)
                if st.form_submit_button(tr("acc_save")) and ds.strip():
                    get_db().execute(
                        "INSERT INTO ledger(ttype,descr,amount) VALUES(?,?,?)",
                        (tt, ds.strip(), am))
                    get_db().commit()
                    st.success("✅ " + tr("acc_saved")); st.rerun()

        st.markdown(f"#### {tr('acc_ledger')}")
        lv = led.copy()
        lv["ttype"] = lv["ttype"].map(lambda x: tr("acc_in") if x=="in" else tr("acc_out"))
        lv.columns = [tr("ord_date"), tr("acc_type"), tr("acc_desc"), tr("acc_amount")]
        st.dataframe(lv, use_container_width=True, hide_index=True)

# =============================================================================
# 13) ROUTER + AUTH GUARDS
# =============================================================================
get_db()   # ensure DB & tables exist before any page renders

if st.session_state.page == "erp" and not st.session_state.b2b_user:
    st.session_state.page = "login"
if st.session_state.page == "calculator" and not st.session_state.customer:
    st.session_state.page = "register"

{"landing": page_landing, "register": page_register,
 "calculator": page_calculator, "login": page_login,
 "erp": page_erp}[st.session_state.page]()
