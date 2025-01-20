import requests

from prod.config import ChartImgConfig
from prod.logger_output import log_error


def fetch_chart_as_url(api_key, layout_id, session_id, session_sign):
    api_url = f'https://api.chart-img.com/v2/tradingview/layout-chart/storage/{layout_id}'
    params = {
        'width': 800,
        'height': 600,
        'resetZoom': 'true',
        'zoomOut': 1,
        'watermarkOpacity': 0.5
    }
    headers = {
        'x-api-key': api_key,
        'tradingview-session-id': session_id,
        'tradingview-session-id-sign': session_sign
    }

    response = requests.post(api_url, params=params, headers=headers)
    if response.status_code == 200:
        return response.json()['url']
    else:
        log_error(f"Error fetching chart: {response.status_code}, {response.text}")
        return None

def fetch_chart():
    if not ChartImgConfig.enabled:
        return None

    return fetch_chart_as_url(ChartImgConfig.API_KEY, ChartImgConfig.layout_id,
                                ChartImgConfig.session_id, ChartImgConfig.session_sign)

