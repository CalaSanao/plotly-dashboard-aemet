from aemet import Aemet, Estacion
from dash import Dash, dcc, html, callback
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import dash
from flask import Flask


server = Flask(__name__)
app = dash.Dash(server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'Dashboard'

API_KEY = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJtaXF1ZWxmczE5ODFAZ21haWwuY29tIiwianRpIjoiNDg0ZTFhYzItZjc5MC00M2Q2LTk0ZmItYTdhODQ4ZjlhZjNiIiwiaXNzIjoiQUVNRVQiLCJpYXQiOjE3MDI2NTg5NDMsInVzZXJJZCI6IjQ4NGUxYWMyLWY3OTAtNDNkNi05NGZiLWE3YTg0OGY5YWYzYiIsInJvbGUiOiIifQ.IMTU23MQGm9_26bAAU0iXa5JifXkH1qsKaK2ciHhDU0'
aemet = Aemet(api_key=API_KEY)

LOCATION = 'ILLES BALEARS'

paleta_personalizada = [
  'rgb(255, 180, 180)', 'rgb(255, 200, 180)', 'rgb(255, 220, 180)',
  'rgb(255, 240, 180)', 'rgb(240, 255, 180)', 'rgb(220, 255, 180)',
  'rgb(180, 255, 180)', 'rgb(180, 255, 200)', 'rgb(180, 255, 220)',
  'rgb(180, 255, 240)', 'rgb(180, 255, 255)', 'rgb(180, 240, 255)',
  'rgb(180, 220, 255)', 'rgb(180, 180, 255)', 'rgb(200, 180, 255)',
  'rgb(220, 180, 255)', 'rgb(240, 180, 255)', 'rgb(255, 180, 255)',
  'rgb(255, 180, 240)', 'rgb(255, 180, 220)', 'rgb(255, 180, 200)',
  'rgb(255, 200, 200)', 'rgb(255, 220, 200)'
]

def degs_decimal_to_sexagesimal(degrees):
  float_data = float(degrees)
  degrees = int(float_data)
  float_data -= degrees
  float_data *= 60
  minutes = int(float_data)
  float_data -= minutes
  float_data *= 60
  seconds = float_data
  return f'{degrees:02d}º {minutes:02d}\' {seconds:05.2f}"'
  
def get_stations(province):
  stations = []
  for station in Estacion.get_estaciones(API_KEY):
    if station['provincia'] == province:
      stations.append(station)
  return stations

stations = pd.DataFrame(get_stations(LOCATION))
stations_list = stations.nombre.to_list()
actual_station = None
rain_graph = dcc.Graph(id='rain_graph')

def get_station_id_by_name(name):
  return stations['indicativo'] == name

# Callbacks -------------------------
# Obtenir informació de s'estació quan es canvia al dropdown
@callback(
  Output('idema', 'children'),
  Output('latitude', 'children'),
  Output('longitude', 'children'),
  Output('height', 'children'),
  Input('provincies_dropdown', 'value'))
def get_station_data(station_name):
  # Control de variable global
  global actual_station
  if actual_station != station_name:
    actual_station = station_name
  
  # Obtenir dades de s'estació
  station = stations.loc[stations['nombre'] == station_name].iloc[0]
  aemet_data = aemet.get_observacion_convencional(station.indicativo)
  df_data = pd.DataFrame([aemet_data[0].__dict__])

  # Etiquetes
  station_id = df_data.iloc[0].idema
  station_latitude = degs_decimal_to_sexagesimal(df_data.iloc[0].lat)
  station_longitude = degs_decimal_to_sexagesimal(df_data.iloc[0].lon)
  station_height = df_data.iloc[0].alt
  
  return station_id, station_latitude, station_longitude, station_height

# Actualitza sa imatge de radar a intervals regulars
@callback(
  Output('radar', 'src'),
  Input('update-radar', 'n_intervals')
)
def update_radar( _ ):
  file_path = 'assets/radar.jpg'
  aemet.descargar_mapa_radar_regional(archivo_salida=file_path, region='pm')
  return file_path

# Actualitza informació des Dashboard
@callback(
  Output('temp_max', 'children'),
  Output('temp_min', 'children'),
  Output('hr_max', 'children'),
  Output('hr_min', 'children'),
  Output('wind_max', 'children'),
  Output('temp_graph', 'figure'),
  Output('wind_graph', 'figure'),
  Output('rain_graph', 'figure'),
  [
    Input('update-dashboard', 'n_intervals'),
    Input('provincies_dropdown', 'value')
  ]
)
def update_dashboard(_, station_name):
  global actual_station
  if(station_name):
    if actual_station != station_name:
      actual_station = station_name
  
  # Obtenir dades de s'estació
  station = stations.loc[stations['nombre'] == actual_station].iloc[0]
  aemet_data = aemet.get_observacion_convencional(station.indicativo)
  df_data = pd.DataFrame()
  for row_data in aemet_data:
    df_data = pd.concat([df_data, pd.DataFrame([row_data.__dict__])])
  df_observations = df_data[['fint', 'prec', 'vmax', 'vv', 'dmax', 'dv', 'hr', 'tamin', 'tamax', 'ta']]
  df_observations.set_index(['fint'], inplace=True)
  df_observations.index = pd.to_datetime(df_observations.index, format='%Y-%m-%dT%H:%M:%S')
  
  # Grafiques ----------------------------

  initial_xaxis_range = df_observations.index

  #   Temperatura i humitat
  temp_hr_graph = make_subplots(specs=[[{"secondary_y": True}]], shared_xaxes=True)
  temp_hr_graph.add_trace(
    go.Scatter(
      x=initial_xaxis_range,
      y=df_observations['tamax'],
      mode='lines',
      name='Temperatura màxima(ºC)',
      line=dict(color='red')
    ),
    secondary_y=False
  )
  temp_hr_graph.add_trace(
    go.Scatter(
      x=initial_xaxis_range,
      y=df_observations['ta'],
      mode='lines',
      name='Temperatura (ºC)',
      line=dict(color='yellow')
    ),
    secondary_y=False
  )
  temp_hr_graph.add_trace(
    go.Scatter(
      x=initial_xaxis_range,
      y=df_observations['tamin'],
      mode='lines',
      name='Temperatura mínima(ºC)',
      line=dict(color='blue')
    ),
    secondary_y=False
  )
  temp_hr_graph.add_trace(
    go.Scatter(
      x=initial_xaxis_range,
      y=df_observations['hr'],
      mode='lines',
      name='Humitat relativa (%)',
      line=dict(dash='dash')
    ),
    secondary_y=True
  )
  temp_hr_graph.update_layout(
    xaxis=dict(title='Dia/hora'),
    yaxis=dict(title='Temperatura (ºC)'),
    yaxis2=dict(title='Humitat relativa (%)', overlaying='y', side='right'),
    template='plotly_dark',
  )

  #   Vent
  wind_graph = px.bar_polar(df_observations, r='vv', theta='dv', color=df_observations.index.strftime('%H:%M'), template='plotly_dark', color_discrete_sequence=paleta_personalizada)
  wind_graph.update_layout(legend_title_text='Hora')
  
  #   Pluja
  rain_graph = px.bar(df_observations, y='prec', template='plotly_dark')
  rain_graph.update_layout(xaxis_title='Dia/hora', yaxis_title='Quantitat (l/m2)')
  rain_graph.update_yaxes(range=[0, None])
  
  # Etiquetes
  temp_max = df_observations['tamax'].max()
  temp_min = df_observations['tamin'].min()
  hr_max = df_observations['hr'].max()
  hr_min = df_observations['hr'].min()
  wind_max = df_observations['vv'].max()

  temp_hr_graph.update_layout(
    height=400,
  )

  wind_graph.update_layout(
    height=350,
  )

  rain_graph.update_layout(
    height=350,
  )
  
  return temp_max, temp_min, hr_max, hr_min, wind_max, temp_hr_graph, wind_graph, rain_graph

# On zoom event trigger zoom in others graphs
# @callback(
#         [Output('rain_graph', 'figure')],
#          [Input('temp_graph', 'relayoutData')], # this triggers the event
#          [State('rain_graph', 'figure')])
# def zoom_event(relayout_data, *figures):
#     outputs = []
#     for fig in figures:
#         try:
#             fig['layout']["xaxis"]["range"] = [relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']]
#             fig['layout']["xaxis"]["autorange"] = False
#         except (KeyError, TypeError):
#             fig['layout']["xaxis"]["autorange"] = True

#         outputs.append(fig)

#     return outputs

# Vista
app.config.suppress_callback_exceptions = True
app.layout = html.Div([
  dcc.Dropdown(stations_list, str(stations_list[0]), id='provincies_dropdown', style={'align-text':'center'}),
  html.Div([
    dbc.Row([
      dbc.Col(html.P(['idema: ', html.Span(id='idema')], style={'text-align':'center'})),
      dbc.Col(html.P(['Latitut: ', html.Span(id='latitude')], style={'text-align':'center'})),
      dbc.Col(html.P(['Longitut: ', html.Span(id='longitude')], style={'text-align':'center'})),
      dbc.Col(html.P(['Altura: ', html.Span(id='height'), 'm'], style={'text-align':'center'}))
    ]),
    dbc.Row([
      dbc.Col(
        html.Div([
          html.H4('Temperatura/Humitat relativa'),
          dcc.Graph(id='temp_graph'),
        ]),
        width = 9
      ),
      dbc.Col(
        html.Div([
          html.H4('Radar'),
          html.Div([html.Img(id='radar', alt='Mapa de predicció', style={'height': '400px'})],
                    className="d-flex align-items-center justify-content-center",
                    style={'border':'1px solid gray'}
          )
        ]),
        width=3
      )
    ]),
    dbc.Row([
      dbc.Col(
        html.Div([
          html.H4('Pluja'),
          rain_graph,
        ]),
        width=8
      ),
      dbc.Col(
        html.Div([
          html.H4('Vent'),
          dcc.Graph(id='wind_graph'),
        ]),
        width=4
      ),
    ]),
    dbc.Row([
      dbc.Col(html.P(['Temp. max: ', html.Span(id='temp_max'), 'ºC']), style={'text-align':'center'}),
      dbc.Col(html.P(['Temp. min: ', html.Span(id='temp_min'), 'ºC']), style={'text-align':'center'}),
      dbc.Col(html.P(['H.R. max: ', html.Span(id='hr_max'), '%']), style={'text-align':'center'}),
      dbc.Col(html.P(['H.R. min: ', html.Span(id='hr_min'), '%']), style={'text-align':'center'}),
      dbc.Col(html.P(['Vel. vent max: ', html.Span(id='wind_max'), 'm/s']), style={'text-align':'center'}),
    ])
  ]),
  # Cronòmetres
  #    1 hora
  dcc.Interval(
    id = 'update-dashboard',
    interval = 1000 * 60 * 60,
    n_intervals=0
  ),
  #   10 minuts
  dcc.Interval(
    id='update-radar',
    interval = 1000 * 60 * 10,
    n_intervals = 0
  )
], style={'color':'lightgrey', 'overflow':'hidden', 'padding':'0 10px'})
  
if __name__ == '__main__':
  app.run_server(debug=True)