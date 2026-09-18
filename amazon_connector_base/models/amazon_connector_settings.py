# amazon_connector/models/amazon_connector_settings.py
from odoo import models, api


class AmazonConnectorSettings(models.TransientModel):
    """
    Placeholder settings screen under Settings > Amazon Connector > Advanced.
    No config fields yet — kept here so future connector-wide options (retry
    policy, default timeouts, etc.) have a home without adding a new menu.
    """
    _name = 'amazon.connector.settings'
    _description = 'Amazon Connector advanced settings'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res.update(self.get_values())
        return res

    def get_values(self):
        return {}

    def set_values(self):
        pass
