from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from account.models import UserProfile, Lab, LabStatus
from django.db.models import QuerySet
from django.db.utils import IntegrityError

# Small test script in order to test if user auth tokens are being created
# as expected
class TokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create()
        userprof = UserProfile.objects.create(user=self.user)
        user_2 = User.objects.create(username='2')
        userprof_2 = UserProfile.objects.create(user=user_2)
        user_3 = User.objects.create(username='3')
        userprof_3 = UserProfile.objects.create(user=user_3)
    # Checking if calling the single use create tokens for all
    # leaves users who have token
    def test_no_double_tokens(self):
        UserProfile.create_tokens_for_all()
        UserProfile.create_tokens_for_all()
        self.assertEqual(len(Token.objects.filter(user=self.user)), 1)
    # Checking each user has one token
    def test_one_to_one_tokens(self):
        self.assertEqual(len(Token.objects.all()), len(UserProfile.objects.all()))
    # Checking if the new user profile created has token
    def test_tokens_created(self):
        self.assertEqual(len(Token.objects.filter(user=self.user)), 1)

class SchemaTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        
        cls.user_count = 20

        for i in range(cls.user_count):
            UserProfile.objects.create(
                user=User.objects.create_user(
                f"testuser{i}",
                f"testuser{i}@email.com",
                f"testpass{i}",
                )
            )


        cls.all_users = User.objects.all()
        cls.all_profiles = UserProfile.objects.all()
    def test_users_exist_with_correct_fields(self):
        self.assertEqual(len(self.all_users), self.user_count)
        for i in range(self.user_count):
            user: QuerySet[User] = self.all_users.filter(username=f'testuser{i}')
            self.assertEqual(len(user), 1)

            user: User = user.first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, f'testuser{i}@email.com')
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)
            
    def test_profile_exists_for_each_user(self):
        self.assertEqual(len(self.all_profiles), self.user_count)
        
        for user in self.all_users:
            profile = UserProfile.objects.get(user=user)
            self.assertIsNotNone(profile)
            
    def test_create_duplicate_user_fails(self):
        User.objects.create_user(
            "duplicateuser",
            "duplicateuser@email.com",
            "testpass"
        )
        self.assertRaises(
            IntegrityError,
            User.objects.create_user,
            "duplicateuser",
            "duplicateuser@email.com",
            "testpass" 
        )

    def test_create_lab_succeeds(self):
        name = "TestLab",
        contact_email = "test@email.com",
        contact_phone =" 555-555-5555"
        location = "Test Location",
        description = "Test Description",
        project = "Test Project"
        lab_user = User.objects.create_user("admin")

        lab = Lab.objects.create(
            name=name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            location=location,
            description=description,
            project=project,
            lab_user=lab_user
        )
        
        self.assertEqual(name, lab.name)
        self.assertEqual(contact_email, lab.contact_email)
        self.assertEqual(contact_phone, lab.contact_phone)
        self.assertEqual(location, lab.location)
        self.assertEqual(description, lab.description)
        self.assertEqual(project, lab.project)
        self.assertEqual(lab_user, lab.lab_user)
        
        # defaults
        self.assertEqual(lab.status, LabStatus.UP)
        self.assertEqual(lab.api_token, "")
        self.assertEqual(lab.lab_info_link, None)

