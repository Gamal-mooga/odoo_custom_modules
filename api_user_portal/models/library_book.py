from odoo import models, fields

class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'

    name = fields.Char(string="Title", required=True)
    author = fields.Char(string="Author")
    date_published = fields.Date(string="Published Date")
    isbn = fields.Char(string="ISBN")
    age=fields.Integer()