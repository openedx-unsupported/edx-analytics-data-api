"""
Tests for the custom REST framework renderers.
"""

from unittest.mock import MagicMock, PropertyMock

from django.test import TestCase

from analytics_data_api.renderers import PaginatedCsvRenderer


class PaginatedCsvRendererTests(TestCase):

    def setUp(self):
        super().setUp()
        self.renderer = PaginatedCsvRenderer()
        self.data = {'results': [
            {
                'string': 'ab,c',
                'list': ['a', 'b', 'c'],
                'dict': {'a': 1, 'b': 2, 'c': 3},
            }, {
                'string': 'def',
                'string2': 'ghi',
                'list': ['d', 'e', 'f', 'g'],
                'dict': {'d': 4, 'b': 5, 'c': 6},
            },
        ]}
        self.context = {}

    def set_request(self, params=None):
        request = MagicMock()
        mock_params = PropertyMock(return_value=params)
        type(request).query_params = mock_params
        self.context['request'] = request

    def test_csv_media_type(self):
        self.assertEqual(self.renderer.media_type, 'text/csv')

    def test_render(self):
        rendered_data = self.renderer.render(self.data, renderer_context=self.context)
        self.assertEqual(rendered_data,
                         b'dict.a,dict.b,dict.c,dict.d,list,string,string2\r\n'
                         b'1,2,3,,"a, b, c","ab,c",\r\n'
                         b',5,6,4,"d, e, f, g",def,ghi\r\n')

    def test_render_fields(self):
        self.set_request(dict(fields='string2,invalid,dict.b,list,dict.a,string'))
        rendered_data = self.renderer.render(self.data, renderer_context=self.context)
        self.assertEqual(rendered_data,
                         b'string2,dict.b,list,dict.a,string\r\n'
                         b',2,"a, b, c",1,"ab,c"\r\n'
                         b'ghi,5,"d, e, f, g",,def\r\n')

    def test_render_flatten_lists(self):
        self.renderer.concatenate_lists_sep = None
        rendered_data = self.renderer.render(self.data, renderer_context=self.context)
        self.assertEqual(rendered_data,
                         b'dict.a,dict.b,dict.c,dict.d,list.0,list.1,list.2,list.3,string,string2\r\n'
                         b'1,2,3,,a,b,c,,"ab,c",\r\n'
                         b',5,6,4,d,e,f,g,def,ghi\r\n')

    def test_render_fields_flatten_lists(self):
        self.renderer.concatenate_lists_sep = None
        self.set_request(dict(fields='string2,invalid,list.2,dict.a,list.1,string'))
        rendered_data = self.renderer.render(self.data, renderer_context=self.context)
        self.assertEqual(rendered_data,
                         b'string2,list.2,dict.a,list.1,string\r\n'
                         b',c,1,b,"ab,c"\r\n'
                         b'ghi,f,,e,def\r\n')

    def test_render_fields_limit_headers(self):
        self.renderer.header = ('string2', 'invalid', 'dict.a')
        self.set_request(dict(fields='string2,invalid,dict.b,list,dict.a,string'))
        rendered_data = self.renderer.render(self.data, renderer_context=self.context)
        self.assertEqual(rendered_data,
                         b'string2,invalid,dict.a\r\n'
                         b',,1\r\n'
                         b'ghi,,\r\n')
