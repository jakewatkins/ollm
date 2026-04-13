---
name: data-analysis
description: Analyze data using Python scripts for calculations, visualizations, and data processing.
requiredMcpServers: []
preferredTools: []
resources: []
scriptExecution: true
---

# Data Analysis Skill

This skill provides data analysis capabilities using Python scripts for:

- Statistical calculations and analysis
- Data visualization with matplotlib/seaborn
- Data processing with pandas
- Mathematical computations with numpy
- File processing and data transformation

## Script Execution

This skill uses Docker-based script execution to run Python code safely in an isolated environment.

Available Python libraries in the container:
- pandas: Data manipulation and analysis
- numpy: Numerical computing
- matplotlib: Plotting and visualization  
- seaborn: Statistical data visualization
- scipy: Scientific computing
- scikit-learn: Machine learning

## Usage

When you need to perform data analysis, calculations, or create visualizations, this skill will:

1. Generate appropriate Python code for your analysis
2. Execute the code in a secure container
3. Return the results and any outputs
4. Handle data processing and transformations

## Examples

- "Calculate the mean and standard deviation of this dataset"
- "Create a histogram of these values"  
- "Process this CSV data and find trends"
- "Generate a correlation matrix"
- "Perform statistical tests on this data"