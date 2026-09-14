# -*- coding: utf-8 -*-
import requests
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json

_logger = logging.getLogger(__name__)

# SP-API base URL per region
SP_API_ENDPOINTS = {
    'EU': 'https://sellingpartnerapi-eu.amazon.com',
    'NA': 'https://sellingpartnerapi-na.amazon.com',
    'FE': 'https://sellingpartnerapi-fe.amazon.com',
}

# URL to obtain the access token (LWA)
LWA_TOKEN_URL = 'https://api.amazon.com/auth/o2/token'

# Marketplace IDs by country
MARKETPLACE_IDS = {
    # ============================
    # EU REGION (Europe)
    # ============================

    # Spain
    'ES': 'A1RKKUPIHCS9HS',

    # Germany
    'DE': 'A1PA6795UKMFR9',

    # France
    'FR': 'A13V1IB3VIYZZH',

    # Italy
    'IT': 'APJ6JRA9NG5V4',

    # United Kingdom
    'UK': 'A1F83G8C2ARO7P',

    # Netherlands
    'NL': 'A1805IZSGTT6HS',

    # Sweden
    'SE': 'A2NODRKZP88ZB9',

    # Poland
    'PL': 'A1C3SOZRARQ6R3',

    # Turkey
    'TR': 'A33AVAJ2PDY3EV',

    # Belgium
    'BE': 'AMEN7PMS3EDWL',

    # Ireland
    'IE': 'A28R8C7NBKEWEA',

    # Egypt
    'EG': 'ARBP9OOSHTCHU',

    # South Africa
    'ZA': 'AE08WJ6YKNBMC',

    # Saudi Arabia
    'SA': 'A17E79C6D8DWNP',

    # United Arab Emirates
    'AE': 'A2VIGQ35RCS4UG',

    # India
    'IN': 'A21TJRUUN4KGV',

    # ============================
    # NA REGION (North America)
    # ============================

    # United States
    'US': 'ATVPDKIKX0DER',

    # Canada
    'CA': 'A2EUQ1WTGCTBG2',

    # Mexico
    'MX': 'A1AM78C64UM0Y8',

    # Brazil
    'BR': 'A2Q3Y263D00KWC',

    # ============================
    # FE REGION (Far East)
    # ============================

    # Japan
    'JP': 'A1VC38T7YXB528',

    # Australia
    'AU': 'A39IBJ37TRP1C6',

    # Singapore
    'SG': 'A19VAU5U5O7RUS',
}

class AmazonConnection(models.Model):
    """
    Amazon SP-API connection configuration.
    Stores the credentials and manages access tokens.

    Usage from other modules:
        config = self.env['amazon.connection'].get_active_config()
        response = config.call('/orders/v0/orders', params={'MarketplaceIds': 'A1RKKUPIHCS9HS'})
    """
    _name = 'amazon.connection'
    _description = 'Amazon SP-API connection'
    _rec_name = 'name'

    # ─── Identification ────────────────────────────────────────────
    name = fields.Char(
        string='Profile Name',
        required=True,
        default='My Amazon Account',
        help='Descriptive name to identify this configuration.'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    is_default = fields.Boolean(
        string='Default Configuration',
        default=False,
        help='If checked, this profile is used when no specific one is specified.'
    )

    # ─── LWA (Login With Amazon) credentials ──────────────────────
    # Obtained in Seller Central > Develop Apps > your app > LWA credentials
    lwa_client_id = fields.Char(
        string='LWA Client ID',
        required=True,
        help='Client Identifier of your application. Format: amzn1.application-oa2-client.xxx'
    )
    lwa_client_secret = fields.Char(
        string='LWA Client Secret',
        required=True,
        help='Client Secret of your application in Seller Central.'
    )
    refresh_token = fields.Char(
        string='Refresh Token',
        required=True,
        help='Refresh token generated when authorizing the app. Format: Atzr|IwEB...'
    )

    # ─── Region and marketplace configuration ─────────────────────
    region = fields.Selection(
        selection=[('EU', 'Europe (EU)'), ('NA', 'North America (NA)'), ('FE', 'Far East (FE)')],
        string='Region',
        required=True,
        default='EU',
        help='Region of your seller account. Spain → EU'
    )
    marketplace_country = fields.Selection(
        selection=[(k, k) for k in MARKETPLACE_IDS.keys()],
        string='Marketplace Country',
        required=True,
        default='ES',
        help='Main country of the marketplace you sell on.'
    )
    marketplace_id = fields.Char(
        string='Marketplace ID',
        compute='_compute_marketplace_id',
        store=True,
        help="Amazon's internal ID for the selected marketplace."
    )

    # ─── Access token (managed automatically) ─────────────────────
    # Not shown to the end user; managed internally by the system
    access_token = fields.Char(string='Access Token (internal)', copy=False)
    token_expiry = fields.Datetime(string='Token Expiry', copy=False)

    # ─── Connection status ─────────────────────────────────────────
    connection_state = fields.Selection(
        selection=[
            ('not_tested', 'Not Tested'),
            ('ok', 'Connected'),
            ('error', 'Error'),
        ],
        string='Status',
        default='not_tested',
        readonly=True
    )
    last_error = fields.Text(string='Last Error', readonly=True)

    # ──────────────────────────────────────────────────────────────
    # COMPUTED METHODS
    # ──────────────────────────────────────────────────────────────

    @api.depends('marketplace_country')
    def _compute_marketplace_id(self):
        for rec in self:
            rec.marketplace_id = MARKETPLACE_IDS.get(rec.marketplace_country, '')

    # ──────────────────────────────────────────────────────────────
    # PUBLIC API: methods used by other modules
    # ──────────────────────────────────────────────────────────────

    @api.model
    def get_active_config(self):
        """
        Returns the default active configuration.
        Use this in other modules when you don't need to target a specific profile.

        Example:
            config = self.env['amazon.connection'].get_active_config()
        """
        config = self.search([('is_default', '=', True), ('active', '=', True)], limit=1)
        if not config:
            config = self.search([('active', '=', True)], limit=1)
        if not config:
            raise UserError(_('There is no active Amazon configuration. '
                               'Go to Amazon > Settings to add your credentials.'))
        return config

    @api.model
    def get_all_active_configs(self):
        """
        Returns ALL active Amazon accounts (a recordset with 0, 1, 2... N records).
        Use this in modules that need to process every configured account
        (returns sync, orders sync, etc.) regardless of how many there are.

        Typical usage in a child module's cron job:
            for config in self.env['amazon.connection'].get_all_active_configs():
                for page in config.call_paginated('/returns/v0/returns', params={...}):
                    ...  # create/update records, always tagged with config.id

        Adding a third or fourth Amazon account never requires touching any code:
        just create a new 'amazon.connection' record.
        """
        return self.search([('active', '=', True)])

    def call(self, endpoint, method='GET', params=None, body=None, extra_headers=None):
        """
        Makes a call to the Amazon SP-API.

        Args:
            endpoint      (str)  : Endpoint path. E.g. '/orders/v0/orders'
            method        (str)  : HTTP method: 'GET', 'POST', 'PUT', 'DELETE'. Defaults to 'GET'.
            params        (dict) : Query parameters. E.g. {'MarketplaceIds': 'A1RKKUPIHCS9HS'}
            body          (dict) : Request body for POST/PUT (sent as JSON).
            extra_headers (dict) : Extra headers, if the endpoint needs any.

        Returns:
            dict : Amazon's response, already parsed as JSON.

        Raises:
            UserError on authentication failure or a non-OK response.

        Example usage from another module:
            config = self.env['amazon.connection'].get_active_config()

            # Get orders from the last 7 days
            response = config.call(
                '/orders/v0/orders',
                params={
                    'MarketplaceIds': config.marketplace_id,
                    'CreatedAfter': '2024-01-01T00:00:00Z',
                }
            )
            orders = response.get('payload', {}).get('Orders', [])
        """
        self.ensure_one()

        # 1. Get a valid token (refreshes it if expired)
        token = self._get_valid_access_token()

        # 2. Build the full URL
        base_url = SP_API_ENDPOINTS.get(self.region)
        url = f"{base_url}{endpoint}"

        # 3. Build headers
        headers = {
            'x-amz-access-token': token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if extra_headers:
            headers.update(extra_headers)

        # 4. Make the request
        _logger.info("Amazon SP-API → %s %s", method, url)
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params or {},
                json=body,
                timeout=30,
            )
        except requests.exceptions.Timeout:
            self._log_call(endpoint, method, params, None, 'error', 'Timeout after 30 seconds')
            raise UserError(_('The call to Amazon took too long (timeout). Please try again.'))
        except requests.exceptions.ConnectionError as e:
            self._log_call(endpoint, method, params, None, 'error', str(e))
            raise UserError(_('Could not connect to Amazon. Check your internet connection.'))

        # 5. Parse and return the response
        return self._handle_response(response, endpoint, method, params, body)

    def call_paginated(self, endpoint, params=None, method='GET', next_token_param='NextToken',
                        next_token_only=True, max_pages=100):
        """
        Generator that automatically handles SP-API pagination.
        Many endpoints (returns, orders, reports, inventory...) return a
        'NextToken' in the payload when more pages of results are available.

        Args:
            endpoint          (str)  : Endpoint path. E.g. '/returns/v0/returns'
            params            (dict) : Parameters for the first call.
            method            (str)  : HTTP method. Defaults to 'GET'.
            next_token_param  (str)  : Name of the pagination field in Amazon's
                                        response. Defaults to 'NextToken' (some
                                        endpoints use lowercase 'nextToken': check
                                        the docs for the specific endpoint).
            next_token_only   (bool) : If True (the usual SP-API behavior), calls
                                        for subsequent pages are made ONLY with the
                                        NextToken, dropping the rest of the original
                                        filters. If the endpoint requires keeping a
                                        filter alongside the NextToken, set this to False.
            max_pages         (int)  : Safety limit to avoid infinite loops.

        Usage from a child module (e.g. returns):
            config = self.env['amazon.connection'].browse(config_id)
            for payload in config.call_paginated('/returns/v0/returns', params={
                'MarketplaceIds': config.marketplace_id,
                'CreatedAfter': date_from,
            }):
                for item in payload.get('ReturnItems', []):
                    # create/update the Odoo record, always with config_id=config.id
                    ...

        Does not raise on its own: errors from 'call()' propagate as usual
        (UserError), interrupting the pagination.
        """
        self.ensure_one()
        current_params = dict(params or {})
        pages_fetched = 0

        while True:
            pages_fetched += 1
            response = self.call(endpoint, method=method, params=current_params)
            payload = response.get('payload', response) if isinstance(response, dict) else response
            yield payload

            next_token = payload.get(next_token_param) if isinstance(payload, dict) else None
            if not next_token or pages_fetched >= max_pages:
                break

            current_params = {next_token_param: next_token} if next_token_only else {
                **current_params, next_token_param: next_token
            }

    # ──────────────────────────────────────────────────────────────
    # TOKEN MANAGEMENT (internal use)
    # ──────────────────────────────────────────────────────────────

    def _get_valid_access_token(self):
        """
        Returns a valid access token.
        If the current token has expired (or has less than 5 minutes left),
        requests a new one. Amazon access tokens expire after 60 minutes.
        """
        self.ensure_one()
        now = datetime.utcnow()
        margin = timedelta(minutes=5)  # Renew 5 minutes before it expires

        if self.access_token and self.token_expiry:
            expiry = fields.Datetime.from_string(self.token_expiry)
            if now < (expiry - margin):
                return self.access_token  # Token still valid

        # We need a new token
        return self._refresh_access_token()

    def _refresh_access_token(self):
        """
        Requests a new access token from Amazon using the refresh token (LWA).
        Stores the token and its expiry date in the database.
        """
        self.ensure_one()
        _logger.info("Refreshing Amazon access token for profile '%s'", self.name)

        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.lwa_client_id,
            'client_secret': self.lwa_client_secret,
        }

        try:
            response = requests.post(LWA_TOKEN_URL, data=payload, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_msg = f'Error getting token from Amazon: {e}'
            _logger.error(error_msg)
            self.write({'connection_state': 'error', 'last_error': error_msg})
            raise UserError(_(error_msg))

        data = response.json()

        if 'access_token' not in data:
            error_msg = f"Amazon did not return an access_token. Response: {data}"
            self.write({'connection_state': 'error', 'last_error': error_msg})
            raise UserError(_('Authentication error with Amazon. Check your LWA credentials.'))

        # Save the new token (expires in expires_in seconds, usually 3600, one hour)
        expires_in = data.get('expires_in', 3600)
        expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        self.write({
            'access_token': data['access_token'],
            'token_expiry': fields.Datetime.to_string(expiry),
            'connection_state': 'ok',
            'last_error': False,
        })

        _logger.info("Token refreshed. Valid until: %s", expiry)
        return data['access_token']

    # ──────────────────────────────────────────────────────────────
    # RESPONSE AND ERROR HANDLING
    # ──────────────────────────────────────────────────────────────

    def _handle_response(self, response, endpoint, method, params, body=None):
        """Processes the HTTP response and raises clear errors if something fails."""
        try:
            data = response.json()
        except Exception:
            data = {'raw': response.text}

        if response.status_code in (200, 202):
            self._log_call(endpoint, method, params, response.status_code, 'ok', body=body)
            return data

        # Known SP-API errors
        error_messages = {
            400: 'Bad request (400). Check the parameters sent.',
            401: 'Unauthorized (401). The token may have expired or the credentials are incorrect.',
            403: 'Access denied (403). Your application does not have permission for this endpoint.',
            404: 'Resource not found (404). The endpoint or resource does not exist.',
            429: 'Too many requests (429). Amazon has throttled access. Wait a few seconds.',
            500: 'Internal Amazon error (500). Please try again later.',
        }

        error_detail = data.get('errors', [{}])[0].get('message', response.text) if isinstance(data, dict) else response.text
        error_full_detail = data.get('errors', [{}])[0].get('details', '') if isinstance(data, dict) else ''

        base_msg = error_messages.get(response.status_code, f'HTTP Error {response.status_code}')

        # Main message
        full_msg = f"{base_msg}\nDetail: {error_detail}"

        # Extended message if 'details' is present
        if error_full_detail:
            full_msg += f"\nAdditional details: {error_full_detail}"

        # Log
        self._log_call(endpoint, method, params, response.status_code, 'error', full_msg, body=body)
        _logger.error("Amazon SP-API error: %s", full_msg)

        # Raise error to the UI
        raise UserError(_(full_msg))


    # ──────────────────────────────────────────────────────────────
    # CALL LOGGING
    # ──────────────────────────────────────────────────────────────

    def _log_call(self, endpoint, method, params, status_code, state, error_msg=None, body=None):
        data = body if body else params
        self.env['amazon.api.log'].sudo().create({
            'config_id': self.id,
            'endpoint': endpoint,
            'method': method,
            'params': json.dumps(data, indent=4, ensure_ascii=False) if data else '',
            'http_status': status_code,
            'state': state,
            'error_message': error_msg or '',
        })

    # ──────────────────────────────────────────────────────────────
    # UI ACTIONS
    # ──────────────────────────────────────────────────────────────

    def action_test_connection(self):
        """'Test connection' button in the UI. Calls a lightweight endpoint to verify."""
        self.ensure_one()
        try:
            # Marketplace participations endpoint: lightweight and always available
            self.call('/sellers/v1/marketplaceParticipations')
            self.write({'connection_state': 'ok', 'last_error': False})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection successful'),
                    'message': _('The connection to the Amazon SP-API works correctly.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except UserError as e:
            self.write({'connection_state': 'error', 'last_error': str(e)})
            raise
