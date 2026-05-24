from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8'
    )

    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int

    @property
    def DATABASE_URL(self) -> str:

        return (
            f'postgresql+asyncpg://'
            f'{self.DB_USER}:'
            f'{self.DB_PASSWORD}@'
            f'{self.DB_HOST}:'
            f'{self.DB_PORT}/'
            f'{self.DB_NAME}'
        )