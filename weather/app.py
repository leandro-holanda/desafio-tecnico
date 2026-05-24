from fastapi import FastAPI

from .routers import cities

app = FastAPI(title='Weather Pipeline API')

app.include_router(cities.router, prefix='/api/v1/cities', tags=['cities'])


@app.get(path='/health', status_code=200, summary='Health check', tags=['health'])
async def health_check():
    return {'status': 'ok'}
