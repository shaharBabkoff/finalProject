from matplotlib.axes import Axes

from ..data_schemas import Cgshop2025Instance


def plot_instance(ax: Axes, instance: Cgshop2025Instance) -> Axes:
    # Plot points
    ax.scatter(instance.points_x, instance.points_y, color="black")
    # Plot region boundary
    for i in range(len(instance.region_boundary)):
        x1, y1 = (
            instance.points_x[instance.region_boundary[i]],
            instance.points_y[instance.region_boundary[i]],
        )
        x2, y2 = (
            instance.points_x[
                instance.region_boundary[(i + 1) % len(instance.region_boundary)]
            ],
            instance.points_y[
                instance.region_boundary[(i + 1) % len(instance.region_boundary)]
            ],
        )
        ax.plot([x1, x2], [y1, y2], color="blue", linestyle="-")
    # Plot constraints
    for constraint in instance.additional_constraints:
        x1, y1 = instance.points_x[constraint[0]], instance.points_y[constraint[0]]
        x2, y2 = instance.points_x[constraint[1]], instance.points_y[constraint[1]]
        ax.plot([x1, x2], [y1, y2], color="red", linestyle="-")
    ax.set_aspect("equal")
    ax.set_title(instance.instance_uid)
    return ax
