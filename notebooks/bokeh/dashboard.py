from datetime import datetime
import json

from bokeh.models import Button
from bokeh.layouts import column, row, layout
from bokeh.io import curdoc
from bokeh.models import ColumnDataSource

import pandas as pd

from heatmap import Heatmap
from radar import RadarPlot


CATEGORIES = ["code", "documentation", "tests", "other"]
CATEGORIES_P = ["code+", "documentation+", "tests+", "other+"]


def read_data(file):
    #print(f"read_data({file=})")
    data = pd.read_json(file)
    #print(data)

    data["date"] = pd.to_datetime(data["date"])
    data["week_of_year"] = data["date"].dt.isocalendar().week
    data["year"] = data["date"].dt.isocalendar().year
    data["day_of_week"] = data["date"].dt.dayofweek

    #print(data[["date", "year", "week_of_year", "day_of_week"]])

    # Map activities to color
    color_map = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39", "#00441b"]

    #print(f"  {CATEGORIES=}")
    #print(f"  {data.columns=}")
    for activity in CATEGORIES:
        for pm in list("+-"):
            #print(f"  >> {activity=} {pm=}")
            data[f"colors_{activity}{pm}"] = data[f"{activity}{pm}"].apply(
                lambda x: color_map[x]
            )

    #print(data)
    return data


# Prepare data for a given year
def prepare_data(data, year):
    #print(f"prepare_data(data=..., {year=})")
    data = data[data['year'] == year]

    return ColumnDataSource(data)


class Dashboard:
    def __init__(self, file="activity_data.json"):
        #print(f"Dashboard({file=})")
        self.file = file
        self.activity_data = read_data(file)
        self.current_year = datetime.now().year
        self.source = prepare_data(self.activity_data, self.current_year)

        # Create heatmaps for each category
        self.heatmaps = {
            "code": Heatmap(self.current_year, "code+", self.source),
            "documentation": Heatmap(self.current_year, "documentation+", self.source),
            "tests": Heatmap(self.current_year, "tests+", self.source),
            "other": Heatmap(self.current_year, "other+", self.source),
        }

        # Create radar plot
        self.radar_plot = RadarPlot(CATEGORIES_P)

        # Create year buttons
        self.year_buttons = self.create_year_buttons()

        # Arrange layout
        self.layout = self.create_layout()

        # Add layout to the current document
        curdoc().add_root(self.layout)
        curdoc().title = "GitHub-like Activity Heatmap"

    def create_year_buttons(self):
        #print("Dashboard::create_year_buttons()")
        buttons = []
        for year in range(self.current_year - 5, self.current_year + 1):
            button = Button(label=str(year), button_type="success")
            # https://stackoverflow.com/questions/7546285/creating-lambda-inside-a-loop
            button.on_click(lambda y=year: self.update_year(y))
            buttons.append(button)
        return column(*buttons)

    def create_layout(self):
        #print("Dashboard::create_layout()")
        return layout(
            row(self.heatmaps["code"].plot, self.year_buttons),
            row(self.heatmaps["documentation"].plot),
            row(self.heatmaps["tests"].plot),
            row(self.heatmaps["other"].plot),
            row(self.radar_plot.plot),
        )

    def update_year(self, new_year):
        #print(f"Dashboard::update_year({new_year=})")
        selected_year = int(new_year)
        new_source = prepare_data(self.activity_data, selected_year)
        self.source.data.update(new_source.data)

        # Update heatmaps
        for category in CATEGORIES:
            for pm in list("+"):
                #print(f"  {category=} {pm=}")
                heatmap = self.heatmaps[f"{category}"]
                heatmap.plot.title.text = (
                    f"{category}{pm} Activities Heatmap for {selected_year}"
                )

        # Calculate the total activities for the radar plot
        # d = self.activity_data[self.activity_data['year'] == new_year]
        # total_values = d[CATEGORIES].sum().values
        # self.radar_plot.update_values(total_values)
