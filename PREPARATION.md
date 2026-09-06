# FreeAgent Connector — Preparation

## Product Scope
Build a comprehensive Imperal connector for **FreeAgent** (C27. Accounting & Bookkeeping). The integration connects directly to the official **FreeAgent REST API v2** (`https://api.freeagent.com/v2` and sandbox `https://api.sandbox.freeagent.com/v2`), allowing UK and international businesses to manage contacts, invoices, bills, bank accounts, and tax rates.

## Official API Specifications
- **API Version:** FreeAgent REST API v2
- **Base URLs:**
  - Production: `https://api.freeagent.com/v2`
  - Sandbox: `https://api.sandbox.freeagent.com/v2`
- **Authentication Model:** OAuth 2.0 Bearer Token in `Authorization: Bearer <token>`
- **HTTP Headers:** `Accept: application/json`, `Content-Type: application/json`
- **Target Resources:**
  - `contacts`: Customers and suppliers
  - `invoices`: Sales invoices
  - `bills`: Vendor bills and expenses
  - `bank_accounts`: Bank ledger accounts
  - `tax_rates`: Sales tax and VAT rates
- **Mandatory Requirements:**
  - Environment switching (Production vs Sandbox, Standard B7).
  - Explicit rate limit detection (HTTP 429) and auth classification (HTTP 401/403).
  - Sanitization of Bearer tokens in exception traces (Standard B8).
  - Multi-tenant connection tracking via `connection_id` (Standard B9).

## Delivery Gates
1. [x] Official API discovery completed with FreeAgent REST API v2 specifications.
2. [x] Production vs Sandbox environment routing verified.
3. [x] Five mandatory specification documents authored.
4. [x] Client implemented with B7-B10 compliance, secret redaction, and 429/401 classification.
5. [x] Panel sidebar implemented conforming to UI_INTERFACE_STANDARD.md.
6. [x] Action prices calibrated per PRICING_POLICY.md.
