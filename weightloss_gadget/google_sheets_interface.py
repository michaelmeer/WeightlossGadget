import httplib2
import os
import re
import string
from datetime import datetime, date
from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage
import logging

class CellReference(object):
    def __init__(self, sheet_name, column_nbr, row_nbr):
        self.sheet_name = sheet_name
        self.column_nbr = column_nbr
        self.row_nbr = row_nbr
        self.column_id = string.ascii_uppercase[self.column_nbr-1]
        self.sheets_range = "%s!%s%i" % (self.sheet_name, self.column_id, self.row_nbr)

    def FromSheetsRange(sheets_range):
        pattern = re.compile("(?P<sheet_name>[\w ]+)!(?P<column_id>[A-Z]{1,2})(?P<row_nbr>[0-9]+)")
        result = pattern.match(sheets_range)
        sheet_name = result.group('sheet_name')
        column_id = result.group('column_id')
        row_nbr = int(result.group('row_nbr'))
        column_nbr = string.ascii_uppercase.index(column_id[0])+1
        return CellReference(sheet_name, column_nbr, row_nbr)

    def FromCellReference(sheet_name, column_nbr, row_nbr):
        return CellReference(sheet_name, column_nbr, row_nbr)

    def add_delta(self, row_delta = 0, column_delta = 0):
        if self.column_nbr + column_delta < 1 or self.row_nbr + row_delta < 1:
            return None
        else:
            return CellReference(self.sheet_name, self.column_nbr + column_delta, self.row_nbr + row_delta)

class GoogleSheetsInterface(object):
    def __init__(self, client_secret_file, application_name, sheet_id):
        self.client_secret_file = client_secret_file
        self.application_name = application_name
        self.sheet_id = sheet_id
        self.header_columns = None
        self.logger = logging.getLogger("GoogleSheetsInterface")

        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        discovery_url = ('https://sheets.googleapis.com/$discovery/rest?'
                        'version=v4')
        self.service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discovery_url, cache_discovery=False)

    def get_credentials(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir, 'sheets.googleapis.%s.json'%self.application_name)

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(self.client_secret_file, SCOPES)
            flow.user_agent = self.application_name
            credentials = tools.run_flow(flow, store, flags)
            print('Storing credentials to ' + credential_path)
        return credentials

    def read_named_range_value_and_location(self, range):
        self.logger.info("self.service.spreadsheets().values().get(spreadsheetId=%s,range=%s).execute()"%(self.sheet_id, range))
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.sheet_id,
            range=range).execute()

        values = result.get('values', [[]])
        assert len(values)==1 and len(values[0])==1, 'Returned more than a single cell value'
        value = values[0][0]

        location = CellReference.FromSheetsRange(result.get('range'))
        return (value, location)

    def read_last_updates(self, person):
        range = "%s!LastUpdates"%person
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.sheet_id,
            range=range).execute()
        values = result["values"]
        dict_result = {entry[0]:entry[1] for entry in values}
        dict_result["Last Set Day"] = datetime.strptime(dict_result["Last Set Day"], "%Y-%m-%d").date().isoformat() # @TODO: Change to builtin conversion method
        dict_result["Latest Measured Weight"] = float(dict_result["Latest Measured Weight"])
        dict_result["Latest Trend Weight"] = float(dict_result["Latest Trend Weight"])
        dict_result["Latest Variance"] = float(dict_result["Latest Variance"])

        return dict_result

    def read_single_cell(self, sheet_id, range):
        result = self.service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range).execute()

        values = result.get('values', None)
        if values:
            assert len(values)==1 and len(values[0])<=1, 'Returned more than a single cell value'
            value = values[0][0]
            return value
        else:
            return None

    def read_startdate(self, person):
        startdate_range_name = "%s!StartDate"%person

        iso_string = self.read_single_cell(self.sheet_id, startdate_range_name)
        startdate = self.convert_iso_string_to_date(iso_string)
        return startdate

    def convert_datetime_to_iso_string(self, datetime_object):
        return datetime_object.isoformat()

    def convert_iso_string_to_date(self, iso_string):
        datetime_object = datetime.strptime(iso_string, '%Y-%m-%d')
        return datetime_object.date()

    def convert_string_to_float(self, value):
        if value:
            return float(value)
        else:
            return None

    def read_last_saved_weight(self, person, datetime_object = date.today()):
        start_date_string, start_date_reference = self.read_named_range_value_and_location("%s!StartDate"%person)
        start_date = self.convert_iso_string_to_date(start_date_string)
        offset_days = (datetime_object - start_date).days

        current_date_reference = start_date_reference.add_delta(row_delta=offset_days)
        value = None
        while current_date_reference.row_nbr >= start_date_reference.row_nbr and value is None:
            row = self.read_row(person, current_date_reference.row_nbr)
            row['Weight in kg'] = self.convert_string_to_float(row['Weight in kg'])
            row['Trend'] = self.convert_string_to_float(row['Trend'])
            row['Variance'] = self.convert_string_to_float(row['Variance'])
            value = row['Weight in kg']
            current_date_reference = current_date_reference.add_delta(row_delta=-1)

        return row

    def read_row(self, person, row):
        if self.header_columns is None:
            self.collect_header_columns(person)

        current_row_cell = CellReference(sheet_name=person, column_nbr=1,row_nbr=row)
        row = {}
        for header_column in self.header_columns:
            value = self.read_single_cell(self.sheet_id, current_row_cell.sheets_range)
            row[header_column]=value
            current_row_cell = current_row_cell.add_delta(column_delta=1)

        return row

    def read_weight_row(self, person, row):
        raw_row = self.read_row(person, row)
        raw_row['Weight in kg'] = float(raw_row['Weight in kg'])
        raw_row['Trend'] = float(raw_row['Trend'])
        raw_row['Variance'] = float(raw_row['Variance'])
        return raw_row

    def read_row_for_date(self, person, datetime_object):
        if self.header_columns is None:
            self.collect_header_columns(person)

        start_date_string, start_date_reference = self.read_named_range_value_and_location("%s!StartDate"%person)
        start_date = self.convert_iso_string_to_date(start_date_string)
        offset_days = (datetime_object - start_date).days

        current_row_cell = start_date_reference.add_delta(row_delta=offset_days)
        row = {}
        for header_column in self.header_columns:
            value = self.read_single_cell(self.sheet_id, current_row_cell.sheets_range)
            row[header_column]=value
            current_row_cell = current_row_cell.add_delta(column_delta=1)

        return row

    def collect_header_columns(self, person):
        current_header_cell = CellReference(person, 1, 1)
        self.header_columns = []
        look_at_next_cell = True
        while look_at_next_cell:
            header_column = self.read_single_cell(self.sheet_id, current_header_cell.sheets_range)
            if header_column:
                self.header_columns.append(header_column)
                current_header_cell = current_header_cell.add_delta(column_delta=1)
            else:
                look_at_next_cell = False

    def write_weight(self, person, weight, date_object = date.today()):
        if isinstance(date_object, str):
            date_object = self.convert_iso_string_to_date(date_object)
        start_date_string, start_date_reference = self.read_named_range_value_and_location("%s!StartDate" % person)
        start_date = self.convert_iso_string_to_date(start_date_string)
        offset_days = (date_object - start_date).days

        current_date_reference = start_date_reference.add_delta(row_delta=offset_days, column_delta=2)

        values = [
            [
                weight  # Cell values
            ],
            # Additional rows
        ]

        data = [
            {
                'range': current_date_reference.sheets_range,
                'values': values
            },
            # Additional ranges to update ...
        ]

        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data
        }
        result = self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.sheet_id, body=body).execute()