# ============================================================
# Crypto Alert
# Binance + CoinGecko
# USD + USDT
# Dynamic Coin Search
# Scrollable Interface
# ============================================================

import json
import threading
import time
import urllib.request
import urllib.error
import urllib.parse

import websocket

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from plyer import notification


class CryptoAlertApp(App):

    def build(self):

        self.price = 0.0
        self.raw_price = 0.0
        self.target_price = None

        self.alert_enabled = False
        self.alert_triggered = False

        self.symbol = "BTCUSDT"
        self.platform = "Binance"
        self.quote_currency = "USD"

        self.ws = None
        self.binance_version = 0

        self.coingecko_running = False
        self.coingecko_version = 0

        self.usdt_to_usd = 1.0
        self.usdt_rate_updated = False

        # Cache for dynamically discovered CoinGecko coins
        self.coin_cache = {}
        self.coin_cache_lock = threading.Lock()

        # ====================================================
        # Scrollable interface
        # ====================================================

        root = BoxLayout(orientation="horizontal")

        scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=12,
            scroll_type=["bars", "content"],
            bar_color=(0.2, 0.65, 1, 1),
            bar_inactive_color=(0.4, 0.4, 0.4, 0.5)
        )

        content = BoxLayout(
            orientation="vertical",
            padding=30,
            spacing=12,
            size_hint_y=None
        )

        content.bind(
            minimum_height=content.setter("height")
        )

        content.add_widget(
            Label(
                text="Crypto Alert",
                font_size=32,
                size_hint_y=None,
                height=65
            )
        )

        content.add_widget(
            Label(
                text="Platform",
                font_size=18,
                size_hint_y=None,
                height=30
            )
        )

        self.platform_box = Spinner(
            text="Binance",
            values=("Binance", "CoinGecko"),
            font_size=20,
            size_hint_y=None,
            height=55
        )

        content.add_widget(self.platform_box)

        content.add_widget(
            Label(
                text="Crypto Symbol / Pair",
                font_size=18,
                size_hint_y=None,
                height=30
            )
        )

        self.symbol_box = TextInput(
            text="BTCUSDT",
            hint_text="Example: BTCUSDT or BTC",
            multiline=False,
            font_size=22,
            size_hint_y=None,
            height=55
        )

        content.add_widget(self.symbol_box)

        # Search button for CoinGecko
        self.search_button = Button(
            text="Search Coin",
            font_size=18,
            size_hint_y=None,
            height=50
        )

        self.search_button.bind(
            on_press=self.search_coin
        )

        content.add_widget(self.search_button)

        self.search_results = Spinner(
            text="Select a search result",
            values=(),
            font_size=16,
            size_hint_y=None,
            height=55
        )

        content.add_widget(self.search_results)

        self.search_results.bind(
            text=self.on_coin_selected
        )

        content.add_widget(
            Label(
                text="Display Currency",
                font_size=18,
                size_hint_y=None,
                height=30
            )
        )

        self.currency_box = Spinner(
            text="USD",
            values=("USD", "USDT"),
            font_size=20,
            size_hint_y=None,
            height=55
        )

        content.add_widget(self.currency_box)

        self.price_label = Label(
            text="BTC/USD\nConnecting...",
            font_size=28,
            size_hint_y=None,
            height=100
        )

        content.add_widget(self.price_label)

        content.add_widget(
            Label(
                text="Target Price (selected currency)",
                font_size=18,
                size_hint_y=None,
                height=30
            )
        )

        self.target_box = TextInput(
            hint_text="Enter target price",
            multiline=False,
            input_filter="float",
            font_size=22,
            size_hint_y=None,
            height=55
        )

        content.add_widget(self.target_box)

        content.add_widget(
            Label(
                text="Alert Condition",
                font_size=18,
                size_hint_y=None,
                height=30
            )
        )

        self.condition_box = Spinner(
            text="Price reaches or goes above",
            values=(
                "Price reaches or goes above",
                "Price reaches or goes below"
            ),
            font_size=16,
            size_hint_y=None,
            height=55
        )

        content.add_widget(self.condition_box)

        self.alert_button = Button(
            text="Enable Alert",
            font_size=22,
            size_hint_y=None,
            height=60
        )

        self.alert_button.bind(
            on_press=self.enable_alert
        )

        content.add_widget(self.alert_button)

        self.refresh_button = Button(
            text="Refresh Now",
            font_size=20,
            size_hint_y=None,
            height=55
        )

        self.refresh_button.bind(
            on_press=self.refresh_price
        )

        content.add_widget(self.refresh_button)

        self.status_label = Label(
            text="Starting...",
            font_size=18,
            size_hint_y=None,
            height=90
        )

        content.add_widget(self.status_label)

        scroll.add_widget(content)
        root.add_widget(scroll)

        # Start USDT/USD conversion updater
        threading.Thread(
            target=self.update_usdt_rate,
            daemon=True
        ).start()

        # Initial Binance connection
        threading.Thread(
            target=self.start_binance,
            args=("BTCUSDT",),
            daemon=True
        ).start()

        return root

    # ========================================================
    # HTTP JSON helper
    # ========================================================

    def get_json(self, url, timeout=15):

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "CryptoAlert/1.0",
                "Accept": "application/json"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=timeout
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    # ========================================================
    # Dynamic CoinGecko search
    # ========================================================

    def search_coin(self, button):

        query = self.symbol_box.text.strip()

        if not query:
            self.status_label.text = "Enter a coin name or symbol"
            return

        self.status_label.text = "Searching CoinGecko..."

        threading.Thread(
            target=self.search_coin_worker,
            args=(query,),
            daemon=True
        ).start()

    def search_coin_worker(self, query):

        try:

            url = (
                "https://api.coingecko.com/api/v3/search?"
                + urllib.parse.urlencode({
                    "query": query
                })
            )

            data = self.get_json(url)

            coins = data.get("coins", [])

            # Match exact symbols first, then partial matches.
            query_lower = query.lower()

            exact = [
                coin for coin in coins
                if coin.get("symbol", "").lower() == query_lower
            ]

            others = [
                coin for coin in coins
                if coin not in exact
            ]

            results = (exact + others)[:30]

            if not results:
                Clock.schedule_once(
                    lambda dt: self.show_search_results(
                        [],
                        "No matching coins found"
                    )
                )
                return

            with self.coin_cache_lock:
                for coin in results:
                    self.coin_cache[coin["id"]] = coin

            Clock.schedule_once(
                lambda dt, items=results:
                self.show_search_results(
                    items,
                    "Choose a coin"
                )
            )

        except Exception as error:

            print("CoinGecko search error:", error)

            Clock.schedule_once(
                lambda dt:
                self.show_status("Coin search failed")
            )

    def show_search_results(self, coins, message):

        self.search_result_map = {}

        values = []

        for coin in coins:

            coin_id = coin.get("id", "")
            name = coin.get("name", "Unknown")
            symbol = coin.get("symbol", "").upper()

            # ID is included to distinguish coins with identical symbols.
            label = "{} ({}) - {}".format(
                name,
                symbol,
                coin_id
            )

            self.search_result_map[label] = coin
            values.append(label)

        self.search_results.values = tuple(values)

        if values:
            self.search_results.text = values[0]
            self.status_label.text = (
                "Found {} coins. Select the correct result.".format(
                    len(values)
                )
            )
            self.on_coin_selected(
                self.search_results,
                values[0]
            )
        else:
            self.search_results.text = message
            self.status_label.text = message

    def on_coin_selected(self, spinner, text):

        coin = getattr(
            self,
            "search_result_map",
            {}
        ).get(text)

        if not coin:
            return

        # Store the real CoinGecko ID.
        self.selected_coin_id = coin.get("id")

        symbol = coin.get("symbol", "").upper()

        if symbol:
            self.symbol_box.text = symbol

        self.status_label.text = (
            "Selected: {} ({})".format(
                coin.get("name", ""),
                self.selected_coin_id
            )
        )

    # ========================================================
    # USDT/USD conversion
    # ========================================================

    def update_usdt_rate(self):

        while True:

            try:

                url = (
                    "https://api.coingecko.com/api/v3/simple/price?"
                    + urllib.parse.urlencode({
                        "ids": "tether",
                        "vs_currencies": "usd"
                    })
                )

                data = self.get_json(url)

                rate = float(data["tether"]["usd"])

                if rate > 0:
                    self.usdt_to_usd = rate
                    self.usdt_rate_updated = True

                    print("USDT/USD rate:", rate)

            except Exception as error:
                print("USDT conversion error:", error)

            time.sleep(60)

    # ========================================================
    # Enable alert
    # ========================================================

    def enable_alert(self, button):

        symbol = self.symbol_box.text.upper().strip()
        symbol = symbol.replace("/", "").replace(" ", "")

        if not symbol:
            self.status_label.text = "Please enter a coin symbol"
            return

        try:
            target = float(self.target_box.text)
        except ValueError:
            self.status_label.text = "Enter a valid target price"
            return

        if target <= 0:
            self.status_label.text = "Price must be greater than 0"
            return

        platform = self.platform_box.text
        quote = self.currency_box.text.upper()

        if platform == "Binance":

            # Binance needs an actual trading pair.
            if not any(
                symbol.endswith(suffix)
                for suffix in (
                    "USDT", "USDC", "BUSD", "FDUSD",
                    "BTC", "ETH", "BNB"
                )
            ):
                self.status_label.text = (
                    "Enter a Binance trading pair, e.g. BTCUSDT"
                )
                return

        else:

            coin_id = self.get_selected_coin_id(symbol)

            if not coin_id:
                self.status_label.text = (
                    "Search for the coin and select the correct result first"
                )
                return

            self.selected_coin_id = coin_id

        self.symbol = symbol
        self.target_price = target
        self.platform = platform
        self.quote_currency = quote

        self.alert_enabled = True
        self.alert_triggered = False

        self.stop_coingecko()
        self.close_binance()

        self.status_label.text = (
            "Connecting...\n"
            + platform
            + "\n"
            + symbol
            + "\nCurrency: "
            + quote
        )

        self.alert_button.text = "Alert Enabled"

        if platform == "Binance":
            self.start_new_binance(symbol)
        else:
            self.start_new_coingecko(symbol)

    def get_selected_coin_id(self, symbol):

        # Prefer the ID explicitly selected in search results.
        coin_id = getattr(self, "selected_coin_id", None)

        if coin_id:
            selected = getattr(
                self,
                "search_result_map",
                {}
            ).get(self.search_results.text)

            if selected and selected.get("id") == coin_id:
                return coin_id

        return None

    # ========================================================
    # Binance connection
    # ========================================================

    def close_binance(self):

        self.binance_version += 1

        ws = self.ws
        self.ws = None

        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    def start_new_binance(self, symbol):

        self.close_binance()
        version = self.binance_version

        threading.Thread(
            target=self.start_binance,
            args=(symbol, version),
            daemon=True
        ).start()

    def start_binance(self, symbol, version=None):

        if version is None:
            version = self.binance_version

        symbol = symbol.lower()

        url = (
            "wss://stream.binance.com:9443/ws/"
            + symbol
            + "@ticker"
        )

        def on_message(ws, message):

            if version != self.binance_version:
                return

            try:
                data = json.loads(message)

                if "c" not in data:
                    return

                raw_price = float(data["c"])

                Clock.schedule_once(
                    lambda dt, p=raw_price, v=version:
                    self.handle_binance_price(p, v)
                )

            except Exception as error:
                print("Binance message error:", error)

        def on_open(ws):
            print("Binance connected:", symbol.upper())

        def on_error(ws, error):
            print("Binance error:", error)

        def on_close(ws, code, message):
            print("Binance connection closed")

        try:

            ws = websocket.WebSocketApp(
                url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            if version != self.binance_version:
                ws.close()
                return

            self.ws = ws
            ws.run_forever()

        except Exception as error:
            print("Binance connection error:", error)

    def handle_binance_price(self, raw_price, version):

        if version != self.binance_version:
            return

        if self.platform != "Binance":
            return

        self.raw_price = raw_price

        if self.symbol.endswith("USDT"):

            if self.quote_currency == "USD":

                if not self.usdt_rate_updated:
                    self.status_label.text = (
                        "Waiting for USDT/USD conversion rate"
                    )
                    return

                display_price = raw_price * self.usdt_to_usd

            else:
                display_price = raw_price

        elif self.symbol.endswith("USDC"):
            # USDC is close to USD, but not guaranteed to equal it.
            if self.quote_currency == "USD":
                display_price = raw_price
            else:
                if not self.usdt_rate_updated:
                    return
                display_price = raw_price / self.usdt_to_usd

        else:
            display_price = raw_price

        self.show_price(display_price)

    # ========================================================
    # CoinGecko lifecycle
    # ========================================================

    def stop_coingecko(self):

        self.coingecko_running = False
        self.coingecko_version += 1

    def start_new_coingecko(self, symbol):

        self.stop_coingecko()
        self.coingecko_version += 1

        version = self.coingecko_version
        self.coingecko_running = True

        threading.Thread(
            target=self.start_coingecko,
            args=(symbol, version),
            daemon=True
        ).start()

    # ========================================================
    # Fetch CoinGecko price
    # Fetch USD and convert USD -> USDT if needed
    # ========================================================

    def fetch_coingecko_price(self, coin_id, quote_currency):

        url = (
            "https://api.coingecko.com/api/v3/simple/price?"
            + urllib.parse.urlencode({
                "ids": coin_id,
                "vs_currencies": "usd"
            })
        )

        data = self.get_json(url)

        try:
            usd_price = float(data[coin_id]["usd"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(
                "USD price not found for " + coin_id
            )

        quote = quote_currency.upper()

        if quote == "USD":
            return usd_price

        if quote == "USDT":

            if not self.usdt_rate_updated:
                raise ValueError(
                    "Waiting for USDT/USD conversion rate"
                )

            if self.usdt_to_usd <= 0:
                raise ValueError(
                    "Invalid USDT/USD conversion rate"
                )

            return usd_price / self.usdt_to_usd

        raise ValueError("Unsupported currency: " + quote)

    def start_coingecko(self, symbol, version):

        coin_id = getattr(self, "selected_coin_id", None)

        if not coin_id:
            Clock.schedule_once(
                lambda dt, v=version:
                self.show_status_if_current(
                    "Search for and select a coin first",
                    v
                )
            )
            return

        quote_currency = self.quote_currency

        print("CoinGecko ID:", coin_id)
        print("Display currency:", quote_currency)

        while True:

            if version != self.coingecko_version:
                return

            if not self.coingecko_running:
                return

            if self.platform != "CoinGecko":
                return

            if self.symbol != symbol:
                return

            if self.quote_currency != quote_currency:
                return

            try:

                price = self.fetch_coingecko_price(
                    coin_id,
                    quote_currency
                )

                Clock.schedule_once(
                    lambda dt, p=price, v=version, q=quote_currency:
                    self.show_coingecko_price_if_current(
                        p, v, q
                    )
                )

                wait_time = 30

            except urllib.error.HTTPError as error:

                print("CoinGecko HTTP error:", error.code)
                wait_time = 60 if error.code == 429 else 30

            except Exception as error:

                print("CoinGecko error:", error)
                wait_time = 30

            for _ in range(wait_time):

                if version != self.coingecko_version:
                    return

                if not self.coingecko_running:
                    return

                if self.platform != "CoinGecko":
                    return

                if self.symbol != symbol:
                    return

                if self.quote_currency != quote_currency:
                    return

                time.sleep(1)

    # ========================================================
    # Manual refresh
    # ========================================================

    def refresh_price(self, button):

        if self.platform != "CoinGecko":
            self.status_label.text = (
                "Refresh Now is for CoinGecko"
            )
            return

        coin_id = getattr(self, "selected_coin_id", None)

        if not coin_id:
            self.status_label.text = (
                "Search for and select a coin first"
            )
            return

        quote_currency = self.currency_box.text.upper()

        self.status_label.text = "Refreshing..."

        threading.Thread(
            target=self.manual_coingecko_request,
            args=(
                self.symbol,
                coin_id,
                quote_currency
            ),
            daemon=True
        ).start()

    def manual_coingecko_request(
        self,
        symbol,
        coin_id,
        quote_currency
    ):

        try:

            price = self.fetch_coingecko_price(
                coin_id,
                quote_currency
            )

            Clock.schedule_once(
                lambda dt, p=price, s=symbol, q=quote_currency:
                self.show_manual_price(p, s, q)
            )

        except urllib.error.HTTPError as error:

            message = (
                "Too many requests. Wait and try again."
                if error.code == 429
                else "HTTP error: " + str(error.code)
            )

            Clock.schedule_once(
                lambda dt, m=message:
                self.show_status(m)
            )

        except Exception as error:

            print("Manual CoinGecko error:", error)

            Clock.schedule_once(
                lambda dt, e=str(error):
                self.show_status(
                    "Could not update price: " + e
                )
            )

    # ========================================================
    # Display helpers
    # ========================================================

    def show_coingecko_price_if_current(
        self,
        price,
        version,
        quote_currency
    ):

        if version != self.coingecko_version:
            return

        if self.platform != "CoinGecko":
            return

        if quote_currency != self.quote_currency:
            return

        self.show_price(price)

    def show_manual_price(
        self,
        price,
        symbol,
        quote_currency
    ):

        if self.platform != "CoinGecko":
            return

        if self.symbol != symbol:
            return

        if self.quote_currency != quote_currency:
            return

        self.show_price(price)
        self.show_status("Price updated")

    def show_price(self, price):

        self.price = price

        if self.platform == "CoinGecko":

            coin = getattr(
                self,
                "search_result_map",
                {}
            ).get(
                getattr(self, "search_results", None).text
                if getattr(self, "search_results", None)
                else ""
            )

            base_symbol = (
                coin.get("symbol", self.symbol).upper()
                if coin
                else self.symbol
            )

            display_symbol = (
                base_symbol + "/" + self.quote_currency
            )

            quote = self.quote_currency

        else:

            symbol = self.symbol

            if symbol.endswith("USDT"):
                base_symbol = symbol[:-4]
                display_symbol = base_symbol + "/" + self.quote_currency
                quote = self.quote_currency

            elif symbol.endswith("USDC"):
                display_symbol = symbol[:-4] + "/USDC"
                quote = "USDC"

            elif symbol.endswith("BUSD"):
                display_symbol = symbol[:-4] + "/BUSD"
                quote = "BUSD"

            else:
                display_symbol = symbol
                quote = self.quote_currency

        self.price_label.text = (
            display_symbol
            + "\n"
            + quote
            + " "
            + f"{price:,.8f}"
        )

        self.check_alert(price)

    # ========================================================
    # Alert check
    # ========================================================

    def check_alert(self, price):

        if not self.alert_enabled:
            return

        if self.alert_triggered:
            return

        if self.target_price is None:
            return

        if self.condition_box.text == "Price reaches or goes above":

            if price >= self.target_price:
                self.trigger_alert()

        else:

            if price <= self.target_price:
                self.trigger_alert()

    # ========================================================
    # Trigger alert
    # ========================================================

    def trigger_alert(self):

        self.alert_enabled = False
        self.alert_triggered = True

        self.stop_coingecko()
        self.close_binance()

        self.status_label.text = "PRICE ALERT!"
        self.alert_button.text = "New Alert"

        try:
            notification.notify(
                title="Crypto Alert",
                message=f"{self.symbol}: {self.price:,.8f} {self.quote_currency} "
                        f"(target: {self.target_price:,.8f})",
                app_name="Crypto Alert",
                timeout=10,
            )
        except Exception as error:
            print("Android notification error:", error)

        print()
        print("==========================")
        print("PRICE ALERT!")
        print("Coin:", self.symbol)
        print("Platform:", self.platform)
        print("Currency:", self.quote_currency)
        print("Price:", self.price)
        print("Target:", self.target_price)
        print("==========================")

    # ========================================================
    # Status
    # ========================================================

    def show_status(self, message):
        self.status_label.text = message

    def show_status_if_current(self, message, version):

        if version != self.coingecko_version:
            return

        if self.platform != "CoinGecko":
            return

        self.show_status(message)


# ============================================================
# Run application
# ============================================================

if __name__ == "__main__":
    CryptoAlertApp().run()