import asyncio
from datetime import datetime

from weather.core.database import AsyncSessionLocal
from weather.models.cities import PLACES
from weather.models.weather_forecast import WeatherForecast
from weather.services.open_meteo import OpenMeteo


async def seed_database():

    service = OpenMeteo()

    async with AsyncSessionLocal() as db:
        for city in PLACES:
            data = await service.get_weather(
                latitude=city['latitude'], longitude=city['longitude']
            )

            daily = data['daily']

            for i in range(len(daily['time'])):
                weather = WeatherForecast(
                    city=city['name'],
                    slug=city['slug'],
                    forecast_date=datetime.strptime(
                        daily['time'][i], '%Y-%m-%d'
                    ).date(),
                    temperature_max=daily['temperature_2m_max'][i],
                    temperature_min=daily['temperature_2m_min'][i],
                    precipitation_sum=daily['precipitation_sum'][i],
                    relative_humidity_2m_max=daily['relative_humidity_2m_max'][i],
                )

                db.add(weather)

        await db.commit()

    print('Banco populado com sucesso.')


if __name__ == '__main__':
    asyncio.run(seed_database())
