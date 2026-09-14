# -*- coding: utf-8 -*-
from odoo import models, fields


class AmazonMarketplace(models.Model):
    """
    Editable catalog of Amazon marketplaces. Replaces a fixed
    EU_MARKETPLACES-style list in Python: adding, removing, or disabling a
    marketplace becomes a data change (UI), not a code change.

    Lives in the base connector (not in a specific child module) because
    several independent child modules (returns, weekly RMA report, and
    whatever comes next) all need the same thing: knowing which
    marketplaces each Amazon account operates in. Each one reads it from
    'amazon.connection.marketplace_ids' without depending on one another.
    """
    _name = 'amazon.marketplace'
    _description = 'Amazon Marketplace'
    _order = 'code'

    active = fields.Boolean(string='Active', default=True)
    code = fields.Char(string='Country', required=True, size=2,
                        help="2-letter country code. E.g. ES, DE, FR, IT, UK.")
    name = fields.Char(string='Name', required=True)
    marketplace_id = fields.Char(
        string='Marketplace ID (Amazon)', required=True,
        help="Amazon's internal ID for this marketplace, e.g. A1RKKUPIHCS9HS (Spain)."
    )

    _sql_constraints = [
        ('marketplace_id_uniq', 'unique(marketplace_id)',
         'A marketplace with this Marketplace ID already exists.'),
    ]

    def name_get(self):
        return [(rec.id, f'{rec.code} — {rec.name}') for rec in self]


class AmazonConnectionMarketplaceConfig(models.Model):
    """
    Extends the Amazon account so each one declares, from the UI, which
    marketplaces it operates in. A typical EU account can cover ES, DE, FR,
    IT, UK with the same credentials; another account (another API key)
    might cover a different subset. Adding a third account never requires
    touching any child module's code: just create the account and check
    its marketplaces.

    This is a single, shared field: if the same Amazon account operates in
    ES/DE/FR, both the returns module (helpdesk/RMA) and the weekly RMA
    report use the SAME list, because conceptually it's the same piece of
    data ("where does this account sell"), not something that depends on
    which module reads it.
    """
    _inherit = 'amazon.connection'

    marketplace_ids = fields.Many2many(
        'amazon.marketplace',
        string='Marketplaces',
        help='Marketplaces this account operates in. Child modules '
             '(returns, weekly RMA report, etc.) read this list to know '
             'which marketplaces to request reports for from Amazon.'
    )
