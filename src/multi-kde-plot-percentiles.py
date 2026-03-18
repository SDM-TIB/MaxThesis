import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import argparse
from pathlib import Path
from matplotlib.lines import Line2D


def generate_multi_kde_plot(csv_paths, dataset_names=None, output_path=None,
                            fig_width=10, fig_height=8, alpha=0.5, fill=True,
                            show_percentiles=True, percentiles=[50, 75, 90],
                            show_grid=True, suffix=None):
    """
    Generate a multi-distribution KDE plot for PCA confidence from multiple datasets.

    Parameters:
    -----------
    csv_paths : list
        List of paths to CSV files containing the rules data
    dataset_names : list, optional
        Names for each dataset. If None, will use filenames.
    output_path : str, optional
        Path to save the output plot. If None, plot will be displayed but not saved.
    fig_width : int, optional
        Width of the figure in inches
    fig_height : int, optional
        Height of the figure in inches
    alpha : float, optional
        Transparency level for the KDE plots
    fill : bool, optional
        Whether to fill the area under the KDE curves
    show_percentiles : bool, optional
        Whether to show percentile lines on the plot
    percentiles : list, optional
        List of percentiles to show (default: [25, 50, 75])
    """
    # Validate inputs
    if not csv_paths:
        raise ValueError("No CSV paths provided")

    if dataset_names is None:
        dataset_names = [Path(path).stem for path in csv_paths]

    if len(dataset_names) != len(csv_paths):
        raise ValueError("Number of dataset names must match number of CSV paths")

    if suffix is None:
        suffix = "NoSuffix"
    else:
        suffix = f"{suffix}"

    # Process output path if provided
    if output_path:
        output_file = Path(output_path)

        # If the path is a directory or doesn't have a file extension, treat it as a directory
        if output_file.is_dir() or not output_file.suffix:
            # Create the directory if it doesn't exist
            output_file.mkdir(parents=True, exist_ok=True)
            # Set a default filename inside that directory
            output_file = output_file / f"multi_kde_distribution_{suffix}.pdf"
        else:
            # Ensure the parent directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

    # Store data and statistics
    datasets = []

    # Process each dataset
    print("Loading and processing datasets...")
    for i, (csv_path, name) in enumerate(zip(csv_paths, dataset_names)):
        try:
            # Read the CSV file
            df = pd.read_csv(csv_path)

            # Validate the PCA confidence column exists
            if 'PCA_Confidence' not in df.columns:
                print(f"Warning: File {csv_path} does not contain a 'PCA_Confidence' column. Skipping.")
                continue

            # Extract and filter PCA confidence values
            pca_values = df['PCA_Confidence'].dropna()

            if len(pca_values) == 0:
                print(f"Warning: No valid PCA confidence values in {csv_path}. Skipping.")
                continue

            # Calculate statistics including percentiles
            stats = {
                'count': len(pca_values),
                'min': pca_values.min(),
                'max': pca_values.max(),
                'mean': pca_values.mean(),
                'median': pca_values.median()
            }

            # Add requested percentiles to statistics
            for p in percentiles:
                stats[f'p{p}'] = pca_values.quantile(p / 100)

            datasets.append({
                'name': name,
                'values': pca_values,
                'stats': stats
            })

            print(
                f"  - Dataset {name}: {stats['count']} rules, range: {stats['min']:.3f}-{stats['max']:.3f}, median: {stats['median']:.3f}")

        except Exception as e:
            print(f"Error processing {csv_path}: {str(e)}")

    if not datasets:
        raise ValueError("No valid datasets could be processed")

    # Create a single figure for all datasets
    plt.figure(figsize=(fig_width, fig_height))

    # Set a nice background style
    sns.set_style("whitegrid")

    # Define a colormap with distinct colors
    # Use a colorblind-friendly palette for better accessibility
    colors = sns.color_palette("YlGn", n_colors=len(datasets))

    farben =  ["#e18ab3", "#3aa590ff", "#3a56a5ff"]

    # Setzen Sie die Farbpalette
    sns.set_palette(farben)

    # Calculate max density for each dataset by creating temporary KDE plots
    max_densities = []

    # First, we'll calculate the density curves separately to get max heights
    for i, dataset in enumerate(datasets):
        values = dataset['values']

        # Calculate KDE values without plotting
        x_grid = np.linspace(values.min() - 0.1, values.max() + 0.1, 1000)
        kde = sns.kdeplot(values, bw_adjust=1).get_lines()[0].get_data()

        # Store max density
        max_densities.append(np.max(kde[1]))

        # Clear the plot for now
        plt.clf()

    # Now create the real plot with all distributions
    plt.figure(figsize=(fig_width, fig_height))
    sns.set_style("whitegrid")

    # Create KDE plots for each dataset
    for i, dataset in enumerate(datasets):
        name = dataset['name']
        values = dataset['values']

        # Create the KDE plot
        sns.kdeplot(
            values,
            color=farben[i],
            linewidth=2.5,
            label=name,
            fill=fill,
            alpha=alpha
        )

    # Add percentile lines for each dataset if requested
    if show_percentiles:
        # Define percentile line styles
        percentile_styles = {
            50: (':', 1.5),  # dotted line
            75: ('--', 2.0),  # dashed line (median)
            90: ('-.', 1.5),  # dash-dot line
        }

        # Define a small vertical offset for text placement
        y_offset_factor = 0.05

        # Create custom legend handles for percentiles
        percentile_legend_elements = []

        # Add percentile lines
        for p in percentiles:
            # Only add to legend if the percentile is in our style definitions
            if p in percentile_styles:
                style, width = percentile_styles[p]
                # Add to legend
                percentile_legend_elements.append(
                    Line2D([0], [0], color='black', linestyle=style, linewidth=width,
                           label=f'{p}th Percentile')
                )

        # Draw percentile lines for each dataset
        for i, dataset in enumerate(datasets):
            color = farben[i]
            name = dataset['name']
            stats = dataset['stats']

            # Get the max density for this dataset
            if i < len(max_densities):
                max_density = max_densities[i]
            else:
                # Fallback if we don't have a calculated density
                max_density = 1.0

            # Calculate a vertical offset based on the max density
            y_offset = max_density * y_offset_factor

            # Draw lines for each requested percentile
            for p in percentiles:
                percentile_value = stats[f'p{p}']

                if p in percentile_styles:
                    style, width = percentile_styles[p]
                else:
                    style, width = '-', 1.0  # default style

                # Draw the vertical line for this percentile
                plt.axvline(
                    x=percentile_value,
                    color=color,
                    linestyle=style,
                    linewidth=width,
                    alpha=0.7
                )

                # Add a text label for the percentile
                # Position it slightly above where we think the KDE curve is
                plt.text(
                    x=percentile_value,
                    y=max_density + y_offset,
                    s=f"{p}%",
                    color=color,
                    fontsize=10,
                    ha='center',
                    va='bottom',
                    bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1)
                )

    # Add a legend for the datasets
    dataset_legend = plt.legend(title="System", fontsize=20, title_fontsize=20,
                                loc='upper right', framealpha=0.9)

    # Add a second legend for percentile lines if they are shown
    if show_percentiles and percentile_legend_elements:
        # Add the first legend back after creating the second one
        plt.gca().add_artist(dataset_legend)

        # Create the percentile legend
        plt.legend(
            handles=percentile_legend_elements,
            loc='upper left',
            fontsize=15,
            framealpha=0.9
        )

    # Set labels and title
    plt.xlabel('PCA Confidence', fontsize=20)
    plt.ylabel('Density', fontsize=20)
    plt.title('French Royalty: Multi-Distribution KDE Plot for PCA Confidence', fontsize=22, fontweight='bold', pad=20)

    # Increase font size for axis ticks
    plt.xticks(fontsize=16, fontweight='bold')
    plt.yticks(fontsize=16, fontweight='bold')


    # Adjust x-axis range if needed
    # Determine a good range that shows all distributions clearly
    all_values = np.concatenate([dataset['values'] for dataset in datasets])
    min_val = max(0, all_values.min() - 0.1)
    max_val = min(1, all_values.max() + 0.1)
    plt.xlim(min_val, max_val)

    # Add grid for better readability if requested
    if show_grid:
        plt.grid(True, linestyle='--', alpha=0.7)
    else:
        plt.grid(False)

    # Tight layout
    plt.tight_layout()

    # Save or display the figure
    if output_path:
        try:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Multi-distribution KDE plot saved to {output_file}")
        except Exception as e:
            print(f"Error saving plot: {str(e)}")
    else:
        plt.show()

    # Generate a more comprehensive statistics summary table with percentiles
    stats_columns = ['Count', 'Min', 'Max', 'Mean', 'Median']
    for p in percentiles:
        stats_columns.append(f'{p}th Percentile')

    # Create the stats dataframe
    stats_data = {}
    for dataset in datasets:
        name = dataset['name']
        stats = dataset['stats']

        stats_data[name] = {
            'Count': stats['count'],
            'Min': stats['min'],
            'Max': stats['max'],
            'Mean': stats['mean'],
            'Median': stats['median']
        }

        # Add percentiles
        for p in percentiles:
            stats_data[name][f'{p}th Percentile'] = stats[f'p{p}']

    stats_df = pd.DataFrame(stats_data).T

    # Print statistics summary
    print("\nSummary Statistics:")
    print("-" * 80)
    print(stats_df.round(4).to_string())

    # Save statistics if output path is provided
    if output_path:
        stats_csv_path = str(Path(output_file).parent / (Path(output_file).stem + '_stats.csv'))
        stats_df.round(4).to_csv(stats_csv_path)
        print(f"Statistics saved to {stats_csv_path}")


def main():
    """Parse command-line arguments and run the script."""
    parser = argparse.ArgumentParser(
        description='Generate a multi-distribution KDE plot for PCA confidence from multiple datasets.'
    )

    parser.add_argument(
        'csv_paths',
        nargs='+',
        help='Paths to CSV files containing the rules data'
    )

    parser.add_argument(
        '--names', '-n',
        nargs='+',
        help='Names for each dataset (should match number of CSV files)'
    )

    parser.add_argument(
        '--output', '-o',
        help='Path to save output plot'
    )

    parser.add_argument(
        '--width', '-w',
        type=int,
        default=10,
        help='Figure width in inches (default: 10)'
    )

    parser.add_argument(
        '--height', '-ht',
        type=int,
        default=8,
        help='Figure height in inches (default: 8)'
    )

    parser.add_argument(
        '--alpha', '-a',
        type=float,
        default=0.5,
        help='Transparency level for KDE fill (default: 0.5)'
    )

    parser.add_argument(
        '--no-fill',
        action='store_false',
        dest='fill',
        help='Do not fill the area under KDE curves'
    )

    parser.add_argument(
        '--no-percentiles',
        action='store_false',
        dest='show_percentiles',
        help='Do not show percentile lines on the plot'
    )

    parser.add_argument(
        '--percentiles', '-p',
        nargs='+',
        type=int,
        default=[50, 75, 90],
        help='Percentiles to show (default: 50, 75, 90)'
    )

    parser.add_argument(
        '--no-grid',
        action='store_false',
        dest='show_grid',
        help='Do not show grid lines on the plot'
    )

    parser.add_argument(
        '--suffix', '-s',
        help='suffix for plots'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.names and len(args.names) != len(args.csv_paths):
        parser.error("Number of dataset names must match number of CSV paths")

    # Generate the plot
    generate_multi_kde_plot(
        args.csv_paths,
        args.names,
        args.output,
        args.width,
        args.height,
        args.alpha,
        args.fill,
        args.show_percentiles,
        args.percentiles,
        args.show_grid,
        args.suffix
    )


if __name__ == "__main__":
    main()


#python fixed-multi-kde-plot.py FrenchRoyalty-full-enriched.csv synLC_1000.csv --names 'FrenchRoyalty' 'SynthLC-1000' --output ./VANILLA --no-grid
#python .\multi-kde-plot-percentiles.py FrenchRoyalty-full-enriched.csv synLC_1000.csv --names 'FrenchRoyalty' 'SynthLC-1000' --output ./plot_thesis/percentile --suffix 'small'
#python .\multi-kde-plot-percentiles.py .\Data\Experimental_results\FrenchRoyalty-AnyBURL_PCA.csv .\Data\Experimental_results\FrenchRoyalty-AMIE_PCA.csv  .\Data\Experimental_results\FrenchRoyalty_PCA.csv --names 'AnyBURL' 'AMIE3' 'RON-a-CON' --output ./Data/Experimental_results/plots --suffix 'small'
#python .\multi-kde-plot-percentiles.py .\Data\Rules\YAGO3-10-AnyBURL.csv .\Data\Rules\YAGO3-10-AMIE.csv  --names 'AnyBURL' 'AMIE3'  --output ./Data/Experimental_results/plots --suffix 'small'
