# Amazon Connector

Base Odoo 16 module for the Amazon Selling Partner API (SP-API). Handles
authentication, token refresh, and generic call/pagination so other modules
don't have to.

This module is **not functional on its own** for any business process — it's
infrastructure that concrete modules (returns, orders, inventory reports...)
build on top of.

## Features

- Multi-account: connect as many Amazon seller profiles as you need, each with
  its own LWA credentials and region (EU / NA / FE).
- Automatic access token refresh (SP-API tokens expire every 60 minutes).
- Generic `call()` / `call_paginated()` methods any child module can use —
  adding a module never means re-implementing auth or pagination.
- Editable marketplace catalog (country + Marketplace ID) instead of hardcoded
  constants in Python.
- Full API call log (endpoint, params, HTTP status, error) for debugging, with
  a monthly cleanup cron and a manual "clean old logs" wizard.
- `amazon.synced.record.mixin` for child modules: gives any model a
  `config_id` + `amazon_ref` pair with the right compound uniqueness
  constraint out of the box, so records stay correctly scoped per Amazon
  account.

## Requirements

- Odoo 16 Community
- An Amazon Seller Central app with SP-API access (Client ID, Client Secret,
  and an authorized Refresh Token)
- Python `requests` (already an Odoo dependency)

## Installation

1. Drop the `amazon_connector` folder into your addons path.
2. Update the apps list and install **Amazon Connector**.
3. Go to **Amazon Connector → Connector Settings → API Connections** and
   create a record with your LWA credentials.

## Configuration

**Amazon Connector → Connector Settings**:

| Menu | What it's for |
|---|---|
| API Connections | Register each Amazon account: LWA Client ID/Secret, Refresh Token, region, default marketplace. |
| Marketplaces | Catalog of country + Marketplace ID. Assign the ones each account operates in from that account's form. |
| API Call Log | History of every SP-API call made, with status and error detail. |
| Advanced Settings | Placeholder for future connector-wide options. |

Credentials are obtained in **Seller Central → Apps and Services → Develop
Apps → your app → LWA credentials**. The Refresh Token is generated from that
app's *Authorize* section.

## Usage from a child module

```python
config = self.env['amazon.connection'].get_active_config()

response = config.call(
    '/orders/v0/orders',
    params={
        'MarketplaceIds': config.marketplace_id,
        'CreatedAfter': '2024-01-01T00:00:00Z',
    },
)
orders = response.get('payload', {}).get('Orders', [])
```

Paginated endpoints:

```python
for config in self.env['amazon.connection'].get_all_active_configs():
    for payload in config.call_paginated('/returns/v0/returns', params={
        'MarketplaceIds': config.marketplace_id,
        'CreatedAfter': date_from,
    }):
        for item in payload.get('ReturnItems', []):
            ...  # create/update, always tagged with config.id
```

Models that store a resource synced from Amazon should inherit the mixin
instead of adding `config_id` / uniqueness constraints by hand:

```python
class AmazonReturn(models.Model):
    _name = 'amazon.return'
    _inherit = 'amazon.synced.record.mixin'
    _description = 'Amazon Return'

    order_id = fields.Char(string='Amazon Order')
    reason = fields.Char(string='Reason')
```

## Models

| Model | Purpose |
|---|---|
| `amazon.connection` | Stores credentials per account, manages the access token, exposes `call()` / `call_paginated()`. |
| `amazon.marketplace` | Editable catalog of country ↔ Marketplace ID. |
| `amazon.api.log` | One row per SP-API call, success or failure. |
| `amazon.synced.record.mixin` | Abstract mixin for child-module records tied to an Amazon account. |
| `amazon.connector.settings` | Empty settings placeholder for future connector-wide options. |

## License

LGPL-3
