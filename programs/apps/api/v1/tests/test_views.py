"""
Tests for Programs API views (v1).
"""
import json

import ddt
from django.core.urlresolvers import reverse
from django.test import TestCase
from mock import ANY

from programs.apps.api.v1.tests.mixins import AuthClientMixin, JwtMixin
from programs.apps.core.constants import Role
from programs.apps.core.tests.factories import UserFactory
from programs.apps.programs.constants import ProgramCategory, ProgramStatus
from programs.apps.programs.tests.factories import (
    CourseCodeFactory,
    OrganizationFactory,
    ProgramCourseCodeFactory,
    ProgramFactory,
    ProgramOrganizationFactory,
)


USERNAME = 'preferred_username'
POST_FIELDS = ("name", "subtitle", "category", "status")
CATEGORIES = (ProgramCategory.XSERIES, )
STATUSES = (ProgramStatus.UNPUBLISHED, ProgramStatus.ACTIVE, ProgramStatus.RETIRED, ProgramStatus.DELETED)
DRF_DATE_FORMAT = u'%Y-%m-%dT%H:%M:%S.%fZ'


@ddt.ddt
class ProgramsViewTests(JwtMixin, TestCase):
    """
    Tests for listing / creating / viewing Programs.
    """
    @staticmethod
    def _build_post_data(**kwargs):
        """
        Build and return a dict representation to use for POST / create.
        """
        instance = ProgramFactory.build(**kwargs)
        return {k: getattr(instance, k) for k in POST_FIELDS}

    def _make_request(self, method='get', program_id=None, data=None, admin=False):
        """
        DRY helper.
        """
        token = self.generate_id_token(UserFactory(), admin=admin)
        auth = 'JWT {0}'.format(token)
        if program_id is not None:
            url = reverse("api:v1:programs-detail", kwargs={'pk': program_id})
        else:
            url = reverse("api:v1:programs-list")
        return getattr(self.client, method)(url, data=data, HTTP_AUTHORIZATION=auth)

    def test_authentication(self):
        """
        Ensure that authentication is required to use the view
        """
        response = self.client.get(reverse("api:v1:programs-list"))
        self.assertEqual(response.status_code, 401)

        response = self.client.post(reverse("api:v1:programs-list"), data=self._build_post_data())
        self.assertEqual(response.status_code, 401)

    def test_permission_add_program(self):
        """
        Ensure that add_program permission is required to create a program
        """
        response = self._make_request(method='post', data=self._build_post_data())
        self.assertEqual(response.status_code, 403)

    def test_list_admin(self):
        """
        Verify the list includes all Programs, except those with DELETED status, for ADMINS.
        """
        # create one Program of each status
        for status in STATUSES:
            ProgramFactory(name="{} program".format(status), status=status)

        response = self._make_request(admin=True)
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)['results']
        self.assertEqual(len(results), 3)
        self.assertNotIn(ProgramStatus.DELETED, set(obj["status"] for obj in results))

    def test_list_learner(self):
        """
        Verify the list includes only UNPUBLISHED and RETIRED Programs, for LEARNERS.
        """
        # create one Program of each status
        for status in STATUSES:
            ProgramFactory(name="{} program".format(status), status=status)

        response = self._make_request()
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)['results']
        self.assertEqual(len(results), 2)
        statuses = set(obj["status"] for obj in results)
        self.assertNotIn(ProgramStatus.DELETED, statuses)
        self.assertNotIn(ProgramStatus.UNPUBLISHED, statuses)

    @ddt.data(ProgramStatus.UNPUBLISHED, ProgramStatus.ACTIVE, ProgramStatus.RETIRED)
    def test_status_list_filter(self, query_status):
        """
        Verify that list results can be filtered by a 'status' query string argument.
        """
        # create one Program of each status
        for status in STATUSES:
            ProgramFactory(name="{} program".format(status), status=status)

        response = self._make_request(admin=True, data={'status': query_status})
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], query_status)

    def test_org_list_filter(self):
        """
        Verify that list results can be filtered by an 'organization' query string argument.
        """
        org_keys = ("org1", "org2")
        for org_key in org_keys:
            org = OrganizationFactory.create(key=org_key)
            program = ProgramFactory.create()
            ProgramOrganizationFactory.create(organization=org, program=program)

        for org_key in org_keys:
            response = self._make_request(admin=True, data={'organization': org_key})
            self.assertEqual(response.status_code, 200)
            results = json.loads(response.content)['results']
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['organizations'][0]['key'], org_key)

    def test_create(self):
        """
        Ensure the API supports creation of Programs.
        """
        data = self._build_post_data()
        response = self._make_request(method='post', data=data, admin=True)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            json.loads(response.content),
            {
                u"name": data["name"],
                u"subtitle": data["subtitle"],
                u"category": data["category"],
                u"status": data["status"],
                u"organizations": [],
                u"course_codes": [],
                u"id": ANY,
                u"created": ANY,
                u"modified": ANY,
            }
        )

    @ddt.data(*STATUSES)
    def test_view_admin(self, status):
        """
        Test that the detail view works correctly for ADMINS, and that deleted
        Programs are filtered out.
        """
        program = ProgramFactory.create(status=status)
        response = self._make_request(program_id=program.id, admin=True)
        self.assertEqual(response.status_code, 404 if status == ProgramStatus.DELETED else 200)
        if status != ProgramStatus.DELETED:
            self.assertEqual(
                json.loads(response.content),
                {
                    u"name": program.name,
                    u"subtitle": program.subtitle,
                    u"category": program.category,
                    u"status": status,
                    u"organizations": [],
                    u"course_codes": [],
                    u"id": program.id,
                    u"created": program.created.strftime(DRF_DATE_FORMAT),
                    u"modified": program.modified.strftime(DRF_DATE_FORMAT),
                }
            )

    @ddt.data(*STATUSES)
    def test_view_learner(self, status):
        """
        Test that the detail view works correctly for non-ADMINS, and that
        unpublished and deleted Programs are filtered out.
        """
        filtered_statuses = (ProgramStatus.DELETED, ProgramStatus.UNPUBLISHED)
        program = ProgramFactory.create(status=status)
        response = self._make_request(program_id=program.id)
        self.assertEqual(response.status_code, 404 if status in filtered_statuses else 200)
        if status not in filtered_statuses:
            self.assertEqual(
                json.loads(response.content),
                {
                    u"name": program.name,
                    u"subtitle": program.subtitle,
                    u"category": program.category,
                    u"status": status,
                    u"organizations": [],
                    u"course_codes": [],
                    u"id": program.id,
                    u"created": program.created.strftime(DRF_DATE_FORMAT),
                    u"modified": program.modified.strftime(DRF_DATE_FORMAT),
                }
            )

    def test_view_with_nested(self):
        """
        Ensure that nested serializers are working in program detail views.
        """
        org = OrganizationFactory.create(key="test-org-key", display_name="test-org-display_name")
        program = ProgramFactory.create()
        ProgramOrganizationFactory.create(program=program, organization=org)
        course_code = CourseCodeFactory.create(
            key="test-course-key",
            display_name="test-course-display_name",
            organization=org,
        )
        ProgramCourseCodeFactory.create(program=program, course_code=course_code)

        response = self._make_request(program_id=program.id, admin=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {
                u"name": program.name,
                u"subtitle": program.subtitle,
                u"category": program.category,
                u"status": ProgramStatus.UNPUBLISHED,
                u"organizations": [
                    {
                        u"key": "test-org-key",
                        u"display_name": "test-org-display_name",
                    }
                ],
                u"course_codes": [
                    {
                        u"key": "test-course-key",
                        u"display_name": "test-course-display_name",
                        u"organization": {
                            u"key": "test-org-key",
                            u"display_name": "test-org-display_name",
                        },
                        u"run_modes": [],
                    }
                ],
                u"id": program.id,
                u"created": program.created.strftime(DRF_DATE_FORMAT),
                u"modified": program.modified.strftime(DRF_DATE_FORMAT),
            }
        )

    @ddt.data(*POST_FIELDS)
    def test_missing_fields(self, field):
        """
        Ensure that missing fields cause validation errors if required, and create with correct defaults otherwise.
        """
        defaults = {
            "subtitle": None,
            "status": ProgramStatus.UNPUBLISHED,
        }

        data = self._build_post_data()
        del data[field]
        if field in defaults:
            expected_status = 201
        else:
            expected_status = 400

        response = self._make_request(method='post', data=data, admin=True)
        self.assertEqual(response.status_code, expected_status)
        content = json.loads(response.content)
        if expected_status == 201:
            self.assertEqual(content[field], defaults[field])
        else:
            self.assertIn("field is required", content[field][0])

    @ddt.data(ProgramStatus.ACTIVE, ProgramStatus.RETIRED, ProgramStatus.DELETED, None, "", " ", "unrecognized")
    def test_create_with_invalid_status(self, status):
        """
        Ensure that it is not allowed to create a Program with a status other than "unpublished"
        """
        data = self._build_post_data(status=status)
        response = self._make_request(method='post', data=data, admin=True)
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertIn("not a valid choice", content["status"][0])

    @ddt.data(None, "", "unrecognized")
    def test_create_with_invalid_category(self, category):
        """
        Ensure that it is not allowed to create a Program with an empty or unrecognized category
        """
        data = self._build_post_data(category=category)
        response = self._make_request(method='post', data=data, admin=True)
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertIn("not a valid choice", content["category"][0])

    def test_create_duplicated_name(self):
        """
        Ensure that it is not allowed to create a Program with a duplicate name
        """
        ProgramFactory(name="duplicated name")  # saved directly to db
        data = self._build_post_data(name="duplicated name")
        response = self._make_request(method='post', data=data, admin=True)
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertIn("must be unique", content["name"][0])


class OrganizationViewTests(AuthClientMixin, TestCase):
    """
    Tests for listing / creating Organizations.
    """

    def test_create(self):
        """
        Ensure the API supports creation of Organizations.
        """
        data = {'key': 'edX', 'display_name': 'edX University'}
        client = self.get_authenticated_client(Role.ADMINS)
        response = client.post(reverse("api:v1:organizations-list"), data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data,  # pylint: disable=no-member
            {
                u"key": data["key"],
                u"display_name": data["display_name"],
            }
        )

    def test_create_unauthorized(self):
        """
        Ensure the API prevents unauthorized users from creating organizations.
        """
        data = {'key': 'edX', 'display_name': 'edX University'}
        client = self.get_authenticated_client(Role.LEARNERS)
        response = client.post(reverse("api:v1:organizations-list"), data)
        self.assertEqual(response.status_code, 403)

    def test_list(self):
        """
        Ensure the API supports listing of Organizations by admins.
        """
        for _ in range(3):
            OrganizationFactory.create()
        client = self.get_authenticated_client(Role.ADMINS)
        response = client.get(reverse("api:v1:organizations-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # pylint: disable=no-member

    def test_list_unauthorized(self):
        """
        Ensure the API prevents unauthorized users from listing organizations.
        """
        for _ in range(3):
            OrganizationFactory.create()
        client = self.get_authenticated_client(Role.LEARNERS)
        response = client.get(reverse("api:v1:organizations-list"))
        self.assertEqual(response.status_code, 403)


class CourseCodesViewTests(AuthClientMixin, TestCase):
    """
    Tests for listing / creating Organizations.
    """

    def test_list(self):
        """
        Ensure the API supports listing of Organizations by system users and admins.
        """
        org = OrganizationFactory.create()
        for _ in range(3):
            CourseCodeFactory.create(organization=org)
        client = self.get_authenticated_client(Role.ADMINS)
        response = client.get(reverse("api:v1:course_codes-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # pylint: disable=no-member

    def test_list_unauthorized(self):
        """
        Ensure the API prevents unauthorized users from listing organizations.
        """
        client = self.get_authenticated_client(Role.LEARNERS)
        response = client.get(reverse("api:v1:course_codes-list"))
        self.assertEqual(response.status_code, 403)

    def test_org_list_filter(self):
        """
        """
        org_keys = (u'org1', u'org2')
        for org_key in org_keys:
            org = OrganizationFactory.create(key=org_key)
            CourseCodeFactory.create(organization=org)

        client = self.get_authenticated_client(Role.ADMINS)
        for org_key in org_keys:
            response = client.get(reverse("api:v1:course_codes-list"), {"organization": org_key})
            self.assertEqual(response.status_code, 200)
            results = response.data['results']  # pylint: disable=no-member
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['organization']['key'], org_key)
