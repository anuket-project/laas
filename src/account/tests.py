from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from account.models import UserProfile, Lab, LabStatus
from django.db.models import QuerySet
from django.db.utils import IntegrityError
from django.http.response import JsonResponse, HttpResponse

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
        location = "Test Location",
        description = "Test Description",
        project = "Test Project"
        lab_user = User.objects.create_user("admin")
        about_text = "Test about us text"

        lab = Lab.objects.create(
            name=name,
            contact_email=contact_email,
            location=location,
            description=description,
            project=project,
            lab_user=lab_user,
            about_text=about_text
        )
        
        self.assertEqual(name, lab.name)
        self.assertEqual(contact_email, lab.contact_email)
        self.assertEqual(location, lab.location)
        self.assertEqual(description, lab.description)
        self.assertEqual(project, lab.project)
        self.assertEqual(lab_user, lab.lab_user)
        self.assertEqual(about_text, lab.about_text)
        
        # defaults
        self.assertEqual(lab.status, LabStatus.UP)
        self.assertEqual(lab.api_token, "")
        self.assertEqual(lab.lab_info_link, None)
        self.assertEqual(lab.lab_logo_link, None)
        self.assertEqual(lab.lab_home_link, None)
        

class UserApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        usersToMake = {
            "requester" : {
                "email_addr" : "tester@test.org",
                "name" : "",
                "public" : True,
            },
            ################################
            "bucktooth" : {
                "email_addr" : "sfayx8tx@test.org",
                "name" : "",
                "public" : True,
            },
            "disposal" : {
                "email_addr" : "zyruwsjs@ya.com",
                "name" : "",
                "public" : True,
            },
            "copilot2" : {
                "email_addr" : "uypmkhpg@real.com",
                "name" : "",
                "public" : True,
            },
            "residency" : {
                "email_addr" : "uermkppj@mail.co",
                "name" : "",
                "public" : True,
            },
            "copilot" : {
                "email_addr" : "uermkppj@mail.co",
                "name" : "",
                "public" : False,
            },
            "parasitic" : {
                "email_addr" : "mail@mail.com",
                "name" : "",
                "public" : False,
            },
            "mail@mail.com" : {
                "email_addr" : "disposal@mail.com",
                "name" : "",
                "public" : False,
            }
        }
        
        for username, info in usersToMake.items():
            newUser = User.objects.create(username=username)
            UserProfile.objects.create(user=newUser, ipa_username=username, email_addr=info["email_addr"], public_user=info["public"])
        
        self.requestUser = User.objects.get(username="requester")
        self.requestUserProfile = UserProfile.objects.get(user=self.requestUser)
        self.client.force_login(self.requestUser)


    def test_all_pub_collaborators(self):
        
        response: HttpResponse = self.client.get('/accounts/users/collaborators')
        query = UserProfile.objects.filter(public_user=True).exclude(user=self.requestUser)
        
        response_payload: dict = response.json()
        
        self.assertEqual(len(response_payload), query.count())
        for id, user in response_payload.items():
            small_set = query.filter(ipa_username=user['ipa'], email_addr=user['email'], full_name=user['full_name'])
            self.assertEqual(len(small_set), 1)
            self.assertEqual(small_set.first().pk, int(id))


    def test_query_user(self):
        expected_bad_query_result = {
            'is_user': False,
            'id' : None,
            'ipa' : '',
            'email': '',
            }


        bad_response: HttpResponse = self.client.get('/accounts/users/collaborators/validate')
        self.assertEqual(bad_response.status_code, 400)

        # Match neither, match an email and username, partial match email, partial match username
        bad_queries = ["garbage", "mail@mail.com", "uypmkhpg", "copilo"]
        for q in bad_queries:
            bad_query_response: HttpResponse = self.client.get('/accounts/users/collaborators/validate', data={"query":q})
            self.assertEqual(type(bad_query_response), type(JsonResponse({"dummy": "data"})))
            bad_json: dict = bad_query_response.json()
            self.assertDictEqual(bad_json, expected_bad_query_result)

        # pub user name match, email match. Repeat for private
        good_queries = ["disposal", "uypmkhpg@real.com", "parasitic", "disposal@mail.com"]
        for q in good_queries:
            good_query_response: HttpResponse = self.client.get('/accounts/users/collaborators/validate', data={"query":q})
            self.assertEqual(type(good_query_response), type(JsonResponse({"dummy": "data"})))
            good_json: dict = good_query_response.json()
            self.assertTrue(good_json["ipa"] == q or good_json["email"] == q)
            self.assertTrue(UserProfile.objects.filter(pk=good_json["id"]).count() == 1)