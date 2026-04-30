"""
PowerFactory Pyro5 Server with EMT Incremental Stepping
Exposes PowerFactory API as a remote Pyro5 object for EMT co-simulation.

This represents the Pyro5 server side of the connection, while the client side is implemented in the ecosimpy repository.
"""
import sys
import os
import argparse
import logging
import time
from configparser import ConfigParser
from pathlib import Path

PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024 SP7"
PF_PYTHON_PATH = os.path.join(PF_PATH, "Python", "3.12")
sys.path.insert(0, PF_PYTHON_PATH)
os.add_dll_directory(PF_PATH)

from Pyro5.api import expose, behavior  # noqa: E402
import Pyro5.api  # noqa: E402
import Pyro5.server  # noqa: E402

pf = None


def sanitize_name(name: str) -> str:
    """Convert a PowerFactory loc_name to a valid dict key by replacing non-identifier characters."""
    result = name
    for ch in (" ", "/", "-", ".", ":"):
        result = result.replace(ch, "_")
    return result


@expose
@behavior(instance_mode="session")
class Sub_server:
    def __init__(
        self,
        daemon,
        project_name: str,
        study_case: str,
        terminal_name: str,
        line_names: list[str],
        dt: float,
    ):
        if dt <= 0.0:
            raise ValueError(f"dt must be > 0, got {dt}")
        if not line_names:
            raise ValueError("line_names must not be empty")

        self.daemon = daemon
        self.project_name = project_name
        self.study_case = study_case
        self.terminal_name = terminal_name
        # Supports an arbitrary number of lines; resolved during initialize().
        self.line_names: list[str] = line_names
        self.dt = dt

        self.app = None
        self.terminal = None
        self.lines: list = []               # PF ElmLne objects, ordered as line_names
        self.line_sides: dict[str, str] = {}  # maps loc_name -> "bus1" or "bus2"
        self.inc = None
        self.sim = None
        self.current_time = 0.0
        self.current_step = 0

        self.logger = logging.getLogger("pf_pyro_validation")
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        self._reset_runtime_state()

    def _reset_runtime_state(self) -> None:
        """Reset dynamic state so initialize() always starts from a clean baseline."""
        self.current_time = 0.0
        self.current_step = 0

    def _read_required_attribute(self, obj, name: str, label: str) -> float:
        """Read a required PowerFactory attribute and fail with context if unavailable."""
        try:
            value = obj.GetAttribute(name)
            if value is None:
                raise RuntimeError(f"Attribute {name} returned None")
            return float(value)
        except Exception as exc:
            raise RuntimeError(f"Failed to read {label} from attribute {name}: {exc}") from exc

    def _get_object_attribute_or_none(self, obj, name: str):
        """Best-effort attribute getter for PowerFactory objects."""
        try:
            return getattr(obj, name)
        except Exception:
            pass
        try:
            return obj.GetAttribute(name)
        except Exception:
            return None

    def _object_loc_name(self, obj) -> str | None:
        """Best-effort loc_name extraction for matching/logging."""
        if obj is None:
            return None
        loc_name = self._get_object_attribute_or_none(obj, "loc_name")
        if loc_name is None:
            return None
        return str(loc_name)

    def _line_side_matches_terminal(self, line_obj, side: str, terminal_obj) -> bool:
        """Return True if line side bus1/bus2 refers to the configured terminal."""
        side_obj = self._get_object_attribute_or_none(line_obj, side)
        if side_obj is None:
            return False

        candidates = [side_obj]
        side_terminal = self._get_object_attribute_or_none(side_obj, "cterm")
        if side_terminal is not None:
            candidates.append(side_terminal)

        terminal_name = self._object_loc_name(terminal_obj)
        for candidate in candidates:
            if candidate is terminal_obj:
                return True
            candidate_name = self._object_loc_name(candidate)
            if terminal_name is not None and candidate_name == terminal_name:
                return True
        return False

    def _resolve_line_current_side_for_terminal(self, line_obj, line_label: str) -> str:
        """Resolve whether bus1 or bus2 corresponds to the configured terminal for a line."""
        match_bus1 = self._line_side_matches_terminal(line_obj, "bus1", self.terminal)
        match_bus2 = self._line_side_matches_terminal(line_obj, "bus2", self.terminal)

        if match_bus1 and not match_bus2:
            return "bus1"
        if match_bus2 and not match_bus1:
            return "bus2"

        bus1_name = self._object_loc_name(self._get_object_attribute_or_none(line_obj, "bus1"))
        bus2_name = self._object_loc_name(self._get_object_attribute_or_none(line_obj, "bus2"))
        terminal_name = self._object_loc_name(self.terminal)
        raise RuntimeError(
            f"Could not uniquely resolve bus side for {line_label} and terminal '{terminal_name}'. "
            f"match_bus1={match_bus1}, match_bus2={match_bus2}, "
            f"line.bus1='{bus1_name}', line.bus2='{bus2_name}'",
        )

    def _read_line_phase_current_emt_side(self, line_obj, side: str, phase: str, label: str) -> float:
        """Read EMT line current in kA on a given side (bus1/bus2) for phase A/B/C."""
        attr = f"m:I:{side}:{phase}"
        return self._read_required_attribute(line_obj, attr, label)

    def _read_line_psum_side(self, line_obj, side: str, label: str) -> float:
        """Read EMT line active power sum in MW on a given side (bus1/bus2)."""
        attr = f"m:Psum:{side}"
        return self._read_required_attribute(line_obj, attr, label)

    def _execute_incremental_step(self) -> None:
        """Advance ComSim by one incremental EMT step."""
        tstop_value = self.current_time + self.dt
        self.sim.SetAttribute("tstop", tstop_value)
        ret = self.sim.Execute()
        if ret:
            raise RuntimeError(f"ComSim.Execute() failed at step {self.current_step + 1} with return code {ret}")
        # Derive time from step count to avoid floating-point drift.
        self.current_step += 1
        self.current_time = self.current_step * self.dt

    def _resolve_single_object(self, name: str, class_name: str, label: str):
        """Resolve one calc-relevant object by exact loc_name within the given class."""
        objects = self.app.GetCalcRelevantObjects(f"*.{class_name}") or []

        matches = []
        available_names = []
        for obj in objects:
            try:
                loc_name = obj.loc_name
            except Exception:
                loc_name = obj.GetAttribute("loc_name")
            if loc_name is not None:
                available_names.append(str(loc_name))
            if loc_name == name:
                matches.append(obj)

        if not matches:
            available_display = sorted(set(available_names))
            raise RuntimeError(
                f"{label} not found: requested name='{name}', class='{class_name}'. "
                f"Available loc_name values: {available_display}",
            )

        if len(matches) > 1:
            self.logger.warning(
                "Multiple %s objects found with loc_name '%s' in class %s, using first match",
                label,
                name,
                class_name,
            )
        return matches[0]

    def _read_measurements(self) -> tuple[float, float, float, dict[str, dict[str, float]], float, float, float, float]:
        """Read voltages, per-line currents (kA), total currents (A), and total active power (MW).

        Supports an arbitrary number of lines configured in line_names.
        m:U:A/B/C are phase voltages in kV, converted to V for FMU compatibility.
        m:I:<side>:<phase> are in kA; per-line values kept in kA, summed totals converted to A.
        Power computation is performed exclusively by the FMU — only Psum reference values are read here.
        """
        # Phase voltages: kV -> V
        va = self._read_required_attribute(self.terminal, "m:U:A", "Va") * 1e3
        vb = self._read_required_attribute(self.terminal, "m:U:B", "Vb") * 1e3
        vc = self._read_required_attribute(self.terminal, "m:U:C", "Vc") * 1e3

        # Loop over all configured lines; accumulate per-line data and running totals.
        per_line: dict[str, dict[str, float]] = {}
        ia_total_ka = 0.0
        ib_total_ka = 0.0
        ic_total_ka = 0.0
        p_pf = 0.0

        for name, line_obj in zip(self.line_names, self.lines):
            side = self.line_sides[name]
            ia_ka = self._read_line_phase_current_emt_side(line_obj, side, "A", f"Ia_{name}")
            ib_ka = self._read_line_phase_current_emt_side(line_obj, side, "B", f"Ib_{name}")
            ic_ka = self._read_line_phase_current_emt_side(line_obj, side, "C", f"Ic_{name}")
            p_mw = self._read_line_psum_side(line_obj, side, f"P_{name}")
            per_line[name] = {"ia_ka": ia_ka, "ib_ka": ib_ka, "ic_ka": ic_ka, "p_mw": p_mw}
            ia_total_ka += ia_ka
            ib_total_ka += ib_ka
            ic_total_ka += ic_ka
            p_pf += p_mw

        # Convert summed line currents from kA to A for FMU input.
        ia = ia_total_ka * 1e3
        ib = ib_total_ka * 1e3
        ic = ic_total_ka * 1e3

        return va, vb, vc, per_line, ia, ib, ic, p_pf

    def _build_result(
        self,
        va: float,
        vb: float,
        vc: float,
        per_line: dict[str, dict[str, float]],
        ia: float,
        ib: float,
        ic: float,
        p_pf: float,
        step_pf_time_s: float,
        step_total_time_s: float,
    ) -> dict[str, float]:
        """Build step result payload.

        Voltages (V) and currents (A/kA) are raw measurements for the FMU.
        Power computation is performed exclusively by the FMU.
        P_pf and per-line P_<name>_MW are PowerFactory reference values from m:Psum (MW).

        Generalized keys are always added for every configured line:
            Ia_<sanitized_name>_kA, Ib_<sanitized_name>_kA, Ic_<sanitized_name>_kA
            P_<sanitized_name>_MW
        For backward compatibility, when exactly two lines are configured the legacy keys
            Ia_line_1, Ib_line_1, ..., P_line_1, P_line_2 are also included.
        """
        result: dict[str, float] = {
            "Va": va,
            "Vb": vb,
            "Vc": vc,
            "Va_V": va,
            "Vb_V": vb,
            "Vc_V": vc,
            "Ia": ia,
            "Ib": ib,
            "Ic": ic,
            "Ia_A": ia,
            "Ib_A": ib,
            "Ic_A": ic,
            "P_pf": p_pf,
            "step_pf_time_s": float(step_pf_time_s),
            "step_total_time_s": float(step_total_time_s),
            "time": float(self.current_time),
            "step": int(self.current_step),
        }

        # Generalized per-line keys: work for any number of lines.
        for name, data in per_line.items():
            key = sanitize_name(name)
            result[f"Ia_{key}_kA"] = data["ia_ka"]
            result[f"Ib_{key}_kA"] = data["ib_ka"]
            result[f"Ic_{key}_kA"] = data["ic_ka"]
            result[f"P_{key}_MW"] = data["p_mw"]

        # Backward-compatible legacy keys — preserved when exactly two lines are configured.
        if len(self.line_names) == 2:
            name1, name2 = self.line_names
            result["Ia_line_1"] = per_line[name1]["ia_ka"]
            result["Ib_line_1"] = per_line[name1]["ib_ka"]
            result["Ic_line_1"] = per_line[name1]["ic_ka"]
            result["Ia_line_2"] = per_line[name2]["ia_ka"]
            result["Ib_line_2"] = per_line[name2]["ib_ka"]
            result["Ic_line_2"] = per_line[name2]["ic_ka"]
            result["P_line_1"] = per_line[name1]["p_mw"]
            result["P_line_2"] = per_line[name2]["p_mw"]

        return result

    @expose
    def initialize(self) -> dict[str, float]:
        """Initialize PowerFactory handles and reset state for a new validation run."""
        # Import and connect to PowerFactory
        global pf
        if pf is None:
            import powerfactory as pf_module
            pf = pf_module

        self.app = pf.GetApplicationExt() or pf.GetApplication()
        if not self.app:
            raise RuntimeError("Failed to connect to PowerFactory")

        # Activate project and study case
        if self.app.ActivateProject(self.project_name):
            raise RuntimeError(f"Project activation failed: {self.project_name}")
        study_cases = self.app.GetProjectFolder("study").GetContents(f"{self.study_case}.IntCase")
        if not study_cases:
            raise RuntimeError(f"Study case not found: {self.study_case}")
        study_cases[0].Activate()

        # Get terminal and all configured line objects.
        self.terminal = self._resolve_single_object(self.terminal_name, "ElmTerm", "Terminal")
        self.lines = []
        self.line_sides = {}
        for i, name in enumerate(self.line_names, start=1):
            line_obj = self._resolve_single_object(name, "ElmLne", f"Line {i} ({name})")
            side = self._resolve_line_current_side_for_terminal(line_obj, f"Line {i} ({name})")
            self.lines.append(line_obj)
            self.line_sides[name] = side

        # EMT line currents and powers are read from the resolved terminal side (bus1 or bus2) of each line.

        self._reset_runtime_state()

        # Get simulation commands (ComInc for initial conditions, ComSim for time-domain)
        self.inc = self.app.GetFromStudyCase("ComInc")
        self.sim = self.app.GetFromStudyCase("ComSim")
        if not self.inc or not self.sim:
            raise RuntimeError("ComInc or ComSim command not found")

        # Compute initial steady-state conditions
        ret = self.inc.Execute()
        if ret:
            raise RuntimeError(f"ComInc.Execute() failed with return code {ret}")

        va, vb, vc, per_line, ia, ib, ic, p_pf = self._read_measurements()
        result = self._build_result(va, vb, vc, per_line, ia, ib, ic, p_pf, 0.0, 0.0)
        self.logger.info(
            "Initialize: Va=%.6e V, Vb=%.6e V, Vc=%.6e V; P_pf=%.6e MW",
            result["Va"], result["Vb"], result["Vc"], result["P_pf"],
        )
        self.logger.info(
            "Voltage attributes: m:U:A/B/C (kV → V); Current attributes: m:I:<side>:A/B/C (kA → A)",
        )
        for name in self.line_names:
            self.logger.info(
                "Line '%s': side=%s", name, self.line_sides[name],
            )
        return result

    @expose
    def do_step(self, _input_dict: dict[str, float]) -> dict[str, float]:
        """Run one aligned incremental step and return validation signals."""
        total_start = time.perf_counter()
        pf_start = time.perf_counter()
        self._execute_incremental_step()
        step_pf_time_s = time.perf_counter() - pf_start
        va, vb, vc, per_line, ia, ib, ic, p_pf = self._read_measurements()
        step_total_time_s = time.perf_counter() - total_start

        self.logger.debug(
            "Step %d | pf_time=%.6e s | total_time=%.6e s",
            self.current_step,
            step_pf_time_s,
            step_total_time_s,
        )

        return self._build_result(va, vb, vc, per_line, ia, ib, ic, p_pf, step_pf_time_s, step_total_time_s)

    @expose
    def clear(self):
        """Release references and transient state for cleanup."""
        self.app = None
        self.terminal = None
        self.lines = []
        self.line_sides = {}
        self.inc = None
        self.sim = None
        self._reset_runtime_state()


def load_config(config_file: Path) -> dict:
    """Load configuration from INI file."""
    config = ConfigParser()
    config.read(config_file)

    timestep = config.getfloat('powerfactory', 'timestep')
    if timestep <= 0.0:
        raise ValueError(f"powerfactory.timestep must be > 0, got {timestep}")

    # line_names is a comma-separated list, e.g.: Line 5-10/1, Line 5-10/2
    raw_line_names = config.get('powerfactory', 'line_names')
    line_names = [name.strip() for name in raw_line_names.split(',') if name.strip()]
    if not line_names:
        raise ValueError("powerfactory.line_names must contain at least one line name")

    return {
        'project_name': config.get('powerfactory', 'project_name'),
        'study_case': config.get('powerfactory', 'study_case'),
        'terminal_name': config.get('powerfactory', 'terminal_name'),
        'line_names': line_names,
        'timestep': timestep,
        'pyro_host': config.get('pyro', 'host'),
        'pyro_port': config.getint('pyro', 'port'),
        'pyro_object_name': config.get('pyro', 'object_name'),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PowerFactory Pyro5 Server')
    parser.add_argument('--config-file', type=str, help='Path to configuration file (default: pyro_config.ini in script directory)')
    args = parser.parse_args()

    # Determine config file path
    if args.config_file:
        config_path = Path(args.config_file)
    else:
        config_path = Path(__file__).parent / "pyro_config.ini"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load configuration
    config = load_config(config_path)

    print("PowerFactory Pyro5 Server - EMT Mode")
    print(f"Config: {config_path}")
    print(f"Listening on {config['pyro_host']}:{config['pyro_port']}")
    print(f"Timestep: {config['timestep']*1e6:.1f} µs")
    print(f"Project: {config['project_name']}")
    print(f"Study case: {config['study_case']}")
    print(f"Terminal: {config['terminal_name']}")
    for i, name in enumerate(config['line_names'], start=1):
        print(f"Line {i}: {name}")
    print()

    Pyro5.config.SERVERTYPE = "multiplex"
    pyro_simulator = Sub_server(
        None,
        project_name=config['project_name'],
        study_case=config['study_case'],
        terminal_name=config['terminal_name'],
        line_names=config['line_names'],
        dt=config['timestep'],
    )
    daemon = Pyro5.server.Daemon(host=config['pyro_host'], port=config['pyro_port'])
    daemon.register(pyro_simulator, config['pyro_object_name'])

    try:
        daemon.requestLoop()
    finally:
        daemon.close()
