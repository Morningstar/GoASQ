# -*- coding: utf-8 -*-

# Copyright (c) 2012, Kenneth Reitz
# All rights reserved.

# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:

# Redistributions of source code must retain the above copyright notice, this list 
# of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice, this 
# list of conditions and the following disclaimer in the documentation and/or other 
# materials provided with the distribution.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE 
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from flask import current_app, redirect, request

YEAR_IN_SECS = 31536000

class SSLify(object):
    """Secures your Flask App."""

    def __init__(self, app=None, age=YEAR_IN_SECS, subdomains=False, permanent=False, skips=None, ssl_debug=False, preload=False):
        self.app = app or current_app
        self.hsts_age = age
        self.ssl_debug = ssl_debug
        self.preload = preload

        self.hsts_include_subdomains = subdomains
        self.permanent = permanent
        self.skip_list = skips

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Configures the specified Flask app to enforce SSL."""
        app.config.setdefault('SSLIFY_SUBDOMAINS', False)
        app.config.setdefault('SSLIFY_PERMANENT', False)
        app.config.setdefault('SSLIFY_SKIPS', None)

        self.hsts_include_subdomains = self.hsts_include_subdomains or app.config['SSLIFY_SUBDOMAINS']
        self.permanent = self.permanent or self.app.config['SSLIFY_PERMANENT']
        self.skip_list = self.skip_list or self.app.config['SSLIFY_SKIPS']
        self.hsts_include_preload = self.preload or self.app.config['SSLIFY_PRELOAD']

        app.before_request(self.redirect_to_ssl)
        app.after_request(self.set_hsts_header)

    @property
    def hsts_header(self):
        """Returns the proper HSTS policy."""
        hsts_policy = 'max-age={0}'.format(self.hsts_age)

        if self.hsts_include_subdomains:
            hsts_policy += '; includeSubDomains'

        if self.hsts_include_preload:
            hsts_policy += '; preload'

        return hsts_policy

    @property
    def skip(self):
        """Checks the skip list."""
        # Should we skip?
        if self.skip_list and isinstance(self.skip_list, list):
            for skip in self.skip_list:
                if request.path.startswith('/{0}'.format(skip)):
                    return True
        return False

    @property
    def debug_criteria(self):
        if self.ssl_debug:
            return False
        else:
            return current_app.debug

    def redirect_to_ssl(self):
        """Redirect incoming requests to HTTPS."""
        # Should we redirect?
        criteria = [
            request.is_secure,
            self.debug_criteria,
            current_app.testing,
            request.headers.get('X-Forwarded-Proto', 'http') == 'https',
            "X-Appengine-Cron" in request.headers,
            "X-Appengine-TaskName" in request.headers
        ]

        if not any(criteria) and not self.skip:
            if request.url.startswith('http://'):
                url = request.url.replace('http://', 'https://', 1)
                code = 302
                if self.permanent:
                    code = 301
                r = redirect(url, code=code)
                return r

    def set_hsts_header(self, response):
        """Adds HSTS header to each response."""
        # Should we add STS header?
        if request.is_secure and not self.skip:
            response.headers.setdefault('Strict-Transport-Security', self.hsts_header)
        return response
