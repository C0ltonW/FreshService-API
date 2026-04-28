"""
Freshservice API Client

A reusable, standalone Python client for the Freshservice REST API with:
- Automatic retries and timeout handling
- Pagination helpers
- Safe error handling with structured exceptions
- Optional Pydantic models for validation
- Explicit, script-friendly method design (no implicit globals)

This client is intentionally designed without a main entry point.
Consumers are expected to import FreshserviceClient and build
use-case-specific tooling around it.

Example:

    from freshservice import FreshserviceClient

    with FreshserviceClient("company.freshservice.com", API_KEY) as fs:
        ticket = fs.get_ticket(123)
        fs.add_ticket_note(123, "Investigating issue", private=True)

"""

import functools
import logging
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from settings.constants import DEFAULT_PER_PAGE, DEFAULT_MAX_PAGES, TicketStatus
from models.fresh_ticket_model import FreshTicket
from utils.exceptions import FreshserviceAPIError

logger = logging.getLogger(__name__)


def _validate_id(self, name: str, value: int):
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _build_session(api_key: str) -> requests.Session:
    def _build_session(api_key: str) -> requests.Session:
        """
        Build and configure a requests.Session for Freshservice API usage.

        Configuration includes:
        - HTTP Basic authentication using the Freshservice API key
        - Automatic retries with exponential backoff for transient failures
        - A default request timeout to prevent hanging connections
        - JSON request and response headers

        This session is owned by FreshserviceClient and closed automatically
        when the client exits a context manager.
        """

    s = requests.Session()
    s.request = functools.partial(s.request, timeout=30)
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods={"GET", "POST", "PUT", "PATCH", "DELETE"},
        raise_on_status=False
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    s.auth = (api_key, "X")
    return s


class FreshserviceClient:
    class FreshserviceClient:
        """
        FreshserviceClient

        A thin but robust wrapper around the Freshservice REST API.

        Responsibilities:
        - HTTP transport with retries, timeouts, and rate-limit logging
        - Endpoint normalization and query encoding
        - Pagination helpers for list endpoints
        - Optional model validation for tickets and conversations

        Design principles:
        - No global config or singleton behavior
        - No background threads or async requirements
        - Explicit method calls for all side effects
        - Safe defaults, but configurable where behavior matters

        This class is safe to reuse across scripts, services, and automation tools.
        """

    def __init__(self, domain: str, api_key: str):
        if "." not in domain:
            raise ValueError(
                "Freshservice domain must be full hostname "
                "(e.g. company.freshservice.com)"
            )

        self._agent_cache = None
        self.base_url = f"https://{domain}".rstrip("/")
        self.api_key = api_key
        self.s = _build_session(api_key)

        try:
            self._base_host = urlparse(self.base_url).netloc.lower()
        except Exception:
            self._base_host = ""

    def __enter__(self) -> "FreshserviceClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.s.close()
        except Exception:
            pass


    # --- HTTP helpers --- #
    def create_request(
            self,
            endpoint: str,
            method: str,
            data: Optional[Any] = None,
    ) -> requests.Response:
        return self._request(method, endpoint, json=data)

    def _get_json(
            self,
            endpoint: str,
            *,
            params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        resp = self._request("GET", endpoint, params=params)
        return resp.json() if resp.content else {}

    def _paginate(
        self,
        path: str,
        *,
        item_key: str,
        params: Optional[Dict[str, Any]] = None,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> Iterable[Dict[str, Any]]:
        """
        Generator helper for paginated Freshservice endpoints.

        Repeatedly requests pages until:
        - No items are returned
        - Fewer items than per_page are returned
        - max_pages is reached

        Yields individual items from each page instead of entire responses.

        This helper assumes standard Freshservice pagination semantics
        using 'page' and 'per_page' query parameters.
        """

        page = 1
        params = dict(params or {})

        while page <= max_pages:
            params.update({"page": page, "per_page": per_page})
            data = self._get_json(path, params=params)
            items = data.get(item_key, [])
            if not items:
                break

            for it in items:
                yield it

            if len(items) < per_page:
                break

            page += 1
    """
    Generator helper for paginated Freshservice endpoints.

    Repeatedly requests pages until:
    - No items are returned
    - Fewer items than per_page are returned
    - max_pages is reached

    Yields individual items from each page instead of entire responses.

    This helper assumes standard Freshservice pagination semantics
    using 'page' and 'per_page' query parameters.
    """

    def _request(
            self,
            method: str,
            endpoint: str,
            *,
            params: Optional[Dict[str, Any]] = None,
            json: Optional[Any] = None,
            stream: bool = False,
    ) -> requests.Response:
        """
        Perform a single HTTP request against the Freshservice API.

        This method is the central request pipeline used by all public APIs.

        Behavior:
        - Normalizes endpoint paths
        - Applies retries and timeout handling
        - Raises FreshserviceAPIError for all non-2xx responses
        - Logs rate-limit information when available

        Parameters:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint path (with or without leading '/')
            params: Optional query parameters
            json: Optional JSON request body
            stream: Whether to stream the response content

        Returns:
            requests.Response on success

        Raises:
            FreshserviceAPIError on API failure
            requests.RequestException on transport errors
        """

        # Central endpoint normalization
        endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        url = f"{self.base_url}{endpoint}"

        try:
            resp = self.s.request(
                method=method,
                url=url,
                params=params,
                json=json,
                stream=stream,
            )
        except Exception as e:
            logger.error(
                "Freshservice request failed: %s %s -> %s",
                method,
                url,
                e,
            )
            raise

        if resp.status_code // 100 != 2:
            logger.error(
                "Freshservice API error %s for %s %s: %s",
                resp.status_code,
                method,
                url,
                resp.text,
            )
            raise FreshserviceAPIError(
                resp.status_code,
                resp.text,
                endpoint=endpoint,
            )

        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        if remaining is not None:
            logger.debug(
                "Freshservice rate limit remaining=%s reset=%s",
                remaining,
                reset,
            )

        return resp

    def raw_request(
            self,
            method: str,
            endpoint: str,
            *,
            params: Optional[Dict[str, Any]] = None,
            json: Optional[Any] = None,
    ) -> Dict[str, Any]:
        resp = self._request(method, endpoint, params=params, json=json)
        return resp.json() if resp.content else {}


    # --- Tickets --- #
    def create_ticket(
            self,
            subject: str,
            description: str,
            *,
            requester_id: Optional[int] = None,
            email: Optional[str] = None,
            priority: Optional[int] = None,
            status: Optional[int] = None,
            group_id: Optional[int] = None,
            custom_fields: Optional[Dict[str, Any]] = None,
    ) -> dict:
        payload: Dict[str, Any] = {
            "subject": subject,
            "description": description,
        }

        if requester_id:
            payload["requester_id"] = requester_id
        if email:
            payload["email"] = email
        if priority:
            payload["priority"] = priority
        if status:
            payload["status"] = status
        if group_id:
            payload["group_id"] = group_id
        if custom_fields:
            payload["custom_fields"] = custom_fields

        resp = self._request("POST", "/api/v2/tickets", json=payload)
        return resp.json() if resp.content else {}

    def bulk_update_tickets(
            self,
            ticket_ids: List[int],
            *,
            status: Optional[int] = None,
            group_id: Optional[int] = None,
            priority: Optional[int] = None,
            custom_fields: Optional[Dict[str, Any]] = None,
    ) -> dict:
        if not ticket_ids:
            return {}

        payload: Dict[str, Any] = {"ids": ticket_ids}

        if status is not None:
            payload["status"] = status
        if group_id is not None:
            payload["group_id"] = group_id
        if priority is not None:
            payload["priority"] = priority
        if custom_fields:
            payload["custom_fields"] = custom_fields

        resp = self._request("PUT", "/api/v2/tickets/bulk_update", json=payload)
        return resp.json() if resp.content else {}


    def get_all_open_ticket_ids(self, per_page: int = DEFAULT_PER_PAGE) -> list[int]:
        """
        Retrieve the IDs of all open or pending tickets.

        Open statuses are determined using Freshservice status codes:
        - OPEN
        - PENDING

        Returns:
            List of ticket IDs matching the criteria
        """

        ticket_ids: list[int] = []

        for ticket in self._paginate(
                "/api/v2/tickets",
                item_key="tickets",
                per_page=per_page,
        ):
            status = ticket.get("status")
            if status in (TicketStatus.OPEN, TicketStatus.PENDING):
                ticket_ids.append(ticket["id"])

        return ticket_ids

    def get_ticket(
            self,
            ticket_id: int,
            include_requester: bool = False,
    ) -> Optional[FreshTicket]:
        """
        Retrieve a single Freshservice ticket by ID.

        Optionally enriches the ticket with requester information
        when include_requester=True.

        Note:
        - Freshservice payloads can vary by account and endpoint.
        - This method defensively fills commonly missing fields such as
          name, phone, department_id, and location when possible.

        Parameters:
            ticket_id: Freshservice ticket ID
            include_requester: Whether to include requester details

        Returns:
            FreshTicket instance on success, or None if parsing fails

        Raises:
            FreshserviceAPIError for API-level failures
        """

        endpoint = f"/api/v2/tickets/{ticket_id}"
        if include_requester:
            endpoint += "?include=requester"

        resp = self._request("GET", endpoint)

        try:
            payload = resp.json()
            data = payload.get("ticket", payload)

            if include_requester and isinstance(data.get("requester"), dict):
                req = data["requester"]

                data["name"] = data.get("name") or req.get("name")
                data["phone"] = (
                        data.get("phone")
                        or req.get("phone")
                        or req.get("mobile")
                        or req.get("mobile_number")
                        or req.get("work_phone_number")
                        or req.get("work_phone")
                        or req.get("primary_phone")
                )

                if not data.get("department_id"):
                    requester_id = data.get("requester_id")
                    if requester_id:
                        try:
                            full_req = self.get_requester_by_id(int(requester_id)) or {}
                            dept_ids = full_req.get("department_ids") or []
                            data["department_id"] = (
                                    full_req.get("department_id")
                                    or (dept_ids[0] if dept_ids else None)
                            )
                        except Exception as e:
                            logger.debug(
                                "Failed to enrich requester department (ticket %s): %s",
                                ticket_id,
                                e,
                            )

                if not data.get("location"):
                    data["location"] = req.get("location") or req.get("location_id")

            return FreshTicket.model_validate(data)

        except Exception as e:
            logger.exception(
                "Error parsing Freshservice ticket %s: %s",
                ticket_id,
                e,
            )
            if "Internal Error" in resp.text:
                raise FreshserviceAPIError(resp.status_code, resp.text)
            return None

    def reply_to_ticket(
            self,
            ticket_id: int,
            body: str,
            *,
            user_id: Optional[int] = None,
    ) -> dict:
        payload: Dict[str, Any] = {
            "body": body,
            "private": False,
        }
        if user_id:
            payload["user_id"] = user_id

        resp = self._request(
            "POST",
            f"/api/v2/tickets/{ticket_id}/notes",
            json=payload,
        )
        return resp.json() if resp.content else {}

    def ticket_has_private_note(
            self,
            ticket_id: int,
            marker: str,
            max_pages: int = 5,
            per_page: int = DEFAULT_PER_PAGE,
    ) -> bool:
        for conv in self._paginate(
                f"/api/v2/tickets/{ticket_id}/conversations",
                item_key="conversations",
                per_page=per_page,
                max_pages=max_pages,
        ):
            body = (
                    conv.get("body_text")
                    or conv.get("body")
                    or ""
            )

            if marker in body:
                return True

        return False


    def get_all_tickets_by_agent(
        self,
        agent_id: int,
        extra: Optional[str] = None,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> List[FreshTicket]:
        all_tickets: List[FreshTicket] = []
        page = 1

        while page <= max_pages:
            batch = self.filter_tickets_by_agent(
                agent_id=agent_id,
                extra=extra,
                per_page=per_page,
                page=page,
            )
            if not batch:
                break
            all_tickets.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

        return all_tickets

    def filter_tickets_by_agent(
            self,
            agent_id: int,
            extra: Optional[str] = None,
            *,
            allow_closed: bool = False,
            status_include: Optional[List[int]] = None,
            per_page: int = DEFAULT_PER_PAGE,
            page: int = 1,
    ) -> List[FreshTicket]:
        """
        Retrieve tickets assigned to a specific agent using the Freshservice filter API.

        Supports:
        - Optional additional query clauses
        - Optional exclusion of closed states
        - Pagination via page/per_page

        This method returns validated FreshTicket models where possible.

        Parameters:
            agent_id: Agent ID to filter by
            extra: Optional additional filter query string
            allow_closed: Whether to include closed tickets
            status_include: Explicit list of status codes to include

        Returns:
            List of FreshTicket objects
            :param page:
            :param allow_closed:
            :param extra:
            :param agent_id:
            :param status_include:
            :param per_page:
        """

        base_query = f"agent_id:{agent_id}"

        status_clause = ""
        if not allow_closed:
            include_statuses = status_include or [
                TicketStatus.OPEN,
                TicketStatus.PENDING,
                TicketStatus.RESOLVED,
            ]
            parts = [f"status:{int(s)}" for s in include_statuses]
            status_clause = "(" + " OR ".join(parts) + ")"

        if extra:
            full_query = f"{base_query} AND {extra}"
            if status_clause and "status:" not in extra.lower():
                full_query = f"{full_query} AND {status_clause}"
        else:
            full_query = base_query + (f" AND {status_clause}" if status_clause else "")

        resp = self._request(
            "GET",
            "/api/v2/tickets/filter",
            params={
                "query": f'"{full_query}"',
                "per_page": per_page,
                "page": page,
            },
        )

        try:
            items = resp.json().get("tickets", [])
            return [FreshTicket.model_validate(t) for t in items]
        except Exception as e:
            logger.exception(
                "Error parsing Freshservice tickets (agent_id=%s): %s",
                agent_id,
                e,
            )
            if "Internal Error" in resp.text:
                raise FreshserviceAPIError(resp.status_code, resp.text)
            return []

    # --- Agents --- #

    def get_all_agents(
        self,
        per_page: int = DEFAULT_PER_PAGE,
        include_inactive: bool = True,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> List[dict]:
        """
        Get all agents from Freshservice.

        FIXED:
        - Removed noisy print()
        - Fixed bug where function returned during first loop iteration
        """
        agents: List[dict] = []

        for a in self._paginate(
            "/api/v2/agents",
            item_key="agents",
            params={},
            per_page=per_page,
            max_pages=max_pages,
        ):
            if include_inactive or a.get("active", True):
                agents.append(a)

        logger.debug("Fetched %d agents (include_inactive=%s)", len(agents), include_inactive)
        return agents

    # --- Conversations --- #

    def get_ticket_conversations(
            self,
            ticket_id: int,
            per_page: int = DEFAULT_PER_PAGE,
            page: int = 1,
    ) -> List[dict]:
        resp = self._request(
            "GET",
            f"/api/v2/tickets/{ticket_id}/conversations",
            params={
                "per_page": per_page,
                "page": page,
            },
        )
        payload = resp.json()
        return payload.get("conversations", payload if isinstance(payload, list) else [])

    def get_all_ticket_conversations(
            self,
            ticket_id: int,
            per_page: int = DEFAULT_PER_PAGE,
            max_pages: int = DEFAULT_MAX_PAGES,
    ) -> List[dict]:
        return list(
            self._paginate(
                f"/api/v2/tickets/{ticket_id}/conversations",
                item_key="conversations",
                per_page=per_page,
                max_pages=max_pages,
            )
        )
    # --- User/Agent lookup --- #

    def get_agent_by_id(self, agent_id: int) -> Optional[dict]:
        if agent_id in self._agent_cache:
            return self._agent_cache[agent_id]

        try:
            data = self._get_json(f"/api/v2/agents/{agent_id}")
            agent = data.get("agent", data)
            self._agent_cache[agent_id] = agent
            return agent
        except FreshserviceAPIError:
            return None


    def get_requester_by_id(self, requester_id: int) -> Optional[dict]:
        try:
            data = self._get_json(f"/api/v2/requesters/{requester_id}")
            return data.get("requester", data)
        except FreshserviceAPIError:
            return None

    # --- Departments and Groups --- #

    def get_departments(self, per_page: int = DEFAULT_PER_PAGE, max_page: int = DEFAULT_MAX_PAGES) -> List[dict]:
        return list(self._paginate(
            "/api/v2/departments",
            item_key="departments",
            params={},
            per_page=per_page,
            max_pages=max_page,
        ))

    def get_groups(self, per_page: int = DEFAULT_PER_PAGE, max_page: int = DEFAULT_MAX_PAGES) -> List[dict]:
        return list(self._paginate(
            "/api/v2/groups",
            item_key="groups",
            params={},
            per_page=per_page,
            max_pages=max_page,
        ))

    # --- Attachments / Assets --- #

    def download_attachment(self, url: str) -> bytes:
        if not url:
            return b""

        full_url = url if url.startswith("http") else f"{self.base_url}{url}"

        try:
            host = urlparse(full_url).netloc.lower()
        except Exception:
            host = ""

        prefer_auth = bool(self._base_host and host.endswith(self._base_host))

        def _get(use_auth: bool) -> requests.Response:
            return self.s.get(
                full_url,
                stream=True,
                auth=self.s.auth if use_auth else None,
            )

        resp = _get(prefer_auth)
        if resp.status_code // 100 != 2:
            resp = _get(not prefer_auth)

        if resp.status_code // 100 != 2:
            logger.error(
                "Freshservice download failed %s for %s",
                resp.status_code,
                full_url,
            )
            raise FreshserviceAPIError(
                resp.status_code,
                resp.text,
                endpoint=full_url,
            )

        length = resp.headers.get("Content-Length")
        if length and int(length) > 50_000_000:
            raise FreshserviceAPIError(
                resp.status_code,
                "Attachment too large",
                endpoint=full_url,
            )

        return resp.content

    def get_assets(
            self,
            *,
            asset_type_id: Optional[int] = None,
    ) -> List[dict]:
        params = {}
        if asset_type_id:
            params["asset_type_id"] = asset_type_id

        return list(self._paginate(
            "/api/v2/assets",
            item_key="assets",
            params=params,
        ))

    # --- Ticket updates (notes, status, tags) --- #

    def search_tickets(
            self,
            query: str,
            *,
            per_page: int = DEFAULT_PER_PAGE,
            max_pages: int = DEFAULT_MAX_PAGES,
    ) -> List[dict]:
        return list(self._paginate(
            "/api/v2/search/tickets",
            item_key="results",
            params={"query": query},
            per_page=per_page,
            max_pages=max_pages,
        ))

    def get_ticket_time_entries(
            self,
            ticket_id: int,
    ) -> List[dict]:
        data = self._get_json(f"/api/v2/tickets/{ticket_id}/time_entries")
        return data.get("time_entries", [])

    def add_ticket_note(
        self,
        ticket_id: int,
        body: str,
        *,
        private: bool = True,
        user_id: Optional[int] = None,
    ) -> dict:
        """
        Add a note to an existing ticket.

        Notes can be private (internal) or public depending on the 'private' flag.

        Parameters:
            ticket_id: Target ticket ID
            body: Note content
            private: Whether the note is private/internal
            user_id: Optional user ID to attribute the note to

        Returns:
            API response payload as a dict
        """

        endpoint = f"/api/v2/tickets/{ticket_id}/notes"
        payload: Dict[str, Any] = {"body": body, "private": private}
        if user_id is not None:
            payload["user_id"] = user_id
        resp = self.create_request(endpoint, "POST", data=payload)
        return resp.json() if resp.content else {}

    def update_ticket(
        self,
        ticket_id: int,
        *,
        status: Optional[int] = None,
        group_id: Optional[int] = None,
        priority: Optional[int] = None,
        tags_to_add: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        Update mutable fields on an existing Freshservice ticket.

        Only fields explicitly provided will be updated.

        Supported fields:
        - status
        - group_id
        - priority
        - tags
        - custom_fields

        Returns:
            API response payload as a dict
        """

        endpoint = f"/api/v2/tickets/{ticket_id}"
        payload: Dict[str, Any] = {}

        if status is not None:
            payload["status"] = status
        if group_id is not None:
            payload["group_id"] = group_id
        if priority is not None:
            payload["priority"] = priority
        if tags_to_add:
            payload["tags"] = tags_to_add
        if custom_fields:
            payload["custom_fields"] = custom_fields

        if not payload:
            return {}

        resp = self.create_request(endpoint, "PUT", data=payload)
        return resp.json() if resp.content else {}