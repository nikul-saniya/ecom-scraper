"""
Utility functions for the scraper package.
"""

import pandas as pd


def merge_dataframes(dataframes):
    """Merge multiple dataframes into one with consistent columns"""
    if not dataframes:
        return pd.DataFrame()

    # Merge all dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)

    # Ensure all columns exist in the dataframe
    for col in ["site", "title", "price", "rating", "reviews", "link", "image_url", "page"]:
        if col not in combined_df.columns:
            combined_df[col] = "N/A"

    return combined_df