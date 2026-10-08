import json
import os
import time

import websocket
from plyer import notification


# =========================================================
# الإعدادات
# =========================================================

TARGET_PRICE = 110000.0

# اختر:
# "above"  = عند الوصول للسعر أو تجاوزه
# "below"  = عند الوصول للسعر أو النزول تحته

CONDITION = "above"

CHECK_INTERVAL = 1


# =========================================================
# متغيرات الخدمة
# =========================================================

alert_triggered = False
current_price = 0.0


# =========================================================
# إشعار Android
# =========================================================

def send_notification(price):

    notification.notify(
        title="🚨 Crypto Alert",
        message=(
            f"BTC/USDT وصل إلى "
            f"${price:,.2f}\n"
            f"السعر المستهدف: "
            f"${TARGET_PRICE:,.2f}"
        ),
        app_name="Crypto Alert",
        timeout=10
    )

    print(
        f"ALERT! BTC = ${price:,.2f}"
    )


# =========================================================
# فحص السعر
# =========================================================

def check_price(price):

    global alert_triggered

    if alert_triggered:
        return

    if CONDITION == "above":

        if price >= TARGET_PRICE:

            alert_triggered = True

            send_notification(price)

    elif CONDITION == "below":

        if price <= TARGET_PRICE:

            alert_triggered = True

            send_notification(price)


# =========================================================
# WebSocket
# =========================================================

def on_message(ws, message):

    global current_price

    try:

        data = json.loads(message)

        current_price = float(data["c"])

        print(
            f"BTC/USDT: ${current_price:,.2f}"
        )

        check_price(current_price)

    except Exception as e:

        print(
            "Message error:",
            e
        )


def on_error(ws, error):

    print(
        "WebSocket error:",
        error
    )


def on_close(
    ws,
    close_status_code,
    close_msg
):

    print(
        "WebSocket closed"
    )


# =========================================================
# تشغيل WebSocket
# =========================================================

def start_websocket():

    url = (
        "wss://stream.binance.com:9443/"
        "ws/btcusdt@ticker"
    )

    while True:

        try:

            print(
                "Connecting to Binance..."
            )

            ws = websocket.WebSocketApp(
                url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ws.run_forever()

        except Exception as e:

            print(
                "Connection error:",
                e
            )

        print(
            "Reconnecting in 5 seconds..."
        )

        time.sleep(5)


# =========================================================
# تشغيل الخدمة
# =========================================================

if __name__ == "__main__":

    print(
        "Crypto Alert Service Started"
    )

    start_websocket()