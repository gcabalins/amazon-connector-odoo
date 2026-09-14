# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 30

class AmazonApiLog(models.Model):
    """
    Record of every call made to the Amazon SP-API.
    Used to debug errors and audit API usage across all connected accounts.

    One log entry is created per call to `amazon.connection.call()`,
    whether it succeeds or fails, so failures are traceable even without
    reproducing the original request.
    """
    _name = 'amazon.api.log'
    _description = 'Amazon SP-API call log'
    _order = 'create_date desc'
    _rec_name = 'endpoint'

    config_id = fields.Many2one('amazon.connection', string='Amazon Profile', ondelete='cascade')
    endpoint = fields.Char(string='Endpoint', readonly=True)
    method = fields.Char(string='HTTP Method', readonly=True)
    params = fields.Text(string='Parameters', readonly=True)
    http_status = fields.Integer(string='HTTP Status', readonly=True)
    state = fields.Selection(
        selection=[('ok', 'OK'), ('error', 'Error')],
        string='Result',
        readonly=True
    )
    error_message = fields.Text(string='Error Message', readonly=True)
    create_date = fields.Datetime(string='Date')

    @api.model
    def action_clean_old_logs(self, days=DEFAULT_RETENTION_DAYS):
        """Delete log entries older than `days` and return how many were removed."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        old_logs = self.search([('create_date', '<', fields.Datetime.to_string(cutoff))])
        count = len(old_logs)
        old_logs.unlink()
        return count

    def action_clean_logs_wizard(self):
        """Open the confirmation wizard for the 'Clean old logs' action (list view button)."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Clean old logs'),
            'res_model': 'amazon.log.clean.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def _cron_clean_old_logs(self):
        """Scheduled monthly cleanup, see data/cron.xml."""
        self.action_clean_old_logs(days=DEFAULT_RETENTION_DAYS)

class AmazonLogCleanWizard(models.TransientModel):
    _name = 'amazon.log.clean.wizard'
    _description = 'Clean old Amazon logs'

    days = fields.Integer(string='Delete logs older than N days', default=DEFAULT_RETENTION_DAYS)
    records_to_delete = fields.Integer(string='Records to delete', compute='_compute_records_to_delete')

    @api.depends('days')
    def _compute_records_to_delete(self):
        for rec in self:
            cutoff = datetime.utcnow() - timedelta(days=rec.days)
            rec.records_to_delete = self.env['amazon.api.log'].search_count([
                ('create_date', '<', fields.Datetime.to_string(cutoff))
            ])

    def action_confirm(self):
        count = self.env['amazon.api.log'].action_clean_old_logs(days=self.days)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Logs deleted'),
                'message': _('%d log records were deleted.') % count,
                'type': 'success',
                'sticky': False,
            }
        }
