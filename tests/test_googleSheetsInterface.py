from datetime import date
from unittest import TestCase

from weightloss_gadget import google_sheets_interface


class TestGoogleSheetsInterface(TestCase):
    def setUp(self):
        self.interface = google_sheets_interface.GoogleSheetsInterface(
            client_secret_file = r'..\resources\client_secret_1082141044520-n0cg7u76fd8pvvagh929o91538u1val1.apps.googleusercontent.com.json',
            application_name = 'dailycalories',
            sheet_id = '1VHbeWIq21ib7MndwwCHRon52of1MI4z9RVproZ_kpCk'
        )
        self.testperson = "Testperson"

    def test_startdate(self):
        self.assertEqual(date(2017,1,1), self.interface.read_startdate(self.testperson))

    def test_read_last_saved_weight(self):
        self.assertEqual(self.interface.read_last_saved_weight(self.testperson, date(2017,1,1))['Weight in kg'], 100)
        self.assertEqual(self.interface.read_last_saved_weight(self.testperson, date(2017,1,2))['Weight in kg'], 99.9)
        self.assertEqual(self.interface.read_last_saved_weight(self.testperson, date(2017,11,7))['Weight in kg'], 69.0)
        self.assertEqual(self.interface.read_last_saved_weight(self.testperson, date(2017,12,31))['Weight in kg'], 63.6)
        self.assertEqual(self.interface.read_last_saved_weight(self.testperson, date(2018,1,1))['Weight in kg'], 63.6)
        self.assertEqual(self.interface.read_last_saved_weight(self.testperson, date(2018,1,10))['Weight in kg'], 63.6)

    def test_read_last_updates(self):
        last_updates = self.interface.read_last_updates(self.testperson)
        self.assertEqual(last_updates["Last Set Day"], "2017-12-31")
        self.assertEqual(last_updates["Latest Measured Weight"], 63.6)
        self.assertEqual(last_updates["Latest Trend Weight"], 64.5)
        self.assertEqual(last_updates["Latest Variance"], -0.9)

    def test_cell_reference_from_sheets_range(self):
        cell_A1 = google_sheets_interface.CellReference.FromSheetsRange("Testperson!A1")
        self.assertEqual(cell_A1.sheet_name, "Testperson")
        self.assertEqual(cell_A1.column_nbr, 1)
        self.assertEqual(cell_A1.column_id, "A")
        self.assertEqual(cell_A1.row_nbr, 1)

        cell_B3 = google_sheets_interface.CellReference.FromSheetsRange("Testperson!B3")
        self.assertEqual(cell_B3.sheet_name, "Testperson")
        self.assertEqual(cell_B3.column_nbr, 2)
        self.assertEqual(cell_B3.column_id, "B")
        self.assertEqual(cell_B3.row_nbr, 3)

    def test_sheets_range_from_cell_reference(self):
        cell_A1 = google_sheets_interface.CellReference.FromCellReference(sheet_name='Testperson', column_nbr=1, row_nbr=1)
        self.assertEqual(cell_A1.sheets_range, "Testperson!A1")

        cell_B3 = google_sheets_interface.CellReference.FromCellReference(sheet_name='Testperson', column_nbr=2, row_nbr=3)
        self.assertEqual(cell_B3.sheets_range, "Testperson!B3")

    def test_sheets_range_add_delta(self):
        cell_A1 = google_sheets_interface.CellReference.FromSheetsRange("Testperson!A1")
        self.assertEqual(cell_A1.add_delta(row_delta = 1, column_delta = 1).sheets_range, "Testperson!B2")
        self.assertEqual(cell_A1.add_delta(row_delta = 1, column_delta = 0).sheets_range, "Testperson!A2")
        self.assertEqual(cell_A1.add_delta(row_delta = 0, column_delta = 1).sheets_range, "Testperson!B1")
        self.assertEqual(cell_A1.add_delta(row_delta = -1, column_delta = -1), None)

    def test_read_named_range_value_and_location(self):
        value, start_date_reference = self.interface.read_named_range_value_and_location("StartDate")

        self.assertEqual(value, "2017-01-01")
        self.assertEqual(start_date_reference.sheets_range, "Testperson!A2")

    def test_read_row_for_date(self):
        row = self.interface.read_row_for_date(self.testperson, date(2017,1,1))
        self.assertEqual(row['Date'], '2017-01-01')
        self.assertEqual(row['Weekday'], 'Sunday')
        self.assertEqual(row['Weight in kg'], '100.0')
        self.assertEqual(row['Trend'], '100.0')
        self.assertEqual(row['Variance'], '0')

        row = self.interface.read_row_for_date(self.testperson, date(2017,1,10))
        self.assertEqual(row['Date'], '2017-01-10')
        self.assertEqual(row['Weekday'], 'Tuesday')
        self.assertEqual(row['Weight in kg'], '99.1')
        self.assertEqual(row['Trend'], '99.7')
        self.assertEqual(row['Variance'], '-0.6')

        row = self.interface.read_row_for_date(self.testperson, date(2017,2,1))
        self.assertEqual(row['Date'], '2017-02-01')
        self.assertEqual(row['Weekday'], 'Wednesday')
        self.assertEqual(row['Weight in kg'], '96.9')
        self.assertEqual(row['Trend'], '97.8')
        self.assertEqual(row['Variance'], '-0.9')

    def test_read_row(self):
        row = self.interface.read_row(self.testperson, 2)
        self.assertEqual(row['Date'], '2017-01-01')
        self.assertEqual(row['Weekday'], 'Sunday')
        self.assertEqual(row['Weight in kg'], '100.0')
        self.assertEqual(row['Trend'], '100.0')
        self.assertEqual(row['Variance'], '0')

        row = self.interface.read_row(self.testperson, 11)
        self.assertEqual(row['Date'], '2017-01-10')
        self.assertEqual(row['Weekday'], 'Tuesday')
        self.assertEqual(row['Weight in kg'], '99.1')
        self.assertEqual(row['Trend'], '99.7')
        self.assertEqual(row['Variance'], '-0.6')

        row = self.interface.read_row(self.testperson, 33)
        self.assertEqual(row['Date'], '2017-02-01')
        self.assertEqual(row['Weekday'], 'Wednesday')
        self.assertEqual(row['Weight in kg'], '96.9')
        self.assertEqual(row['Trend'], '97.8')
        self.assertEqual(row['Variance'], '-0.9')

    def test_read_weight_row(self):
        row = self.interface.read_weight_row(self.testperson, 2)
        self.assertEqual(row['Date'], '2017-01-01')
        self.assertEqual(row['Weekday'], 'Sunday')
        self.assertEqual(row['Weight in kg'], 100.0)
        self.assertEqual(row['Trend'], 100.0)
        self.assertEqual(row['Variance'], 0)

        row = self.interface.read_weight_row(self.testperson, 11)
        self.assertEqual(row['Date'], '2017-01-10')
        self.assertEqual(row['Weekday'], 'Tuesday')
        self.assertEqual(row['Weight in kg'], 99.1)
        self.assertEqual(row['Trend'], 99.7)
        self.assertEqual(row['Variance'], -0.6)

        row = self.interface.read_weight_row(self.testperson, 33)
        self.assertEqual(row['Date'], '2017-02-01')
        self.assertEqual(row['Weekday'], 'Wednesday')
        self.assertEqual(row['Weight in kg'], 96.9)
        self.assertEqual(row['Trend'], 97.8)
        self.assertEqual(row['Variance'], -0.9)

    def test_write_weight(self):
        test_weight = 200
        row =  self.interface.read_weight_row(self.testperson, 2)
        original_weight = row['Weight in kg']
        original_date = row['Date']
        self.interface.write_weight(person = self.testperson, date_object = original_date, weight = test_weight)

        row = self.interface.read_weight_row(self.testperson, 2)
        self.assertEqual(row['Weight in kg'], test_weight)
        self.assertEqual(row['Date'], original_date)
        original_date = row['Date']

        self.interface.write_weight(person=self.testperson, date_object = original_date, weight=original_weight)
        row = self.interface.read_weight_row(self.testperson, 2)
        self.assertEqual(row['Weight in kg'], original_weight)
        self.assertEqual(row['Date'], original_date)