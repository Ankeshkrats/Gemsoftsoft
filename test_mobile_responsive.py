import re
import unittest
from app import app
import db_mongo

class TestMobileResponsive(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_01_viewport_meta_tag_on_all_pages(self):
        # 1. Login page
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>', html)

        # 2. Register route redirects to login with register tab
        res = self.client.get('/register', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>', html)

        # Also verify raw template register.html has viewport meta tag
        with open('templates/register.html', 'r', encoding='utf-8') as f:
            reg_html = f.read()
            self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>', reg_html)

        # 3. Verify page
        res = self.client.get('/verify')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>', html)

    def test_02_dashboard_and_drawer(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'test_gemologist'
            sess['full_name'] = 'Test Gemologist'

        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check viewport tag
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>', html)

        # Check mobile drawer elements
        self.assertIn('id="sidebar"', html)
        self.assertIn('id="sidebar-backdrop"', html)
        self.assertIn('id="mobile-menu-btn"', html)
        self.assertIn('id="sidebar-close-btn"', html)
        self.assertIn('-translate-x-full lg:translate-x-0', html)
        self.assertIn('ml-0 lg:ml-64', html)

        # Check responsive stats grid
        self.assertIn('grid grid-cols-3', html)

        # Check responsive table container
        self.assertIn('responsive-table-container', html)
        self.assertIn('min-w-[680px]', html)

    def test_03_new_certificate_form_responsive(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'test_gemologist'
            sess['full_name'] = 'Test Gemologist'

        res = self.client.get('/certificate/new')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check viewport tag
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>', html)

        # Check mobile drawer & hamburger
        self.assertIn('id="sidebar"', html)
        self.assertIn('id="mobile-menu-btn"', html)
        self.assertIn('ml-0 lg:ml-64', html)

        # Check responsive form grids
        self.assertIn('grid grid-cols-1 sm:grid-cols-2 gap-4', html)

        # Check drop zone and preview
        self.assertIn('id="drop-zone"', html)
        self.assertIn('id="img-preview"', html)

    def test_04_certificate_preview_responsive(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'test_gemologist'
            sess['full_name'] = 'Test Gemologist'

        certs = db_mongo.get_all_certificates()[:1]
        if certs:
            cert_id = certs[0]['id']
            res = self.client.get(f'/certificate/{cert_id}')
            self.assertEqual(res.status_code, 200)
            html = res.data.decode('utf-8')

            # Check viewport tag
            self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>', html)

            # Check cert screen wrapper
            self.assertIn('cert-screen-wrapper', html)
            self.assertIn('certificate-page', html)

            # Check responsive screen toolbar
            self.assertIn('no-print bg-[#1e3a5f]', html)
            self.assertIn('flex flex-wrap items-center justify-between', html)

    def test_05_print_labels_responsive(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'test_gemologist'
            sess['full_name'] = 'Test Gemologist'

        certs = db_mongo.get_all_certificates()[:1]
        if certs:
            cert_id = certs[0]['id']
            res = self.client.get(f'/labels/{cert_id}')
            self.assertEqual(res.status_code, 200)
            html = res.data.decode('utf-8')

            # Check viewport tag
            self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>', html)

            # Check responsive toolbar and grid
            self.assertIn('label-print-grid flex flex-wrap gap-4 justify-center sm:justify-start', html)
            self.assertIn('label-card', html)

            # Verify 'Comment' is present and 'Crystal Sys.' is removed
            self.assertIn('Comment', html)
            self.assertNotIn('Crystal Sys.', html)

    def test_06_verify_page_responsive(self):
        res = self.client.get('/verify')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check viewport tag
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0"/>', html)

        # Check camera scanner button and responsive inputs
        self.assertIn('Open Camera Scanner', html)
        self.assertIn('qr-reader', html)
        self.assertIn('id="v-report"', html)
        self.assertIn('id="v-pin"', html)

        # Test verify with an existing report number if available
        certs = db_mongo.get_all_certificates()[:1]
        if certs:
            cert = certs[0]
            res_v = self.client.get(f"/verify?report={cert['report_number']}")
            self.assertEqual(res_v.status_code, 200)
            v_html = res_v.data.decode('utf-8')
            self.assertIn(cert['report_number'], v_html)
            self.assertIn(cert['gemstone_name'], v_html)

    def test_07_api_gemstone_fetch(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'test_gemologist'
            sess['full_name'] = 'Test Gemologist'
        res = self.client.get('/api/gemstone/Natural%20Ruby')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('name'), 'Natural Ruby')
        self.assertIn('refractive_index', data)

    def test_08_api_verify_endpoint(self):
        certs = db_mongo.get_all_certificates()[:1]
        if certs:
            cert = certs[0]
            res = self.client.get(f"/api/verify?report={cert['report_number']}")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data['report_number'], cert['report_number'])
            self.assertEqual(data['gemstone_name'], cert['gemstone_name'])

    def test_09_static_assets_deliverable(self):
        # Verify CSS is served with 200
        res_css = self.client.get('/static/css/style.css')
        self.assertEqual(res_css.status_code, 200)
        css_content = res_css.data.decode('utf-8')
        self.assertIn('.cert-screen-wrapper', css_content)
        self.assertIn('.responsive-table-container', css_content)

        # Verify JS is served with 200
        res_js = self.client.get('/static/js/main.js')
        self.assertEqual(res_js.status_code, 200)
        js_content = res_js.data.decode('utf-8')
        self.assertIn('toggleMobileSidebar', js_content)

        # Verify Logo is served with 200
        res_logo = self.client.get('/static/logo.jpeg')
        self.assertEqual(res_logo.status_code, 200)

    def test_10_merge_labels_view_and_pdf(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'test_gemologist'
            sess['full_name'] = 'Test Gemologist'

        certs = db_mongo.get_all_certificates()[:10]
        if certs:
            ids_str = ','.join(str(c['id']) for c in certs)

            # Test HTML view of merged cards
            res_view = self.client.get(f'/labels/merge?ids={ids_str}')
            self.assertEqual(res_view.status_code, 200)
            html = res_view.data.decode('utf-8')
            self.assertIn('label-card', html)
            self.assertIn('Save Merged PDF', html)

            # Test direct PDF download of merged cards
            res_pdf = self.client.get(f'/labels/merge/pdf?ids={ids_str}')
            self.assertEqual(res_pdf.status_code, 200)
            self.assertEqual(res_pdf.headers['Content-Type'], 'application/pdf')
            self.assertTrue(len(res_pdf.data) > 1000)

            # Verify it generates exactly 1 A4 page
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(res_pdf.data))
            self.assertEqual(len(reader.pages), 1)

    def test_11_single_card_pdf_download(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'test_gemologist'
            sess['full_name'] = 'Test Gemologist'

        certs = db_mongo.get_all_certificates()[:1]
        if certs:
            cert_id = certs[0]['id']
            res = self.client.get(f'/labels/{cert_id}/pdf')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers['Content-Type'], 'application/pdf')
            self.assertTrue(len(res.data) > 1000)

    def test_12_dashboard_features(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'test_gemologist'
            sess['full_name'] = 'Test Gemologist'

        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Batch merge action bar
        self.assertIn('id="batch-action-bar"', html)
        self.assertIn('cert-select-cb', html)
        self.assertIn('Save Merged PDF', html)

        # Direct card PDF download button exists
        self.assertIn('/pdf', html)

if __name__ == '__main__':
    unittest.main()

