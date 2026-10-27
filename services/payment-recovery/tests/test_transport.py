import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from recovery import BillingError, Settings, StripeAPI


class TransportTests(unittest.TestCase):
    def setUp(self):
        settings=Settings('acct_fixture',frozenset(['price_pro']),'price_pro','https://www.wrenchrelayllc.com')
        self.api=StripeAPI(settings,key=lambda:'sk_live_fixture')

    def test_retry_keeps_same_key_and_body(self):
        class Opener:
            def __init__(self):self.requests=[]
            def open(self,request,timeout):
                self.requests.append(request)
                if len(self.requests)<3:
                    raise urllib.error.HTTPError(request.full_url,503,'unavailable',{},None)
                return io.BytesIO(json.dumps({'id':'cs_fixture'}).encode())
        opener=Opener()
        with patch('urllib.request.build_opener',return_value=opener),patch('recovery.time.sleep'):
            self.api._request('POST','/v1/checkout/sessions',{'mode':'subscription'},'fixed-intent-key','sk_live_fixture')
        self.assertEqual(len(opener.requests),3)
        self.assertEqual({r.get_header('Idempotency-key') for r in opener.requests},{'fixed-intent-key'})
        self.assertEqual({r.data for r in opener.requests},{b'mode=subscription'})

    def test_auth_failure_does_not_retry(self):
        with patch('urllib.request.build_opener') as build,patch('recovery.time.sleep') as sleep:
            build.return_value.open.side_effect=urllib.error.HTTPError('https://api.stripe.com',401,'no',{},None)
            with self.assertRaisesRegex(BillingError,'stripe_http_401'):
                self.api._request('GET','/v1/account',None,None,'sk_live_fixture')
            self.assertEqual(build.return_value.open.call_count,1);sleep.assert_not_called()

    def test_arbitrary_paths_and_non_idempotent_posts_are_rejected(self):
        with patch('urllib.request.build_opener') as build:
            for method,path in [('POST','/v1/checkout/sessions'),('GET','https://attacker.test'),('POST','/v1/refunds')]:
                with self.assertRaises(BillingError):self.api._request(method,path,{},None,'sk_live_fixture')
            build.assert_not_called()


if __name__=='__main__':unittest.main()
