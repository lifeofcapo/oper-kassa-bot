# /opt/oper-kassa-bot/api.py
import os
from flask import Flask, jsonify, request, session, redirect, url_for, render_template_string
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

load_dotenv('/opt/oper-kassa-bot/.env')

MONGO_URI = os.getenv("MONGO_URI")
ADMIN_PASSWORD = os.getenv("BOT_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())

if not MONGO_URI:
    raise RuntimeError("MONGO_URI не установлен в /opt/oper-kassa-bot/.env")

client = MongoClient(MONGO_URI)
db = client["operkassa_db"]
rates_collection = db["rates"]

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app, resources={r"/api/*": {"origins": "*"}})

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated
@app.route("/api/rates", methods=["GET"])
def get_rates():
    try:
        data = list(rates_collection.find({}, {"_id": 0}))
        return jsonify({"currencies": data}), 200
    except Exception as e:
        return jsonify({"error": "Не удалось получить курсы", "detail": str(e)}), 500

@app.route("/api/health", methods=["GET"])
def health():
    try:
        client.admin.command("ping")
        return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()}), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OperKassa — Вход</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0a0a0a;
    --surface: #111111;
    --border: #222;
    --accent: #c8f135;
    --accent-dim: #a0c020;
    --text: #f0f0f0;
    --muted: #555;
    --error: #ff4444;
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Mono', monospace;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background-image:
      repeating-linear-gradient(0deg, transparent, transparent 39px, #ffffff06 39px, #ffffff06 40px),
      repeating-linear-gradient(90deg, transparent, transparent 39px, #ffffff06 39px, #ffffff06 40px);
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    width: 100%;
    max-width: 420px;
    padding: 48px 40px;
    position: relative;
  }
  .card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent);
  }
  .logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.4rem;
    letter-spacing: 0.05em;
    color: var(--accent);
    margin-bottom: 4px;
  }
  .subtitle {
    font-size: 0.7rem;
    color: var(--muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 40px;
  }
  label {
    display: block;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 8px;
  }
  input[type="password"] {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1rem;
    padding: 14px 16px;
    outline: none;
    transition: border-color 0.2s;
  }
  input[type="password"]:focus { border-color: var(--accent); }
  button {
    width: 100%;
    margin-top: 24px;
    background: var(--accent);
    color: #0a0a0a;
    border: none;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    font-weight: 500;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    padding: 16px;
    cursor: pointer;
    transition: background 0.15s;
  }
  button:hover { background: var(--accent-dim); }
  .error {
    margin-top: 16px;
    font-size: 0.75rem;
    color: var(--error);
    letter-spacing: 0.05em;
  }
</style>
</head>
<body>
<div class="card">
  <div class="logo">OperKassa</div>
  <div class="subtitle">Панель управления курсами</div>
  <form method="POST">
    <label>Пароль доступа</label>
    <input type="password" name="password" autofocus placeholder="••••••••">
    <button type="submit">Войти</button>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
  </form>
</div>
</body>
</html>"""

ADMIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OperKassa — Курсы валют</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0a0a0a;
    --surface: #111111;
    --border: #222;
    --accent: #c8f135;
    --accent-dim: #a0c020;
    --text: #f0f0f0;
    --muted: #555;
    --muted2: #888;
    --success: #4caf50;
    --error: #ff4444;
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Mono', monospace;
    min-height: 100vh;
    background-image:
      repeating-linear-gradient(0deg, transparent, transparent 39px, #ffffff04 39px, #ffffff04 40px),
      repeating-linear-gradient(90deg, transparent, transparent 39px, #ffffff04 39px, #ffffff04 40px);
  }
  header {
    border-bottom: 1px solid var(--border);
    padding: 20px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    background: rgba(10,10,10,0.95);
    backdrop-filter: blur(8px);
    z-index: 10;
  }
  .logo {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.8rem;
    letter-spacing: 0.05em;
    color: var(--accent);
  }
  .header-right { display: flex; align-items: center; gap: 24px; }
  .status-dot { display: flex; align-items: center; gap: 8px; font-size: 0.65rem; color: var(--muted2); letter-spacing: 0.1em; }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success); box-shadow: 0 0 6px var(--success); animation: pulse 2s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .logout { font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--muted); text-decoration: none; border: 1px solid var(--border); padding: 6px 14px; transition: all 0.15s; }
  .logout:hover { color: var(--error); border-color: var(--error); }
  main { max-width: 900px; margin: 0 auto; padding: 48px 40px; }
  .page-title { font-size: 0.65rem; letter-spacing: 0.25em; text-transform: uppercase; color: var(--muted); margin-bottom: 32px; }
  #toast {
    position: fixed; bottom: 32px; right: 32px;
    padding: 14px 24px; font-size: 0.75rem; letter-spacing: 0.1em;
    border-left: 3px solid var(--accent);
    background: var(--surface); color: var(--text);
    opacity: 0; transform: translateY(10px);
    transition: all 0.3s; pointer-events: none; z-index: 100;
  }
  #toast.show { opacity: 1; transform: translateY(0); }
  #toast.error { border-color: var(--error); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 2px; }
  .currency-card { background: var(--surface); border: 1px solid var(--border); padding: 28px; position: relative; transition: border-color 0.2s; }
  .currency-card:hover { border-color: #333; }
  .currency-card.disabled { opacity: 0.45; }
  .card-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; }
  .currency-name { font-size: 0.75rem; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase; }
  .currency-code { font-size: 0.6rem; color: var(--muted); letter-spacing: 0.1em; margin-top: 4px; }
  .badge { font-size: 0.55rem; letter-spacing: 0.15em; text-transform: uppercase; padding: 4px 8px; border: 1px solid; }
  .badge.active { color: var(--accent); border-color: var(--accent); }
  .badge.phone { color: var(--muted); border-color: var(--muted); }
  .updated { font-size: 0.6rem; color: var(--muted); letter-spacing: 0.05em; margin-bottom: 20px; }
  .rate-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
  .rate-field label { display: block; font-size: 0.58rem; letter-spacing: 0.2em; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }
  .rate-field input { width: 100%; background: var(--bg); border: 1px solid var(--border); color: var(--text); font-family: 'IBM Plex Mono', monospace; font-size: 1rem; padding: 10px 12px; outline: none; transition: border-color 0.2s; }
  .rate-field input:focus { border-color: var(--accent); }
  .rate-field input:disabled { opacity: 0.3; cursor: not-allowed; }
  .save-btn { width: 100%; background: transparent; border: 1px solid var(--accent); color: var(--accent); font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; font-weight: 500; letter-spacing: 0.2em; text-transform: uppercase; padding: 12px; cursor: pointer; transition: all 0.15s; }
  .save-btn:hover { background: var(--accent); color: #0a0a0a; }
  .save-btn:disabled { opacity: 0.3; cursor: not-allowed; }
  .save-btn:disabled:hover { background: transparent; color: var(--accent); }
  @media (max-width: 600px) {
    header { padding: 16px 20px; }
    main { padding: 32px 20px; }
    .grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<header>
  <div class="logo">OperKassa</div>
  <div class="header-right">
    <div class="status-dot"><span class="dot"></span><span>MongoDB подключена</span></div>
    <a href="/admin/logout" class="logout">Выйти</a>
  </div>
</header>
<main>
  <div class="page-title">Управление курсами валют</div>
  <div class="grid" id="grid">Загрузка...</div>
</main>
<div id="toast"></div>
<script>
const NAMES = {
  USD_BLUE: 'Доллар США (синий)', USD_WHITE: 'Доллар США (белый)',
  EUR: 'Евро', GBP: 'Фунт стерлингов', CNY: 'Китайский юань', RUB: 'Российский рубль'
};

function showToast(msg, isError=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'show' + (isError ? ' error' : '');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.className = '', 3000);
}

function formatTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'}) +
           ' · ' + d.toLocaleDateString('ru-RU', {day:'2-digit', month:'2-digit'});
  } catch { return iso; }
}

async function saveRate(code, buyInput, sellInput, btn) {
  const buy  = parseFloat(buyInput.value.replace(',', '.'));
  const sell = parseFloat(sellInput.value.replace(',', '.'));
  if (isNaN(buy) || isNaN(sell) || buy <= 0 || sell <= 0) { showToast('Введите корректные числа', true); return; }
  if (sell <= buy) { showToast('Курс продажи должен быть выше покупки', true); return; }
  btn.disabled = true; btn.textContent = 'Сохранение...';
  try {
    const res = await fetch('/admin/update', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({code, buy, sell})
    });
    const data = await res.json();
    if (data.ok) {
      showToast('✓ ' + (NAMES[code] || code) + ' обновлён');
      const upd = btn.closest('.currency-card').querySelector('.updated');
      if (upd) upd.textContent = 'Обновлено: ' + formatTime(new Date().toISOString());
    } else {
      showToast('Ошибка: ' + (data.error || 'неизвестно'), true);
    }
  } catch(e) { showToast('Ошибка соединения', true); }
  finally { btn.disabled = false; btn.textContent = 'Сохранить'; }
}

async function loadRates() {
  const grid = document.getElementById('grid');
  try {
    const res = await fetch('/api/rates');
    const { currencies } = await res.json();
    grid.innerHTML = '';
    currencies.forEach(c => {
      const show = c.showRates;
      const card = document.createElement('div');
      card.className = 'currency-card' + (show ? '' : ' disabled');
      card.innerHTML = `
        <div class="card-header">
          <div>
            <div class="currency-name">${NAMES[c.code] || c.code}</div>
            <div class="currency-code">${c.code}</div>
          </div>
          <span class="badge ${show ? 'active' : 'phone'}">${show ? 'отображается' : 'по телефону'}</span>
        </div>
        <div class="updated">Обновлено: ${formatTime(c.updated)}</div>
        <div class="rate-row">
          <div class="rate-field">
            <label>Покупка ₽</label>
            <input type="number" step="0.01" value="${c.buy || ''}" ${!show ? 'disabled' : ''} id="buy_${c.code}">
          </div>
          <div class="rate-field">
            <label>Продажа ₽</label>
            <input type="number" step="0.01" value="${c.sell || ''}" ${!show ? 'disabled' : ''} id="sell_${c.code}">
          </div>
        </div>
        <button class="save-btn" ${!show ? 'disabled' : ''}
          onclick="saveRate('${c.code}', document.getElementById('buy_${c.code}'), document.getElementById('sell_${c.code}'), this)">
          Сохранить
        </button>`;
      grid.appendChild(card);
    });
  } catch(e) {
    grid.innerHTML = '<div style="color:var(--error);font-size:0.8rem">Ошибка загрузки данных</div>';
  }
}

loadRates();
</script>
</body>
</html>"""

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin_panel"))
        error = "Неверный пароль"
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/admin")
@login_required
def admin_panel():
    return render_template_string(ADMIN_HTML)

@app.route("/admin/update", methods=["POST"])
@login_required
def admin_update():
    data = request.get_json()
    code = data.get("code")
    buy  = data.get("buy")
    sell = data.get("sell")
    if not code or buy is None or sell is None:
        return jsonify({"ok": False, "error": "Неверные данные"}), 400
    try:
        rates_collection.update_one(
            {"code": code},
            {"$set": {"buy": float(buy), "sell": float(sell), "updated": datetime.now().isoformat()}},
            upsert=True
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)