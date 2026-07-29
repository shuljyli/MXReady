from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from mxready import __version__
from mxready.api import rules_router, scans_router
from mxready.config import Settings
from mxready.errors import MxReadyError
from mxready.repository.git_client import GitClient
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog
from mxready.services.scans import ScanService
from mxready.storage import SQLiteStore

_ERROR_STATUS_CODES = {
    "INVALID_REPOSITORY_URL": 400,
    "UNSUPPORTED_REPOSITORY_HOST": 400,
    "INVALID_GIT_REF": 400,
    "SCAN_NOT_FOUND": 404,
    "SCAN_NOT_COMPLETED": 409,
    "VERIFICATION_COMMIT_MISMATCH": 409,
    "UPLOAD_TOO_LARGE": 413,
    "VERIFICATION_SCHEMA_INVALID": 422,
}


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
        catalog = load_rule_catalog(resolved.rules_dir)
        app.state.rule_catalog = catalog
        app.state.scan_service = ScanService(
            store,
            GitClient(),
            ScanAnalyzer(catalog),
            resolved,
        )
        yield

    app = FastAPI(title="MXReady", version=__version__, lifespan=lifespan)
    app.include_router(scans_router, prefix="/api")
    app.include_router(rules_router, prefix="/api")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.exception_handler(MxReadyError)
    async def handle_mxready_error(
        request: Request,
        error: MxReadyError,
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=_ERROR_STATUS_CODES.get(error.code, 500),
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        del request, error
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "The request body or path parameters are invalid.",
                    "details": {},
                }
            },
        )

    return app
