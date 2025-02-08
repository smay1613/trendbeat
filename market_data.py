import websocket
import json
import threading

from config import BacktestConfig
from logger_output import log_error, log


class PriceTracker:
    def __init__(self):
        self.symbol = BacktestConfig.symbol.lower()
        self.url = f"wss://fstream.binance.com/ws/{self.symbol}@markPrice"
        self.ws = None
        self.running = False
        self.price = None
        self.lock = threading.Lock()
        self._connect()

    def _on_message(self, ws, message):
        data = json.loads(message)
        if "p" in data:
            price = float(data['p'])
            with self.lock:
                self.price = price

    def _on_close(self, ws, close_status_code, close_msg):
        log_error(f"Price websocket connection closed: {close_status_code} | {close_msg}")
        self._connect()

    def _on_error(self, ws, error):
        log_error(f"Error in price websocket: {error}")

    def _on_open(self, ws):
        log(f"{self.symbol} websocket connection opened")

    def _connect(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        self.running = True
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def start(self):
        if not self.running:
            self._connect()

    def stop(self):
        if self.running:
            self.ws.close()
            self.running = False

    def get_price(self):
        with self.lock:
            return self.price


price_tracker = PriceTracker()
