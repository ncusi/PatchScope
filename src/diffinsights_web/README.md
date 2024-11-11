# DiffInsights - web interface for analyzing DiffAnnotator results

This directory includes various web dashboards
that demonstrate how one can use the **`diffanotator`** project.

All web applications in this directory use
the [HoloViz Panel][Panel] framework.


## Contributors graph

This dashboard is meant to be
enhanced version of the Contributors subpage
in the Insights tab
for the GitHub repository
(example: <https://github.com/qtile/qtile/graphs/contributors>)

Below there is a
simplified graph of dependencies between 
- functions (rounded rectangle),
- widgets (hexagons, in green), and 
- outputs ("subroutine" shape, in blue)
in `02-contributors_graph.py`:
```mermaid
flowchart TD
    classDef widgetClass fill:#9f8;
    classDef finalClass fill:#cef;

    select_file_widget{{"input JSON file"}}
    select_repo_widget{{"repository"}}
    resample_frequency_widget{{"frequency"}}
    select_period_from_widget{{"Period:"}}
    select_contribution_type_widget{{"Contributions:"}}

    class select_file_widget widgetClass
    class select_repo_widget widgetClass
    class resample_frequency_widget widgetClass
    class select_period_from_widget widgetClass
    class select_contribution_type_widget widgetClass

    find_dataset_dir("`find_dataset_dir()`")
    find_timeline_files("`find_timeline_files(dataset_dir)`")
    get_timeline_data("`get_timeline_data(json_path)`")
    find_repos("`find_repos(timeline_data)`")
    get_timeline_df("`get_timeline_df(timeline_data, repo)`")
    authors_info_df("`authors_info_df(timeline_df, column, from_date)`")
    resample_timeline("`resample_timeline(timeline_df, resample_rate, group_by)`")
    %% add_pm_count_perc("`add_pm_count_perc(resampled_df)`")
    %% filter_df_by_from_date("`filter_df_by_from_date(resampled_df, from_date, date_column)`")
    get_date_range("`get_date_range(timeline_df, from_date)`")
    get_value_range("`get_value_range(resampled_df, column)`")
    %% head_info(["`head_info(repo, resample_rate)`"])
    %% sampling_info(["`sampling_info(resample_rate, column, date_range)`"])
    %% author_info(["`author_info(authors_df, author)`"])
    plot_commits[["`plot_commits(resampled_df, column, from_date)`"]]
    authors_cards[["`authors_cards(authors_df, resample_by_author_df, top_n)`"]]

    class sampling_info finalClass
    class head_info finalClass
    class plot_commits finalClass
    class authors_cards finalClass

    resample_frequency_widget -.-> resample_timeline

    find_dataset_dir --> find_timeline_files
    get_timeline_data --> find_repos
    get_timeline_data --> get_timeline_df
    get_timeline_df --> resample_timeline
    get_timeline_df --> authors_info_df
    %% get_timeline_df --> get_date_range
    %% resample_timeline --> add_pm_count_perc
    resample_timeline --> plot_commits
    %% resample_timeline --> filter_df_by_from_date
    resample_timeline --> get_date_range
    resample_timeline --> get_value_range
    resample_timeline --> authors_cards
    %% get_date_range --> plot_commits
    get_date_range --> authors_cards
    %% get_date_range --> sampling_info
    %% get_value_range --> plot_commits
    get_value_range --> authors_cards
    %% authors_info_df --> author_info
    authors_info_df --> authors_cards

    find_timeline_files ---> select_file_widget
    find_repos ---> select_repo_widget

    select_file_widget -.-> get_timeline_data
    %% select_repo_widget -.-> head_info
    select_repo_widget -.-> get_timeline_df
    %% resample_frequency_widget -.-> head_info
    %% resample_frequency_widget -.-> sampling_info
    select_period_from_widget -.-> authors_info_df
    select_period_from_widget -.-> get_date_range
    select_period_from_widget -.-> plot_commits
    select_contribution_type_widget -.-> authors_info_df
    select_contribution_type_widget -.-> get_value_range
    %% select_contribution_type_widget -.-> sampling_info
    select_contribution_type_widget -.-> plot_commits 
    
    plot_commits ---o authors_cards

    linkStyle 23 stroke:#ff3,stroke-width:4px,color:red;
```

[Panel]: https://panel.holoviz.org/ "Panel: The Powerful Data Exploration & Web App Framework for Python"
