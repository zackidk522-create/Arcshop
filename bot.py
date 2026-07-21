import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import asyncio
import datetime
import os
import json
import html
from keep_alive import keep_alive

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
SERVER_ID = 1361045464719556739
DEFAULT_TICKET_CATEGORY_ID = 1503402971516506163

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
DAILY_PATH = os.path.join(os.path.dirname(__file__), "daily_tickets.json")
TRANSCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "log_channel_id": None,
    "log_channel_name": "arc-orders",
    "orders_channel_id": None,
    "orders_channel_name": "arc-requests",
    "category_id": DEFAULT_TICKET_CATEGORY_ID,
    "max_tickets_per_day": 5,
    "transcript_enabled": True,
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_daily():
    if not os.path.exists(DAILY_PATH):
        return {}
    with open(DAILY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_daily(data):
    with open(DAILY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_log_channel(guild):
    cfg = load_config()
    if cfg.get("log_channel_id"):
        ch = guild.get_channel(cfg["log_channel_id"])
        if ch:
            return ch
    return discord.utils.get(guild.text_channels, name=cfg["log_channel_name"])

def get_orders_channel(guild):
    cfg = load_config()
    if cfg.get("orders_channel_id"):
        ch = guild.get_channel(cfg["orders_channel_id"])
        if ch:
            return ch
    return discord.utils.get(guild.text_channels, name=cfg["orders_channel_name"])

config = load_config()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_tickets = {}  # user_id -> channel_id

PAYMENT_METHODS = [
    discord.SelectOption(label="إنستا باي",   value="انستا باي",   emoji=discord.PartialEmoji.from_str("<:ENSTAPAY:1528927174713937940>")),
    discord.SelectOption(label="فودافون كاش", value="فودافون كاش", emoji=discord.PartialEmoji.from_str("<:Vodafonecash:1528928189198504116>")),
    discord.SelectOption(label="فيزا",         value="فيزا",         emoji=discord.PartialEmoji.from_str("<:VISA:1528928315958755448>")),
    discord.SelectOption(label="باي بال",      value="باي بال",      emoji=discord.PartialEmoji.from_str("<:PayPal:1528928392194555955>")),
    discord.SelectOption(label="كريبتو",       value="كريبتو",       emoji=discord.PartialEmoji.from_str("<:CRYPTO:1528928509450387537>")),
    discord.SelectOption(label="كليك",         value="كليك",         emoji=discord.PartialEmoji.from_str("<:Click:1528928605445558292>")),
    discord.SelectOption(label="موبايلي",      value="موبايلي",      emoji=discord.PartialEmoji.from_str("<:Mobily:1528928665943937264>")),
    discord.SelectOption(label="STC Pay",      value="STC Pay",      emoji=discord.PartialEmoji.from_str("<:Stcpay:1528928726581248242>")),
]

# ─────────────────────────────────────────
# ترجمات نظام التذاكر (عربي / إنجليزي)
# ─────────────────────────────────────────
TRANSLATIONS = {
    "ar": {
        "welcome_title": "🎫 مرحباً بك في نظام التذاكر",
        "welcome_desc": "أهلاً {mention}! 👋\n\nاختر نوع تذكرتك من الأزرار أدناه 👇",
        "field_product": "🛒 طلب منتج",
        "field_product_desc": "اطلب منتج من المتجر (سلاح، برنت، غرض...)",
        "field_question": "❓ سؤال",
        "field_question_desc": "اسأل أي سؤال عن المتجر أو اللعبة",
        "btn_product": "🛒 طلب منتج",
        "btn_question": "❓ سؤال",
        "modal_product_title": "🛒 طلب منتج",
        "modal_product_name_label": "اسم المنتج",
        "modal_product_name_placeholder": "مثال: سلاح، غرض، برنت...",
        "modal_price_label": "السعر",
        "modal_price_placeholder": "مثال: 100 جنيه",
        "modal_notes_label": "ملاحظات إضافية (اختياري)",
        "modal_notes_placeholder": "أي تفاصيل تانية؟",
        "modal_question_title": "❓ تقديم سؤال",
        "modal_question_label": "سؤالك",
        "modal_question_placeholder": "اكتب سؤالك هنا...",
        "payment_prompt_title": "💳 اختر طريقة الدفع",
        "payment_prompt_desc": "**المنتج:** {product}\n\nاختر طريقة الدفع من القائمة 👇",
        "payment_placeholder": "اختر طريقة الدفع...",
        "product_order_title": "🛒 طلب منتج جديد",
        "field_user": "👤 المستخدم",
        "field_product_name": "📦 المنتج",
        "field_price": "💰 السعر",
        "field_payment": "💳 طريقة الدفع",
        "field_notes": "📝 ملاحظات",
        "question_title": "❓ سؤال جديد",
        "field_question_full": "💬 السؤال",
        "close_button": "🔒 إغلاق التذكرة",
        "ticket_closing_msg": "✅ تم إغلاق التذكرة، سيتم حذف القناة خلال 5 ثواني...",
    },
    "en": {
        "welcome_title": "🎫 Welcome to the Ticket System",
        "welcome_desc": "Hey {mention}! 👋\n\nChoose your ticket type from the buttons below 👇",
        "field_product": "🛒 Order a Product",
        "field_product_desc": "Order a product from the store (weapon, item, print...)",
        "field_question": "❓ Question",
        "field_question_desc": "Ask any question about the store or the game",
        "btn_product": "🛒 Order Product",
        "btn_question": "❓ Question",
        "modal_product_title": "🛒 Order a Product",
        "modal_product_name_label": "Product Name",
        "modal_product_name_placeholder": "e.g: weapon, item, print...",
        "modal_price_label": "Price",
        "modal_price_placeholder": "e.g: 100 EGP",
        "modal_notes_label": "Additional Notes (optional)",
        "modal_notes_placeholder": "Any other details?",
        "modal_question_title": "❓ Ask a Question",
        "modal_question_label": "Your Question",
        "modal_question_placeholder": "Type your question here...",
        "payment_prompt_title": "💳 Choose Payment Method",
        "payment_prompt_desc": "**Product:** {product}\n\nChoose a payment method from the list 👇",
        "payment_placeholder": "Choose payment method...",
        "product_order_title": "🛒 New Product Order",
        "field_user": "👤 Customer",
        "field_product_name": "📦 Product",
        "field_price": "💰 Price",
        "field_payment": "💳 Payment Method",
        "field_notes": "📝 Notes",
        "question_title": "❓ New Question",
        "field_question_full": "💬 Question",
        "close_button": "🔒 Close Ticket",
        "ticket_closing_msg": "✅ Ticket closed, this channel will be deleted in 5 seconds...",
    },
}

ticket_language = {}  # channel_id -> "ar" | "en"


# ─────────────────────────────────────────
# Daily ticket limit helpers
# ─────────────────────────────────────────
def can_open_ticket(user_id: int) -> tuple[bool, int]:
    today = datetime.date.today().isoformat()
    data = load_daily()
    entry = data.get(str(user_id))
    if not entry or entry.get("date") != today:
        return True, 0
    cfg = load_config()
    return entry.get("count", 0) < cfg["max_tickets_per_day"], entry.get("count", 0)

def register_ticket_open(user_id: int):
    today = datetime.date.today().isoformat()
    data = load_daily()
    entry = data.get(str(user_id))
    if not entry or entry.get("date") != today:
        entry = {"date": today, "count": 0}
    entry["count"] += 1
    data[str(user_id)] = entry
    save_daily(data)


# ─────────────────────────────────────────
# Transcript generator (HTML, Discord dark theme style, RTL)
# ─────────────────────────────────────────
async def generate_transcript(channel: discord.TextChannel) -> str:
    messages = [m async for m in channel.history(limit=500, oldest_first=True)]

    rows = []
    for m in messages:
        author = html.escape(str(m.author.display_name))
        avatar = m.author.display_avatar.url if m.author.display_avatar else ""
        time_str = m.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
        content = html.escape(m.content) if m.content else ""
        content = content.replace("\n", "<br>")

        embeds_html = ""
        for e in m.embeds:
            title = html.escape(e.title) if e.title else ""
            desc = html.escape(e.description) if e.description else ""
            fields_html = ""
            for field in e.fields:
                fields_html += f'<div class="field"><b>{html.escape(field.name)}</b>: {html.escape(str(field.value))}</div>'
            embeds_html += f'<div class="embed"><div class="embed-title">{title}</div><div class="embed-desc">{desc}</div>{fields_html}</div>'

        attachments_html = ""
        for a in m.attachments:
            attachments_html += f'<div class="attachment">📎 <a href="{a.url}" target="_blank">{html.escape(a.filename)}</a></div>'

        rows.append(f"""
        <div class="message">
          <img class="avatar" src="{avatar}" onerror="this.style.display='none'">
          <div class="msg-body">
            <div class="msg-header"><span class="author">{author}</span><span class="time">{time_str}</span></div>
            <div class="content">{content}</div>
            {embeds_html}
            {attachments_html}
          </div>
        </div>""")

    html_doc = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>محادثة التذكرة - {html.escape(channel.name)}</title>
<style>
  body {{
    background: #313338;
    color: #dbdee1;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    margin: 0;
    padding: 20px;
  }}
  .header {{
    background: #2b2d31;
    padding: 16px 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    border-right: 4px solid #FFD700;
  }}
  .header h1 {{ margin: 0; font-size: 20px; color: #fff; }}
  .header p {{ margin: 4px 0 0; color: #949ba4; font-size: 13px; }}
  .message {{
    display: flex;
    gap: 12px;
    padding: 10px 8px;
    border-radius: 6px;
    margin-bottom: 4px;
  }}
  .message:hover {{ background: #2e3035; }}
  .avatar {{
    width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
  }}
  .msg-header {{ display: flex; gap: 8px; align-items: baseline; }}
  .author {{ font-weight: 600; color: #f2f3f5; }}
  .time {{ font-size: 11px; color: #949ba4; }}
  .content {{ margin-top: 2px; white-space: pre-wrap; word-break: break-word; }}
  .embed {{
    margin-top: 6px;
    background: #2b2d31;
    border-right: 4px solid #FFD700;
    border-radius: 4px;
    padding: 10px 12px;
    max-width: 500px;
  }}
  .embed-title {{ font-weight: 700; color: #fff; margin-bottom: 4px; }}
  .embed-desc {{ color: #dbdee1; font-size: 14px; }}
  .field {{ font-size: 13px; margin-top: 4px; color: #dbdee1; }}
  .attachment {{ margin-top: 6px; font-size: 13px; }}
  .attachment a {{ color: #00a8fc; text-decoration: none; }}
  .footer {{ margin-top: 20px; text-align: center; color: #6d6f78; font-size: 12px; }}
</style>
</head>
<body>
  <div class="header">
    <h1>📋 محادثة التذكرة: {html.escape(channel.name)}</h1>
    <p>تم إنشاء هذا السجل في {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
  </div>
  {''.join(rows)}
  <div class="footer">ARC Raiders Store — سجل تذاكر تلقائي</div>
</body>
</html>"""

    file_path = os.path.join(TRANSCRIPTS_DIR, f"transcript-{channel.id}.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return file_path


# ─────────────────────────────────────────
# Select: اختيار طريقة الدفع
# ─────────────────────────────────────────
class PaymentSelect(Select):
    def __init__(self, product_name: str, price: str, notes: str, opener_id: int, lang: str = "ar"):
        self.lang = lang
        t = TRANSLATIONS[lang]
        super().__init__(placeholder=t["payment_placeholder"], options=PAYMENT_METHODS, custom_id="payment_select")
        self.product_name = product_name
        self.price = price
        self.notes = notes
        self.opener_id = opener_id

    async def callback(self, interaction: discord.Interaction):
        payment = self.values[0]
        t = TRANSLATIONS[self.lang]

        embed = discord.Embed(title=t["product_order_title"], color=0x00ff99, timestamp=datetime.datetime.now())
        embed.add_field(name=t["field_user"], value=interaction.user.mention, inline=True)
        embed.add_field(name=t["field_product_name"], value=self.product_name, inline=True)
        embed.add_field(name=t["field_price"], value=self.price, inline=True)
        embed.add_field(name=t["field_payment"], value=payment, inline=True)
        if self.notes:
            embed.add_field(name=t["field_notes"], value=self.notes, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        close_view = CloseTicketView(
            opener_id=self.opener_id, ticket_type="منتج",
            product_name=self.product_name, price=self.price, payment_method=payment, notes=self.notes, lang=self.lang
        )

        self.disabled = True
        await interaction.response.edit_message(view=self.view)
        await interaction.channel.send(embed=embed, view=close_view)

        # ── نشر الطلب في قناة "الطلبات" مع حالة قابلة للتحديث ──
        orders_channel = get_orders_channel(interaction.guild)
        if orders_channel:
            order_embed = discord.Embed(title="🆕 طلب جديد", color=0xFFD700, timestamp=datetime.datetime.now())
            order_embed.add_field(name="👤 العميل", value=interaction.user.mention, inline=True)
            order_embed.add_field(name="📦 المنتج", value=self.product_name, inline=True)
            order_embed.add_field(name="💰 السعر", value=self.price, inline=True)
            order_embed.add_field(name="💳 طريقة الدفع", value=payment, inline=True)
            order_embed.add_field(name="📊 الحالة", value="🔄 قيد الإنشاء", inline=True)
            if self.notes:
                order_embed.add_field(name="📝 ملاحظات", value=self.notes, inline=False)
            order_embed.add_field(name="🎫 التذكرة", value=interaction.channel.mention, inline=False)
            order_embed.set_footer(text=f"ID: {interaction.user.id}")
            await orders_channel.send(embed=order_embed, view=OrderStatusView())


class PaymentView(View):
    def __init__(self, product_name: str, price: str, notes: str, opener_id: int, lang: str = "ar"):
        super().__init__(timeout=300)
        self.add_item(PaymentSelect(product_name, price, notes, opener_id, lang))


# ─────────────────────────────────────────
# Modal: طلب منتج
# ─────────────────────────────────────────
class ProductModal(Modal, title="🛒 طلب منتج"):
    product_name = TextInput(label="اسم المنتج", placeholder="مثال: سلاح، غرض، برنت...", required=True, max_length=200)
    price = TextInput(label="السعر", placeholder="مثال: 100 جنيه", required=True, max_length=100)
    notes = TextInput(label="ملاحظات إضافية (اختياري)", placeholder="أي تفاصيل تانية؟", required=False,
                       style=discord.TextStyle.paragraph, max_length=500)

    def __init__(self, opener_id: int, lang: str = "ar"):
        super().__init__()
        self.opener_id = opener_id
        self.lang = lang
        t = TRANSLATIONS[lang]
        self.title = t["modal_product_title"]
        self.product_name.label = t["modal_product_name_label"]
        self.product_name.placeholder = t["modal_product_name_placeholder"]
        self.price.label = t["modal_price_label"]
        self.price.placeholder = t["modal_price_placeholder"]
        self.notes.label = t["modal_notes_label"]
        self.notes.placeholder = t["modal_notes_placeholder"]

    async def on_submit(self, interaction: discord.Interaction):
        t = TRANSLATIONS[self.lang]
        embed = discord.Embed(
            title=t["payment_prompt_title"],
            description=t["payment_prompt_desc"].format(product=self.product_name.value),
            color=0xFFD700
        )
        view = PaymentView(
            product_name=self.product_name.value, price=self.price.value,
            notes=self.notes.value, opener_id=self.opener_id, lang=self.lang
        )
        await interaction.response.send_message(embed=embed, view=view)


# ─────────────────────────────────────────
# Modal: سؤال
# ─────────────────────────────────────────
class QuestionModal(Modal, title="❓ تقديم سؤال"):
    question = TextInput(label="سؤالك", placeholder="اكتب سؤالك هنا...", required=True,
                          style=discord.TextStyle.paragraph, max_length=1000)

    def __init__(self, opener_id: int, lang: str = "ar"):
        super().__init__()
        self.opener_id = opener_id
        self.lang = lang
        t = TRANSLATIONS[lang]
        self.title = t["modal_question_title"]
        self.question.label = t["modal_question_label"]
        self.question.placeholder = t["modal_question_placeholder"]

    async def on_submit(self, interaction: discord.Interaction):
        t = TRANSLATIONS[self.lang]
        embed = discord.Embed(title=t["question_title"], color=0x5865F2, timestamp=datetime.datetime.now())
        embed.add_field(name=t["field_user"], value=interaction.user.mention, inline=True)
        embed.add_field(name=t["field_question_full"], value=self.question.value, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        close_view = CloseTicketView(opener_id=self.opener_id, ticket_type="سؤال", question=self.question.value, lang=self.lang)
        await interaction.response.send_message(embed=embed, view=close_view)


# ─────────────────────────────────────────
# View: اختيار نوع التذكرة
# ─────────────────────────────────────────
class TicketTypeView(View):
    def __init__(self, opener_id: int, lang: str = "ar"):
        super().__init__(timeout=300)
        self.opener_id = opener_id
        self.lang = lang
        t = TRANSLATIONS[lang]
        self.product_button.label = t["btn_product"]
        self.question_button.label = t["btn_question"]

    @discord.ui.button(label="🛒 طلب منتج", style=discord.ButtonStyle.success, custom_id="btn_product")
    async def product_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ProductModal(self.opener_id, self.lang))

    @discord.ui.button(label="❓ سؤال", style=discord.ButtonStyle.primary, custom_id="btn_question")
    async def question_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(QuestionModal(self.opener_id, self.lang))


# ─────────────────────────────────────────
# View: اختيار اللغة (تظهر أول ما تتفتح التذكرة)
# ─────────────────────────────────────────
class LanguageSelectView(View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    async def _proceed(self, interaction: discord.Interaction, lang: str):
        ticket_language[interaction.channel.id] = lang
        t = TRANSLATIONS[lang]
        embed = discord.Embed(
            title=t["welcome_title"],
            description=t["welcome_desc"].format(mention=f"<@{self.opener_id}>"),
            color=0xFFD700, timestamp=datetime.datetime.now()
        )
        embed.add_field(name=t["field_product"], value=t["field_product_desc"], inline=False)
        embed.add_field(name=t["field_question"], value=t["field_question_desc"], inline=False)
        embed.set_footer(text="ARC Raiders Store")
        await interaction.response.edit_message(embed=embed, view=TicketTypeView(opener_id=self.opener_id, lang=lang))

    @discord.ui.button(label="🇸🇦 العربية", style=discord.ButtonStyle.success, custom_id="lang_ar")
    async def lang_ar(self, interaction: discord.Interaction, button: Button):
        await self._proceed(interaction, "ar")

    @discord.ui.button(label="🇬🇧 English", style=discord.ButtonStyle.primary, custom_id="lang_en")
    async def lang_en(self, interaction: discord.Interaction, button: Button):
        await self._proceed(interaction, "en")


# ─────────────────────────────────────────
# View: تحديث حالة الطلب (قيد الإنشاء ⇄ تم)
# ─────────────────────────────────────────
class OrderStatusView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ تحديد كـ: تم", style=discord.ButtonStyle.success, custom_id="order_toggle_status")
    async def toggle_status(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ لازم تكون من فريق العمل عشان تعدل حالة الطلب", ephemeral=True)
            return

        old_embed = interaction.message.embeds[0]
        new_embed = discord.Embed.from_dict(old_embed.to_dict())

        for i, field in enumerate(new_embed.fields):
            if field.name == "📊 الحالة":
                if "قيد الإنشاء" in field.value:
                    new_embed.set_field_at(i, name="📊 الحالة", value="✅ تم", inline=field.inline)
                    new_embed.color = 0x2ecc71
                    button.label = "🔄 إرجاع لـ: قيد الإنشاء"
                    button.style = discord.ButtonStyle.secondary
                else:
                    new_embed.set_field_at(i, name="📊 الحالة", value="🔄 قيد الإنشاء", inline=field.inline)
                    new_embed.color = 0xFFD700
                    button.label = "✅ تحديد كـ: تم"
                    button.style = discord.ButtonStyle.success
                break

        await interaction.response.edit_message(embed=new_embed, view=self)


# ─────────────────────────────────────────
# View: زر إغلاق التذكرة
# ─────────────────────────────────────────
class CloseTicketView(View):
    def __init__(self, opener_id, ticket_type, product_name=None, price=None, payment_method=None, notes=None, question=None, lang="ar"):
        super().__init__(timeout=None)
        self.opener_id = opener_id
        self.ticket_type = ticket_type
        self.product_name = product_name
        self.price = price
        self.payment_method = payment_method
        self.notes = notes
        self.question = question
        self.lang = lang
        self.close_button.label = TRANSLATIONS[lang]["close_button"]

    @discord.ui.button(label="🔒 إغلاق التذكرة", style=discord.ButtonStyle.danger, custom_id="btn_close")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()

        guild = interaction.guild
        channel = interaction.channel
        cfg = load_config()

        log_channel = get_log_channel(guild)

        try:
            opener = await guild.fetch_member(self.opener_id)
            opener_str = opener.mention
        except Exception:
            opener_str = f"<@{self.opener_id}>"

        transcript_url = None
        if cfg.get("transcript_enabled", True) and log_channel:
            try:
                file_path = await generate_transcript(channel)
                transcript_msg = await log_channel.send(file=discord.File(file_path, filename=f"transcript-{channel.name}.html"))
                if transcript_msg.attachments:
                    transcript_url = transcript_msg.attachments[0].url
                os.remove(file_path)
            except Exception as e:
                print(f"⚠️ فشل إنشاء السجل: {e}")

        embed = discord.Embed(title="📋 ملخص التذكرة المغلقة", color=0xff4444, timestamp=datetime.datetime.now())
        embed.add_field(name="👤 فاتح التذكرة", value=opener_str, inline=True)
        embed.add_field(name="🔒 أغلقها", value=interaction.user.mention, inline=True)
        embed.add_field(name="📁 نوع التذكرة", value=self.ticket_type, inline=True)
        embed.add_field(name="🕐 وقت الإغلاق", value=discord.utils.format_dt(datetime.datetime.now(), "F"), inline=False)

        if self.ticket_type == "منتج":
            embed.add_field(name="📦 المنتج", value=self.product_name or "—", inline=True)
            embed.add_field(name="💰 السعر", value=self.price or "—", inline=True)
            embed.add_field(name="💳 طريقة الدفع", value=self.payment_method or "—", inline=True)
            if self.notes:
                embed.add_field(name="📝 ملاحظات", value=self.notes, inline=False)
        elif self.ticket_type == "سؤال":
            embed.add_field(name="💬 السؤال", value=self.question or "—", inline=False)

        embed.set_footer(text=f"قناة: {channel.name}")

        log_view = None
        if transcript_url:
            log_view = View()
            log_view.add_item(Button(label="📄 عرض المحادثة كاملة", style=discord.ButtonStyle.link, url=transcript_url))

        if log_channel:
            await log_channel.send(embed=embed, view=log_view)

        if self.opener_id in user_tickets:
            del user_tickets[self.opener_id]
        ticket_language.pop(channel.id, None)

        await channel.send(TRANSLATIONS[self.lang]["ticket_closing_msg"])
        await asyncio.sleep(5)
        await channel.delete(reason=f"تذكرة مغلقة بواسطة {interaction.user}")


# ─────────────────────────────────────────
# View: زر فتح تذكرة (الرسالة الرئيسية)
# ─────────────────────────────────────────
class OpenTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 افتح تذكرة", style=discord.ButtonStyle.success, custom_id="open_ticket_main")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user
        cfg = load_config()

        if user.id in user_tickets:
            existing = guild.get_channel(user_tickets[user.id])
            if existing:
                await interaction.response.send_message(f"❌ عندك تذكرة مفتوحة بالفعل! {existing.mention}", ephemeral=True)
                return
            else:
                del user_tickets[user.id]

        allowed, current_count = can_open_ticket(user.id)
        if not allowed:
            await interaction.response.send_message(
                f"❌ لقد وصلت للحد الأقصى المسموح به من التذاكر اليوم ({cfg['max_tickets_per_day']} تذاكر). حاول غداً 🙏",
                ephemeral=True
            )
            return

        category = guild.get_channel(cfg["category_id"])

        ticket_name = f"ticket-{user.name}".lower().replace(" ", "-")[:80]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=ticket_name, category=category, overwrites=overwrites,
            topic=f"تذكرة خاصة بـ {user.name} | ID: {user.id}"
        )

        user_tickets[user.id] = ticket_channel.id
        register_ticket_open(user.id)

        lang_embed = discord.Embed(
            title="🌐 اختر لغتك | Choose your language",
            description="الرجاء اختيار اللغة المفضلة لديك 👇\nPlease choose your preferred language 👇",
            color=0xFFD700
        )
        lang_embed.set_footer(text="ARC Raiders Store")

        await ticket_channel.send(content=f"{user.mention}", embed=lang_embed, view=LanguageSelectView(opener_id=user.id))
        await interaction.response.send_message(f"✅ تم إنشاء تذكرتك! {ticket_channel.mention}", ephemeral=True)


# ─────────────────────────────────────────
# Setup panel (إعدادات تفاعلية كاملة)
# ─────────────────────────────────────────
class DailyLimitModal(Modal, title="🔢 تحديد الحد اليومي للتذاكر"):
    limit = TextInput(label="عدد التذاكر المسموح بها يومياً", placeholder="مثال: 5", required=True, max_length=3)

    def __init__(self, setup_view):
        super().__init__()
        self.setup_view = setup_view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.limit.value)
            if value < 1:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ لازم تكتب رقم صحيح أكبر من صفر", ephemeral=True)
            return

        cfg = load_config()
        cfg["max_tickets_per_day"] = value
        save_config(cfg)
        await self.setup_view.refresh(interaction)


class CategorySelect(discord.ui.ChannelSelect):
    def __init__(self, setup_view):
        super().__init__(
            placeholder="📁 اختر الكاتيجوري اللي هتتفتح فيها قنوات التذاكر...",
            channel_types=[discord.ChannelType.category],
            custom_id="category_select",
            row=0
        )
        self.setup_view = setup_view

    async def callback(self, interaction: discord.Interaction):
        cfg = load_config()
        cfg["category_id"] = self.values[0].id
        save_config(cfg)
        await self.setup_view.refresh(interaction)


class LogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, setup_view):
        super().__init__(
            placeholder="📋 اختر قناة سجل الطلبات (اللي بيوصلها ملخص كل تذكرة)...",
            channel_types=[discord.ChannelType.text],
            custom_id="log_channel_select",
            row=1
        )
        self.setup_view = setup_view

    async def callback(self, interaction: discord.Interaction):
        cfg = load_config()
        ch = self.values[0]
        cfg["log_channel_id"] = ch.id
        cfg["log_channel_name"] = ch.name
        save_config(cfg)
        await self.setup_view.refresh(interaction)


class OrdersChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, setup_view):
        super().__init__(
            placeholder="🧾 اختر روم الطلبات (تظهر فيه كل الطلبات وحالتها)...",
            channel_types=[discord.ChannelType.text],
            custom_id="orders_channel_select",
            row=2
        )
        self.setup_view = setup_view

    async def callback(self, interaction: discord.Interaction):
        cfg = load_config()
        ch = self.values[0]
        cfg["orders_channel_id"] = ch.id
        cfg["orders_channel_name"] = ch.name
        save_config(cfg)
        await self.setup_view.refresh(interaction)


class SetupView(View):
    def __init__(self):
        super().__init__(timeout=600)
        self.add_item(CategorySelect(self))
        self.add_item(LogChannelSelect(self))
        self.add_item(OrdersChannelSelect(self))
        self.update_labels()

    def update_labels(self):
        cfg = load_config()
        self.toggle_transcript.label = (
            "📄 تعطيل تسجيل المحادثة" if cfg.get("transcript_enabled", True) else "📄 تفعيل تسجيل المحادثة"
        )
        self.toggle_transcript.style = (
            discord.ButtonStyle.danger if cfg.get("transcript_enabled", True) else discord.ButtonStyle.success
        )
        self.set_limit.label = f"🔢 الحد اليومي (حالياً: {cfg['max_tickets_per_day']})"

    async def build_embed(self, guild: discord.Guild):
        cfg = load_config()

        category = guild.get_channel(cfg["category_id"]) if cfg.get("category_id") else None
        log_channel = get_log_channel(guild)
        orders_channel = get_orders_channel(guild)

        embed = discord.Embed(title="⚙️ إعدادات نظام التذاكر", color=0x5865F2)
        embed.add_field(name="📁 كاتيجوري التذاكر", value=category.name if category else "❌ غير محدد", inline=True)
        embed.add_field(name="📋 قناة السجل", value=log_channel.mention if log_channel else "❌ غير محدد", inline=True)
        embed.add_field(name="🧾 روم الطلبات", value=orders_channel.mention if orders_channel else "❌ غير محدد", inline=True)
        embed.add_field(name="🔢 الحد اليومي للتذاكر", value=f"{cfg['max_tickets_per_day']} تذاكر/يوم", inline=True)
        embed.add_field(
            name="📄 تسجيل المحادثة الكامل",
            value="✅ مفعّل" if cfg.get("transcript_enabled", True) else "❌ معطّل",
            inline=True
        )
        embed.set_footer(text="اضبط كل الإعدادات، ثم اضغط 'نشر رسالة فتح التذاكر' في القناة اللي تبيها")
        return embed

    async def refresh(self, interaction: discord.Interaction):
        self.update_labels()
        embed = await self.build_embed(interaction.guild)
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="📄 تعطيل تسجيل المحادثة", style=discord.ButtonStyle.danger, row=3)
    async def toggle_transcript(self, interaction: discord.Interaction, button: Button):
        cfg = load_config()
        cfg["transcript_enabled"] = not cfg.get("transcript_enabled", True)
        save_config(cfg)
        await self.refresh(interaction)

    @discord.ui.button(label="🔢 الحد اليومي", style=discord.ButtonStyle.secondary, row=3)
    async def set_limit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DailyLimitModal(self))

    @discord.ui.button(label="🚀 نشر رسالة فتح التذاكر هنا", style=discord.ButtonStyle.success, row=4)
    async def publish(self, interaction: discord.Interaction, button: Button):
        cfg = load_config()
        if not cfg.get("category_id"):
            await interaction.response.send_message("❌ لازم تحدد الكاتيجوري الأول قبل النشر", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎫 نظام تذاكر المتجر | ARC Raiders",
            description=(
                "مرحباً بكم في متجر **ARC Raiders**! 🎮\n\n"
                "اضغط على الزر أدناه لفتح تذكرة خاصة بك\n\n"
                "**يمكنك:**\n"
                "🛒 طلب منتج (سلاح، برنت، غرض...)\n"
                "❓ طرح سؤال على الفريق\n\n"
                f"⚠️ **ملاحظة:** حد أقصى {cfg['max_tickets_per_day']} تذاكر لكل مستخدم يومياً"
            ),
            color=0xFFD700
        )
        embed.set_footer(text="ARC Raiders Store • نظام التذاكر العربي")
        await interaction.channel.send(embed=embed, view=OpenTicketView())
        await interaction.response.send_message("✅ تم نشر رسالة فتح التذاكر بنجاح في هذه القناة!", ephemeral=True)


# ─────────────────────────────────────────
# Events & Commands
# ─────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ البوت شغال: {bot.user}")
    print(f"📡 متصل بـ {len(bot.guilds)} سيرفر")
    bot.add_view(OpenTicketView())
    bot.add_view(OrderStatusView())
    bot.add_view(LanguageSelectView(opener_id=0))

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    """فتح لوحة إعدادات نظام التذاكر الكاملة"""
    view = SetupView()
    embed = await view.build_embed(ctx.guild)
    await ctx.send(embed=embed, view=view)
    await ctx.message.delete()

keep_alive()
bot.run(TOKEN)
