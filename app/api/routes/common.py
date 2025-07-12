from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
import httpx
import logging
from typing import Optional, Dict, Any
from fastapi.responses import Response

router = APIRouter(prefix="/common", tags=["common"])
logger = logging.getLogger("common")


# Pydantic models for proxy request
class ProxyRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, str]] = None


@router.post("/proxy")
async def proxy_request(
    proxy_req: ProxyRequest,
    request: Request,
):
    """
    Proxy function to forward requests to external services and avoid CORS issues.
    This endpoint acts as a middleware between frontend and external APIs.

    Args:
        proxy_req: ProxyRequest containing target URL, method, headers, data, and params
        request: FastAPI Request object

    Returns:
        Response from the external service
    """
    try:
        # Validate URL to prevent potential security issues
        if not proxy_req.url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format. URL must start with http:// or https://",
            )

        # Prepare headers for the external request
        headers = proxy_req.headers or {}

        # Add default headers if not provided
        default_headers = {
            "User-Agent": "StartomationAPI/1.0",
            "Accept": "application/json",
        }

        for key, value in default_headers.items():
            if key not in headers:
                headers[key] = value

        # Log the proxy request for debugging
        logger.info(f"Proxying {proxy_req.method} request to: {proxy_req.url}")

        # Create HTTP client with timeout
        timeout = httpx.Timeout(30.0)  # 30 seconds timeout

        async with httpx.AsyncClient(timeout=timeout) as client:
            # Prepare request parameters based on method
            if proxy_req.method.upper() == "GET":
                response = await client.get(
                    proxy_req.url, headers=headers, params=proxy_req.params
                )
            elif proxy_req.method.upper() == "POST":
                response = await client.post(
                    proxy_req.url,
                    headers=headers,
                    json=proxy_req.data,
                    params=proxy_req.params,
                )
            elif proxy_req.method.upper() == "PUT":
                response = await client.put(
                    proxy_req.url,
                    headers=headers,
                    json=proxy_req.data,
                    params=proxy_req.params,
                )
            elif proxy_req.method.upper() == "DELETE":
                response = await client.delete(
                    proxy_req.url, headers=headers, params=proxy_req.params
                )
            elif proxy_req.method.upper() == "PATCH":
                response = await client.patch(
                    proxy_req.url,
                    headers=headers,
                    json=proxy_req.data,
                    params=proxy_req.params,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                    detail=f"Method {proxy_req.method} not supported",
                )

        # Log response status for debugging
        logger.info(f"Proxy response status: {response.status_code}")

        # Return response with appropriate headers to avoid CORS
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Content-Type": response.headers.get(
                    "content-type", "application/json"
                ),
            },
        )

    except httpx.TimeoutException:
        logger.error(f"Timeout while proxying request to: {proxy_req.url}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request timeout while contacting external service",
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error while proxying request: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"External service returned error: {e.response.text}",
        )
    except Exception as e:
        logger.error(f"Unexpected error while proxying request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing proxy request",
        )


@router.options("/proxy")
async def proxy_options():
    """
    Handle OPTIONS request for CORS preflight
    """
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.get("/proxy")
async def proxy_get_request(
    url: str,
    request: Request,
):
    """
    Simple GET proxy endpoint for quick external API calls.
    Usage: /api/common/proxy?url=https://api.example.com/data

    Args:
        url: Target URL to proxy the request to
        request: FastAPI Request object

    Returns:
        Response from the external service
    """
    try:
        # Validate URL
        if not url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format. URL must start with http:// or https://",
            )

        logger.info(f"Proxying GET request to: {url}")

        # Default headers for GET requests
        headers = {
            "User-Agent": "StartomationAPI/1.0",
            "Accept": "application/json",
        }

        timeout = httpx.Timeout(30.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)

        logger.info(f"Proxy GET response status: {response.status_code}")

        # Return response with CORS headers
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Content-Type": response.headers.get(
                    "content-type", "application/json"
                ),
            },
        )

    except httpx.TimeoutException:
        logger.error(f"Timeout while proxying GET request to: {url}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request timeout while contacting external service",
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error while proxying GET request: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"External service returned error: {e.response.text}",
        )
    except Exception as e:
        logger.error(f"Unexpected error while proxying GET request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing proxy request",
        )
