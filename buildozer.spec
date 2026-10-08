[app]

# اسم التطبيق
title = Crypto Alert

# اسم الحزمة
package.name = cryptoalert

# الدومين
package.domain = org.cryptoalert

# ملف التطبيق
source.dir = .

# ملفات المشروع
source.include_exts = py,png,jpg,kv,atlas

# المتطلبات
requirements = python3,kivy,plyer,websocket-client

# إصدار التطبيق
version = 1.0

# اتجاه الشاشة
orientation = portrait

# الصلاحيات
android.permissions = INTERNET,POST_NOTIFICATIONS,FOREGROUND_SERVICE

# الخدمات
# The provided service.py has hard-coded BTC settings and is not launched.
# Background monitoring needs a separate implementation before enabling a service.
# services = CryptoService:service.py

# Android API
android.api = 35

# الحد الأدنى
android.minapi = 24
android.ndk_api = 24

# معماريات Android
android.archs = arm64-v8a,armeabi-v7a

# اسم التطبيق
android.entrypoint = org.kivy.android.PythonActivity

# إظهار سجل الأخطاء
log_level = 2


[buildozer]

# الدليل الذي سيتم وضع ملفات البناء فيه
build_dir = .buildozer

# الدليل النهائي للـ APK
bin_dir = bin

# مستوى السجل
log_level = 2
