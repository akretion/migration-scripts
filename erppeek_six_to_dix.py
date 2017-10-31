# -*- coding: utf-8 -*-
# Copyright 2017 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ssl
import types

import erppeek

# Only use if necessary (bypass ssl certificate host check)
ssl._create_default_https_context = ssl._create_unverified_context


class Importer(object):
    """
    This class allows to migrate partners, partner addresses and
    stock locations from OpenERP 6.1 to Odoo 10.0

    You should create fields in res.partner and stock.location in order to
    store the OpenERP ids before running this script.
    """

    def _get_relation(self, name, relation):
        for elem in relation:
            if elem.name == name:
                return elem.id

    def _append_not_null(self, dico, key, value):
        if value and not isinstance(value, types.MethodType):
            dico[key] = value
        return dico

    def _get_partner_or_address(self, partner, title):
        values = {}
        # DEBUT MAPPING SIMPLE
        self._append_not_null(values, 'name',   partner.name)
        self._append_not_null(values, 'city',   partner.city)
        self._append_not_null(values, 'color',  partner.color)
        self._append_not_null(values, 'email',  partner.email)
        self._append_not_null(values, 'mobile', partner.mobile)
        self._append_not_null(values, 'phone',  partner.phone)
        if title:
            values['title'] = title
        return values

    def _get_address(self, address, title, country_id, parent_id):
        values = self._get_partner_or_address(address, title)
        new_values = {}
        # DEBUT MAPPING SIMPLE
        self._append_not_null(new_values, 'fax',          address.fax)
        self._append_not_null(new_values, 'function',     address.function)
        self._append_not_null(new_values, 'street',       address.street)
        self._append_not_null(new_values, 'street2',      address.street2)
        self._append_not_null(new_values, 'zip',          address.zip)
        #  FIN MAPPING SIMPLE
        self._append_not_null(new_values, 'country_id',   country_id)
        values.update(new_values)
        if parent_id:
            values['parent_id'] = parent_id
        return values

    def _get_partner(self, partner, title):
        values = self._get_partner_or_address(partner, title)
        new_values = {}
        # DEBUT MAPPING SIMPLE
        self._append_not_null(new_values, 'comment',     partner.comment)
        self._append_not_null(new_values, 'customer',    partner.customer)
        self._append_not_null(new_values, 'date',        partner.date)
        self._append_not_null(new_values, 'debit',       partner.debit)
        self._append_not_null(new_values, 'debit_limit', partner.debit_limit)
        self._append_not_null(new_values, 'employee',    partner.employee)
        self._append_not_null(new_values, 'lang',        partner.lang)
        self._append_not_null(new_values, 'opt_out',     partner.opt_out)
        self._append_not_null(new_values, 'ref',         partner.ref)
        self._append_not_null(new_values, 'supplier',    partner.supplier)
        self._append_not_null(new_values, 'vat',         partner.vat)
        #  FIN MAPPING SIMPLE
        values.update(new_values)
        return values

    def _get_partner_and_address(self, address, title, country_id):
        values_for_partners = address
        if address.partner_id:
            values_for_partners = address.partner_id
        values = self._get_partner(values_for_partners, title)
        new_values = self._get_address(address, title, country_id, None)

        values.update(new_values)
        return values

    def _get_stock_location(self, stock, parent_id):
        vals = {}
        self._append_not_null(vals, 'active', stock.active)
        self._append_not_null(vals, 'comment', stock.comment)
        self._append_not_null(vals, 'complete_name', stock.complete_name)
        self._append_not_null(vals, 'name', 'AAA ' + stock.name)
        self._append_not_null(vals, 'parent_left', stock.parent_left)
        self._append_not_null(vals, 'parent_right', stock.parent_right)
        self._append_not_null(vals, 'posx', stock.posx)
        self._append_not_null(vals, 'posy', stock.posy)
        self._append_not_null(vals, 'posz', stock.posz)
        self._append_not_null(vals, 'scrap_location', stock.scrap_location)
        self._append_not_null(vals, 'usage', stock.usage)
        self._append_not_null(vals, 'location_id', parent_id)
        return vals

    def _import_stock_location(self, stock, new):
        parent_id = None
        parent = None
        if stock.location_id and not isinstance(stock.location_id,
                                                types.MethodType):
            print(stock.location_id, stock.location_id.id)
            parent = new.StockLocation.get([
                ('openerp_six_id', '=', stock.location_id.id)
            ])
            if not parent:
                # recursively create the missing parent(s)
                parent = self._import_stock_location(stock, new)
            parent_id = parent.id
        values = self._get_stock_location(stock, parent_id)
        values['openerp_six_id'] = stock.id
        return new.StockLocation.create(values)

    def import_stock_locations(self, old, new):
        """
        """
        stock_locations = old.StockLocation.browse([])

        for stock in stock_locations:
            self._import_stock_location(stock, new)

    def import_partners(self, old, new):
        """
        Imports partners and partner addresses from 6.1
        to 10.0 partners
        """
        addresses = old.ResPartnerAddress.browse([('dix', '=', True)], limit=9)
        titles = new.ResPartnerTitle.browse([])
        countries = new.ResCountry.browse([])

        for addr in addresses:
            if addr.title:
                title_name = addr.title.name
                if title_name == 'Sir':
                    title_name = 'Mister'
                title = self._get_relation(title_name, titles)
                if not title:
                    title = new.ResPartnerTitle.create(
                        {'name': addr.title.name}
                    )
            else:
                title = None

            country_id = self._get_relation(addr.country_id.name, countries)

            # create one res.partner from both the partner and the address
            if not addr.partner_id or len(addr.partner_id.address) < 2:
                partner_vals = self._get_partner_and_address(addr,
                                                             title, country_id)
                print partner_vals
                if partner_vals.get('name'):
                    partner_vals['openerp_six_id'] = addr.id
                    print(addr.id)
                    partner_vals['openerp_six_address'] = True
                    new.ResPartner.create(partner_vals)
            else:
                new_partner = None
                if addr.partner_id:
                    new_partner = new.ResPartner.get([
                        ('openerp_six_id', '=', addr.partner_id.id)
                    ])
                    if not new_partner:
                        # create the missing parent
                        partner_vals = self._get_partner(addr.partner_id,
                                                         title)
                        partner_vals['openerp_six_id'] = addr.partner_id.id
                        new_partner = new.ResPartner.create(partner_vals)
                # create a res.partner from the address
                partner_vals = self._get_address(addr, title,
                                                 country_id, new_partner)
                print partner_vals
                if not partner_vals.get('name'):
                    partner_vals['name'] = addr.partner_id.name
                partner_vals['openerp_six_id'] = addr.id
                partner_vals['openerp_six_address'] = True
                new.ResPartner.create(partner_vals)


OLD = erppeek.Client.from_config('old')
NEW = erppeek.Client.from_config('new')

IMPORTER = Importer()
IMPORTER.import_stock_locations(OLD, NEW)
