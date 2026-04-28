Freshservice API Client

A robust, reusable Python client for the Freshservice REST API, designed for automation, scripting, and long-term reuse across multiple projects.

This repository intentionally does NOT include a `main.py`, CLI, or executable entry point. It is a library, not an application. Consumers are expected to import `FreshserviceClient` and build purpose-specific tooling on top of it.

--------------------------------------------------------------------

OVERVIEW

This client was built to solve common problems encountered when working with the Freshservice API:

• Inconsistent API responses
• Aggressive rate limiting
• Pagination-heavy endpoints
• Long-running automation jobs
• Repetitive boilerplate HTTP logic

The client centralizes those concerns so downstream scripts remain small, explicit, and safe.

--------------------------------------------------------------------

FEATURES

• Automatic retries with exponential backoff
• Global request timeouts (prevents hung connections)
• Centralized HTTP handling and error normalization
• Built-in pagination helpers for list endpoints
• Rate-limit visibility through logging
• Context-managed session lifecycle
• Optional Pydantic models for data validation
• Bulk operations for ticket updates
• Safe raw request escape hatch

--------------------------------------------------------------------

DESIGN PHILOSOPHY

This client follows a few strict rules:

1. Explicit over magical
   Every network call is a direct method invocation.

2. Forgiving over rigid
   Freshservice payloads vary by account and endpoint. Models allow missing or partial data.

3. Library over framework
   No global config, no background workers, no forced patterns.

4. Fail fast, fail clearly
   API failures raise structured exceptions immediately.

--------------------------------------------------------------------

INSTALLATION

This repository is intended to be vendored or installed directly.

Clone the repository:

    git clone https://github.com/your-org/FreshService-API.git

Add it to your project or PYTHONPATH and import the client:

    from freshservice import FreshserviceClient

--------------------------------------------------------------------

BASIC USAGE

    from freshservice import FreshserviceClient

    API_KEY = "your_api_key_here"

    with FreshserviceClient("company.freshservice.com", API_KEY) as fs:
        ticket = fs.get_ticket(123)
        print(ticket.subject)

        fs.add_ticket_note(
            ticket_id=123,
            body="Investigating the issue.",
            private=True,
        )

The context manager guarantees the underlying HTTP session is closed cleanly.

--------------------------------------------------------------------

COMMON OPERATIONS

GET A TICKET

    ticket = fs.get_ticket(123, include_requester=True)

Returns a `FreshTicket` Pydantic model when possible. Fields may be partially populated depending on the endpoint.

--------------------------------------------------------------------

GET ALL OPEN TICKET IDS

    open_ids = fs.get_all_open_ticket_ids()

Returns a list of ticket IDs with Open or Pending status.

--------------------------------------------------------------------

FILTER TICKETS BY AGENT

    tickets = fs.filter_tickets_by_agent(
        agent_id=456,
        allow_closed=False,
    )

Uses the Freshservice filter API and supports pagination automatically.

--------------------------------------------------------------------

CREATE A TICKET

    ticket = fs.create_ticket(
        subject="VPN Not Working",
        description="User unable to connect to VPN",
        priority=2,
    )

--------------------------------------------------------------------

ADD A PRIVATE NOTE

    fs.add_ticket_note(
        ticket_id=123,
        body="Internal troubleshooting started.",
        private=True,
    )

--------------------------------------------------------------------

REPLY PUBLICLY TO A TICKET

    fs.reply_to_ticket(
        ticket_id=123,
        body="Thanks for reporting this. We're investigating now.",
    )

--------------------------------------------------------------------

UPDATE A TICKET

    fs.update_ticket(
        ticket_id=123,
        status=4,
        priority=1,
    )

Only fields explicitly provided are updated.

--------------------------------------------------------------------

BULK UPDATE TICKETS

    fs.bulk_update_tickets(
        ticket_ids=[101, 102, 103],
        status=4,
    )

Significantly faster and safer than looping updates.

--------------------------------------------------------------------

SEARCH TICKETS

    results = fs.search_tickets('subject:"VPN Issue"')

Uses Freshservice's search API for flexible matching.

--------------------------------------------------------------------

ERROR HANDLING

All API-level failures raise `FreshserviceAPIError`.

    from utils.exceptions import FreshserviceAPIError

    try:
        fs.get_ticket(999999)
    except FreshserviceAPIError as e:
        print(e.status_code)
        print(e)

Transport errors raise standard `requests` exceptions.

--------------------------------------------------------------------

MODELS

The client includes optional Pydantic models:

• FreshTicket
• FreshConversation
• FreshRequester

Models are intentionally permissive:

• Many fields are optional
• Payload inconsistencies are tolerated
• custom_fields are preserved as raw dictionaries

Not all endpoints return fully populated objects.

--------------------------------------------------------------------

WHAT THIS CLIENT DOES NOT DO

By design, this client does not include:

• Async HTTP or asyncio integration
• CLI interface
• Webhook listeners
• Background job scheduling
• Opinionated business logic

Those responsibilities belong in higher-level tooling.

--------------------------------------------------------------------

WHEN TO USE THIS CLIENT

• Automation scripts
• Admin workflows
• Scheduled jobs / cron
• Service integrations
• Data collection and reporting

If you need a reliable Freshservice API foundation, this client is intended to be that foundation.

--------------------------------------------------------------------

STABILITY

Actively used in production; backward‑compatible changes are preferred but not guaranteed.

--------------------------------------------------------------------

LICENSE

Internal or project-specific use.
See repository licensing terms if applicable.

--------------------------------------------------------------------
