# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx",
#   "pandas",
#   "numpy",
#   "requests",
#   "seaborn",
#   "matplotlib",
#   "chardet",
#   "python-dotenv",
#   "tenacity"
# ]
# ///

import sys
import os
import pandas as pd
import numpy as np
import requests
import json
import seaborn as sns
import matplotlib.pyplot as plt
import chardet
import base64
from tenacity import retry, stop_after_attempt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve API key from environment variables
api_key = os.getenv('AIPROXY_TOKEN')

def encode_image(image_path):
    """
    Encodes an image to base64 format.
    
    Args:
        image_path (str): The path to the image file to encode.

    Returns:
        str: The base64 encoded image as a string.
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None
    
@retry(stop=stop_after_attempt(3))
def vision_analysis(folder_name, image_name):
    """
    Advanced analysis of the image(chart) using GPT model and append the analysis in a README file.
    
    Args:
        folder_name (str): The folder where the analysis and images will be stored.
        image_name (str): The name of the image file to analyze.
    """
    image_path = os.path.join(folder_name, image_name)
    encoded_image = encode_image(image_path)
    
    # If encoding fails, skip the analysis
    if not encoded_image:
        return

    vision_params = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze the following image and provide key insights and analyses in the readme.md format in 300 or less words and dont include readme.md heading",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}",
                            "detail": "low"
                        },
                    },
                ],
            }
        ],
    }

    # Sending request to OpenAI API
    try:
        request = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, json=vision_params)
        response = request.json()
        content = response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error with OpenAI API request: {e}")
        return

    # Save the analysis in README.md
    image_path = os.path.join('histogram_plot.png')
    image_markdown = f"![Image Description]({(image_path)})"
    readme_path = os.path.join(folder_name, 'README.md')

    try:
        with open(readme_path, 'a') as readme:
            readme.write("\n")
            readme.write("## Analysis of histogram\n")
            readme.write(image_markdown)
            readme.write("\n\n")
            readme.write(content)
            readme.write("\n\n")
    except Exception as e:
        print(f"Error writing to README.md: {e}")

@retry(stop=stop_after_attempt(3))
def create_visualization(df, column_data, filename):
    """
    Creates various visualizations based on columns suggested by GPT.
    
    Args:
        df (DataFrame): The dataset to visualize.
        column_data (dict): Dictionary containing column names for visualizations.
        filename (str): Directory where visualizations will be saved.
    """
    try:
        scatter_column = column_data["scatter_column"]
        hist_column = column_data["hist_column"]
        line_column = column_data["line_column"]

        # Scatter plot
        x_col, y_col = scatter_column
        plt.figure(figsize=(10, 6))
        sns.scatterplot(x=df[x_col], y=df[y_col])
        plt.title(f"Scatter Plot of {x_col} vs {y_col}")
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.grid(True)

        if not os.path.exists(filename):
            os.makedirs(filename)

        # Save scatter plot
        scatter_file_path = os.path.join(filename, 'scatter_plot.png')
        plt.savefig(scatter_file_path, bbox_inches='tight')
        plt.close()

        # Histogram
        hist_file_path = os.path.join(filename, 'histogram_plot.png')
        plt.figure(figsize=(5.12, 5.12))
        sns.histplot(df[hist_column], kde=True)
        plt.title(f"Histogram of {hist_column}")
        plt.xlabel(hist_column)
        plt.ylabel("Frequency")
        plt.savefig(hist_file_path, dpi=100)
        plt.close()

        # Line plot
        line_file_path = os.path.join(filename, 'line_plot.png')
        sns.lineplot(data=df, x=line_column[0], y=line_column[1])
        plt.title(f"Line Plot of {line_column[0]} vs {line_column[1]}")
        plt.xlabel(line_column[0])
        plt.ylabel(line_column[1])
        plt.savefig(line_file_path)
        plt.close()

    except Exception as e:
        print(f"Error creating visualizations: {e}")

@retry(stop=stop_after_attempt(3))
def analysis(csv_file):
    """
    Analyzes the provided CSV file, performs advanced data analysis, creates meaningful narrative, creates visualizations, and generates a README file.
    
    Args:
        csv_file (str): Path to the CSV file to analyze.
    """
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        # Try reading with a different encoding if the default fails
        try:
            with open(csv_file, 'rb') as file:
                result = chardet.detect(file.read())
            df = pd.read_csv(csv_file, encoding=result['encoding'])
        except Exception as e:
            print(f"Error reading CSV file with detected encoding: {e}")
            return

    # Perform basic analysis on the dataset
    filename = os.path.basename(csv_file)
    columns = df.columns
    summary = df.describe(include='all')
    missing_values = df.isnull().sum()
    sample_rows = df.head()
    shape = df.shape
    correlation_m = df.corr(numeric_only=True)
    info = df.info()

    # Request analysis from OpenAI API
    try:
        params = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "Analyze the following dataset summary and provide key insights, unique characteristics etc. and analyses in the readme.md format. Give story-like narration with advanced analytics. (dont include ```markdown```) :\n\nFilename: {}\nShape: {}\nColumns: {}\nSummary: {}\nMissing Values: {}\nSample Rows: {}".format(filename, shape, columns, summary, missing_values, sample_rows)}
            ],
        }
        request = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, json=params)
        response = request.json()
        folder_name = filename.split('.')[0]

        # Create folder for storing results
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        
        # Save the analysis in README.md
        readme_path = os.path.join(folder_name, 'README.md')
        with open(readme_path, 'w') as readme:
            readme.write(response['choices'][0]['message']['content'])
    except Exception as e:
        print(f"Error with OpenAI API analysis request: {e}")
        return

    # Visualization suggestion request
    try:
        visualization_params = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "Analyze the following data suggest columns for creating visualizations:\n\nFilename: {}\nShape: {}\nColumns: {}\nSummary: {}\nMissing Values: {}\nSample Rows: {}\nCorrelation matrix: {}\nInfo: {}".format(filename, shape, columns, summary, missing_values, sample_rows, correlation_m, info)}
            ],
            "functions": [
                {
                    "name": "visualization_columns",
                    "description": "Provide the column name for creating visualizations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scatter_column": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Provide the 2 correct and important columns name from the dataset for scatter plot."
                            },
                            "hist_column": {
                                "type": "string",
                                "description": "The column name to use for the x-axis in the histplot."
                            },
                            "line_column": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Provide the 2 correct and important columns name from the dataset for line plot."
                            },
                        },
                        "required": ["scatter_column", "hist_column", "line_column"]
                    }
                }
            ],
            "function_call": {"name": "visualization_columns"}
        }

        get_columns = requests.post("https://aiproxy.sanand.workers.dev/openai/v1/chat/completions", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, json=visualization_params)
        get_columns_json = get_columns.json()
        column_data = json.loads(get_columns_json["choices"][0]['message']["function_call"]["arguments"])
        
        # Create visualizations
        create_visualization(df, column_data, folder_name)
        vision_analysis(folder_name, 'histogram_plot.png')

    except Exception as e:
        print(f"Error with visualization or OpenAI request: {e}")
        return

    print('Analysis completed successfully!')

if __name__ == "__main__":
    # Ensure the script is run with a CSV file argument
    if len(sys.argv) < 2:
        print("Usage: python autolysis.py <dataset_file>")
        sys.exit(1)

    csv_file = sys.argv[1]
    analysis(csv_file)
