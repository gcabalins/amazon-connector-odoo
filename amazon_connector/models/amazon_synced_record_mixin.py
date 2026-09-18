# -*- coding: utf-8 -*-
from odoo import models, fields


class AmazonSyncedRecordMixin(models.AbstractModel):
    """
    Mixin for any model that represents an Odoo resource created from an
    Amazon API call (a return, an order, a ticket...).

    Solves, once and for all for every child module, the problem of
    working with several Amazon accounts at the same time:

    - 'config_id': which Amazon account the record came from. Essential
      for filtering, debugging, and re-running syncs per account.
    - 'amazon_ref': the identifier Amazon gives you (ReturnId, AmazonOrderId, etc.)
    - COMPOUND uniqueness constraint (config_id + amazon_ref), not just on
      amazon_ref: two different Amazon accounts are independent ID spaces,
      so the same ID could coincidentally match across accounts without
      being the same resource.

    Usage in a child module:

        class AmazonReturn(models.Model):
            _name = 'amazon.return'
            _inherit = 'amazon.synced.record.mixin'
            _description = 'Amazon Return'

            # add only the fields specific to a return here
            order_id = fields.Char(string='Amazon Order')
            reason = fields.Char(string='Reason')
            status = fields.Selection([...])

    With this, 'amazon.return' already has config_id + amazon_ref + the
    uniqueness constraint without writing another line, and it works the
    same whether there's 1, 2, or 10 accounts.
    """
    _name = 'amazon.synced.record.mixin'
    _description = 'Mixin: record linked to an Amazon account and external reference'

    config_id = fields.Many2one(
        'amazon.connection', string='Amazon Account',
        required=True, ondelete='restrict', index=True
    )
    amazon_ref = fields.Char(
        string='Amazon Reference', required=True, index=True,
        help='Unique identifier of the resource in Amazon (ReturnId, AmazonOrderId, etc.)'
    )

    _sql_constraints = [
        ('config_amazonref_uniq', 'unique(config_id, amazon_ref)',
         'A record with this reference already exists for this Amazon account.'),
    ]
