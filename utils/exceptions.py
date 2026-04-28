from typing import Optional


class FreshserviceAPIError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        endpoint: Optional[str] = None,
        payload: Optional[dict] = None,
    ):
        self.status_code = status_code
        self.endpoint = endpoint
        self.payload = payload
        super().__init__(f"Freshservice API error {status_code}: {message}")