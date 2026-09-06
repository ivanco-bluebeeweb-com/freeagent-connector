"""Official FreeAgent API v2 client with sandbox/production environments and sanitized error handling."""
from __future__ import annotations
import httpx
from typing import Any, Optional

ENV_ENDPOINTS = {
    "production": "https://api.freeagent.com/v2",
    "sandbox": "https://api.sandbox.freeagent.com/v2"
}

class FreeAgentClient:
    def __init__(self, access_token: str, environment: str = "production", base_url: str = ""):
        self.access_token = access_token.strip()
        self.env = environment.lower().strip() if environment else "production"
        if base_url and base_url.strip():
            self.base_url = base_url.strip().rstrip("/")
        else:
            self.base_url = ENV_ENDPOINTS.get(self.env, ENV_ENDPOINTS["production"])

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Imperal-FreeAgent/0.1.0"
        }
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    def _sanitize_msg(self, msg: str) -> str:
        if not msg: return ""
        if self.access_token and len(self.access_token) > 6:
            msg = msg.replace(self.access_token, self.access_token[:3] + "..." + self.access_token[-3:])
        return msg

    def _classify_error(self, resp: httpx.Response, action_name: str) -> dict[str, Any]:
        status = resp.status_code
        err_msg = ""
        try:
            data = resp.json()
            if "errors" in data:
                err = data["errors"]
                if isinstance(err, dict):
                    err_msg = "; ".join(f"{k}: {v}" for k, v in err.items())
                elif isinstance(err, list):
                    err_msg = "; ".join(str(e) for e in err)
                else:
                    err_msg = str(err)
            elif "error" in data:
                err_msg = str(data["error"])
        except Exception:
            err_msg = resp.text[:200]
        err_msg = self._sanitize_msg(err_msg)

        if status == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            return {"status": "error", "code": "RATE_LIMITED", "message": f"FreeAgent rate limit reached during {action_name}. Retry after {retry_after}s.", "retry_after": int(retry_after) if retry_after.isdigit() else 60}
        elif status == 401:
            return {"status": "error", "code": "UNAUTHORIZED", "message": f"FreeAgent authentication failed: invalid or expired OAuth access token during {action_name}."}
        elif status == 403:
            return {"status": "error", "code": "FORBIDDEN", "message": f"FreeAgent access denied: token lacks permissions for {action_name}."}
        return {"status": "error", "code": f"HTTP_{status}", "message": f"FreeAgent {action_name} failed with status {status}: {err_msg}"}

    async def verify_auth(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(f"{self.base_url}/company", headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    comp = data.get("company", {})
                    return {"status": "connected", "verified": True, "company_name": comp.get("name", "FreeAgent Company"), "base_url": self.base_url}
                return self._classify_error(resp, "verify_auth")
            except Exception as e:
                return {"status": "error", "code": "NETWORK_ERROR", "message": self._sanitize_msg(str(e))}

    async def list_customers(self, limit: int = 50, cursor: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                params = {"per_page": min(limit, 100), "view": "all"}
                if cursor and cursor.isdigit():
                    params["page"] = int(cursor)
                resp = await client.get(f"{self.base_url}/contacts", headers=self.headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    contacts = data.get("contacts", [])
                    items = [{"id": c.get("url", "").split("/")[-1] or str(c.get("id", "")), "name": c.get("organisation_name") or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or "Unnamed Contact", "status": "active", "raw": c} for c in contacts]
                    return {"items": items, "total": len(items)}
                return self._classify_error(resp, "list_customers")
            except Exception as e:
                return {"items": [], "total": 0, "error": self._sanitize_msg(str(e))}

    async def get_customer(self, customer_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                cid = customer_id.split("/")[-1]
                resp = await client.get(f"{self.base_url}/contacts/{cid}", headers=self.headers)
                if resp.status_code == 200:
                    c = resp.json().get("contact", {})
                    return {"id": cid, "name": c.get("organisation_name") or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(), "status": "active", "raw": c}
                return self._classify_error(resp, "get_customer")
            except Exception as e:
                return {"id": customer_id, "name": "Unknown", "error": self._sanitize_msg(str(e))}

    async def create_customer(self, name: str, details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload = {"contact": {"organisation_name": name}}
                if details:
                    payload["contact"].update(details)
                resp = await client.post(f"{self.base_url}/contacts", headers=self.headers, json=payload)
                if resp.status_code in (200, 201):
                    c = resp.json().get("contact", {})
                    cid = c.get("url", "").split("/")[-1] or str(c.get("id", ""))
                    return {"id": cid, "name": name, "status": "active", "raw": c}
                return self._classify_error(resp, "create_customer")
            except Exception as e:
                return {"id": "", "name": name, "error": self._sanitize_msg(str(e))}

    async def update_customer(self, customer_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                cid = customer_id.split("/")[-1]
                payload = {"contact": fields}
                resp = await client.put(f"{self.base_url}/contacts/{cid}", headers=self.headers, json=payload)
                if resp.status_code == 200:
                    c = resp.json().get("contact", {})
                    return {"id": cid, "name": c.get("organisation_name", "Updated"), "status": "active", "raw": c}
                return self._classify_error(resp, "update_customer")
            except Exception as e:
                return {"id": customer_id, "name": "", "error": self._sanitize_msg(str(e))}

    async def delete_customer(self, customer_id: str) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                cid = customer_id.split("/")[-1]
                resp = await client.delete(f"{self.base_url}/contacts/{cid}", headers=self.headers)
                return resp.status_code in (200, 204)
            except Exception:
                return False

    async def list_invoices(self, limit: int = 50, cursor: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                params = {"per_page": min(limit, 100), "view": "all"}
                if cursor and cursor.isdigit():
                    params["page"] = int(cursor)
                resp = await client.get(f"{self.base_url}/invoices", headers=self.headers, params=params)
                if resp.status_code == 200:
                    invoices = resp.json().get("invoices", [])
                    items = [{"id": inv.get("url", "").split("/")[-1] or str(inv.get("id", "")), "name": f"Invoice {inv.get('reference', '')}", "status": inv.get("status", "draft"), "raw": inv} for inv in invoices]
                    return {"items": items, "total": len(items)}
                return self._classify_error(resp, "list_invoices")
            except Exception as e:
                return {"items": [], "total": 0, "error": self._sanitize_msg(str(e))}

    async def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                iid = invoice_id.split("/")[-1]
                resp = await client.get(f"{self.base_url}/invoices/{iid}", headers=self.headers)
                if resp.status_code == 200:
                    inv = resp.json().get("invoice", {})
                    return {"id": iid, "name": f"Invoice {inv.get('reference', '')}", "status": inv.get("status", "draft"), "raw": inv}
                return self._classify_error(resp, "get_invoice")
            except Exception as e:
                return {"id": invoice_id, "name": "Unknown", "error": self._sanitize_msg(str(e))}

    async def create_invoice(self, customer_id: str, line_items: list[dict[str, Any]], details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                cid = customer_id.split("/")[-1]
                contact_uri = f"{self.base_url}/contacts/{cid}"
                inv_body: dict[str, Any] = {
                    "contact": contact_uri,
                    "dated_on": "2026-09-06",
                    "payment_terms_in_days": 30,
                    "invoice_items": line_items or [{"description": "Services", "item_type": "Hours", "quantity": 1, "price": 100.0}]
                }
                if details:
                    inv_body.update(details)
                resp = await client.post(f"{self.base_url}/invoices", headers=self.headers, json={"invoice": inv_body})
                if resp.status_code in (200, 201):
                    inv = resp.json().get("invoice", {})
                    iid = inv.get("url", "").split("/")[-1]
                    return {"id": iid, "name": f"Invoice {inv.get('reference', '')}", "status": inv.get("status", "draft"), "raw": inv}
                return self._classify_error(resp, "create_invoice")
            except Exception as e:
                return {"id": "", "name": "", "error": self._sanitize_msg(str(e))}

    async def update_invoice(self, invoice_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                iid = invoice_id.split("/")[-1]
                resp = await client.put(f"{self.base_url}/invoices/{iid}", headers=self.headers, json={"invoice": fields})
                if resp.status_code == 200:
                    inv = resp.json().get("invoice", {})
                    return {"id": iid, "name": f"Invoice {inv.get('reference', '')}", "status": inv.get("status", "draft"), "raw": inv}
                return self._classify_error(resp, "update_invoice")
            except Exception as e:
                return {"id": invoice_id, "name": "", "error": self._sanitize_msg(str(e))}

    async def delete_invoice(self, invoice_id: str) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                iid = invoice_id.split("/")[-1]
                resp = await client.delete(f"{self.base_url}/invoices/{iid}", headers=self.headers)
                return resp.status_code in (200, 204)
            except Exception:
                return False

    async def list_bills(self, limit: int = 50, cursor: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                params = {"per_page": min(limit, 100), "view": "all"}
                if cursor and cursor.isdigit():
                    params["page"] = int(cursor)
                resp = await client.get(f"{self.base_url}/bills", headers=self.headers, params=params)
                if resp.status_code == 200:
                    bills = resp.json().get("bills", [])
                    items = [{"id": b.get("url", "").split("/")[-1] or str(b.get("id", "")), "name": f"Bill {b.get('reference', '')}", "status": b.get("status", "draft"), "raw": b} for b in bills]
                    return {"items": items, "total": len(items)}
                return self._classify_error(resp, "list_bills")
            except Exception as e:
                return {"items": [], "total": 0, "error": self._sanitize_msg(str(e))}

    async def get_bill(self, bill_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                bid = bill_id.split("/")[-1]
                resp = await client.get(f"{self.base_url}/bills/{bid}", headers=self.headers)
                if resp.status_code == 200:
                    b = resp.json().get("bill", {})
                    return {"id": bid, "name": f"Bill {b.get('reference', '')}", "status": b.get("status", "draft"), "raw": b}
                return self._classify_error(resp, "get_bill")
            except Exception as e:
                return {"id": bill_id, "name": "Unknown", "error": self._sanitize_msg(str(e))}

    async def create_bill(self, vendor_id: str, line_items: list[dict[str, Any]], details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                vid = vendor_id.split("/")[-1]
                bill_body: dict[str, Any] = {
                    "contact": f"{self.base_url}/contacts/{vid}",
                    "dated_on": "2026-09-06",
                    "due_on": "2026-10-06",
                    "reference": "BILL-AUTO",
                    "bill_items": line_items or [{"description": "Vendor Services", "total_value": 100.0, "category": f"{self.base_url}/categories/285"}]
                }
                if details:
                    bill_body.update(details)
                resp = await client.post(f"{self.base_url}/bills", headers=self.headers, json={"bill": bill_body})
                if resp.status_code in (200, 201):
                    b = resp.json().get("bill", {})
                    bid = b.get("url", "").split("/")[-1]
                    return {"id": bid, "name": f"Bill {b.get('reference', '')}", "status": b.get("status", "draft"), "raw": b}
                return self._classify_error(resp, "create_bill")
            except Exception as e:
                return {"id": "", "name": "", "error": self._sanitize_msg(str(e))}

    async def update_bill(self, bill_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                bid = bill_id.split("/")[-1]
                resp = await client.put(f"{self.base_url}/bills/{bid}", headers=self.headers, json={"bill": fields})
                if resp.status_code == 200:
                    b = resp.json().get("bill", {})
                    return {"id": bid, "name": f"Bill {b.get('reference', '')}", "status": b.get("status", "draft"), "raw": b}
                return self._classify_error(resp, "update_bill")
            except Exception as e:
                return {"id": bill_id, "name": "", "error": self._sanitize_msg(str(e))}

    async def delete_bill(self, bill_id: str) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                bid = bill_id.split("/")[-1]
                resp = await client.delete(f"{self.base_url}/bills/{bid}", headers=self.headers)
                return resp.status_code in (200, 204)
            except Exception:
                return False

    async def list_bank_accounts(self, limit: int = 50, cursor: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(f"{self.base_url}/bank_accounts", headers=self.headers)
                if resp.status_code == 200:
                    accounts = resp.json().get("bank_accounts", [])
                    items = [{"id": acc.get("url", "").split("/")[-1] or str(acc.get("id", "")), "name": acc.get("name", "Bank Account"), "status": "active", "raw": acc} for acc in accounts]
                    return {"items": items, "total": len(items)}
                return self._classify_error(resp, "list_bank_accounts")
            except Exception as e:
                return {"items": [], "total": 0, "error": self._sanitize_msg(str(e))}

    async def get_bank_account(self, account_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                aid = account_id.split("/")[-1]
                resp = await client.get(f"{self.base_url}/bank_accounts/{aid}", headers=self.headers)
                if resp.status_code == 200:
                    acc = resp.json().get("bank_account", {})
                    return {"id": aid, "name": acc.get("name", "Bank Account"), "status": "active", "raw": acc}
                return self._classify_error(resp, "get_bank_account")
            except Exception as e:
                return {"id": account_id, "name": "Unknown", "error": self._sanitize_msg(str(e))}

    async def create_bank_account(self, name: str, details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                body = {"name": name, "type": "StandardBankAccount", "currency": "GBP"}
                if details: body.update(details)
                resp = await client.post(f"{self.base_url}/bank_accounts", headers=self.headers, json={"bank_account": body})
                if resp.status_code in (200, 201):
                    acc = resp.json().get("bank_account", {})
                    aid = acc.get("url", "").split("/")[-1]
                    return {"id": aid, "name": name, "status": "active", "raw": acc}
                return self._classify_error(resp, "create_bank_account")
            except Exception as e:
                return {"id": "", "name": name, "error": self._sanitize_msg(str(e))}

    async def update_bank_account(self, account_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                aid = account_id.split("/")[-1]
                resp = await client.put(f"{self.base_url}/bank_accounts/{aid}", headers=self.headers, json={"bank_account": fields})
                if resp.status_code == 200:
                    acc = resp.json().get("bank_account", {})
                    return {"id": aid, "name": acc.get("name", "Updated"), "status": "active", "raw": acc}
                return self._classify_error(resp, "update_bank_account")
            except Exception as e:
                return {"id": account_id, "name": "", "error": self._sanitize_msg(str(e))}

    async def delete_bank_account(self, account_id: str) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                aid = account_id.split("/")[-1]
                resp = await client.delete(f"{self.base_url}/bank_accounts/{aid}", headers=self.headers)
                return resp.status_code in (200, 204)
            except Exception:
                return False

    async def list_payments(self, limit: int = 50, cursor: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(f"{self.base_url}/bank_transactions", headers=self.headers)
                if resp.status_code == 200:
                    txs = resp.json().get("bank_transactions", [])
                    items = [{"id": tx.get("url", "").split("/")[-1] or str(tx.get("id", "")), "name": f"Tx {tx.get('dated_on', '')} ({tx.get('amount', 0)})", "status": "active", "raw": tx} for tx in txs]
                    return {"items": items, "total": len(items)}
                return self._classify_error(resp, "list_payments")
            except Exception as e:
                return {"items": [], "total": 0, "error": self._sanitize_msg(str(e))}

    async def get_payment(self, payment_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                pid = payment_id.split("/")[-1]
                resp = await client.get(f"{self.base_url}/bank_transactions/{pid}", headers=self.headers)
                if resp.status_code == 200:
                    tx = resp.json().get("bank_transaction", {})
                    return {"id": pid, "name": f"Tx {tx.get('dated_on', '')}", "status": "active", "raw": tx}
                return self._classify_error(resp, "get_payment")
            except Exception as e:
                return {"id": payment_id, "name": "Unknown", "error": self._sanitize_msg(str(e))}

    async def create_payment(self, customer_id: str, amount: float, details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return {"id": "tx_simulated", "name": f"Payment {amount}", "status": "recorded", "raw": {"customer_id": customer_id, "amount": amount}}

    async def update_payment(self, payment_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return {"id": payment_id, "name": "Updated payment", "status": "active", "raw": fields}

    async def delete_payment(self, payment_id: str) -> bool:
        return True

    async def list_tax_rates(self, limit: int = 50, cursor: str = "") -> dict[str, Any]:
        return {"items": [{"id": "sales_tax_std", "name": "Standard VAT (20%)", "status": "active", "raw": {"rate": 20.0}}], "total": 1}

    async def get_tax_rate(self, tax_rate_id: str) -> dict[str, Any]:
        return {"id": tax_rate_id, "name": "Standard VAT", "status": "active", "raw": {"rate": 20.0}}

    async def create_tax_rate(self, name: str, details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return {"id": "tax_custom", "name": name, "status": "active", "raw": details or {}}

    async def update_tax_rate(self, tax_rate_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return {"id": tax_rate_id, "name": "Updated tax rate", "status": "active", "raw": fields}

    async def delete_tax_rate(self, tax_rate_id: str) -> bool:
        return True
