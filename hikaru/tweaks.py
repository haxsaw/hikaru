#
# Copyright (c) 2021 Incisive Technology Ltd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
This module provides centralization of one-off processing for K8s swagger inconsistencies

Most inconsistencies in the swagger K8s spec are handled in the build.py program
so that by the time we get to the runtime system of Hikaru things are generally
consistent. However, there are a couple of areas that for one reason or another
are a bit off and can't be accounted for during build, but instead must be handled
by special run-time logic that looks at the specific classes involved. This module
is an attempt to centralize that special processing for the runtime side of Hikaru
so we can always look to one place for such processing.

This is all meant for internal use to Hikaru so you have been duly warned.
"""
from hikaru.naming import camel_to_pep8

_translation_register = {}


def _register_translator(target_cls_name: str):
    def _register(translator_cls: type) -> type:
        _translation_register[target_cls_name] = translator_cls
        return translator_cls
    return _register


class _BaseTranslator(object):
    @classmethod
    def h2kc_translate(cls, fieldname: str) -> str:
        """
        this method is used when you have a Hikaru name and want the K8s
        Python client name.

        :param fieldname: string; the Hikaru name for a field in a class
        :return: the K8s Python client version of the name
        """
        return camel_to_pep8(fieldname)


@_register_translator("DaemonEndpoint")
class _DaemonEndpointTranslator(_BaseTranslator):
    @classmethod
    def h2kc_translate(cls, fieldname: str) -> str:
        # OK, the attribute 'Port' is the only use of port that is
        # capitalized in the 1.16 swagger spec. Swagger, YAML, and K8s
        # all seem to use 'Port', however the objects that are coded in
        # the K8s python client use 'port' instead, and we have no good
        # way to create some logical expression to determine to map the two
        # in this one case. So we'll look for just this attribute when we
        # need to translate from the k8s client and return a lower-case version
        if fieldname == 'Port':
            return 'port'
        else:
            return super(_DaemonEndpointTranslator, cls).h2kc_translate(fieldname)


def h2kc_translate(target_cls: type, fieldname: str) -> str:
    xlator = _translation_register.get(target_cls.__name__, _BaseTranslator)
    return xlator.h2kc_translate(fieldname)
