from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from weather.models.base import Base


class WeatherForecast(Base):
    __tablename__ = 'weather_forecast'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), index=True)
    forecast_date: Mapped[date] = mapped_column(Date)
    temperature_max: Mapped[float] = mapped_column(Numeric(5, 2))
    temperature_min: Mapped[float] = mapped_column(Numeric(5, 2))
    precipitation_sum: Mapped[float] = mapped_column(Numeric(5, 2))
    relative_humidity_2m_max: Mapped[float] = mapped_column(Numeric(5, 2))
