import base64
import json
import struct
import time
import zlib

import pyotp
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad


class CustomParser:
    @staticmethod
    def parse(data: str):
        """
        Аналог функции parse на Python. Преобразует строку в массив чисел.
        :param data: Входная строка.
        :return: Словарь с ключами 'n' (массив чисел) и 'e' (длина строки).
        """
        length = len(data)
        n = [0] * ((length + 3) // 4)  # Создаём массив для хранения чисел.

        for r in range(length):
            n[r >> 2] |= (ord(data[r]) & 255) << (24 - (r % 4) * 8)

        # Возвращаем данные в формате, эквивалентном new c.init(n, e)
        return {"n": n, "e": length}


# class CoinGlassApi:
def decrypt_coinglass(data, user_header, url):
    """
    Основной процесс дешифровки ответа от API Coinglass.
    :param data: Зашифрованные данные ответа.
    :param user_header: Заголовок 'user' из ответа.
    :param url: URL запроса.
    :return: Расшифрованные данные.
    """
    # Генерация базового ключа
    base_key = base64.b64encode(f"coinglass{url}coinglass".encode("utf-8")).decode("utf-8")[:16]
    processed_key = CustomParser.parse(base_key)
    decrypted_key = (decrypt_and_clean(user_header, processed_key))
    session_key = decrypt_and_clean(data, CustomParser.parse(decrypted_key))

    return session_key


def convert_words_to_bytes(words):
    """
    Converts an array of integers (words) to a byte array.
    :param words: List of integers (4 bytes each).
    :return: Byte array representing the key.
    """
    byte_array = b"".join(struct.pack(">I", word) for word in words)  # Big-endian conversion
    return byte_array

def decrypt_and_clean(t, e):
    """
    Decrypts, decompresses, and cleans the input string.
    :param t: Encrypted Base64 string.
    :param e: Decryption key.
    :return: Decrypted and cleaned string.
    """
    # AES Decryption
    aes_key = convert_words_to_bytes(e['n'])
    cipher = AES.new(aes_key, AES.MODE_ECB)

    # Decode Base64 input and decrypt
    encrypted_data = base64.b64decode(t)
    decrypted_data = cipher.decrypt(encrypted_data)

    unpadded_data = unpad(decrypted_data, AES.block_size)

    # Decompress using zlib
    decompressed_data = zlib.decompress(unpadded_data, wbits=16 + zlib.MAX_WBITS).decode('utf-8')

    return decompressed_data

import requests

url = 'https://capi.coinglass.com/api/index/v2/liqHeatMap'
params = {
    'merge': 'true',
    'symbol': 'Binance_BTCUSDT',
    'interval': '5',
    'limit': '288',
    'data': 'TYcPjrL%2BGhPLjROjGd8wmEkwYPHL5PbnP20%2BoK37blA%3D',
}

headers = {
    'accept': 'application/json',
    'accept-language': 'ru-RU,ru;q=0.9',
    'cache-ts': '1732483284432',
    'dnt': '1',
    'encryption': 'true',
    'language': 'en',
    'origin': 'https://www.coinglass.com',
    'priority': 'u=1, i',
    'referer': 'https://www.coinglass.com/',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}


def generate_encrypted_token():
    current_time = int(time.time())
    # Генерация TOTP (аналог authenticator.generate)
    secret_key = "I65VU7K5ZQL7WB4E"  # Секретный ключ
    totp = pyotp.TOTP(secret_key, interval=30, digits=6, digest="sha1")  # step=30, digits=6
    otp = totp.at(current_time)
    # Комбинирование времени и TOTP
    combined_string = f"{current_time},{otp}"
    # AES ключ
    aes_key = "1f68efd73f8d4921acc0dead41dd39bc"
    aes_key_bytes = CustomParser.parse(aes_key)
    final_key = convert_words_to_bytes(aes_key_bytes['n'])
    cipher = AES.new(final_key, AES.MODE_ECB)

    # Шифрование строки (с выравниванием PKCS7)
    padded_data = pad(combined_string.encode('utf-8'), AES.block_size)
    encrypted_bytes = cipher.encrypt(padded_data)

    # Преобразование зашифрованных данных в строку Base64
    encrypted_string = base64.b64encode(encrypted_bytes).decode('utf-8')
    return encrypted_string

# Пример вызова
if __name__ == "__main__":
    # Пример данных
    params['data'] = generate_encrypted_token()
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        encrypted_data = response.json()['data']
    else:
        print(f"Request failed with status code {response.status_code}: {response.text}")
    request_url = "/api/index/v2/liqHeatMap"
    encrypted_user_header = response.headers.get("user", "HEADERNOTFOUND")
    decrypted = decrypt_coinglass(encrypted_data, encrypted_user_header, request_url)

    # print("Расшифрованные данные:", decrypted)

    decrypted_response_data = json.loads(decrypted)
    heatmap = decrypted_response_data['liq']
    price_array = decrypted_response_data['y']
    i = 0
    liquidation_data = {}
    max_liquidation = 0
    max_liquid_price = 0
    for price in price_array:
        last_liquidation = [int(item[2]) for item in heatmap if str(item[1]) == str(i)]
        i += 1
        # print(f"Last liquidation {price}: {last_liquidation}")
        if not len(last_liquidation):
            continue
        last_liquidation = last_liquidation[-1]
        liquidation_data[price] = last_liquidation
        prev_max_liq = max_liquidation

        max_liquidation = max(max_liquidation, int(last_liquidation))
        if prev_max_liq != max_liquidation:
            max_liquid_price = price

    print(f"Max liquid: {max_liquid_price} = {max_liquidation}")