# 🎫 ARC Raiders - نظام التذاكر العربي

## التشغيل محلياً
```bash
pip install -r requirements.txt
DISCORD_BOT_TOKEN=your_token_here python bot.py
```

## 🌐 استضافة مجانية 24/7 على Render.com

### 1. ارفع الملفات على GitHub
- اعمل حساب GitHub مجاني (لو مفيش عندك)
- اعمل Repository جديد (Public أو Private)
- ارفع كل ملفات هذا المجلد فيه

### 2. اعمل حساب على Render.com
- روح [render.com](https://render.com) واعمل حساب (تقدر تسجل بحساب GitHub مباشرة، من غير بطاقة ائتمان)

### 3. أنشئ Web Service جديد
- اضغط **New +** → **Web Service**
- اختار الـ Repository اللي رفعته
- الإعدادات:
  - **Environment:** Python 3
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `python bot.py`
  - **Instance Type:** Free

### 4. ضيف متغير البيئة (Environment Variable)
- من تبويب **Environment** ضيف:
  - Key: `DISCORD_BOT_TOKEN`
  - Value: توكن البوت بتاعك

### 5. Deploy
- اضغط **Create Web Service** وسيبه يشتغل (بياخد دقيقة أو اتنين)
- هيديك رابط زي: `https://your-bot.onrender.com`

### 6. خليه صاحي 24/7 (مهم!)
Render المجاني بيوقف السيرفس لو مافيش زيارات لمدة 15 دقيقة. الحل:
- اعمل حساب مجاني على [UptimeRobot.com](https://uptimerobot.com)
- اعمل **New Monitor** → HTTP(s) → حط رابط Render بتاعك
- خليه يفحص كل **5 دقايق**
- كده البوت هيفضل شغال 24/7 من غير ما ينام أبداً، ومجاناً بالكامل ✅

## الإعداد داخل الديسكورد
في أي قناة اكتب:
```
!setup
```
هتظهر لوحة إعدادات فيها:
- 📁 اختيار كاتيجوري التذاكر
- 📋 اختيار قناة السجل
- 🔢 تحديد الحد اليومي للتذاكر
- 📄 تفعيل/تعطيل تسجيل المحادثة
- 🚀 نشر رسالة "افتح تذكرة"

## الميزات
- ✅ اختيار نوع التذكرة: منتج أو سؤال
- ✅ طرق دفع متعددة (إنستا باي، فودافون كاش، فيزا، باي بال، كريبتو، كليك، موبايلي، STC Pay)
- ✅ حد يومي قابل للتعديل لعدد التذاكر لكل مستخدم
- ✅ أي شخص يقدر يقفل التذكرة
- ✅ ملخص كامل + رابط تسجيل (transcript) HTML أنيق يتبعت لقناة السجل
- ✅ القناة تتحذف تلقائياً بعد الإغلاق
- ✅ كل الإعدادات قابلة للتعديل من `!setup` بدون لمس الكود
