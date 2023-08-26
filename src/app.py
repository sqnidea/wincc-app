from dash import dcc, html, dash,dash_table
from dash import Output, Input
import dash_bootstrap_components as dbc
import json
from datetime import datetime, timedelta
import threading
import AWSIoTPythonSDK.MQTTLib as AWSIoTPyMQTT
import pandas as pd


#-------------------------------------------AWS SDK CONFIGURATION START-------------------------------------------------
# Define ENDPOINT, CLIENT_ID, PATH_TO_CERT, PATH_TO_KEY, PATH_TO_ROOT, MESSAGE, TOPIC, and RANGE
ENDPOINT = "/etc/secrets/endpoint"
CLIENT_ID = "/etc/secrets/client_id"
PATH_TO_CERT = "/etc/secrets/certificate.pem.crt"
PATH_TO_KEY = "/etc/secrets/private.pem.key"
PATH_TO_ROOT = "/etc/secrets/AmazonRootCA1.pem"
#-------------------------------------------AWS SDK CONFIGURATION END---------------------------------------------------
#-------------------------------------Initialize the AWS IoT SDK MQTT client START--------------------------------------------
myAWSIoTMQTTClient = AWSIoTPyMQTT.AWSIoTMQTTClient(CLIENT_ID)
myAWSIoTMQTTClient.configureEndpoint(ENDPOINT, 8883)
myAWSIoTMQTTClient.configureCredentials(PATH_TO_ROOT, PATH_TO_KEY, PATH_TO_CERT)
myAWSIoTMQTTClient.configureMQTTOperationTimeout(30)
myAWSIoTMQTTClient.connect()
#-------------------------------------Initialize the AWS IoT SDK MQTT client END--------------------------------------------
# Global variable to store the latest received data
latest_data_lock = threading.Lock()
latest_data = {"lp_date": "", "lp_name": "", "lp_value": "",
                "c5to10_date":"","c5to10_name":"","c5to10_value":"",
                "c11to20_date":"","c11to20_name":"","c11to20_value":""
               }
#Arrays per Tag
time_value_tag1 = []
tag_value_tag1 = []

time_value_tag2 = []
tag_value_tag2 = []

time_value_tag3 = []
tag_value_tag3 = []

public_data = {}
app = dash.Dash(__name__,external_stylesheets=[dbc.themes.FLATLY])
server = app.server
#Function Declaration
def customCallback(client, userdata, message):
    payload = message.payload
    try:
        data = json.loads(payload)
        raw_date_cloud_ts = str(data["time"])
        name = str(data["name"])
        value = str(data["value"])

        # Convert the raw date string to a datetime object
        datetime_obj = datetime.strptime(raw_date_cloud_ts, "%Y-%m-%dT%H:%M:%S.%fZ")

        # Add 8 hours to the datetime object
        updated_datetime = datetime_obj + timedelta(hours=8)

        # Format the updated datetime object as "yyyy-mm-dd hh:mm"
        date = updated_datetime.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f'Error: {e}')
        return

    print("Received message on topic:", message.topic)
    #print("Name:", name, "Value:", value)

    with latest_data_lock:
        if name == "Level_Percentage":
            latest_data["lp_date"] = date
            latest_data["lp_name"] = name
            latest_data["lp_value"] = value

        elif name == "Counter_5_to_10":
            latest_data["c5to10_date"] = date
            latest_data["c5to10_name"] = name
            latest_data["c5to10_value"] = value

        elif name == "Counter_11_to_20":
            latest_data["c11to20_date"] = date
            latest_data["c11to20_name"] = name
            latest_data["c11to20_value"] = value

#App Components
webTitle = dcc.Markdown(children='# Mtech Wincc to Cloud Demo')
webDropdown = dcc.Dropdown(
        id='tag-dropdown',
        options=[
            {'label':'Tag - Level Percentage','value':'tag_lp'},
            {'label':'Tag - Counter 5 to 10','value':'tag_c5-10'},
            {'label':'Tag - Counter 11 to 20','value':'tag_c11-20'}
        ],
        #default dropdown value--
        #value='tag_c11-20',
        #placeholder--
        placeholder='select tag to monitor'
    )
webCyclicUpdates = dcc.Interval(
        id='my-interval',
        interval=1000,# in milliseconds
    n_intervals=0
    )
tagValueLabel = html.Label('This is the Tag Value:')

webTagOutput = html.Div(id='output')

report_table = dash_table.DataTable(
        id='reporting_table',
        columns=[
            {'name': 'Date', 'id': 'date'},
            {'name': 'Value', 'id': 'value'}
        ],
        data=[],
        style_cell={'textAlign': 'center'}
    )

report_cyclic_15s = dcc.Interval(
        id='report-interval',
        interval=15000,# in milliseconds
    n_intervals=0
    )

download_csv_btn = html.Div([
    html.Button("Download CSV", id="btn_csv"),
    dcc.Download(id="download-dataframe-csv"),
])

#App Layout
app.layout = dbc.Container([
    dbc.Row([dbc.Col([webTitle],width=12)]),
    dbc.Row([dbc.Col([webDropdown],width=12)]),
    dbc.Row([dbc.Col([tagValueLabel], width=6)]),
    dbc.Row(webCyclicUpdates),
    dbc.Row([dbc.Col([webTagOutput],width=12)]),
    dbc.Row(report_cyclic_15s),
    dbc.Row(download_csv_btn),
    dbc.Row([dbc.Col([report_table],width=12)])

],fluid=True)
#-------------------Dash Callback Function-------------------------
@app.callback(Output(webTagOutput, 'children'),
    Input(webDropdown, 'value'),
    Input(webCyclicUpdates, 'n_intervals'),
    prevent_initial_call=True
)
def update_output(user_dropdown_input, webCyclicUpdates):
    #Declaration of Topic
    wincc_Level_Tag = "wincc_thing/WebConnector_Wincc/Level_Percentage"
    wincc_Counter5_10 = "wincc_thing/WebConnector_Wincc/Counter_5_to_10"
    wincc_Counter11_20 = "wincc_thing/WebConnector_Wincc/Counter_11_to_20"

    #Subscription to aws cloud per topic
    myAWSIoTMQTTClient.subscribe(wincc_Level_Tag, 1, customCallback)
    myAWSIoTMQTTClient.subscribe(wincc_Counter5_10, 1, customCallback)
    myAWSIoTMQTTClient.subscribe(wincc_Counter11_20, 1, customCallback)

    with latest_data_lock:
        if user_dropdown_input == 'tag_lp':
            output_value = f" \nDate: {latest_data['lp_date']} \nName: {latest_data['lp_name']} \nValue: {latest_data['lp_value']}"
        elif user_dropdown_input == 'tag_c5-10':
            output_value = f" \nDate: {latest_data['c5to10_date']} \nName: {latest_data['c5to10_name']} \nValue: {latest_data['c5to10_value']}"
        elif user_dropdown_input == 'tag_c11-20':
            output_value = f" \nDate: {latest_data['c11to20_date']} \nName: {latest_data['c11to20_name']} \nValue: {latest_data['c11to20_value']}"
            #eturn dcc.Markdown(f"```{output_text3}```")
        else:
            output_value = "Select a valid tag from the dropdown"
            #return dcc.Markdown(f"```{output_text}```")

        return dcc.Markdown(f"```\n{output_value}\n")

#callback for reporting
@app.callback(Output(report_table, 'data'),
                    Input(webDropdown, 'value'),
                    Input(report_cyclic_15s, 'n_intervals'),
                    prevent_initial_call=True
            )
def update_data(user_dropdown_input, trend_cyclic_15s):

    with latest_data_lock:
        global public_data
        if user_dropdown_input == 'tag_lp':
            # Append data to dictionary if tag is selected
            if len(time_value_tag1) > 14 and len(tag_value_tag1) > 14:
                time_value_tag1.pop()
                tag_value_tag1.pop()

                time_value_tag1.insert(0, latest_data["lp_date"])
                tag_value_tag1.insert(0, latest_data["lp_value"])
            else:
                time_value_tag1.append(latest_data["lp_date"])
                tag_value_tag1.append(latest_data["lp_value"])

            public_data = {"date": time_value_tag1, "value": tag_value_tag1}

        elif user_dropdown_input == 'tag_c5-10':
            # Append data to dictionary if tag is selected
            if len(time_value_tag2) > 14 and len(tag_value_tag2) > 14:
                time_value_tag2.pop()
                tag_value_tag2.pop()

                time_value_tag2.insert(0, latest_data["c5to10_date"])
                tag_value_tag2.insert(0, latest_data["c5to10_value"])
            else:
                time_value_tag2.append(latest_data["c5to10_date"])
                tag_value_tag2.append(latest_data["c5to10_value"])

            public_data = {"date": time_value_tag2, "value": tag_value_tag2}

        elif user_dropdown_input == 'tag_c11-20':
            # Append data to dictionary if tag is selected
            if len(time_value_tag3) > 14 and len(tag_value_tag3) > 14:
                time_value_tag3.pop()
                tag_value_tag3.pop()

                time_value_tag3.insert(0, latest_data["c11to20_date"])
                tag_value_tag3.insert(0, latest_data["c11to20_value"])
            else:
                time_value_tag3.append(latest_data["c11to20_date"])
                tag_value_tag3.append(latest_data["c11to20_value"])

            public_data = {"date": time_value_tag3, "value": tag_value_tag3}

        else:
            public_data = {"date": [], "value": []}
        # Create a Plotly figure
        # Create a DataFrame from the data
        df = pd.DataFrame(public_data)

        # Convert DataFrame to a list of dictionaries for DataTable
        table_data = df.to_dict('records')

        return table_data

#callback for download csv
@app.callback(Output('download-dataframe-csv', 'data'),
                    Input('btn_csv', 'n_clicks'),
                    prevent_initial_call=True
            )
def download_data(n_clicks):
    with latest_data_lock:
        global public_data
        print("Downloading" + str(pd.DataFrame(public_data)))
        df = pd.DataFrame(public_data)
        return dcc.send_data_frame(df.to_csv, "mtech_cloud_report.csv")


if __name__ == '__main__':
    app.run_server()