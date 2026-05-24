import httpx


class OpenMeteo:
    def __init__(self):

        self._base_url = 'https://api.open-meteo.com/v1/forecast'

    async def get_weather(self, latitude: float, longitude: float):

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=self._base_url,
                params={
                    'latitude': latitude,
                    'longitude': longitude,
                    'daily': [
                        'temperature_2m_max',
                        'temperature_2m_min',
                        'precipitation_sum',
                        'relative_humidity_2m_max',
                    ],
                    'forecast_days': 7,
                    'timezone': 'America/Sao_Paulo',
                },
                timeout=10,
            )

            response.raise_for_status()

            return response.json()
