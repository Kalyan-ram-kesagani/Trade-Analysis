import os
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("mt5_bridge_client")

class MT5BridgeClient:
    """
    Client for communicating with the Windows MT5 Bridge.
    All communication is authenticated via X-Bridge-Token.
    """
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: float = 15.0):
        self.base_url = (base_url or os.getenv("MT5_BRIDGE_URL", "")).rstrip("/")
        self.token = token or os.getenv("MT5_BRIDGE_TOKEN", "")
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _get_headers(self) -> Dict[str, str]:
        if not self.token:
            raise RuntimeError("MT5_BRIDGE_TOKEN is not configured in backend environment.")
        return {
            "X-Bridge-Token": self.token,
            "Accept": "application/json",
        }

    async def get_health(self) -> Dict[str, Any]:
        """Check bridge health and MT5 terminal connectivity status."""
        if not self.base_url:
            raise RuntimeError("MT5_BRIDGE_URL is not configured in backend environment.")

        url = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 401:
                    raise RuntimeError("MT5 Bridge authentication failed: Invalid bridge token.")
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            raise RuntimeError(f"Unable to connect to MT5 Bridge at {self.base_url}. Ensure the Windows bridge and tunnel are running.")
        except httpx.TimeoutException:
            raise RuntimeError("MT5 Bridge request timed out.")

    async def get_account(self) -> Dict[str, Any]:
        """Retrieve account telemetry from MT5 bridge."""
        if not self.base_url:
            raise RuntimeError("MT5_BRIDGE_URL is not configured in backend environment.")

        url = f"{self.base_url}/account"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 401:
                    raise RuntimeError("MT5 Bridge authentication failed: Invalid bridge token.")
                if resp.status_code == 503:
                    err_msg = resp.json().get("detail", "MT5 terminal error")
                    raise RuntimeError(f"MT5 terminal unavailable: {err_msg}")
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            raise RuntimeError(f"Unable to connect to MT5 Bridge at {self.base_url}. Ensure the Windows bridge and tunnel are running.")
        except httpx.TimeoutException:
            raise RuntimeError("MT5 Bridge request timed out.")

    async def get_price(self, symbol: str) -> Dict[str, Any]:
        """Retrieve latest tick/price for a symbol."""
        if not self.base_url:
            raise RuntimeError("MT5_BRIDGE_URL is not configured in backend environment.")

        url = f"{self.base_url}/price/{symbol}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 401:
                    raise RuntimeError("MT5 Bridge authentication failed: Invalid bridge token.")
                if resp.status_code == 404:
                    raise ValueError(f"Symbol '{symbol}' not found on MT5.")
                if resp.status_code == 503:
                    err_msg = resp.json().get("detail", "MT5 terminal error")
                    raise RuntimeError(f"MT5 terminal unavailable: {err_msg}")
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            raise RuntimeError(f"Unable to connect to MT5 Bridge at {self.base_url}. Ensure the Windows bridge and tunnel are running.")
        except httpx.TimeoutException:
            raise RuntimeError("MT5 Bridge request timed out.")

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Retrieve open positions from MT5 bridge."""
        if not self.base_url:
            raise RuntimeError("MT5_BRIDGE_URL is not configured in backend environment.")

        url = f"{self.base_url}/positions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 401:
                    raise RuntimeError("MT5 Bridge authentication failed: Invalid bridge token.")
                if resp.status_code == 503:
                    err_msg = resp.json().get("detail", "MT5 terminal error")
                    raise RuntimeError(f"MT5 terminal unavailable: {err_msg}")
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            raise RuntimeError(f"Unable to connect to MT5 Bridge at {self.base_url}. Ensure the Windows bridge and tunnel are running.")
        except httpx.TimeoutException:
            raise RuntimeError("MT5 Bridge request timed out.")

    async def get_history_trades(self, days: int = 90) -> List[Dict[str, Any]]:
        """Retrieve historical completed trades from MT5 bridge."""
        if not self.base_url:
            raise RuntimeError("MT5_BRIDGE_URL is not configured in backend environment.")

        url = f"{self.base_url}/history"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params={"days": days}, headers=self._get_headers())
                if resp.status_code == 401:
                    raise RuntimeError("MT5 Bridge authentication failed: Invalid bridge token.")
                if resp.status_code == 503:
                    err_msg = resp.json().get("detail", "MT5 terminal error")
                    raise RuntimeError(f"MT5 terminal unavailable: {err_msg}")
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            raise RuntimeError(f"Unable to connect to MT5 Bridge at {self.base_url}. Ensure the Windows bridge and tunnel are running.")
        except httpx.TimeoutException:
            raise RuntimeError("MT5 Bridge request timed out.")
