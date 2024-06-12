import asyncio
from copy import copy
from starlette.datastructures import MutableHeaders

import settings
from typing import Any, Dict
import google.protobuf.message
import pydantic
import uvicorn
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from fastapi import Request, HTTPException, Depends, FastAPI
import hmac
import hashlib
import base64
import logging

from utils import PokemonStruct
import httpx
import pokedex_pb2

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Guardio Reverse Proxy",
    version="1.0.0",
    openapi_url="/docs",
    docs_url="/api/docs",
)


async def _get_request_data(request: Request) -> Dict[str, Any]:
    message = "Exception while fetching user in App Exception Handler"
    if request.headers.get("Authorization"):
        logger.warning(message, exc_info=True)
    else:
        logger.debug(message, exc_info=True)

    return {
        "method": request.method,
        "url_path": request.url.path,
        "query_params": request.query_params,
    }


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    if exc.status_code == 404 and exc.detail == "Not Found":
        return JSONResponse(
            status_code=exc.status_code,
            content=dict(
                error=dict(message=f"Can't {request.method} {request.url.path}")
            ),
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=dict(
            error=dict(
                message=str(exc.detail), code="exception", type=exc.__class__.__name__
            )
        ),
    )


@app.exception_handler(Exception)
async def unicorn_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_data = await _get_request_data(request)
    logger.critical(
        "REST API Endpoint has raised an unknown exception",
        exc_info=exc,
        extra=request_data,
    )
    return JSONResponse(
        status_code=500,
        content=dict(
            error=dict(
                message="The application has encountered an unknown error.",
                code="exception",
                type=exc.__class__.__name__,
            )
        ),
    )


class GenericResponse(pydantic.BaseModel):
    message: str


def verify_signature(request_body: bytes, received_signature: str, secret_key: bytes) -> bool:
    computed_signature = hmac.new(secret_key, request_body, hashlib.sha256).hexdigest()

    return hmac.compare_digest(computed_signature, received_signature)


async def signature_verification(request: Request):
    x_grd_signature = request.headers.get("X-Grd-Signature")
    if not x_grd_signature:
        logger.error("Forbidden request: Missing or invalid signature")
        raise HTTPException(status_code=403, detail="Forbidden")

    request_body = await request.body()

    if not verify_signature(request_body, x_grd_signature, settings.POKESECRET_KEY.encode()):
        logger.error("Forbidden request: Missing or invalid signature")
        raise HTTPException(status_code=403, detail="Forbidden")


def correct_headers(request: Request, rule_dict: dict, pokemon_json: str) -> dict:
    headers = MutableHeaders(copy(request.headers))
    headers["X-Grd-Reason"] = rule_dict["reason"]
    headers["Content-Type"] = "application/json"
    headers["Content-Length"] = str(len(pokemon_json))

    if 'X-Forwarded-For' in headers:
        del headers['X-Forwarded-For']
    if 'X-Forwarded-Host' in headers:
        headers['X-Forwarded-Host'] = rule_dict["url"]
    if 'X-Forwarded-Proto' in headers:
        del headers['X-Forwarded-Proto']

    del headers["X-Grd-Signature"]

    return headers


@app.post("/stream", dependencies=[Depends(signature_verification)])
async def receive_pokemon(request: Request) -> PokemonStruct:
    pokemon_proto = pokedex_pb2.Pokemon()  # type: ignore
    request_body = await request.body()
    try:
        pokemon_proto.ParseFromString(request_body)
        pokemon = PokemonStruct.from_protobuf(pokemon_proto=pokemon_proto)
    except google.protobuf.message.DecodeError:
        raise HTTPException(status_code=403, detail="bad request")

    async with httpx.AsyncClient() as http_client:
        tasks = []

        for rule_dict in settings.pokeproxy_config["rules"]:
            pokemon_json = pokemon.json()
            headers = correct_headers(request, rule_dict, pokemon_json)
            if pokemon.validate_rules(rule_dict["match"]):
                tasks.append(
                    http_client.request(method="POST", url=rule_dict["url"], data=pokemon_json, headers=headers))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for response in responses:
            logger.debug(f'response for url: {rule_dict["url"]}')
            logger.debug(response)
    return pokemon


@app.get("{path:path}", response_model=GenericResponse)
def hello_world(request: Request):
    return GenericResponse(message="Hello World!")


@app.post("/receive", response_model=GenericResponse)
async def hello_world(request: Request):
    request_body = await request.json()
    logger.info(f"Received valid request: {request_body}")
    return GenericResponse(message="Hello Developers!")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        access_log=False,
    )
