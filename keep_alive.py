import os
import json
import asyncio
import datetime
from flask import Flask, request, session, redirect, url_for, render_template_string, flash
from threading import Thread

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "arc-market-dashboard-secret-key-change-me")

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PRODUCTS_PATH = os.path.join(BASE_DIR, "products.json")
ORDERS_LOG_PATH = os.path.join(BASE_DIR, "orders_log.json")

_bot = None  # يتحدد لاحقاً من bot.py عن طريق keep_alive(bot)


def set_bot_instance(bot_instance):
    global _bot
    _bot = bot_instance


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_config():
    return load_json(CONFIG_PATH, {})


def save_config(cfg):
    save_json(CONFIG_PATH, cfg)


def load_products():
    return load_json(PRODUCTS_PATH, {"categories": []})


def save_products(data):
    save_json(PRODUCTS_PATH, data)


def load_orders_log():
    return load_json(ORDERS_LOG_PATH, [])


def format_price_line(prices):
    flags = {"SAR": "🇸🇦", "USD": "🇺🇸", "EUR": "🇪🇺", "EGP": "🇪🇬", "JOD": "🇯🇴"}
    parts = []
    for code, val in prices.items():
        flag = flags.get(code, "")
        v = int(val) if float(val).is_integer() else val
        parts.append(f"{flag} {v} {code}")
    return "\n".join(parts)


def build_stock_messages():
    """نفس منطق بوت ديسكورد: رسالة هيدر، ثم رسالة لكل كاتيجوري (embed رأسي + embed لكل غرض بصورته)، ثم رسالة فوتر."""
    import discord
    data = load_products()
    messages = []

    header = discord.Embed(
        title="🛒 WRC STORE",
        description="⚔️ **ARC RAIDERS MARKET**\n> 💎 Premium Items • Fast Delivery • Trusted Service",
        color=0xFFD700
    )
    messages.append([header])

    for cat in data.get("categories", []):
        cat_embeds = [discord.Embed(title=cat["name"], color=0xFFD700)]
        items = cat.get("items", [])
        if not items:
            cat_embeds[0].description = "لا يوجد أغراض حالياً"
        for item in items[:9]:
            item_embed = discord.Embed(
                title=f"🖼️ {item['name']}",
                description=format_price_line(item["prices"]),
                color=0x5865F2
            )
            if item.get("image_url"):
                item_embed.set_thumbnail(url=item["image_url"])
            cat_embeds.append(item_embed)
        messages.append(cat_embeds)

    footer = discord.Embed(
        description="✅ Trusted Seller  •  ⚡ Instant Delivery  •  💎 Best Prices\n🎮 WRC STORE • Made by Ramos",
        color=0x2ecc71
    )
    messages.append([footer])
    return messages


async def _post_stock_async():
    cfg = load_config()
    channel_id = cfg.get("stock_channel_id")
    if not channel_id or _bot is None:
        return False, "لازم تحدد قناة المخزون الأول من !setup أو من هذا الموقع"
    channel = _bot.get_channel(channel_id)
    if channel is None:
        return False, "مش لاقي القناة، تأكد إن البوت عضو فيها"

    for old_id in cfg.get("stock_message_ids", []):
        try:
            old_msg = await channel.fetch_message(old_id)
            await old_msg.delete()
        except Exception:
            pass

    new_ids = []
    for embeds in build_stock_messages():
        msg = await channel.send(embeds=embeds)
        new_ids.append(msg.id)

    cfg["stock_message_ids"] = new_ids
    save_config(cfg)
    return True, f"تم نشر الكتالوج في #{channel.name} ({len(new_ids)} رسالة)"


def post_stock_to_discord():
    """يُستدعى من route Flask (Thread عادي) عشان ينشر في ديسكورد (async loop)."""
    if _bot is None or _bot.loop is None:
        return False, "البوت مش شغال حالياً"
    future = asyncio.run_coroutine_threadsafe(_post_stock_async(), _bot.loop)
    try:
        return future.result(timeout=30)
    except Exception as e:
        return False, str(e)


def build_sales_chart_data(days=7):
    """يرجع إحصائيات آخر N يوم من orders_log.json: عدد الطلبات لكل يوم + إجمالي/مكتمل/قيد الإنشاء."""
    log = load_orders_log()
    today = datetime.date.today()
    day_keys = [(today - datetime.timedelta(days=i)) for i in range(days - 1, -1, -1)]
    counts = {d.isoformat(): 0 for d in day_keys}

    total = len(log)
    completed = 0
    in_progress = 0

    for entry in log:
        status = entry.get("status", "")
        if status == "تم":
            completed += 1
        else:
            in_progress += 1
        try:
            created = datetime.datetime.fromisoformat(entry["created_at"]).date()
            key = created.isoformat()
            if key in counts:
                counts[key] += 1
        except Exception:
            continue

    max_count = max(counts.values()) if counts.values() else 0
    bars = []
    for key in sorted(counts.keys()):
        d = datetime.date.fromisoformat(key)
        height_pct = int((counts[key] / max_count) * 100) if max_count else 0
        bars.append({"label": f"{d.day}/{d.month}", "count": counts[key], "height": max(height_pct, 4 if counts[key] else 0)})

    return {"bars": bars, "total": total, "completed": completed, "in_progress": in_progress}


# ───────────────────────── HTML ─────────────────────────

BASE_STYLE = """
<style>
  * { box-sizing: border-box; }
  body {
    background: radial-gradient(circle at 30% 20%, #1a1330 0%, #0a0810 60%);
    color: #f0e8ff; font-family: 'Segoe UI', Tahoma, sans-serif;
    margin: 0; padding: 0; direction: rtl; min-height: 100vh;
  }
  .wrap { max-width: 1000px; margin: 0 auto; padding: 30px 20px; }
  h1 { color: #e6c877; text-shadow: 0 0 10px rgba(230,200,120,0.4); }
  h2 { color: #c4a05a; border-bottom: 2px solid #4a3a6a; padding-bottom: 8px; margin-top: 40px; }
  .card {
    background: rgba(30, 22, 45, 0.7); border: 1px solid #4a3a6a;
    border-radius: 12px; padding: 20px; margin-bottom: 20px;
  }
  input, select {
    background: #221a33; border: 1px solid #5a4a7a; color: #fff;
    padding: 8px 10px; border-radius: 6px; margin: 5px 0; width: 100%;
  }
  label { color: #cbb9ea; font-size: 13px; }
  button {
    background: linear-gradient(135deg, #e6c877, #c4952f); color: #1a1330; border: none;
    padding: 10px 18px; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 8px;
  }
  button:hover { opacity: 0.9; }
  .danger { background: linear-gradient(135deg, #e05a5a, #b33a3a); color: #fff; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  th, td { padding: 8px; border-bottom: 1px solid #4a3a6a; text-align: right; font-size: 14px; vertical-align: middle; }
  th { color: #e6c877; }
  .badge { background: #2ecc71; color: #0a0810; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
  a { color: #e6c877; }
  .flash { background: #2ecc71; color: #0a0810; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-weight: bold; }
  .flash.error { background: #e05a5a; color: #fff; }
  .thumb { width: 36px; height: 36px; border-radius: 6px; object-fit: cover; border: 1px solid #5a4a7a; }
  .stat-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 15px; }
  .stat-tile { background: rgba(20,15,32,0.8); border: 1px solid #4a3a6a; border-radius: 10px; padding: 14px; text-align: center; }
  .stat-tile .num { font-size: 26px; font-weight: bold; color: #e6c877; }
  .stat-tile .lbl { font-size: 12px; color: #cbb9ea; margin-top: 4px; }
  .chart { display: flex; align-items: flex-end; gap: 8px; height: 140px; padding: 10px 0; }
  .bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }
  .bar { width: 70%; background: linear-gradient(180deg, #e6c877, #8a6a2a); border-radius: 4px 4px 0 0; min-height: 3px; }
  .bar-count { font-size: 11px; color: #e6c877; margin-bottom: 3px; }
  .bar-label { font-size: 11px; color: #cbb9ea; margin-top: 5px; }
</style>
"""

LOGIN_PAGE = f"""
<!DOCTYPE html><html lang="ar"><head><meta charset="utf-8"><title>ARC Market Dashboard</title>{BASE_STYLE}</head>
<body><div class="wrap" style="max-width:400px; margin-top:80px;">
<div class="card">
  <h1 style="text-align:center;">🛒 WRC Store</h1>
  <p style="text-align:center; color:#cbb9ea;">لوحة تحكم بوت ARC Market</p>
  {{% if error %}}<div class="flash error">{{{{ error }}}}</div>{{% endif %}}
  <form method="POST">
    <label>كلمة المرور</label>
    <input type="password" name="password" required autofocus>
    <button type="submit" style="width:100%;">دخول</button>
  </form>
</div></div></body></html>
"""

DASHBOARD_PAGE = f"""
<!DOCTYPE html><html lang="ar"><head><meta charset="utf-8"><title>ARC Market Dashboard</title>{BASE_STYLE}</head>
<body><div class="wrap">
  <h1>🛒 WRC Store — لوحة التحكم</h1>
  <p><a href="{{{{ url_for('logout') }}}}">🚪 تسجيل خروج</a></p>

  {{% with messages = get_flashed_messages(with_categories=true) %}}
    {{% for category, msg in messages %}}
      <div class="flash {{{{ 'error' if category == 'error' else '' }}}}">{{{{ msg }}}}</div>
    {{% endfor %}}
  {{% endwith %}}

  <h2 style="margin-top:0;">📊 نظرة عامة على الطلبات</h2>
  <div class="card">
    <div class="stat-tiles">
      <div class="stat-tile"><div class="num">{{{{ sales.total }}}}</div><div class="lbl">إجمالي الطلبات</div></div>
      <div class="stat-tile"><div class="num">{{{{ sales.completed }}}}</div><div class="lbl">تم ✅</div></div>
      <div class="stat-tile"><div class="num">{{{{ sales.in_progress }}}}</div><div class="lbl">قيد الإنشاء 🔄</div></div>
    </div>
    <label>عدد الطلبات آخر 7 أيام</label>
    <div class="chart">
      {{% for bar in sales.bars %}}
      <div class="bar-col">
        <div class="bar-count">{{{{ bar.count }}}}</div>
        <div class="bar" style="height: {{{{ bar.height }}}}%;"></div>
        <div class="bar-label">{{{{ bar.label }}}}</div>
      </div>
      {{% endfor %}}
    </div>
  </div>

  <h2>⚙️ الإعدادات الحالية</h2>
  <div class="card">
    <div class="grid">
      <div><label>الحد اليومي للتذاكر</label><div class="badge">{{{{ cfg.get('max_tickets_per_day') }}}}</div></div>
      <div><label>تسجيل المحادثة</label><div class="badge">{{{{ 'مفعّل' if cfg.get('transcript_enabled') else 'معطّل' }}}}</div></div>
      <div><label>قناة الطلبات (ID)</label><div>{{{{ cfg.get('orders_channel_id') or '❌' }}}}</div></div>
      <div><label>قناة اللوق (ID)</label><div>{{{{ cfg.get('log_channel_id') or '❌' }}}}</div></div>
      <div><label>قناة الترحيب (ID)</label><div>{{{{ cfg.get('welcome_channel_id') or '❌' }}}}</div></div>
      <div><label>قناة المخزون (ID)</label><div>{{{{ cfg.get('stock_channel_id') or '❌' }}}}</div></div>
    </div>
    <form method="POST" action="{{{{ url_for('update_settings') }}}}" style="margin-top:15px;">
      <label>الحد اليومي للتذاكر</label>
      <input type="number" name="max_tickets_per_day" value="{{{{ cfg.get('max_tickets_per_day', 5) }}}}">
      <label style="display:flex; align-items:center; gap:8px; margin-top:10px;">
        <input type="checkbox" name="transcript_enabled" style="width:auto;" {{{{ 'checked' if cfg.get('transcript_enabled') else '' }}}}>
        تفعيل تسجيل المحادثة
      </label>
      <label style="margin-top:10px;">قناة المخزون (ID) — نفس الـ ID اللي تشوفه في ديسكورد (Developer Mode)</label>
      <input type="text" name="stock_channel_id" value="{{{{ cfg.get('stock_channel_id') or '' }}}}" placeholder="مثال: 1234567890">
      <button type="submit">💾 حفظ الإعدادات</button>
    </form>
    <form method="POST" action="{{{{ url_for('refresh_stock_route') }}}}" style="margin-top:10px;">
      <button type="submit">📢 نشر/تحديث كتالوج المخزون في ديسكورد الآن</button>
    </form>
  </div>

  <h2>📦 إدارة المخزون</h2>
  <div class="card">
    <h3 style="margin-top:0; color:#e6c877;">➕ إضافة / تعديل غرض</h3>
    <form method="POST" action="{{{{ url_for('add_item') }}}}">
      <div class="grid">
        <div><label>الكاتيجوري</label><input type="text" name="category" required placeholder="🔫 Weapons"></div>
        <div><label>اسم الغرض</label><input type="text" name="name" required></div>
        <div><label>SAR</label><input type="number" step="0.01" name="SAR" required></div>
        <div><label>USD</label><input type="number" step="0.01" name="USD" required></div>
        <div><label>EUR</label><input type="number" step="0.01" name="EUR" required></div>
        <div><label>EGP</label><input type="number" step="0.01" name="EGP" required></div>
        <div><label>JOD</label><input type="number" step="0.01" name="JOD" required></div>
        <div><label>رابط الصورة (اختياري)</label><input type="text" name="image_url" placeholder="https://..."></div>
      </div>
      <button type="submit">💾 حفظ الغرض</button>
    </form>
  </div>

  {{% for cat in categories %}}
  <div class="card">
    <h3 style="margin-top:0; color:#e6c877;">{{{{ cat.name }}}} <span class="badge">{{{{ cat['items']|length }}}} غرض</span></h3>
    <table>
      <tr><th></th><th>الاسم</th><th>SAR</th><th>USD</th><th>EUR</th><th>EGP</th><th>JOD</th><th></th></tr>
      {{% for item in cat['items'] %}}
      <tr>
        <td>{{% if item.get('image_url') %}}<img class="thumb" src="{{{{ item.image_url }}}}">{{% else %}}—{{% endif %}}</td>
        <td>{{{{ item.name }}}}</td>
        <td>{{{{ item.prices.SAR }}}}</td>
        <td>{{{{ item.prices.USD }}}}</td>
        <td>{{{{ item.prices.EUR }}}}</td>
        <td>{{{{ item.prices.EGP }}}}</td>
        <td>{{{{ item.prices.JOD }}}}</td>
        <td>
          <form method="POST" action="{{{{ url_for('delete_item') }}}}" style="margin:0;">
            <input type="hidden" name="category" value="{{{{ cat.name }}}}">
            <input type="hidden" name="name" value="{{{{ item.name }}}}">
            <button type="submit" class="danger" style="padding:4px 10px; font-size:12px;">حذف</button>
          </form>
        </td>
      </tr>
      {{% endfor %}}
    </table>
  </div>
  {{% endfor %}}

</div></body></html>
"""


def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    return "✅ ARC Raiders Ticket Bot is alive!"


@app.route("/dashboard/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = "❌ كلمة المرور غلط"
    return render_template_string(LOGIN_PAGE, error=error)


@app.route("/dashboard/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    cfg = load_config()
    products = load_products()
    sales = build_sales_chart_data()
    return render_template_string(DASHBOARD_PAGE, cfg=cfg, categories=products.get("categories", []), sales=sales)


@app.route("/dashboard/settings", methods=["POST"])
@login_required
def update_settings():
    cfg = load_config()
    try:
        cfg["max_tickets_per_day"] = int(request.form.get("max_tickets_per_day", cfg.get("max_tickets_per_day", 5)))
    except ValueError:
        pass
    cfg["transcript_enabled"] = bool(request.form.get("transcript_enabled"))
    stock_id = request.form.get("stock_channel_id", "").strip()
    if stock_id:
        try:
            cfg["stock_channel_id"] = int(stock_id)
        except ValueError:
            flash("⚠️ الـ ID اللي كتبته مش رقم صحيح", "error")
    save_config(cfg)
    flash("✅ تم حفظ الإعدادات")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/products/add", methods=["POST"])
@login_required
def add_item():
    category = request.form.get("category", "").strip()
    name = request.form.get("name", "").strip()
    image_url = request.form.get("image_url", "").strip()
    try:
        prices = {
            "SAR": float(request.form.get("SAR", 0)),
            "USD": float(request.form.get("USD", 0)),
            "EUR": float(request.form.get("EUR", 0)),
            "EGP": float(request.form.get("EGP", 0)),
            "JOD": float(request.form.get("JOD", 0)),
        }
    except ValueError:
        flash("❌ الأسعار لازم تكون أرقام", "error")
        return redirect(url_for("dashboard"))

    data = load_products()
    cat = next((c for c in data["categories"] if c["name"].lower() == category.lower()), None)
    if not cat:
        cat = {"name": category, "items": []}
        data["categories"].append(cat)
    existing = next((i for i in cat["items"] if i["name"].lower() == name.lower()), None)
    if existing:
        existing["prices"] = prices
        if image_url:
            existing["image_url"] = image_url
    else:
        item = {"name": name, "prices": prices}
        if image_url:
            item["image_url"] = image_url
        cat["items"].append(item)
    save_products(data)
    flash(f"✅ تم حفظ {name}")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/products/delete", methods=["POST"])
@login_required
def delete_item():
    category = request.form.get("category", "")
    name = request.form.get("name", "")
    data = load_products()
    cat = next((c for c in data["categories"] if c["name"] == category), None)
    if cat:
        cat["items"] = [i for i in cat["items"] if i["name"] != name]
        save_products(data)
        flash(f"🗑️ تم حذف {name}")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/refresh-stock", methods=["POST"])
@login_required
def refresh_stock_route():
    ok, msg = post_stock_to_discord()
    flash(("✅ " if ok else "❌ ") + msg, "success" if ok else "error")
    return redirect(url_for("dashboard"))


def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


def keep_alive(bot_instance=None):
    if bot_instance is not None:
        set_bot_instance(bot_instance)
    t = Thread(target=run)
    t.daemon = True
    t.start()
