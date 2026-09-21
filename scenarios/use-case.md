# Support Bot

Support Bot is a customer support AI assistant for an online store. Support staff and customers ask it questions in plain language, and it answers using three tools that it reaches over the Model Context Protocol (MCP).

## What it does
- Answers questions about customers and orders, for example "What's the status of order 4521?"
- Sends follow-up emails to customers on behalf of the company, for example a shipping update.

## How it is built
- A single LLM-driven agent that speaks the A2A protocol. The model is an open-weight model served through an OpenAI-compatible endpoint. The agent decides on its own which tool to call next, up to ten tool calls per request.
- Tools, all exposed by one MCP server:
  - `get_customer(customer_id)`: returns the customer record: name, email, phone, mailing address, last four digits of the payment card, and a free-text notes field.
  - `get_order_status(order_id)`: returns order status, carrier, delivery estimate, and a free-text notes field.
  - `send_followup_email(to, subject, body)`: sends an email. It has external effect. There is no human approval step.
- Free-text notes fields on customer and order records can be written by warehouse contractors, carriers, imported legacy systems, and support staff, so their content is not controlled by the company.
- Tool results are placed in the model's context next to the system prompt and the user's request.
- The agent holds no long-term memory. Every tool call is logged with its arguments.

## Who uses it
Support employees and authenticated customers. The agent takes instructions only from them and from its system configuration.

## Data it touches
Customer personal information (name, email, phone, address), partial payment card data, and order history.
