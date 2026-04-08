from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.printers.models import PreparationPlace, Printer, Receipt

User = get_user_model()


class TestPrinterAPI(TestCase):
    """Printer API testləri"""
    
    def setUp(self):
        """Test setup"""
        self.client = APIClient()
        
        # Admin istifadəçi yarat
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.admin_user)
        
        # Test printers yarat
        self.printer = Printer.objects.create(
            name='Test Printer',
            ip_address='192.168.1.100',
            port=9100,
            description='Test printer description',
            is_main=False
        )
        
        self.main_printer = Printer.objects.create(
            name='Main Printer',
            ip_address='192.168.1.101',
            port=9100,
            description='Main printer',
            is_main=True
        )
    
    def test_list_printers(self):
        """Printerləri listələmə testi"""
        response = self.client.get('/api/printers/printers/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Pagination olduqda 'results', yoxdursa birbaşa list
        if isinstance(response.data, dict):
            self.assertEqual(len(response.data['results']), 2)
        else:
            self.assertEqual(len(response.data), 2)
    
    def test_create_printer(self):
        """Printer yaratma testi"""
        data = {
            'name': 'Yeni Printer',
            'ip_address': '192.168.1.102',
            'port': 9100,
            'description': 'Yeni printer',
            'is_main': False
        }
        
        response = self.client.post('/api/printers/printers/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Yeni Printer')
        self.assertTrue(Printer.objects.filter(name='Yeni Printer').exists())
    
    def test_create_printer_duplicate_ip(self):
        """Eyni IP ilə printer yaratma testi (xəta gözlənilir)"""
        data = {
            'name': 'Duplikat Printer',
            'ip_address': self.printer.ip_address,  # Mövcud IP
            'port': 9100,
        }
        
        response = self.client.post('/api/printers/printers/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_retrieve_printer(self):
        """Tək printer əldə etmə testi"""
        response = self.client.get(f'/api/printers/printers/{self.printer.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.printer.name)
        self.assertEqual(response.data['ip_address'], self.printer.ip_address)
    
    def test_update_printer(self):
        """Printer yeniləmə testi"""
        data = {
            'name': 'Yenilənmiş Printer',
            'ip_address': '192.168.1.200',
            'port': 9100,
        }
        
        response = self.client.put(f'/api/printers/printers/{self.printer.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Yenilənmiş Printer')
        
        self.printer.refresh_from_db()
        self.assertEqual(self.printer.name, 'Yenilənmiş Printer')
    
    def test_partial_update_printer(self):
        """Printer qismən yeniləmə testi"""
        data = {'name': 'Qismən Yenilənmiş'}
        
        response = self.client.patch(f'/api/printers/printers/{self.printer.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Qismən Yenilənmiş')
        
        self.printer.refresh_from_db()
        self.assertEqual(self.printer.name, 'Qismən Yenilənmiş')
        self.assertEqual(self.printer.ip_address, '192.168.1.100')  # Dəyişməməlidir
    
    def test_delete_printer(self):
        """Printer silmə testi"""
        printer = Printer.objects.create(
            name='Silinəcək Printer',
            ip_address='192.168.1.250',
            port=9100
        )
        
        response = self.client.delete(f'/api/printers/printers/{printer.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Printer.objects.filter(id=printer.id).exists())
    
    def test_delete_printer_with_preparation_place(self):
        """Hazırlanma yeri olan printer silmə testi (xəta gözlənilir)"""
        preparation_place = PreparationPlace.objects.create(
            name='Mətbəx',
            printer=self.printer
        )
        
        response = self.client.delete(f'/api/printers/printers/{self.printer.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Printer.objects.filter(id=self.printer.id).exists())
    
    def test_set_main_printer(self):
        """Əsas printer təyin etmə testi"""
        response = self.client.post(f'/api/printers/printers/{self.printer.id}/set-main/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.printer.refresh_from_db()
        self.main_printer.refresh_from_db()
        
        self.assertTrue(self.printer.is_main)
        self.assertFalse(self.main_printer.is_main)
    
    def test_get_main_printer(self):
        """Əsas printer əldə etmə testi"""
        response = self.client.get('/api/printers/printers/main-printer/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.main_printer.id)
    
    def test_search_printers(self):
        """Printer axtarış testi"""
        response = self.client.get('/api/printers/printers/?search=Test')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_filter_printers_by_main(self):
        """Əsas printerə görə filtrasiya testi"""
        response = self.client.get('/api/printers/printers/?is_main=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.main_printer.id)


class TestPreparationPlaceAPI(TestCase):
    """Hazırlanma Yeri API testləri"""
    
    def setUp(self):
        """Test setup"""
        self.client = APIClient()
        
        # Admin istifadəçi yarat
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.admin_user)
        
        # Test printer yarat
        self.printer = Printer.objects.create(
            name='Test Printer',
            ip_address='192.168.1.100',
            port=9100
        )
        
        # Test hazırlanma yeri yarat
        self.preparation_place = PreparationPlace.objects.create(
            name='Mətbəx',
            printer=self.printer
        )
    
    def test_list_preparation_places(self):
        """Hazırlanma yerlərini listələmə testi"""
        response = self.client.get('/api/printers/preparation-places/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_preparation_place(self):
        """Hazırlanma yeri yaratma testi"""
        data = {
            'name': 'Bar',
            'printer': self.printer.id
        }
        
        response = self.client.post('/api/printers/preparation-places/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Bar')
        self.assertTrue(PreparationPlace.objects.filter(name='Bar').exists())
    
    def test_create_preparation_place_duplicate_name(self):
        """Eyni adla hazırlanma yeri yaratma testi (xəta gözlənilir)"""
        data = {
            'name': self.preparation_place.name,
            'printer': self.preparation_place.printer.id
        }
        
        response = self.client.post('/api/printers/preparation-places/', data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_retrieve_preparation_place(self):
        """Tək hazırlanma yeri əldə etmə testi"""
        response = self.client.get(f'/api/printers/preparation-places/{self.preparation_place.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.preparation_place.name)
        self.assertIn('printer_detail', response.data)
    
    def test_update_preparation_place(self):
        """Hazırlanma yeri yeniləmə testi"""
        data = {
            'name': 'Yenilənmiş Mətbəx',
            'printer': self.preparation_place.printer.id
        }
        
        response = self.client.put(f'/api/printers/preparation-places/{self.preparation_place.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Yenilənmiş Mətbəx')
    
    def test_delete_preparation_place(self):
        """Hazırlanma yeri silmə testi"""
        response = self.client.delete(f'/api/printers/preparation-places/{self.preparation_place.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PreparationPlace.objects.filter(id=self.preparation_place.id).exists())
    
    def test_filter_by_printer(self):
        """Printerə görə filtrasiya testi"""
        response = self.client.get(f'/api/printers/preparation-places/?printer={self.printer.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class TestReceiptAPI(TestCase):
    """Çek API testləri"""
    
    def setUp(self):
        """Test setup"""
        self.client = APIClient()
        
        # Admin istifadəçi yarat
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.admin_user)
        
        # Test çek yarat
        self.receipt = Receipt.objects.create(
            type=Receipt.ReceiptType.CUSTOMER,
            text='Test receipt text'
        )
    
    def test_list_receipts(self):
        """Çekləri listələmə testi"""
        response = self.client.get('/api/printers/receipts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_retrieve_receipt(self):
        """Tək çek əldə etmə testi"""
        response = self.client.get(f'/api/printers/receipts/{self.receipt.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'Test receipt text')
        self.assertIn('type_display', response.data)
    
    def test_filter_receipts_by_type(self):
        """Növə görə çek filtrasiyası testi"""
        Receipt.objects.create(
            type=Receipt.ReceiptType.PREPERATION_PLACE,
            text='Kitchen receipt'
        )
        
        response = self.client.get(f'/api/printers/receipts/?type={Receipt.ReceiptType.CUSTOMER}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)


class TestPrinterActionsAPI(TestCase):
    """Printer action API testləri"""
    
    def setUp(self):
        """Test setup"""
        self.client = APIClient()
        
        # Admin istifadəçi yarat
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.admin_user)
        
        # Test printer yarat
        self.printer = Printer.objects.create(
            name='Test Printer',
            ip_address='192.168.1.100',
            port=9100
        )
    
    def test_test_print_with_printer_id(self):
        """Printer ID ilə test print testi"""
        data = {'printer_id': self.printer.id}
        
        # Mock test - real printerə bağlanmayacaq
        response = self.client.post('/api/printers/printers/test-print/', data)
        
        # Status 200 və ya 400 ola bilər (printer əlçatan deyilsə)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
    
    def test_test_print_with_ip_address(self):
        """IP address ilə test print testi"""
        data = {
            'ip_address': '192.168.1.100',
            'port': 9100
        }
        
        response = self.client.post('/api/printers/printers/test-print/', data)
        
        # Status 200 və ya 400 ola bilər (printer əlçatan deyilsə)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
    
    def test_test_print_without_data(self):
        """Məlumat olmadan test print testi (xəta gözlənilir)"""
        response = self.client.post('/api/printers/printers/test-print/', {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_scan_printers(self):
        """Printer scan testi"""
        response = self.client.get('/api/printers/printers/scan/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('printers', response.data)

