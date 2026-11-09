import datetime
import ipaddress
import ssl
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import certifi
import stripe
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from stripe._http_client import RequestsClient



class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"tls-ok")

    def log_message(self, *args):
        pass


class StripeTLSTest(unittest.TestCase):
    def test_real_client_tls_authentication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "WrenchRelay local TLS test")])
            now = datetime.datetime.now(datetime.timezone.utc)
            cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                    .public_key(key.public_key()).serial_number(x509.random_serial_number())
                    .not_valid_before(now - datetime.timedelta(minutes=1))
                    .not_valid_after(now + datetime.timedelta(hours=1))
                    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                    .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
                    .sign(key, hashes.SHA256()))
            certpath, keypath = root / "test.pem", root / "key.pem"
            certpath.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            keypath.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            server = HTTPServer(("127.0.0.1", 0), Handler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certpath, keypath)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                original_bundle = stripe.ca_bundle_path
                original_verify = stripe.verify_ssl_certs
                self.assertTrue(original_verify)
                url = f"https://127.0.0.1:{server.server_port}/"
                with self.assertRaises(stripe.error.APIConnectionError):
                    RequestsClient(timeout=3).request("get", url, {})
                # Positive control: explicitly trust the generated test CA.
                stripe.ca_bundle_path = str(certpath)
                body, status, _ = RequestsClient(timeout=3).request("get", url, {})
                self.assertEqual((body, status), (b"tls-ok", 200))
                # Trusted chain with a mismatched hostname must still fail.
                with self.assertRaises(stripe.error.APIConnectionError):
                    RequestsClient(timeout=3).request("get", url.replace("127.0.0.1", "localhost"), {})
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                stripe.ca_bundle_path = original_bundle
                stripe.verify_ssl_certs = original_verify


if __name__ == "__main__":
    unittest.main()


def test_stripe_bundle_excludes_compromised_roots():
    # Parse the shipped PEM bytes rather than inferring contents from version metadata.
    certificates = x509.load_pem_x509_certificates(Path(stripe.ca_bundle_path).read_bytes())
    assert len(certificates) == 12
    names = {cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value for cert in certificates}
    assert "DigiCert TLS ECC P384 Root G5" in names
    assert not names & {"emSign ECC Root CA - G3", "emSign Root TLS CA - G3", "AAA Certificate Services"}
