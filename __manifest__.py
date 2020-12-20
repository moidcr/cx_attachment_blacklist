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

# -*- coding: utf-8 -*-
{
    'name': 'Lista negra de adjuntos. Bloquea adjuntos por Contenido, Nombre o Tamaño',
    'version': '11.0.1.0',
    'summary': """Bloquea adjuntos por Contenido, Nombre, o Tamaño""",
    'author': 'Ivan Sokolov, Cetmix',
    'category': 'Extra Tools',
    'license': 'LGPL-3',
    'website': 'https://cetmix.com',
    'description': """
 Bloquea archivos no deseados, permite generar una lista de archivos con características específicas. Bloquea adjuntos por Contenido, Nombre, o Tamaño.
""",
    'depends': ['base', 'web', 'mail'],
    'images': ['static/description/banner.png'],

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/cx_attachment.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}


