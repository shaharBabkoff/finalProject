import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cgshop2025_pyutils.visualization import plot_instance
from cgshop2025_pyutils.data_schemas.instance import Cgshop2025Instance
from cgshop2025_pyutils.verifier.verifier import verify
from main import BESolver
from cgshop2025_pyutils.naive_algorithm.delaunay_based import DelaunayBasedSolver


INSTANCE_DIR = Path(__file__).parent / "example_instances"
VIZ_DIR = Path("outputs") / "viz"
VIZ_DIR.mkdir(parents=True, exist_ok=True)


def load_instance(filename: str) -> Cgshop2025Instance:
    path = (INSTANCE_DIR / filename).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Instance file not found:\n  {path}\n"
            f"Make sure it is under: {INSTANCE_DIR}"
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Cgshop2025Instance(**data)


def _save_instance_baseline(instance: Cgshop2025Instance, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    plot_instance(ax, instance)
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    fig.savefig(out_path, dpi=220, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def _save_overlay(instance: Cgshop2025Instance, solver: BESolver, solution, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    plot_instance(ax, instance)

    base_x = list(instance.points_x)
    base_y = list(instance.points_y)
    steiner_x = list(getattr(solution, "steiner_points_x", []) or [])
    steiner_y = list(getattr(solution, "steiner_points_y", []) or [])
    all_x = base_x + steiner_x
    all_y = base_y + steiner_y


    triangles = list(getattr(solver, "last_triangles", []) or [])
    if triangles:
        e_set = set()
        for (a, b, c) in triangles:
            e_set.add(tuple(sorted((a, b))))
            e_set.add(tuple(sorted((b, c))))
            e_set.add(tuple(sorted((c, a))))
    else:
        e_set = {tuple(sorted(e)) for e in (solution.edges or [])}

    for (u, v) in sorted(e_set):
        ax.plot([all_x[u], all_x[v]], [all_y[u], all_y[v]], color="black", linewidth=0.9, alpha=0.95)

    if steiner_x:
        ax.scatter(steiner_x, steiner_y, marker="x", s=25, color="black")

    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    fig.savefig(out_path, dpi=220, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def run_one(filename: str) -> bool:
    instance = load_instance(filename)
    solver = BESolver(instance)
    solution = solver.solve()


    try:
        uid = instance.instance_uid
        baseline_png = VIZ_DIR / f"{uid}__baseline.png"
        overlay_png = VIZ_DIR / f"{uid}__overlay.png"
        _save_instance_baseline(instance, baseline_png)
        _save_overlay(instance, solver, solution, overlay_png)
    except Exception as viz_err:
        print(f"[viz] WARNING: failed to save visualization: {viz_err}")


    verification = verify(instance, solution)
    if verification.errors:
        print("\n Verifier found errors:")
        for e in verification.errors:
            print("   •", e)
        return False
    else:
        print("\npass verifier successfully")
        print("obtuse triangles:", verification.num_obtuse_triangles)
        return True
def run_one_naive(filename: str) -> bool:
    instance = load_instance(filename)
    solver = DelaunayBasedSolver(instance)
    solution = solver.solve()

    verification = verify(instance, solution)
    if verification.errors:
        print("\n [naive] Verifier found errors:")
        for e in verification.errors:
            print("   •", e)
        return False
    else:
        print("\n[naive] pass verifier successfully")
        print("obtuse triangles:", verification.num_obtuse_triangles)
        return True

def test_1():
    filename = "cgshop2025_examples_ortho_10_ff68423e.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2

def test_2():
    filename = "cgshop2025_examples_ortho_20_b099d1fe.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2
def test_3():
    filename = "cgshop2025_examples_ortho_40_e5365b34.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2
def test_4():
    filename = "cgshop2025_examples_ortho_60_f31194db.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2
def test_5():
    filename = "ortho_10_d2723dcc.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2
def test_6():
    filename = "ortho_20_5a9e8244.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2
def test_7():
    filename = "ortho_20_e2aff192.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2

def test_8():
    filename = "ortho_40_56a6f463.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2
def test_9():
    filename = "ortho_40_df58ce3b.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2

def test_10():
    filename = "ortho_60_5c5796a0.instance.json"
    ok1 = run_one(filename)
    ok2 = run_one_naive(filename)
    assert ok1
    assert ok2



