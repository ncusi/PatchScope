from bokeh.plotting import figure
import numpy as np


class RadarPlot:
    def __init__(self, categories):
        #print(f"RadarPlot({categories=})")
        self.categories = categories
        self.values = [0] * len(categories)  # Initialize values here
        self.max_value = 1  # Prevent division by zero
        self.labels = []  # Initialize the labels list
        self.plot = self.create_radar_plot()  # Create the plot

    def create_radar_plot(self):
        #print("RadarPlot::create_radar_plot()")
        radar = figure(
            title="User Activity Distribution",
            width=400,
            height=400,
            x_range=(-1, 1),
            y_range=(-1, 1),
            tools="",
            title_location="above",
        )

        self.update_plot(radar)

        return radar

    def update_plot(self, radar=None):
        #print(f"RadarPlot::update_plot({radar=})")
        if radar is None:
            radar = self.plot  # Use existing plot if not passed

        # Normalize the values
        normalized_values = [v / self.max_value for v in self.values]

        # Clear previous radar lines and patches
        radar.renderers = []

        # Create lines connecting points
        for i in range(len(self.categories)):
            angle = np.deg2rad(360 / len(self.categories) * i)
            radar.line([0, np.cos(angle)], [0, np.sin(angle)], line_width=2)

        # Create a polygon representing user activity
        radar.patch(
            [
                np.cos(np.deg2rad(360 / len(self.categories) * i))
                * normalized_values[i]
                for i in range(len(self.categories))
            ],
            [
                np.sin(np.deg2rad(360 / len(self.categories) * i))
                * normalized_values[i]
                for i in range(len(self.categories))
            ],
            fill_alpha=0.5,
            line_color="green",
        )

        # Clear previous labels
        self.labels.clear()  # Clear the labels before updating
        for i in range(len(self.categories)):
            angle = np.deg2rad(360 / len(self.categories) * i)
            label = radar.text(
                np.cos(angle) * 1.1,
                np.sin(angle) * 1.1,
                self.categories[i],
                text_align="center",
            )
            self.labels.append(label)

    def update_values(self, new_values):
        #print(f"RadarPlot::update_values({new_values=})")
        self.values = new_values
        self.max_value = max(self.values) if self.values else 1  # Update max_value
        self.update_plot()
