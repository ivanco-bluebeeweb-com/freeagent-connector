# FreeAgent Connector — Connector Discovery

## Official API Landscape
FreeAgent API v2 uses resource-oriented REST endpoints:
- `GET /v2/company`: Inspect account name, currency, and tax registration.
- `GET /v2/contacts`: List customers/suppliers with query parameters `view=all|clients|suppliers`.
- `GET /v2/invoices`: Invoices with status tracking (Draft, Sent, Paid, Overdue).
- `GET /v2/bills`: Bills from suppliers.
- `GET /v2/bank_accounts`: Business bank accounts and credit cards.
- `GET /v2/tax_rates`: VAT and sales tax percentages.

## Authentication & Authorization
- **Protocol:** OAuth 2.0 Authorization Code flow or App Bearer tokens.
- **Header:** `Authorization: Bearer <token>`.
- **Headers:** `User-Agent` identifying the application.
