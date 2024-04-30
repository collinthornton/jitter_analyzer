#! /usr/bin/env python3

import os

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def load_data(data_dir: str) -> tuple[list[pd.DataFrame], list[str]]:
    """
    Load all CSV dumps in a directory to a list of dataframes
    :param data_dir: fully resolved directory containing the UDP dumps in .csv format
    :return: tuple(list of pandas dataframes representing the UDP dumps, list of names)
    """
    names = [name for name in os.listdir(data_dir) if '.csv' in name]
    filepaths = [os.path.join(data_dir, name) for name in os.listdir(data_dir) if '.csv' in name]
    frames = [pd.read_csv(filepath) for filepath in filepaths]

    return frames, [name.split('.')[0] for name in names]


def filter_data(dataframes: list[pd.DataFrame]) -> tuple[tuple[pd.DataFrame]]:
    """
    Filter a CSV dataset to separate status frames and command frames
    :param dataframes: list of dataframes with the UDP dump
    :return: tuple(tuple(status_frames, command_frames))
    """
    frames = [[]]*len(dataframes)

    for i in range(len(dataframes)):
        frame = dataframes[i]

        to_arm = frame[(frame["Destination"] == '192.168.38.1') & (frame["Source"] == '192.168.38.11')]
        from_arm = frame[(frame["Destination"] == '192.168.38.11') & (frame["Source"] == '192.168.38.1')]

        frames[i] = (from_arm, to_arm)

    return tuple(frames)


def set_axis_props(axis: plt.Axes, title: str, xlabel: str, ylabel: str, ylim: list[float]) -> None:
    """
    Set common properties of a plt.Axes (ie a plot)
    :param axis: Axis to be updated
    :param title: Title of axis
    :param xlabel: Label of the x-axis
    :param ylabel: Label of the y-axis
    :param ylim: Limits of the y-axis
    :return: None
    """
    axis.set_title(title)
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.set_xlim([0, 20])
    axis.set_ylim(ylim)
    axis.grid(True)


def make_plot(status_frame: pd.DataFrame, command_frame: pd.DataFrame, title: str,
              save=True, show=False, figures_dir=None) -> None:
    """
    Generate a plot given status frames and command frames of a trajectory
    :param status_frame: Filtered UDP status frames
    :param command_frame: Filtered UDP command frames
    :param title: Title of main figure
    :param save: Whether to save the figure to a file
    :param show: Whether to show the figure
    :param figures_dir: Where to save the figure
    :return: None
    """
    if save and figures_dir is None:
        raise ValueError("figures_dir must be specified if save == True")

    # Top 2 plots are the frames. Bottom big plot is difference between frames
    fig, axs = plt.subplots(2, 2, constrained_layout=True)

    # Make the bottom big plot
    gs = axs[1, 1].get_gridspec()

    # Remove the underlying axes
    for ax in axs[1, 0:]:
        ax.remove()

    # Create reference to the combined axes
    axbig = fig.add_subplot(gs[1, 0:])

    # Adding title to the figure
    fig.suptitle(title)
    # fig.tight_layout()

    status_array = status_frame["Time"].to_numpy()
    command_array = command_frame["Time"].to_numpy()

    # Ensure the arrays are the same size
    #   command_array is usually smaller (though not always), as the ROS2 controller is typically terminated
    #   before the Kassow is power cycled

    if command_array.size > status_array.size:
        command_array = command_array[:status_array.size]
    else:
        status_array = status_array[:command_array.size]

    status_jitter = status_array - np.roll(status_array, 1)
    command_jitter = command_array - np.roll(command_array, 1)
    command_delay = command_array - status_array

    # Annotate the top left plot (status frame jitter plot)
    axs[0, 0].plot(status_array[1:], 1000.*status_jitter[1:])
    set_axis_props(axs[0, 0], "Status Frame Jitter", "Traj. Time [s]", "Jitter [ms]", [0., 8.])

    # Annotate the top right plot (command jitter plot)
    axs[0, 1].plot(command_array[1:], 1000.*command_jitter[1:])
    set_axis_props(axs[0, 1], "Command Frame Jitter", "Traj. Time [s]", "Jitter [ms]", [0., 8.])

    # Annotate the bottom plot (error plot)
    axbig.plot(command_array, 1000.*command_delay)
    set_axis_props(axbig, "Command Frame Delay", "Traj. Time [s]", "Delay [ms]", [0., 0.6])

    if save:
        figure_path = os.path.join(os.getcwd(), 'figures')

        if not os.path.exists(figure_path):
            os.makedirs(figure_path)

        plt.savefig(os.path.join(figure_path, title + '.png'))

    if show:
        plt.show()


def main(data_dir: str, figures_dir: str, save: bool, show: bool) -> None:
    # Get all csv files from data/
    dataframes, names = load_data(data_dir)

    if len(dataframes) == 0:
        raise RuntimeError(f"No .csv files were found in {data_dir}")

    filtered_frames = filter_data(dataframes)

    for i in range(len(dataframes)):
        make_plot(filtered_frames[i][0], filtered_frames[i][1], names[i], figures_dir=figures_dir, save=save, show=show)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, help="location of data files. Default './data'")
    parser.add_argument('--figure-dir', type=str, help="location to store generated figures. Default './figures")
    parser.add_argument("--hide", action='store_true', help="Don't show the figures")
    parser.add_argument('--save', action='store_true', help="Save the figures")
    args = parser.parse_args()

    if args.data_dir is None:
        args.data_dir = os.path.join(os.getcwd(), "data")

    if args.figure_dir is None:
        args.figure_dir = os.path.join(os.getcwd(), "figures")
        
    if args.hide and not args.save:
        raise ValueError("You don't want to show the plots and you don't want to save them, so why make them?")

    main(args.data_dir, args.figure_dir, args.save, not args.hide)
