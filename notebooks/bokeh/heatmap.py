from datetime import datetime
import calendar
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, LabelSet


class Heatmap:
    def __init__(self, year, category, source):
        #print(f"Heatmap({year=}, {category=}, {source=})")
        self.year = year
        self.category = category
        self.source = source
        self.plot = self.create_heatmap()

    def create_heatmap(self):
        #print("Heatmap::create_heatmap()")
        p = figure(
            title=f"{self.category} Activities Heatmap for {self.year}",
            x_range=(-1, 53),
            y_range=(7, -1),
            width=int(0.8 * 800),
            height=200,
            tools="hover",
            tooltips=[
                ("Date", "@date{%F}"),
                (self.category, f"@{self.category.lower()}"),
            ],
            x_axis_location="above",
            toolbar_location=None,
        )

        color_field = f"colors_{self.category.lower()}"

        p.rect(
            x="week_of_year",
            y="day_of_week",
            width=1,
            height=1,
            source=self.source,
            line_color=None,
            fill_color=color_field,
        )

        p.grid.visible = False
        p.axis.visible = False
        p.outline_line_color = None

        # Adding month labels
        month_starts = []
        month_labels = []
        for i in range(1, 13):
            start_date = datetime(self.year, i, 1)
            week_of_year = (start_date - datetime(self.year, 1, 1)).days // 7
            month_starts.append(week_of_year)
            month_labels.append(calendar.month_abbr[i])

        label_source = ColumnDataSource(
            data={'x':month_starts, 'y':[-0.5] * len(month_starts), 'text':month_labels}
        )
        labels = LabelSet(
            x="x",
            y="y",
            text="text",
            source=label_source,
            text_align="center",
            text_font_size="10px",
        )
        p.add_layout(labels)

        return p
