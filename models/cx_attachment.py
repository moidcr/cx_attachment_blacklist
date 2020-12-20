###################################################################################
# 
#    Copyright (C) 2020 Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

from odoo import models, fields, api, exceptions, _
import fnmatch
import logging

_logger = logging.getLogger(__name__)


########################
# Attachment Blacklist #
########################
class CxAttachmentBlacklist(models.Model):
    _name = "cx.attachment.blacklist"
    _description = "Attachment Blacklist"
    _order = 'id desc'

    name = fields.Char(string="Name")
    type = fields.Selection([
        ('f', 'Filename Patterns'),
        ('c', 'Contents'),
    ], string="Type", required=True)
    active = fields.Boolean(string="Active", default=True)
    checksum = fields.Char(string="Checksum", size=40, readonly=True, index=True)
    pattern = fields.Char(string="Filename Patterns",
                          help="Comma-separated string of OS-shell-style filename patterns"
                               " (e.g. *.exe,logo.jpg,archive?.zip)")
    condition = fields.Selection([
        ('=', '='),
        ('>', '>'),
        ('<', '<'),
    ], string="File Size")

    size = fields.Float(string="Size")
    unit = fields.Selection([
        ('k', 'Kilobytes'),
        ('m', 'Megabytes'),
    ], string="Unit", default='k')

# -- Add attachments to blacklist
    @api.model
    def blacklist_by_checksum(self, checksums_arg):
        """
        Adds attachments to blacklist
        :param checksums [String]: list of attachment checksums
        :param force_delete Boolean: force deletion of blacklisted attachments
        :return: True if ok False if error
        """

        # Check if already in blacklist
        """
        May occur that same attachments will be added by same users same time.
        To avoid raising exception check if attachments not in list already
        """
        # Remove checksum duplicates
        checksum_set = set(checksums_arg)
        checksums = list(checksum_set)
        # Activate inactive first
        blacklisted = self.sudo().search([('checksum', 'in', checksums), ('active', '=', False)])
        if blacklisted:
            blacklisted.sudo().write({'active': True})

        # Now check all
        blacklisted = self.sudo().search([('checksum', 'in', checksums)])

        # Blacklist only non-blacklisted
        if len(blacklisted) > 0:
            final_checksums = checksums not in blacklisted.mapped('checksum')
        else:
            final_checksums = checksums

        # Add attachment to blacklist
        for checksum in final_checksums:
            attachment_ids = self.env['ir.attachment'].sudo().search([('checksum', '=', checksum)], order="id desc")
            attachment_name = attachment_ids[0].name if len(attachment_ids) > 0 else _("Blacklisted by contents")
            self.create({
                'active': True,
                'type': 'c',
                'checksum': checksum,
                'name': attachment_name
            })

        # Make sure that all other attachments are blacklisted as well
        if len(blacklisted) > 0:
            for bl_item in blacklisted:
                attachment_ids = self.env['ir.attachment'].sudo().search([('checksum', '=', bl_item.checksum)])
                if len(attachment_ids) > 0:
                    attachment_ids.sudo().write({'active': False, 'blacklist_id': bl_item.id})

# -- Check if attachment is blacklisted
    @api.model
    def is_blacklisted(self, name=False, checksum=False, file_size=False):
        """
        Check is attachment matches any blacklist
        :param name: filename
        :param checksum:
        :return: id of blacklist if match found else False
        """
        
        # Match checksum
        if checksum:
            blacklist_ids = self.sudo().search([('type', '=', 'c'),
                                                ('checksum', '=', checksum)])
            if len(blacklist_ids) > 0:
                return blacklist_ids[0].id

        # Match filename pattern
        if name:
            blacklist_ids = self.sudo().search([('type', '=', 'f')])

            # Check blacklist for matching pattern
            for blacklist in blacklist_ids:
                condition = blacklist.condition
                if condition:
                    size = int(blacklist.size * 1048576 if blacklist.unit == 'm' else blacklist.size * 1024)

                patterns = blacklist.pattern.replace(" ", "").split(",")
                for pattern in patterns:
                    if fnmatch.fnmatch(name, pattern):
                        if not condition:
                            return blacklist.id
                        if condition == "=" and file_size == size:
                            return blacklist.id
                        if condition == ">" and file_size > size: 
                            return blacklist.id
                        if condition == "<" and file_size < size:
                            return blacklist.id

        # Return False if nothing found
        return False

# -- Create
    @api.model
    def create(self, vals):
        
        res = super(CxAttachmentBlacklist, self).create(vals)

        # Blacklist existing attachments
        res.refresh_blacklist()
        return res

# -- Write
    @api.multi
    def write(self, vals):

        # Type cannot be changed once created!
        if "type" in vals:
            vals.pop("type", False)

        # Write
        res = super(CxAttachmentBlacklist, self).write(vals)

        # Check if "Active" status is changed. If 'active' set to False return
        active = vals.get('active', False)
        if 'active' in vals and not active:
            return res

        # In case any were inactive already
        active_ids = []
        for rec in self:
            if rec.active:
                active_ids.append(rec.id)

        if len(active_ids) == 0:
            return res

        # If any val changed refresh blacklists
        checksum = vals.get("checksum", False)
        if checksum or active or 'pattern' in vals or 'condition' in vals or 'size' in vals or 'unit' in vals:

            # Unblacklist blacklisted in case blacklist criteria changed
            attachment_ids = self.env['ir.attachment'].sudo().search([('active', '=', False),
                                                                      ('blacklist_id', 'in', active_ids)])
            if len(attachment_ids) > 0:
                attachment_ids.sudo().write({'active': True, 'blacklist_id': False})

            # Re-blacklist again
            self.refresh_blacklist()

        return res


# -- Unlink
    @api.multi
    def unlink(self):
        blacklisted = self.env['ir.attachment'].sudo().search([('blacklist_id', 'in', self.ids),
                                                               ('active', '=', False)])
        if blacklisted:
            blacklisted.sudo().write({'active': True})

        # Unlink
        res = super(CxAttachmentBlacklist, self).unlink()

        # Check if any other blacklist can be applied to previously blacklisted by deleted blacklists
        remaining_ids = []

        # By contents
        for attachment in blacklisted:
            blacklist = self.sudo().search([('type', '=', 'c'), ('checksum', '=', attachment.checksum)])
            if len(blacklist) > 0:
                attachment.sudo().write({'active': False, 'blacklist_id': blacklist[0].id})

            # Need to check by filename pattern later
            else:
                remaining_ids.append(attachment.id)

        del blacklisted
        if len(remaining_ids) == 0:
            return res

        # By filename pattern
        for blacklist in self.sudo().search([('type', '=', 'f')]):
            pattern_string = blacklist.pattern
            if blacklist.condition:
                domain = [('file_size', blacklist.condition, int(blacklist.size * 1048576 if blacklist.unit == 'm' else blacklist.size * 1024))]
            else:
                domain = False
            # Replace symbols to match SQL search
            patterns = pattern_string.replace("_", "\\_").replace(" ", "").replace("*", "%").replace("?", "_").split(",")
            for pattern in patterns:
                if len(pattern) > 0:
                    pattern_domain = domain + [('type', '=', 'binary'),
                                               ('id', 'in', remaining_ids),
                                               ('datas_fname', '=ilike', pattern)] if domain else [('type', '=', 'binary'),
                                                                                                  ('id', 'in', remaining_ids),
                                                                                                  ('datas_fname', '=ilike', pattern)]
                    attachment_ids = self.env['ir.attachment'].sudo().search(pattern_domain)
                    if len(attachment_ids) > 0:
                        attachment_ids.sudo().write({'active': False, 'blacklist_id': blacklist.id})

        return res

# -- Re-check blacklist(s). Find and blacklist any unblacklisted attachments
    @api.multi
    def refresh_blacklist(self):
        """
        Refresh blacklist(s). Find any unblacklisted attachments and blacklist them
        :return:
        """
        for rec in self:
            # Check if active
            if not rec.active:
                continue

            # Checksum
            if rec.type == 'c':
                attachment_ids = self.env['ir.attachment'].sudo().search([('checksum', '=', rec.checksum)])
                if len(attachment_ids) > 0:
                    attachment_ids.sudo().write({'active': False, 'blacklist_id': rec.id})

            # Pattern
            if rec.type == 'f':
                pattern_string = rec.pattern
                if not pattern_string:
                    continue
                if rec.condition:
                    domain = [('file_size', rec.condition,
                               int(rec.size * 1048576 if rec.unit == 'm' else rec.size * 1024))]
                else:
                    domain = False
                # Replace symbols to match SQL search
                patterns = pattern_string.replace("_", "\\_").replace(" ", "").replace("*", "%").replace("?",
                                                                                                         "_").split(",")
                for pattern in patterns:
                    if len(pattern) > 0:
                        pattern_domain = domain + [('type', '=', 'binary'),
                                                   ('datas_fname', '=ilike', pattern)] if domain else [
                            ('type', '=', 'binary'),
                            ('datas_fname', '=ilike', pattern)]
                        attachment_ids = self.env['ir.attachment'].sudo().search(pattern_domain)
                        if len(attachment_ids) > 0:
                            attachment_ids.sudo().write({'active': False, 'blacklist_id': rec.id})


# -- Open blacklisted
    @api.multi
    def open_blacklisted(self):
        self.ensure_one()

        return {
            'name': _("Blacklisted Attachments"),
            "views": [[False, "tree"], [False, "kanban"], [False, "form"]],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('blacklist_id', '=', self.id), ('active', '=', False)]
        }


###############################
# Attachment Blacklist Wizard #
###############################
class CxAttachmentBlacklistWizard(models.TransientModel):
    _name = "cx.attachment.blacklist.wiz"

# -- Get attachments
    def _get_attachments(self):
        ids = self._context.get('attachment_ids', False)
        if not ids:
            ids = self._context.get('active_ids', False)
        if not ids:
            return False

        attachment_ids = self.env['ir.attachment'].sudo().search([('id', 'in', ids),
                                                                  ('type', '=', 'binary'),
                                                                  ('blacklist_id', '=', False)
                                                                  ])

        return attachment_ids.ids

    attachment_ids = fields.Many2many(string="Attachments",
                                      comodel_name='ir.attachment',
                                      default=_get_attachments)

# -- Add attachments to blacklist
    @api.multi
    def blacklist_attachments(self):
        if len(self.attachment_ids) > 0:
            self.env['cx.attachment.blacklist'].blacklist_by_checksum(self.attachment_ids.mapped('checksum'))


###############
# Attachments #
###############
class CxAttachment(models.Model):
    _name = "ir.attachment"
    _inherit = "ir.attachment"

    active = fields.Boolean(string="Active", default=True)
    blacklist_id = fields.Many2one(string="Blacklist", comodel_name='cx.attachment.blacklist',
                                   ondelete='set null')


# -- Create
    @api.model
    def create(self, vals):
        """
        Check if attachment is in blacklist
        """
        res = super(CxAttachment, self).create(vals)
        if res.type == 'binary':
            blacklist_id = self.env['cx.attachment.blacklist'].is_blacklisted(name=res.datas_fname,
                                                                              checksum=res.checksum,
                                                                              file_size=res.file_size)
            if blacklist_id:
                res.write({'active': False, 'blacklist_id': blacklist_id})
                raise exceptions.Warning('El archivo no se puede adjuntar, su tamaño, tipo o contenido no está permitido!!')
        
        return res


################
# Mail Message #
################
class CxMailMessage(models.Model):
    _name = "mail.message"
    _inherit = "mail.message"

    # -- Write
    @api.multi
    def write(self, vals):
        """
        Ensure that blacklisted attachments are also moved in case of message move
        """

        res = super(CxMailMessage, self).write(vals)

        model = vals.get("model", False)
        res_id = vals.get("res_id", False)

        if model or res_id:

            # search directly in SQL to improve performances
            self._cr.execute(""" SELECT attachment_id FROM message_attachment_rel
                                    WHERE message_id = ANY(%s) """, (list(self.ids),))
            ids = [result[0] for result in self._cr.fetchall()]
            if len(ids) > 0:
                attachment_ids = self.env['ir.attachment'].sudo().search([('active', '=', False),
                                                                          ('id', 'in', ids)])
                if len(attachment_ids) > 0:
                    att_vals = {'res_model': model} if model else {}
                    if res_id:
                        att_vals.update({'res_id': res_id})

                    attachment_ids.write(att_vals)

        return res
