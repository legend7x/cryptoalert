# ============================================================
# Crypto Alert
# Binance + CoinGecko
# ============================================================

import json
import threading
import time
import urllib.request
import urllib.error

import websocket
from plyer import notification

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner


class CryptoAlertApp(App):

    # ========================================================
    # بداية البرنامج
    # ========================================================

    def build(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.POST_NOTIFICATIONS])
        except (ImportError, AttributeError):
            pass

        # السعر الحالي
        self.price = 0.0

        # السعر المستهدف
        self.target_price = None

        # هل التنبيه يعمل؟
        self.alert_enabled = False

        # هل تم تنفيذ التنبيه؟
        self.alert_triggered = False

        # العملة الحالية
        self.symbol = "BTCUSDT"

        # المنصة الحالية
        self.platform = "Binance"

        # اتصال Binance
        self.ws = None

        # ====================================================
        # CoinGecko
        # ====================================================

        # هل CoinGecko يعمل؟
        self.coingecko_running = False

        # رقم المراقب الحالي
        #
        # يستخدم لمنع تشغيل أكثر من Thread
        # قديم في نفس الوقت.
        #
        self.coingecko_version = 0

        # ====================================================
        # إنشاء الواجهة
        # ====================================================

        layout = BoxLayout(
            orientation="vertical",
            padding=30,
            spacing=12
        )

        # ====================================================
        # العنوان
        # ====================================================

        title = Label(
            text="Crypto Alert",
            font_size=32,
            size_hint_y=None,
            height=55
        )

        layout.add_widget(title)

        # ====================================================
        # المنصة
        # ====================================================

        layout.add_widget(
            Label(
                text="Platform",
                font_size=18,
                size_hint_y=None,
                height=30
            )
        )

        self.platform_box = Spinner(
            text="Binance",
            values=(
                "Binance",
                "CoinGecko"
            ),
            font_size=20,
            size_hint_y=None,
            height=55
        )

        layout.add_widget(
            self.platform_box
        )

        # ====================================================
        # العملة
        # ====================================================

        layout.add_widget(
            Label(
                text="Crypto pair",
                font_size=18,
                size_hint_y=None,
                height=30
            )
        )

        self.symbol_box = TextInput(
            text="BTCUSDT",
            hint_text="Example: BTCUSDT",
            multiline=False,
            font_size=22,
            size_hint_y=None,
            height=55
        )

        layout.add_widget(
            self.symbol_box
        )

        # ====================================================
        # السعر الحالي
        # ====================================================

        self.price_label = Label(
            text="BTC/USDT\nConnecting...",
            font_size=28
        )

        layout.add_widget(
            self.price_label
        )

        # ====================================================
        # السعر المستهدف
        # ====================================================

        self.target_box = TextInput(
            hint_text="Target price",
            multiline=False,
            input_filter="float",
            font_size=22,
            size_hint_y=None,
            height=55
        )

        layout.add_widget(
            self.target_box
        )

        # ====================================================
        # نوع التنبيه
        # ====================================================

        self.condition_box = Spinner(
            text="Price reaches or goes above",
            values=(
                "Price reaches or goes above",
                "Price reaches or goes below"
            ),
            font_size=18,
            size_hint_y=None,
            height=55
        )

        layout.add_widget(
            self.condition_box
        )

        # ====================================================
        # زر تشغيل التنبيه
        # ====================================================

        self.alert_button = Button(
            text="Enable Alert",
            font_size=22,
            size_hint_y=None,
            height=60
        )

        self.alert_button.bind(
            on_press=self.enable_alert
        )

        layout.add_widget(
            self.alert_button
        )

        # ====================================================
        # زر التحديث اليدوي
        # ====================================================

        self.refresh_button = Button(
            text="Refresh Now",
            font_size=20,
            size_hint_y=None,
            height=55
        )

        self.refresh_button.bind(
            on_press=self.refresh_price
        )

        layout.add_widget(
            self.refresh_button
        )

        # ====================================================
        # الحالة
        # ====================================================

        self.status_label = Label(
            text="No alert",
            font_size=18
        )

        layout.add_widget(
            self.status_label
        )

        # ====================================================
        # تشغيل Binance عند فتح البرنامج
        # ====================================================

        thread = threading.Thread(
            target=self.start_binance,
            args=("BTCUSDT",),
            daemon=True
        )

        thread.start()

        return layout

    # ========================================================
    # تفعيل التنبيه
    # ========================================================

    def enable_alert(self, button):

        # ----------------------------------------------------
        # قراءة العملة
        # ----------------------------------------------------

        symbol = self.symbol_box.text.upper()

        symbol = symbol.replace(
            " ",
            ""
        )

        symbol = symbol.replace(
            "/",
            ""
        )

        if symbol == "":

            self.status_label.text = (
                "Please enter a crypto pair"
            )

            return

        # ----------------------------------------------------
        # قراءة السعر المستهدف
        # ----------------------------------------------------

        try:

            target = float(
                self.target_box.text
            )

        except ValueError:

            self.status_label.text = (
                "Please enter a correct price"
            )

            return

        if target <= 0:

            self.status_label.text = (
                "Price must be greater than 0"
            )

            return

        # ----------------------------------------------------
        # قراءة المنصة
        # ----------------------------------------------------

        platform = (
            self.platform_box.text
        )

        # ----------------------------------------------------
        # حفظ البيانات
        # ----------------------------------------------------

        self.symbol = symbol

        self.target_price = target

        self.platform = platform

        self.alert_enabled = True

        self.alert_triggered = False

        # ====================================================
        # إيقاف الاتصالات القديمة
        # ====================================================

        self.stop_coingecko()

        self.close_binance()

        # ====================================================
        # تحديث الحالة
        # ====================================================

        self.status_label.text = (
            "Connecting...\n"
            + platform
            + "\n"
            + symbol
        )

        self.alert_button.text = (
            "Alert Enabled"
        )

        # ====================================================
        # تشغيل Binance
        # ====================================================

        if platform == "Binance":

            thread = threading.Thread(
                target=self.start_binance,
                args=(symbol,),
                daemon=True
            )

            thread.start()

        # ====================================================
        # تشغيل CoinGecko
        # ====================================================

        else:

            self.start_new_coingecko(
                symbol
            )

    # ========================================================
    # إغلاق Binance
    # ========================================================

    def close_binance(self):

        if self.ws is not None:

            try:

                self.ws.close()

            except Exception:
                pass

            self.ws = None

    # ========================================================
    # إيقاف CoinGecko
    # ========================================================

    def stop_coingecko(self):

        self.coingecko_running = False

        # تغيير الرقم يجعل أي Thread قديم يتوقف
        self.coingecko_version += 1

    # ========================================================
    # تشغيل CoinGecko جديد
    # ========================================================

    def start_new_coingecko(
        self,
        symbol
    ):

        # أولًا نوقف القديم
        self.stop_coingecko()

        # نزيد الرقم
        self.coingecko_version += 1

        # حفظ رقم هذا Thread
        version = self.coingecko_version

        # تشغيل CoinGecko
        self.coingecko_running = True

        thread = threading.Thread(
            target=self.start_coingecko,
            args=(
                symbol,
                version
            ),
            daemon=True
        )

        thread.start()

    # ========================================================
    # Binance
    # ========================================================

    def start_binance(
        self,
        symbol
    ):

        symbol = symbol.lower()

        url = (
            "wss://stream.binance.com:9443/"
            "ws/"
            + symbol
            + "@ticker"
        )

        print()
        print(
            "Connecting to Binance..."
        )
        print(
            "Symbol:",
            symbol
        )
        print()

        try:

            ws = websocket.WebSocketApp(

                url,

                on_open=self.binance_connected,

                on_message=self.binance_message,

                on_error=self.binance_error,

                on_close=self.binance_closed
            )

            self.ws = ws

            ws.run_forever()

        except Exception as error:

            print(
                "Binance error:",
                error
            )

    # ========================================================
    # Binance - تم الاتصال
    # ========================================================

    def binance_connected(
        self,
        ws
    ):

        print(
            "Binance connected!"
        )

    # ========================================================
    # Binance - رسالة جديدة
    # ========================================================

    def binance_message(
        self,
        ws,
        message
    ):

        try:

            data = json.loads(
                message
            )

            if "c" not in data:

                return

            price = float(
                data["c"]
            )

            Clock.schedule_once(
                lambda dt, p=price:
                self.show_price(p)
            )

        except Exception as error:

            print(
                "Binance message error:",
                error
            )

    # ========================================================
    # Binance - خطأ
    # ========================================================

    def binance_error(
        self,
        ws,
        error
    ):

        print(
            "Binance error:",
            error
        )

    # ========================================================
    # Binance - إغلاق
    # ========================================================

    def binance_closed(
        self,
        ws,
        code,
        message
    ):

        print(
            "Binance connection closed"
        )

    # ========================================================
    # CoinGecko
    # ========================================================

    def start_coingecko(
        self,
        symbol,
        version
    ):

        # ====================================================
        # تحويل BTCUSDT إلى bitcoin
        # ====================================================

        coin_id = self.get_coin_id(
            symbol
        )

        if coin_id is None:

            Clock.schedule_once(
                lambda dt:
                self.show_status(
                    "Coin is not supported"
                )
            )

            return

        print()
        print(
            "CoinGecko ID:",
            coin_id
        )
        print(
            "Monitor version:",
            version
        )
        print()

        # ====================================================
        # حلقة CoinGecko
        # ====================================================

        while True:

            # ------------------------------------------------
            # التأكد أن هذا هو Thread الحالي
            # ------------------------------------------------

            if version != self.coingecko_version:

                print(
                    "Old CoinGecko thread stopped"
                )

                return

            # ------------------------------------------------
            # هل CoinGecko يعمل؟
            # ------------------------------------------------

            if not self.coingecko_running:

                return

            # ------------------------------------------------
            # هل المنصة ما زالت CoinGecko؟
            # ------------------------------------------------

            if self.platform != "CoinGecko":

                return

            # ------------------------------------------------
            # هل العملة تغيرت؟
            # ------------------------------------------------

            if self.symbol != symbol:

                return

            # =================================================
            # طلب السعر
            # =================================================

            try:

                url = (
                    "https://api.coingecko.com/api/v3/"
                    "simple/price"
                    "?ids="
                    + coin_id
                    + "&vs_currencies=usd"
                )

                request = urllib.request.Request(

                    url,

                    headers={
                        "User-Agent":
                        "CryptoAlert/1.0"
                    }
                )

                response = urllib.request.urlopen(
                    request,
                    timeout=10
                )

                text = response.read().decode()

                data = json.loads(
                    text
                )

                # ------------------------------------------------
                # استخراج السعر
                # ------------------------------------------------

                price = float(
                    data[coin_id]["usd"]
                )

                print(
                    "CoinGecko price:",
                    price
                )

                # ------------------------------------------------
                # تحديث الشاشة
                # ------------------------------------------------

                Clock.schedule_once(
                    lambda dt, p=price:
                    self.show_price(p)
                )

            # =================================================
            # HTTP 429
            # =================================================

            except urllib.error.HTTPError as error:

                if error.code == 429:

                    print(
                        "CoinGecko: Too many requests."
                    )

                    print(
                        "Waiting before trying again..."
                    )

                    # انتظار أطول عند 429
                    wait_time = 60

                else:

                    print(
                        "CoinGecko HTTP error:",
                        error.code
                    )

                    wait_time = 20

            # =================================================
            # أخطاء أخرى
            # =================================================

            except Exception as error:

                print(
                    "CoinGecko error:",
                    error
                )

                wait_time = 20

            else:

                # إذا نجح الطلب
                wait_time = 20

            # =================================================
            # الانتظار
            #
            # عند النجاح:
            # 20 ثانية
            #
            # عند 429:
            # 60 ثانية
            # =================================================

            print(
                "Next CoinGecko update in",
                wait_time,
                "seconds"
            )

            for second in range(
                wait_time
            ):

                # إذا تغير Thread
                if version != self.coingecko_version:

                    return

                # إذا توقف CoinGecko
                if not self.coingecko_running:

                    return

                # إذا تغيرت المنصة
                if self.platform != "CoinGecko":

                    return

                # إذا تغيرت العملة
                if self.symbol != symbol:

                    return

                time.sleep(1)

    # ========================================================
    # زر Refresh Now
    # ========================================================

    def refresh_price(
        self,
        button
    ):

        # هذا الزر يعمل مع CoinGecko فقط
        if self.platform != "CoinGecko":

            self.status_label.text = (
                "Refresh Now is for CoinGecko"
            )

            return

        # التأكد من وجود العملة
        symbol = self.symbol_box.text.upper()

        symbol = symbol.replace(
            " ",
            ""
        )

        symbol = symbol.replace(
            "/",
            ""
        )

        if symbol == "":

            self.status_label.text = (
                "Please enter a crypto pair"
            )

            return

        # البحث عن CoinGecko ID
        coin_id = self.get_coin_id(
            symbol
        )

        if coin_id is None:

            self.status_label.text = (
                "Coin is not supported"
            )

            return

        # تشغيل طلب واحد فقط
        thread = threading.Thread(
            target=self.manual_coingecko_request,
            args=(
                symbol,
                coin_id
            ),
            daemon=True
        )

        thread.start()

        self.status_label.text = (
            "Refreshing..."
        )

    # ========================================================
    # طلب CoinGecko يدوي
    # ========================================================

    def manual_coingecko_request(
        self,
        symbol,
        coin_id
    ):

        try:

            url = (
                "https://api.coingecko.com/api/v3/"
                "simple/price"
                "?ids="
                + coin_id
                + "&vs_currencies=usd"
            )

            request = urllib.request.Request(

                url,

                headers={
                    "User-Agent":
                    "CryptoAlert/1.0"
                }
            )

            response = urllib.request.urlopen(
                request,
                timeout=10
            )

            text = response.read().decode()

            data = json.loads(
                text
            )

            price = float(
                data[coin_id]["usd"]
            )

            print(
                "Manual CoinGecko price:",
                price
            )

            # تحديث الشاشة
            Clock.schedule_once(
                lambda dt, p=price:
                self.show_price(p)
            )

            Clock.schedule_once(
                lambda dt:
                self.show_status(
                    "Price updated"
                )
            )

        except urllib.error.HTTPError as error:

            if error.code == 429:

                print(
                    "Manual refresh: HTTP 429"
                )

                Clock.schedule_once(
                    lambda dt:
                    self.show_status(
                        "Too many requests. Please wait."
                    )
                )

            else:

                print(
                    "Manual HTTP error:",
                    error.code
                )

        except Exception as error:

            print(
                "Manual CoinGecko error:",
                error
            )

            Clock.schedule_once(
                lambda dt:
                self.show_status(
                    "Could not update price"
                )
            )

    # ========================================================
    # تحويل Binance symbol إلى CoinGecko ID
    # ========================================================

    def get_coin_id(
        self,
        symbol
    ):

        coins = {

            "BTCUSDT": "bitcoin",

            "ETHUSDT": "ethereum",

            "BNBUSDT": "binancecoin",

            "SOLUSDT": "solana",

            "XRPUSDT": "ripple",

            "ADAUSDT": "cardano",

            "DOGEUSDT": "dogecoin",

            "TRXUSDT": "tron",

            "AVAXUSDT": "avalanche-2",

            "SHIBUSDT": "shiba-inu",

            "DOTUSDT": "polkadot",

            "LINKUSDT": "chainlink",

            "LTCUSDT": "litecoin",

            "BCHUSDT": "bitcoin-cash",

            "ATOMUSDT": "cosmos",

            "UNIUSDT": "uniswap",

            "ETCUSDT": "ethereum-classic",

            "XLMUSDT": "stellar",

            "NEARUSDT": "near",

            "APTUSDT": "aptos",

            "ARBUSDT": "arbitrum",

            "OPUSDT": "optimism",

            "SUIUSDT": "sui",

            "PEPEUSDT": "pepe",

            "TONUSDT": "the-open-network",

            "FILUSDT": "filecoin",

            "ICPUSDT": "internet-computer",

            "HBARUSDT": "hedera-hashgraph",

            "AAVEUSDT": "aave",

            "MKRUSDT": "maker",

            "INJUSDT": "injective-protocol",

            "ALGOUSDT": "algorand",

            "VETUSDT": "vechain",

            "EOSUSDT": "eos",

            "SANDUSDT": "the-sandbox",

            "MANAUSDT": "decentraland",

            "AXSUSDT": "axie-infinity",
        }

        return coins.get(
            symbol
        )

    # ========================================================
    # عرض السعر
    # ========================================================

    def show_price(
        self,
        price
    ):

        self.price = price

        # تحويل BTCUSDT إلى BTC/USDT
        display_symbol = self.symbol

        if display_symbol.endswith(
            "USDT"
        ):

            coin_name = display_symbol[
                :-4
            ]

            display_symbol = (
                coin_name
                + "/USDT"
            )

        self.price_label.text = (
            display_symbol
            + "\n$"
            + f"{price:,.8f}"
        )

        # فحص التنبيه
        self.check_alert(
            price
        )

    # ========================================================
    # فحص التنبيه
    # ========================================================

    def check_alert(
        self,
        price
    ):

        # لا يوجد تنبيه
        if not self.alert_enabled:
            return

        # التنبيه حدث بالفعل
        if self.alert_triggered:
            return

        # لا يوجد سعر مستهدف
        if self.target_price is None:
            return

        # ====================================================
        # السعر وصل إلى الهدف أو أعلى
        # ====================================================

        if (
            self.condition_box.text
            ==
            "Price reaches or goes above"
        ):

            if price >= self.target_price:

                self.trigger_alert()

        # ====================================================
        # السعر وصل إلى الهدف أو أقل
        # ====================================================

        else:

            if price <= self.target_price:

                self.trigger_alert()

    # ========================================================
    # تنفيذ التنبيه
    # ========================================================

    def trigger_alert(self):

        self.alert_enabled = False

        self.alert_triggered = True

        # إيقاف CoinGecko
        self.stop_coingecko()

        # إغلاق Binance
        self.close_binance()

        # تغيير الحالة
        self.status_label.text = (
            "🚨 PRICE ALERT!"
        )

        try:
            notification.notify(
                title="Crypto Alert",
                message=f"{self.symbol}: ${self.price:,.8f} (target: ${self.target_price:,.8f})",
                app_name="Crypto Alert",
                timeout=10,
            )
        except Exception as exc:
            print("Notification error:", exc)

        self.alert_button.text = (
            "New Alert"
        )

        print()
        print(
            "=========================="
        )
        print(
            "🚨 PRICE ALERT!"
        )
        print(
            "Coin:",
            self.symbol
        )
        print(
            "Price:",
            self.price
        )
        print(
            "Target:",
            self.target_price
        )
        print(
            "=========================="
        )
        print()

    # ========================================================
    # عرض حالة
    # ========================================================

    def show_status(
        self,
        message
    ):

        self.status_label.text = message


# ============================================================
# تشغيل البرنامج
# ============================================================

if __name__ == "__main__":

    CryptoAlertApp().run()