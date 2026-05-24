from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from weather.core.database import get_session
from weather.models import cities
from weather.models.weather_forecast import WeatherForecast
from weather.schemas import schemas

router = APIRouter()


@router.get(
    path='/',
    status_code=status.HTTP_200_OK,
    response_model=List[schemas.CityResponse],
    summary='Listar cidades',
)
async def get_cities():
    return cities.PLACES


@router.get(
    path='/{slug}/forecast/',
    status_code=status.HTTP_200_OK,
    summary='Obter previsão do tempo para uma cidade',
)
async def get_city_forecast(
    slug: str,
    days: int = Query(default=7, ge=1, le=7),
    db: AsyncSession = Depends(get_session),
):

    forecast_subquery = (
        select(WeatherForecast)
        .where(WeatherForecast.slug == slug)
        .order_by(WeatherForecast.forecast_date)
        .limit(days)
        .subquery()
    )

    query = select(
        func.avg(
            (forecast_subquery.c.temperature_max + forecast_subquery.c.temperature_min)
            / 2
        ).label('avg_temp'),
        func.min(forecast_subquery.c.temperature_min).label('min_temp'),
        func.max(forecast_subquery.c.temperature_max).label('max_temp'),
        func.sum(forecast_subquery.c.precipitation_sum).label('total_precipitation'),
        func.avg(forecast_subquery.c.relative_humidity_2m_max).label('avg_humidity'),
    )

    result = await db.execute(query)

    data = result.one_or_none()

    if not data or data.avg_temp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Cidade sem previsões encontradas'
        )

    hottest_day_query = (
        select(forecast_subquery.c.forecast_date, forecast_subquery.c.temperature_max)
        .order_by(forecast_subquery.c.temperature_max.desc())
        .limit(1)
    )

    hottest_result = await db.execute(hottest_day_query)

    hottest_day = hottest_result.one()

    avg_temp = round(float(data.avg_temp), 2)

    avg_humidity = round(float(data.avg_humidity), 2)

    total_precipitation = round(float(data.total_precipitation), 2)

    comfort_index = (
        100
        - abs(avg_temp - 22) * 3
        - (avg_humidity - 60) * 0.4
        - total_precipitation * 0.5
    )

    comfort_index = round(max(0, min(100, comfort_index)), 2)

    return {
        'city': slug.replace('-', ' ').title(),
        'slug': slug,
        'period_days': days,
        'temperature': {
            'average': avg_temp,
            'min': round(float(data.min_temp), 2),
            'max': round(float(data.max_temp), 2),
        },
        'precipitation_total': total_precipitation,
        'humidity_average': avg_humidity,
        'hottest_day': {
            'date': hottest_day.forecast_date,
            'temperature': round(float(hottest_day.temperature_max), 2),
        },
        'comfort_index': comfort_index,
    }


@router.get(
    path='/ranking/hottest/',
    status_code=status.HTTP_200_OK,
    summary='Ranking das cidades mais quentes',
)
async def get_hottest_cities(
    limit: int = Query(default=3, ge=1, le=10), db: AsyncSession = Depends(get_session)
):

    query = (
        select(
            WeatherForecast.city,
            WeatherForecast.slug,
            func.avg(WeatherForecast.temperature_max).label('average_temperature'),
        )
        .group_by(WeatherForecast.city, WeatherForecast.slug)
        .order_by(func.avg(WeatherForecast.temperature_max).desc())
        .limit(limit)
    )

    result = await db.execute(query)

    cities = result.all()

    ranking = []

    for index, city in enumerate(cities, start=1):
        ranking.append({
            'position': index,
            'city': city.city,
            'slug': city.slug,
            'average_temperature': round(float(city.average_temperature), 2),
        })

    return {'ranking': ranking, 'total': len(ranking)}


@router.get(
    path='/summary/',
    status_code=status.HTTP_200_OK,
    summary='Resumo geral das cidades',
)
async def get_summary(db: AsyncSession = Depends(get_session)):

    query = select(
        WeatherForecast.city,
        func.avg(WeatherForecast.temperature_max).label('avg_temp'),
        func.sum(WeatherForecast.precipitation_sum).label('total_precipitation'),
        func.avg(WeatherForecast.relative_humidity_2m_max).label('avg_humidity'),
    ).group_by(WeatherForecast.city)

    result = await db.execute(query)

    cities = result.all()

    summary_data = []

    for city in cities:
        avg_temp = round(float(city.avg_temp), 2)

        avg_humidity = round(float(city.avg_humidity), 2)

        total_precipitation = round(float(city.total_precipitation), 2)

        comfort_index = (
            100
            - abs(avg_temp - 22) * 3
            - (avg_humidity - 60) * 0.4
            - total_precipitation * 0.5
        )

        comfort_index = round(max(0, min(100, comfort_index)), 2)

        summary_data.append({
            'city': city.city,
            'avg_temp': avg_temp,
            'total_precipitation': total_precipitation,
            'avg_humidity': avg_humidity,
            'comfort_index': comfort_index,
        })

    hottest_city = max(summary_data, key=lambda x: x['avg_temp'])

    rainiest_city = max(summary_data, key=lambda x: x['total_precipitation'])

    best_comfort_city = max(summary_data, key=lambda x: x['comfort_index'])

    global_avg_temp = round(
        sum(city['avg_temp'] for city in summary_data) / len(summary_data), 2
    )

    global_avg_humidity = round(
        sum(city['avg_humidity'] for city in summary_data) / len(summary_data), 2
    )

    return {
        'hottest_city': {
            'city': hottest_city['city'],
            'average_temperature': hottest_city['avg_temp'],
        },
        'rainiest_city': {
            'city': rainiest_city['city'],
            'total_precipitation': rainiest_city['total_precipitation'],
        },
        'best_comfort_city': {
            'city': best_comfort_city['city'],
            'comfort_index': best_comfort_city['comfort_index'],
        },
        'global_average_temperature': global_avg_temp,
        'global_average_humidity': global_avg_humidity,
        'cities_analyzed': len(summary_data),
    }