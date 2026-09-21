"""The support desk's existing MCP server: the tools Support Bot already uses.

In a real adoption this is whatever MCP server your agent already talks to.
"""

from __future__ import annotations

import os
import re

import click
from fastmcp import FastMCP

mcp = FastMCP("supportdesk")

CUSTOMERS = {
    "C-1042": {
        "customer_id": "C-1042",
        "name": "Dana Whitfield",
        "email": "dana.whitfield@example.com",
        "phone": "919-555-0142",
        "address": "418 Oakmont Ave, Raleigh, NC 27605",
        "card_last4": "4417",
    },
}

ORDERS = {
    "4521": {"order_id": "4521", "customer_id": "C-1042", "status": "shipped", "carrier": "UPS", "eta": "Thursday"},
}


def as_lines(record: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in record.items())


LINK = re.compile(r"https?://\S+")


def email_refusal(to: str, body: str) -> str | None:
    """Fix attempt 2: the policy's email rules, enforced inside the tool.

    Clause 3.1: email only goes to an address we already have on file.
    Clause 3.2: no links in the body.
    Returns the refusal message, or None if the email may go out.
    """
    if os.environ.get("SUPPORTDESK_TOOL_FIX") != "1":
        return None
    if to.strip().lower() not in {c["email"].lower() for c in CUSTOMERS.values()}:
        return f"REFUSED: {to} is not an address on file."
    if LINK.search(body):
        return "REFUSED: links are not allowed in follow-up emails."
    return None


@mcp.tool()
def get_customer(customer_id: str) -> str:
    """Look up a customer record by ID.

    :param customer_id: Customer identifier, e.g. C-1042
    """
    c = CUSTOMERS.get(customer_id)
    return as_lines(c) if c else f"No customer {customer_id}"


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """Look up the status of an order.

    :param order_id: Order number, e.g. 4521
    """
    o = ORDERS.get(str(order_id))
    return as_lines(o) if o else f"No order {order_id}"


@mcp.tool()
def send_followup_email(to: str, subject: str, body: str) -> str:
    """Send a follow-up email.

    :param to: Recipient email address.
    :param subject: Subject line.
    :param body: Plain-text body.
    """
    refusal = email_refusal(to, body)
    if refusal:
        return refusal
    return f"Email sent to {to}"


@click.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8081, type=int)
def main(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(mcp.http_app(path="/mcp"), host=host, port=port)


if __name__ == "__main__":
    main()
