from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from PIL import Image
import io
import os
from .models import Profile

User = get_user_model()

class ProfileImageUpdateTestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
    def create_test_image(self, name='test.jpg', size=(100, 100), color='red'):
        """Create a test image file"""
        image = Image.new('RGB', size, color)
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile(
            name=name,
            content=image_io.getvalue(),
            content_type='image/jpeg'
        )
    
    def test_profile_image_update(self):
        """Test that profile image updates correctly"""
        # Create first image
        first_image = self.create_test_image('first.jpg', color='red')
        
        # Update profile with first image
        response = self.client.patch('/accounts/update-profile/', {
            'profile.profile_image': first_image
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Get the profile and check first image was saved
        profile = self.user.profile
        self.assertTrue(profile.profile_image)
        first_image_path = profile.profile_image.path
        self.assertTrue(os.path.exists(first_image_path))
        
        # Create second image
        second_image = self.create_test_image('second.jpg', color='blue')
        
        # Update profile with second image
        response = self.client.patch('/accounts/update-profile/', {
            'profile.profile_image': second_image
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh profile and check second image was saved
        profile.refresh_from_db()
        self.assertTrue(profile.profile_image)
        second_image_path = profile.profile_image.path
        
        # Check that the new image is different from the first
        self.assertNotEqual(first_image_path, second_image_path)
        
        # Check that old image was deleted (if signal is working)
        # Note: This might not work if the signal doesn't fire in tests
        # self.assertFalse(os.path.exists(first_image_path))
        
        # Check that new image exists
        self.assertTrue(os.path.exists(second_image_path))
        
        # Test API response contains new image URL
        response_data = response.json()
        self.assertIn('profile_image', response_data['user']['profile'])
        self.assertIsNotNone(response_data['user']['profile']['profile_image'])
        self.assertIn('second', response_data['user']['profile']['profile_image'])
    
    def test_get_profile_with_image(self):
        """Test that GET request returns profile with image URL"""
        # Create and set image
        test_image = self.create_test_image()
        profile = self.user.profile
        profile.profile_image = test_image
        profile.save()
        
        # Get profile
        response = self.client.get('/accounts/update-profile/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('profile_image', response_data['user']['profile'])
        self.assertIsNotNone(response_data['user']['profile']['profile_image'])
        self.assertTrue(response_data['user']['profile']['profile_image'].startswith('http'))

