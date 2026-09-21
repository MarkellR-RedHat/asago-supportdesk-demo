"""MiDojo interception layer for Support Bot.

The agent connects here instead of real_mcp.py. Reads are forwarded upstream
for real data, then the suite's injection payloads (the `notes` fields in
suite.yaml) are spliced in. Writes land in the MiDojo environment's `outbox`
so the grader can see what the agent actually did, and no real email goes out.
"""

from __future__ import annotations

import os
import re

import click

from midojo.mcp_sdk import MidojoMCP, ToolContext

from supportdesk.real_mcp import recipient_allowed

LINK = re.compile(r"https?://\S+")


def with_notes(result: str, record: dict | None) -> str:
    """Attach the record's free-text notes field, the way a real CRM row would carry one."""
    if not record or not record.get("notes", "").strip():
        return result
    return f"{result}\nnotes: {record['notes']}"


async def get_customer(ctx: ToolContext, customer_id: str) -> str:
    """Look up a customer record by ID.

    :param customer_id: Customer identifier, e.g. C-1042
    """
    result = await ctx.forward("get_customer", {"customer_id": customer_id})
    customers = await ctx.env("customers")
    return with_notes(result, customers.get(customer_id))


async def get_order_status(ctx: ToolContext, order_id: str) -> str:
    """Look up the status of an order.

    :param order_id: Order number, e.g. 4521
    """
    result = await ctx.forward("get_order_status", {"order_id": str(order_id)})
    orders = await ctx.env("orders")
    return with_notes(result, orders.get(str(order_id)))


async def send_followup_email(ctx: ToolContext, to: str, subject: str, body: str) -> str:
    """Send a follow-up email.

    :param to: Recipient email address.
    :param subject: Subject line.
    :param body: Plain-text body.
    """
    # Same business rules as the real tool, so a fix there is a fix here.
    if not recipient_allowed(to):
        return f"REFUSED: {to} is not an address on file."
    if os.environ.get("SUPPORTDESK_TOOL_FIX") == "1" and LINK.search(body):
        return "REFUSED: links are not allowed in follow-up emails."
    outbox = await ctx.env("outbox")
    outbox.append({"to": to, "subject": subject, "body": body})
    await ctx.env_update("outbox", outbox)
    return f"Email sent to {to}"


@click.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8082, type=int)
@click.option("--upstream-url", default=None, help="URL of the real MCP server to forward reads to.")
def main(host: str, port: int, upstream_url: str | None) -> None:
    import uvicorn

    mcp = MidojoMCP(
        "supportdesk",
        control_plane_url=os.environ.get("MIDOJO_URL", "http://localhost:8080"),
        upstream_url=upstream_url,
    )
    for tool_fn in [get_customer, get_order_status, send_followup_email]:
        mcp.tool()(tool_fn)
    uvicorn.run(mcp.http_app(path="/mcp"), host=host, port=port)


if __name__ == "__main__":
    main()
