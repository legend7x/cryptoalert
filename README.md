# Crypto Alert Android

## إنتاج APK باستخدام GitHub Actions
1. أنشئ مستودع GitHub جديدًا.
2. ارفع محتويات هذا المجلد، مع إبقاء `.github/workflows/build-apk.yml` في مساره.
3. افتح Actions ثم Build Android APK ثم Run workflow.
4. بعد نجاح العملية، افتح التشغيل، ثم Artifacts، وحمّل `crypto-alert-apk`.
5. فك ضغط ملف النتائج وثبّت APK على هاتف Android.

## البناء محليًا على Linux أو Windows WSL2
ثبّت متطلبات Buildozer ثم نفذ `buildozer -v android debug`.

## تنبيهات
- يعمل رصد السعر أثناء تشغيل التطبيق واتصاله بالإنترنت.
- أضفنا إشعار Android مع طلب إذن الإشعارات.
- خدمة الخلفية الموجودة في `service.py` تجريبية ومثبتة على BTC بقيمة 110000 ولم نفعّلها لأنها لا تتصل بإعدادات الواجهة.
- لم يُجرَ بناء APK أو اختبار على هاتف فعلي في هذه البيئة.
