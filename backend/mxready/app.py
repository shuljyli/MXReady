from contextlib import asynccontextmanager

from fastapi import FastAPI

from mxready import __version__
from mxready.config import Settings
from mxready.storage import SQLiteStore


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved.data_dir.mkdir(parents=True, exist_ok=True)
        resolved.temp_dir.mkdir(parents=True, exist_ok=True)
        app.state.settings = resolved
        store = SQLiteStore(resolved.data_dir / "mxready.db")
        store.initialize()
        store.mark_interrupted_jobs_failed()
        app.state.store = store
        yield

    app = FastAPI(title="MXReady", version=__version__, lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
