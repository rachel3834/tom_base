from datetime import datetime, timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from astroplan import Observer, FixedTarget
from astropy import units
from astropy.coordinates import get_sun, SkyCoord
from astropy.time import Time

from .factories import TargetFactory, ObservingRecordFactory, TargetNameFactory
from tom_observations.utils import get_astroplan_sun_and_time, get_sidereal_visibility
from tom_observations.tests.utils import FakeFacility
from tom_observations.models import ObservationRecord
from tom_targets.models import Target
from guardian.shortcuts import assign_perm


@override_settings(TOM_FACILITY_CLASSES=['tom_observations.tests.utils.FakeFacility'])
class TestObservationViews(TestCase):
    def setUp(self):
        self.target = TargetFactory.create()
        self.target_name = TargetNameFactory.create(target=self.target)
        self.observation_record = ObservingRecordFactory.create(
            target_id=self.target.id,
            facility=FakeFacility.name,
            parameters='{}'
        )
        user = User.objects.create_user(username='test', password='test')
        assign_perm('tom_targets.view_target', user, self.target)
        self.client.force_login(user)

    def test_observation_list(self):
        response = self.client.get(reverse('tom_observations:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, reverse('tom_observations:detail', kwargs={'pk': self.observation_record.id})
        )

    def test_observation_detail(self):
        response = self.client.get(
            reverse('tom_observations:detail', kwargs={'pk': self.observation_record.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, FakeFacility().get_observation_url(self.observation_record.observation_id)
        )

    def test_update_observations(self):
        response = self.client.get(reverse('tom_observations:list') + '?update_status=True', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'COMPLETED')

    def test_get_observation_form(self):
        response = self.client.get(
            '{}?target_id={}'.format(
                reverse('tom_observations:create', kwargs={'facility': 'FakeFacility'}),
                self.target.id
            )
        )
        self.assertContains(response, 'fake form input')

    def test_submit_observation(self):
        form_data = {
            'target_id': self.target.id,
            'test_input': 'gnomes',
            'facility': 'FakeFacility',
        }
        self.client.post(
            '{}?target_id={}'.format(
                reverse('tom_observations:create', kwargs={'facility': 'FakeFacility'}),
                self.target.id
            ),
            data=form_data,
            follow=True
        )
        self.assertTrue(ObservationRecord.objects.filter(observation_id='fakeid').exists())


class TestUpdatingObservations(TestCase):
    def setUp(self):
        self.t1 = TargetFactory.create()
        self.or1 = ObservingRecordFactory.create(target_id=self.t1.id, facility='FakeFacility', status='PENDING')
        self.or2 = ObservingRecordFactory.create(target_id=self.t1.id, status='COMPLETED')
        self.or3 = ObservingRecordFactory.create(target_id=self.t1.id, facility='FakeFacility', status='PENDING')
        self.t2 = TargetFactory.create()
        self.or4 = ObservingRecordFactory.create(target_id=self.t2.id, status='PENDING')

    # Tests that only 2 of the three created observing records are updated, as
    # the third is in a completed state
    def test_update_all_observations_for_facility(self):
        with mock.patch.object(FakeFacility, 'update_observation_status') as uos_mock:
            FakeFacility().update_all_observation_statuses()
            self.assertEquals(uos_mock.call_count, 2)

    # Tests that only the observing records associated with the given target are updated
    def test_update_individual_target_observations_for_facility(self):
        with mock.patch.object(FakeFacility, 'update_observation_status', return_value='COMPLETED') as uos_mock:
            FakeFacility().update_all_observation_statuses(target=self.t1)
            self.assertEquals(uos_mock.call_count, 2)


class TestGetVisibility(TestCase):
    def setUp(self):
        self.sun = get_sun(Time(datetime(2019, 10, 9, 13, 56)))
        self.target = Target(
            ra=(self.sun.ra.deg + 180) % 360,
            dec=-(self.sun.dec.deg),
            type=Target.SIDEREAL
        )
        self.start = datetime(2018, 10, 9, 13, 56, 16)
        self.interval = 10
        self.airmass_limit = 10

    def test_get_astroplan_sun_and_time(self):
        end = self.start + timedelta(days=2)
        sun, time_range = get_astroplan_sun_and_time(self.start, end, self.interval)
        self.assertIsInstance(sun, SkyCoord)
        self.assertEqual(len(time_range), 288)
        check_time_range = [time.mjd for time in time_range[::50]]
        expected_time_range = [58400.58074074052, 58400.92796296533,
                               58401.27518519014, 58401.62240741495,
                               58401.96962963976, 58402.31685186457]
        for i in range(0, len(expected_time_range)):
            self.assertEqual(check_time_range[i], expected_time_range[i])

    def test_get_astroplan_sun_and_time_small_range(self):
        end = self.start + timedelta(hours=10)
        sun, time_range = get_astroplan_sun_and_time(self.start, end, self.interval)
        self.assertIsInstance(sun, FixedTarget)
        self.assertEqual(len(time_range), 61)
        check_time_range = [time.mjd for time in time_range[::20]]
        expected_time_range = [58400.58074074052, 58400.71962963045,
                               58400.85851852037, 58400.997407410294]
        for i in range(0, len(expected_time_range)):
            self.assertEqual(check_time_range[i], expected_time_range[i])

    def test_get_visibility_invalid_target_type(self):
        invalid_target = self.target
        invalid_target.type = 'Invalid Type'
        end = self.start + timedelta(minutes=60)
        airmass = get_sidereal_visibility(invalid_target, self.start, end, self.interval, self.airmass_limit)
        self.assertEqual(len(airmass), 0)

    def test_get_visibility_invalid_params(self):
        self.assertRaisesRegex(
            Exception, 'Start must be before end', get_sidereal_visibility,
            self.target, datetime(2018, 10, 10), datetime(2018, 10, 9),
            self.interval, self.airmass_limit
        )

    @mock.patch('tom_observations.utils.facility.get_service_classes')
    def test_get_visibility_sidereal(self, mock_facility):
        mock_facility.return_value = {'Fake Facility': FakeFacility}
        end = self.start + timedelta(minutes=60)
        airmass = get_sidereal_visibility(self.target, self.start, end, self.interval, self.airmass_limit)
        airmass_data = airmass['(Fake Facility) Siding Spring'][1]
        expected_airmass = [
            1.2619096566629477, 1.2648181328558852, 1.2703522349950636, 1.2785703053923894,
            1.2895601364316183, 1.3034413026227516, 1.3203684217446099
        ]
        self.assertEqual(len(airmass_data), len(expected_airmass))
        for i in range(0, len(expected_airmass)):
            self.assertAlmostEqual(airmass_data[i], expected_airmass[i], places=3)
