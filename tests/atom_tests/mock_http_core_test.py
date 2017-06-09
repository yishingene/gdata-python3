#!/usr/bin/env python
#
# Copyright (C) 2009 Google Inc.
#
# Licensed under the Apache License 2.0;



# This module is used for version 2 of the Google Data APIs.
# This test may make an actual HTTP request.


# __author__ = 'j.s@google.com (Jeff Scudder)'

import io
import unittest

import atom.http_core
import atom.mock_http_core


class EchoClientTest(unittest.TestCase):
    def test_echo_response(self):
        client = atom.mock_http_core.EchoHttpClient()
        # Send a bare-bones POST request.
        request = atom.http_core.HttpRequest(method='POST',
                                             uri=atom.http_core.Uri(host='www.jeffscudder.com', path='/'))
        request.add_body_part('hello world!', 'text/plain')
        response = client.request(request)
        self.assertTrue(response.getheader('Echo-Host') == 'www.jeffscudder.com:None')
        self.assertTrue(response.getheader('Echo-Uri') == '/')
        self.assertTrue(response.getheader('Echo-Scheme') is None)
        self.assertTrue(response.getheader('Echo-Method') == 'POST')
        self.assertTrue(response.getheader('Content-Length') == str(len(
            'hello world!')))
        self.assertTrue(response.getheader('Content-Type') == 'text/plain')
        self.assertTrue(response.read() == 'hello world!')

        # Test a path of None should default to /
        request = atom.http_core.HttpRequest(method='POST',
                                             uri=atom.http_core.Uri(host='www.jeffscudder.com', path=None))
        response = client.request(request)
        self.assertTrue(response.getheader('Echo-Host') == 'www.jeffscudder.com:None')
        self.assertTrue(response.getheader('Echo-Method') == 'POST')
        self.assertTrue(response.getheader('Echo-Uri') == '/')

        # Send a multipart request.
        request = atom.http_core.HttpRequest(method='POST',
                                             uri=atom.http_core.Uri(scheme='https', host='www.jeffscudder.com',
                                                                    port=8080, path='/multipart',
                                                                    query={'test': 'true', 'happy': 'yes'}),
                                             headers={'Authorization': 'Test xyzzy', 'Testing': 'True'})
        request.add_body_part('start', 'text/plain')
        request.add_body_part(io.StringIO('<html><body>hi</body></html>'),
                              'text/html', len('<html><body>hi</body></html>'))
        request.add_body_part('alert("Greetings!")', 'text/javascript')
        response = client.request(request)
        self.assertTrue(response.getheader('Echo-Host') == 'www.jeffscudder.com:8080')
        self.assertTrue(
            response.getheader('Echo-Uri') == '/multipart?test=true&happy=yes')
        self.assertTrue(response.getheader('Echo-Scheme') == 'https')
        self.assertTrue(response.getheader('Echo-Method') == 'POST')
        self.assertTrue(response.getheader('Content-Type') == (
            'multipart/related; boundary="%s"' % (atom.http_core.MIME_BOUNDARY,)))
        expected_body = ('Media multipart posting'
                         '\r\n--%s\r\n'
                         'Content-Type: text/plain\r\n\r\n'
                         'start'
                         '\r\n--%s\r\n'
                         'Content-Type: text/html\r\n\r\n'
                         '<html><body>hi</body></html>'
                         '\r\n--%s\r\n'
                         'Content-Type: text/javascript\r\n\r\n'
                         'alert("Greetings!")'
                         '\r\n--%s--') % (atom.http_core.MIME_BOUNDARY,
                                          atom.http_core.MIME_BOUNDARY, atom.http_core.MIME_BOUNDARY,
                                          atom.http_core.MIME_BOUNDARY,)
        self.assertTrue(response.read() == expected_body)
        self.assertTrue(response.getheader('Content-Length') == str(
            len(expected_body)))


class MockHttpClientTest(unittest.TestCase):
    def setUp(self):
        self.client = atom.mock_http_core.MockHttpClient()

    def test_respond_with_recording(self):
        request = atom.http_core.HttpRequest(method='GET')
        atom.http_core.parse_uri('http://www.google.com/').modify_request(request)
        self.client.add_response(request, 200, 'OK', body='Testing')
        response = self.client.request(request)
        self.assertTrue(response.status == 200)
        self.assertTrue(response.reason == 'OK')
        self.assertTrue(response.read() == 'Testing')

    def test_save_and_load_recordings(self):
        request = atom.http_core.HttpRequest(method='GET')
        atom.http_core.parse_uri('http://www.google.com/').modify_request(request)
        self.client.add_response(request, 200, 'OK', body='Testing')
        response = self.client.request(request)
        self.client._save_recordings('test_save_and_load_recordings')
        self.client._recordings = []
        try:
            response = self.client.request(request)
            self.fail('There should be no recording for this request.')
        except atom.mock_http_core.NoRecordingFound:
            pass
        self.client._load_recordings('test_save_and_load_recordings')
        response = self.client.request(request)
        self.assertTrue(response.status == 200)
        self.assertTrue(response.reason == 'OK')
        self.assertTrue(response.read() == 'Testing')

    def test_use_recordings(self):
        request = atom.http_core.HttpRequest(method='GET')
        atom.http_core.parse_uri('http://www.google.com/').modify_request(request)
        self.client._load_or_use_client('test_use_recordings',
                                        atom.http_core.HttpClient())
        response = self.client.request(request)
        if self.client.real_client:
            self.client._save_recordings('test_use_recordings')
        self.assertTrue(response.status in (200, 302))
        self.assertTrue(response.reason in ('OK', 'Found'))
        self.assertTrue(response.getheader('server') == 'gws')
        body = response.read()
        self.assertTrue(body.startswith('<!doctype html>') or
                        body.startswith('<HTML>'))

    def test_match_request(self):
        x = atom.http_core.HttpRequest('http://example.com/', 'GET')
        y = atom.http_core.HttpRequest('http://example.com/', 'GET')
        self.assertTrue(atom.mock_http_core._match_request(x, y))
        y = atom.http_core.HttpRequest('http://example.com/', 'POST')
        self.assertTrue(not atom.mock_http_core._match_request(x, y))
        y = atom.http_core.HttpRequest('http://example.com/1', 'GET')
        self.assertTrue(not atom.mock_http_core._match_request(x, y))
        y = atom.http_core.HttpRequest('http://example.com/?gsessionid=1', 'GET')
        self.assertTrue(not atom.mock_http_core._match_request(x, y))
        y = atom.http_core.HttpRequest('http://example.com/?start_index=1', 'GET')
        self.assertTrue(atom.mock_http_core._match_request(x, y))
        x = atom.http_core.HttpRequest('http://example.com/?gsessionid=1', 'GET')
        y = atom.http_core.HttpRequest('http://example.com/?gsessionid=1', 'GET')
        self.assertTrue(atom.mock_http_core._match_request(x, y))
        y = atom.http_core.HttpRequest('http://example.com/?gsessionid=2', 'GET')
        self.assertTrue(not atom.mock_http_core._match_request(x, y))
        y = atom.http_core.HttpRequest('http://example.com/', 'GET')
        self.assertTrue(not atom.mock_http_core._match_request(x, y))

    def test_use_named_sessions(self):
        self.client._delete_recordings('mock_http_test.test_use_named_sessions')
        self.client.use_cached_session('mock_http_test.test_use_named_sessions',
                                       atom.mock_http_core.EchoHttpClient())
        request = atom.http_core.HttpRequest('http://example.com', 'GET')
        response = self.client.request(request)
        self.assertEqual(response.getheader('Echo-Method'), 'GET')
        self.assertEqual(response.getheader('Echo-Host'), 'example.com:None')
        # We will insert a Cache-Marker header to indicate that this is a
        # recorded response, but initially it should not be present.
        self.assertEqual(response.getheader('Cache-Marker'), None)
        # Modify the recorded response to allow us to identify a cached result
        # from an echoed result. We need to be able to check to see if this
        # came from a recording.
        self.assertTrue('Cache-Marker' not in self.client._recordings[0][1]._headers)
        self.client._recordings[0][1]._headers['Cache-Marker'] = '1'
        self.assertTrue('Cache-Marker' in self.client._recordings[0][1]._headers)
        # Save the recorded responses.
        self.client.close_session()

        # Create a new client, and have it use the recorded session.
        client = atom.mock_http_core.MockHttpClient()
        client.use_cached_session('mock_http_test.test_use_named_sessions',
                                  atom.mock_http_core.EchoHttpClient())
        # Make the same request, which should use the recorded result.
        response = client.request(request)
        self.assertEqual(response.getheader('Echo-Method'), 'GET')
        self.assertEqual(response.getheader('Echo-Host'), 'example.com:None')
        # We should now see the cache marker since the response is replayed.
        self.assertEqual(response.getheader('Cache-Marker'), '1')


def suite():
    return unittest.TestSuite((unittest.makeSuite(MockHttpClientTest, 'test'),
                               unittest.makeSuite(EchoClientTest, 'test')))


if __name__ == '__main__':
    unittest.main()