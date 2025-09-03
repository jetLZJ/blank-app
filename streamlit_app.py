import pandas as pd
import sqlalchemy
import plotly.express as px
import streamlit as st
import os
import dotenv
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

dotenv.load_dotenv()

db_connection_str = os.environ.get('DB_CONNECTION_STRING')
if not db_connection_str:
    raise ValueError("No DB_CONNECTION_STRING found in environment or Streamlit secrets.")
engine = sqlalchemy.create_engine(db_connection_str)

# Get a list of all table names from the database and filter for 'long' tables.
inspector = sqlalchemy.inspect(engine)
all_tables = inspector.get_table_names()
long_tables = [table for table in all_tables if table.endswith('long')]
wide_tables = [table for table in all_tables if table.endswith('wide')]

#get first elemtn of wide_tables to make into pd.dataframe
df_wide = pd.read_sql(f"SELECT * FROM {wide_tables[0]}", engine)
df_long = pd.read_sql(f"SELECT * FROM {long_tables[0]}", engine)

#iterate through long_tables and store it into a dict df_long_dict
df_long_dict = {}
for table in long_tables:
    df_long_dict[table] = pd.read_sql(f"SELECT * FROM {table}", engine)

#iterate through wide_tables and store it into a dict df_wide_dict
df_wide_dict = {}
for table in wide_tables:
    df_wide_dict[table] = pd.read_sql(f"SELECT * FROM {table}", engine)
    
for key, value in df_long_dict.items():
    df_long_dict[key]['year'] = pd.to_datetime(df_long_dict[key]['year'], format="%Y")




df = df_long_dict['unemployment_rate_by_occupation_long']

# Ensure 'year' is datetime
df['year'] = pd.to_datetime(df['year'], errors='coerce')

# List for legend order (if you want a specific order)
occupation_order = [
    'Managers & Administrators (Including Working Proprietors)',
    'Professionals',
    'Associate Professionals & Technicians',
    'Clerical Support Workers',
    'Service & Sales Workers',
    'Craftsmen & Related Trades Workers',
    'Plant & Machine Operators & Assemblers',
    'Cleaners, Labourers & Related Workers',
    'Others'
]

# Segregate df_long by the specified periods
periods = {
    '2014-2016': (pd.Timestamp('2014-01-01'), pd.Timestamp('2016-12-31')),
    '2017-2019': (pd.Timestamp('2017-01-01'), pd.Timestamp('2019-12-31')),
    '2020-2021': (pd.Timestamp('2020-01-01'), pd.Timestamp('2021-12-31')),
    '2022-2024': (pd.Timestamp('2022-01-01'), pd.Timestamp('2024-12-31')),
}



# Assume df_long_dict['unemployment_rate_by_occupation_long'] is available
df_occ = df_long_dict['unemployment_rate_by_occupation_long'].copy()
df_occ['year'] = pd.to_datetime(df_occ['year'])

# Segregate by period
df_occ_periods = {}
for label, (start, end) in periods.items():
    df_occ_periods[label] = df_occ[(df_occ['year'] >= start) & (df_occ['year'] <= end)]

occupations = sorted(df_occ['occupation'].unique())
n_occ = len(occupations)
ncols = 4
nrows = (n_occ + ncols - 1) // ncols

fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(5*ncols, 4*nrows), sharex=True)
axes = axes.flatten()

for i, occ in enumerate(occupations):
    ax = axes[i]
    for label, df_period in df_occ_periods.items():
        sub = df_period[df_period['occupation'] == occ]
        ax.plot(sub['year'], sub['unemployed_rate'], marker='o', label=label)
    ax.set_title(occ)
    ax.set_xlabel('Year')
    ax.set_ylabel('Unemployment Rate')
    ax.grid(True, axis='y')
    ax.legend(title='Period', fontsize=8)

# Hide any unused subplots
for j in range(i+1, len(axes)):
    axes[j].set_visible(False)

plt.tight_layout()
plt.show()


st.title("Unemployment rate between different occupations")
st.write(
    "This is a test"
)
st.pyplot(fig)




df = df_long_dict['unemployed_by_qualification_sex_long']

df_male = df[df['gender'] == 'Male'].copy()
df_female = df[df['gender'] == 'Female'].copy()

def prepare_animated_df(df_group):
    df_group.set_index('year', inplace=True)
    df_interp = df_group.groupby(['gender', 'education'])['unemployed_count'] \
        .resample('ME').mean().interpolate('linear').reset_index()
    df_group_sorted = df_group.sort_values(['gender', 'year'])
    frames = []
    frame_dates = sorted(df_interp['year'].unique())
    for date in frame_dates:
        frame_data = df_interp[df_interp['year'] <= date].copy()
        frame_data['frame'] = date.strftime('%Y-%m')
        frames.append(frame_data)
    return pd.concat(frames)

df_cumulative_male = prepare_animated_df(df_male)
df_cumulative_female = prepare_animated_df(df_female)

fig = make_subplots(
    rows=1,
    cols=2,
    subplot_titles=("Male", "Female"),
    shared_yaxes=True,
    horizontal_spacing=0.08
)
fig.update_layout(width=1200, height=500)

for education in df_cumulative_male['education'].unique():
    d = df_cumulative_male[df_cumulative_male['education'] == education]
    fig.add_trace(
        go.Scatter(
        x=d[d['frame'] == d['frame'].min()]['year'],
        y=d[d['frame'] == d['frame'].min()]['unemployed_count'],
        mode='lines+markers',
        name=education,
        legendgroup=education,
        showlegend=True
        ),
        row=1, col=1
    )

for education in df_cumulative_female['education'].unique():
    d = df_cumulative_female[df_cumulative_female['education'] == education]
    fig.add_trace(
        go.Scatter(
        x=d[d['frame'] == d['frame'].min()]['year'],
        y=d[d['frame'] == d['frame'].min()]['unemployed_count'],
        mode='lines+markers',
        name=education,
        legendgroup=education,
        showlegend=True
        ),
        row=1, col=2
    )

frames = []
frame_labels = sorted(set(df_cumulative_male['frame']) | set(df_cumulative_female['frame']))
for frame in frame_labels:
    frame_data_male = df_cumulative_male[df_cumulative_male['frame'] == frame]
    frame_data_female = df_cumulative_female[df_cumulative_female['frame'] == frame]
    data = []
    for education in df_cumulative_male['education'].unique():
        d = frame_data_male[frame_data_male['education'] == education]
        data.append(go.Scatter(x=d['year'], y=d['unemployed_count'], mode='lines'))
    for education in df_cumulative_female['education'].unique():
        d = frame_data_female[frame_data_female['education'] == education]
        data.append(go.Scatter(x=d['year'], y=d['unemployed_count'], mode='lines'))
    frames.append(go.Frame(data=data, name=frame))

fig.frames = frames

fig.update_layout(
    template='plotly_dark',
    title='Unemployment Trends by Education (Male and Female)',
    font=dict(family='Courier New', size=12, color='lightgray'),
    legend_title_text='Education',
    xaxis=dict(title='Year', type='date', tickformat='%Y', dtick='M12', range=['2014-01-01', '2024-01-01']),
    xaxis2=dict(title='Year', type='date', tickformat='%Y', dtick='M12', range=['2014-01-01', '2024-01-01']),
    yaxis=dict(title='Unemployed Count', range=[3, 25]),
    margin=dict(l=40, r=40, t=60, b=40),
    updatemenus=[{
        "type": "buttons",
        "buttons": [
        {"label": "Play", "method": "animate", "args": [None, {"frame": {"duration": 50, "redraw": True}, "transition": {"duration": 50}, "fromcurrent": True, "mode": "immediate"}]},
        {"label": "Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]}
        ]
    }]
)


st.plotly_chart(fig, use_container_width=True)