"""DA10 Platform Services API (Layer 8).

Exposes Search / Context / Knowledge APIs consumed by DA09.
TODO: register routers from api/routes/.
"""

from fastapi import FastAPI

app = FastAPI(title="DA10 Knowledge & Retrieval Platform")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# TODO:
# from api.routes import search_api, context_api, knowledge_api
# app.include_router(search_api.router)
# app.include_router(context_api.router)
# app.include_router(knowledge_api.router)
