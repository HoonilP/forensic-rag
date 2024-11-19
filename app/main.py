from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .service import router, routertask, routercom, routers3

app = FastAPI(
    title='DFIR Program API',
    summary='API endpoints',
    openapi_tags=[router.metadata],
    docs_url='/',
)

origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router.router)
app.include_router(routertask.router)
app.include_router(routercom.router)
app.include_router(routers3.router)

