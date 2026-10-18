import re
import unittest
import db_mongo
from app import app, init_db


class TestFreshAtlasSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Reset everything to fresh state for testing
        db_mongo.reset_all_data(keep_gemstones=True)
        init_db()

    @classmethod
    def tearDownClass(cls):
        # Leave database 100% clean for the user
        db_mongo.reset_all_data(keep_gemstones=True)

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = True
        self.client = app.test_client()

    def _extract_csrf(self, html: str) -> str:
        match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html)
        if not match:
            match = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', html)
        if match:
            return match.group(1)
        raise ValueError("CSRF token input not found in HTML response")

    def test_01_root_redirects_to_login(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 302)
        self.assertTrue('/login' in res.headers['Location'])

    def test_02_login_page_renders_with_tabs(self):
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        csrf_token = self._extract_csrf(html)
        self.assertTrue(len(csrf_token) > 10)
        self.assertIn('Sign In', html)
        self.assertIn('Create Account', html)

    def test_03_first_user_registration_starts_with_id_1(self):
        res_get = self.client.get('/login?tab=register')
        csrf_token = self._extract_csrf(res_get.data.decode('utf-8'))

        res_post = self.client.post('/login', data={
            'csrf_token': csrf_token,
            'action': 'register',
            'full_name': 'Ankesh Lab Director',
            'username': 'ankesh_director',
            'email': 'director@gemsoftsoft.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })

        # Redirects to dashboard
        self.assertEqual(res_post.status_code, 302)
        self.assertTrue('/dashboard' in res_post.headers['Location'])

        # Verify user in MongoDB Atlas has ID 1
        user = db_mongo.find_user_by_username('ankesh_director')
        self.assertIsNotNone(user)
        self.assertEqual(user['id'], 1)
        self.assertEqual(user['email'], 'director@gemsoftsoft.com')
        self.assertEqual(user['full_name'], 'Ankesh Lab Director')

    def test_04_login_with_new_user(self):
        # Logout first
        self.client.get('/logout')

        res_get = self.client.get('/login')
        csrf_token = self._extract_csrf(res_get.data.decode('utf-8'))

        res_post = self.client.post('/login', data={
            'csrf_token': csrf_token,
            'action': 'login',
            'identifier': 'director@gemsoftsoft.com',
            'password': 'password123'
        })

        self.assertEqual(res_post.status_code, 302)
        self.assertTrue('/dashboard' in res_post.headers['Location'])

    def test_05_first_certificate_starts_with_id_1_in_mongodb(self):
        # 1. Log in
        res_get_login = self.client.get('/login')
        csrf_login = self._extract_csrf(res_get_login.data.decode('utf-8'))
        self.client.post('/login', data={
            'csrf_token': csrf_login,
            'action': 'login',
            'identifier': 'director@gemsoftsoft.com',
            'password': 'password123'
        })

        # 2. Open new certificate page & extract CSRF
        res_new = self.client.get('/certificate/new')
        self.assertEqual(res_new.status_code, 200)
        csrf_cert = self._extract_csrf(res_new.data.decode('utf-8'))

        # Create first certificate
        res_create = self.client.post('/certificate/new', data={
            'csrf_token': csrf_cert,
            'customer_name': 'Premier Jewels Ltd',
            'gemstone_name': 'Natural Ruby',
            'weight_carat': '2.75',
            'shape_cut': 'Oval Mixed Cut',
            'color': 'Pigeon Blood Red',
            'comments': 'Verified Natural Corundum specimen',
            'refractive_index': '1.762 – 1.770',
            'specific_gravity': '4.00',
            'hardness': '9',
            'chemical_formula': 'Al₂O₃',
            'crystal_system': 'Trigonal'
        })

        self.assertEqual(res_create.status_code, 302)
        location = res_create.headers['Location']
        self.assertTrue('/certificate/' in location)

        cert_id = int(location.rstrip('/').split('/')[-1])
        self.assertEqual(cert_id, 1)

        # Verify in MongoDB Atlas
        cert = db_mongo.get_certificate_by_id(1)
        self.assertIsNotNone(cert)
        self.assertEqual(cert['id'], 1)
        self.assertEqual(cert['customer_name'], 'Premier Jewels Ltd')
        self.assertEqual(cert['gemstone_name'], 'Natural Ruby')
        self.assertEqual(cert['weight_carat'], 2.75)
        self.assertTrue(cert['report_number'].startswith('IGI-2026-'))

        # Verify public API verification
        res_verify = self.client.get(f"/api/verify?report={cert['report_number']}&pin={cert['secret_pin']}")
        self.assertEqual(res_verify.status_code, 200)
        vdata = res_verify.get_json()
        self.assertEqual(vdata['report_number'], cert['report_number'])
        self.assertEqual(vdata['customer_name'], 'Premier Jewels Ltd')


if __name__ == '__main__':
    unittest.main()
