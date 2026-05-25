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
        load_names: list[str] | None = None,
        load_p_mw: float | None = None,
        load_q_mvar: float | None = None,
        load_change_time_s: float = -1.0,
        dsl_signal_name: str = "",
        iac_source_name: str = "",
        # Live DSL command interface (per-step current injection)
        iac_ia_cmd_key: str = "Ia_ka",
        iac_ib_cmd_key: str = "Ib_ka",
        iac_ic_cmd_key: str = "Ic_ka",
        # Unit conversion: multiply incoming values by this factor before SetAttribute.
        # FMU outputs A, DSL model expects kA → default 1e-3.
        iac_current_scale: float = 1e-3,
        # Delay injection until simulation time reaches this value (seconds).
        # Negative value = inject from t=0. Useful to show baseline before injection starts.
        iac_injection_start_time_s: float = -1.0,
    ):
        self.daemon = daemon
        self.project_name = project_name
        self.study_case = study_case
        self.terminal_name = terminal_name
        self.line_names: list[str] = line_names
        self.dt = dt
        self.load_names: list[str] = load_names or []
        self.load_p_mw: float | None = load_p_mw
        self.load_q_mvar: float | None = load_q_mvar
        self.load_change_time_s: float = load_change_time_s
        self.dsl_signal_name: str = dsl_signal_name
        self.iac_source_name: str = iac_source_name
        # Live DSL command interface
        self.iac_ia_cmd_key: str = iac_ia_cmd_key
        self.iac_ib_cmd_key: str = iac_ib_cmd_key
        self.iac_ic_cmd_key: str = iac_ic_cmd_key
        self.iac_current_scale: float = iac_current_scale
        self.iac_injection_start_time_s: float = iac_injection_start_time_s
        self.dsl_signal = None
        self.iac_source = None
        self._load_changed: bool = False
        self._load_changed_at_step: int = -1
        self._current_load_p_mw: float | None = load_p_mw
        self._current_load_q_mvar: float | None = load_q_mvar

        self.logger = logging.getLogger("pf_pyro_validation")
        self.logger.setLevel(logging.INFO)

    @expose
    def initialize(self) -> dict[str, float]:
        """Initialize PowerFactory handles and reset state for a new validation run."""
        # Import and connect to PowerFactory
        global pf
        if pf is None:
            import powerfactory as pf_module
            pf = pf_module

        self.app = pf.GetApplicationExt()
        if not self.app:
            raise RuntimeError("Failed to connect to PowerFactory")

        # Activate project and study case
        if self.app.ActivateProject(self.project_name):
            raise RuntimeError(f"Project activation failed: {self.project_name}")
        study_cases = self.app.GetProjectFolder("study").GetContents(f"{self.study_case}.IntCase")
        if not study_cases:
            raise RuntimeError(f"Study case not found: {self.study_case}")
        study_cases[0].Activate()

        # Resolve terminal, lines, and loads.
        self.terminal = self._resolve_single_object(self.terminal_name, "ElmTerm", "Terminal")
        self.lines = []
        self.line_sides = {}
        for i, name in enumerate(self.line_names, start=1):
            line_obj = self._resolve_single_object(name, "ElmLne", f"Line {i} ({name})")
            side = self._resolve_line_current_side_for_terminal(line_obj, f"Line {i} ({name})")
            self.lines.append(line_obj)
            self.line_sides[name] = side

        self.loads = []
        for i, name in enumerate(self.load_names, start=1):
            load_obj = self._resolve_single_object(name, "ElmLod", f"Load {i} ({name})")
            self.loads.append(load_obj)

        # Resolve DSL signal source and zero IAC command params before load flow.
        if self.dsl_signal_name:
            self.dsl_signal = self._resolve_single_object(self.dsl_signal_name, "ElmDsl", "DSL signal source")
            for cmd in ("IA_cmd", "IB_cmd", "IC_cmd"):
                self.dsl_signal.SetAttribute(cmd, 0.0)

        # Resolve ElmIac current source for measurement readback.
        if self.iac_source_name:
            self.iac_source = self._resolve_single_object(self.iac_source_name, "ElmIac", "AC current source")
            self.logger.info("AC current source resolved: '%s'", self.iac_source_name)

        self.current_time = 0.0
        self.current_step = 0

        # Get simulation commands
        self.ldf = self.app.GetFromStudyCase("ComLdf")
        self.inc = self.app.GetFromStudyCase("ComInc")
        self.sim = self.app.GetFromStudyCase("ComSim")

        self.inc.SetAttribute("dtgrd", self.dt)
        self.logger.info("ComInc dtgrd set to %.6f s", self.dt)

        # 1. Set load operating points before load flow (if configured).
        for name, load_obj in zip(self.load_names, self.loads):
            if self.load_p_mw is not None:
                load_obj.SetAttribute("plini", self.load_p_mw)
                self.logger.info("Load '%s': plini=%.4f MW", name, self.load_p_mw)
            if self.load_q_mvar is not None:
                load_obj.SetAttribute("qlini", self.load_q_mvar)
                self.logger.info("Load '%s': qlini=%.4f Mvar", name, self.load_q_mvar)

        # 2. Load flow → converged operating point
        ret = self.ldf.Execute()
        if ret:
            raise RuntimeError(f"ComLdf.Execute() failed with return code {ret}")

        # 3. ComInc → initial EMT conditions
        ret = self.inc.Execute()
        if ret:
            raise RuntimeError(f"ComInc.Execute() failed with return code {ret}")

        self._load_changed = False
        self._load_changed_at_step = -1
        self._current_load_p_mw = self.load_p_mw
        self._current_load_q_mvar = self.load_q_mvar

        va, vb, vc, per_line, ia, ib, ic, p_pf, pa_pf, pb_pf, pc_pf, ia_iac, ib_iac, ic_iac = self._read_measurements()
        result = self._build_result(va, vb, vc, per_line, ia, ib, ic, p_pf, pa_pf, pb_pf, pc_pf, ia_iac, ib_iac, ic_iac, 0.0, 0.0)
        self.logger.info(
            "Initialize: Va=%.6e V, Vb=%.6e V, Vc=%.6e V; P_pf=%.6e MW",
            result["Va"], result["Vb"], result["Vc"], result["P_pf"],
        )
        return result

    @expose
    def do_step(self, input_dict: dict[str, float]) -> dict[str, float]:
        """Run one aligned incremental step and return validation signals."""
        self._check_load_step()
        self._apply_iac_current_command(input_dict)

        total_start = time.perf_counter()
        self._execute_incremental_step()
        step_pf_time_s = time.perf_counter() - total_start

        va, vb, vc, per_line, ia, ib, ic, p_pf, pa_pf, pb_pf, pc_pf, ia_iac, ib_iac, ic_iac = self._read_measurements()
        step_total_time_s = time.perf_counter() - total_start

        # Log first post-change step to verify whether EMT responded
        if self._load_changed and self.current_step == self._load_changed_at_step + 1:
            self.logger.info(
                "Post-change state at step %d: Va=%.6e V, Vb=%.6e V, Vc=%.6e V, "
                "Ia=%.6e A, P_total=%.6e MW",
                self.current_step, va, vb, vc, ia, p_pf,
            )

        self.logger.debug(
            "Step %d | pf_time=%.6e s | total_time=%.6e s",
            self.current_step,
            step_pf_time_s,
            step_total_time_s,
        )

        return self._build_result(
            va, vb, vc, per_line, ia, ib, ic, p_pf, pa_pf, pb_pf, pc_pf,
            ia_iac, ib_iac, ic_iac, step_pf_time_s, step_total_time_s,
        )

    @expose
    def clear(self):
        """Release references and transient state for cleanup."""
        self.app = None
        self.terminal = None
        self.lines = []
        self.line_sides = {}
        self.loads = []
        self.ldf = None
        self.inc = None
        self.sim = None
        self.dsl_signal = None
        self.iac_source = None
        self.current_time = 0.0
        self.current_step = 0
        self._load_changed = False
        self._load_changed_at_step = -1
        self._current_load_p_mw = self.load_p_mw
        self._current_load_q_mvar = self.load_q_mvar

    def _apply_iac_current_command(self, input_dict: dict[str, float]) -> None:
        """Forward IA_cmd/IB_cmd/IC_cmd from input_dict to the DSL model before each step.

        Values are scaled by iac_current_scale before being passed to SetAttribute.
        Default scale 1e-3 converts the incoming A values to kA as the DSL model expects.
        Injection is suppressed (0 A) until current_time >= iac_injection_start_time_s.
        """
        if self.dsl_signal is None:
            return
        # Hold at zero until the configured start time.
        inject = self.iac_injection_start_time_s < 0 or self.current_time >= self.iac_injection_start_time_s
        if not inject:
            for attr in ("IA_cmd", "IB_cmd", "IC_cmd"):
                self.dsl_signal.SetAttribute(attr, 0.0)
            return
        for key, attr in [
            (self.iac_ia_cmd_key, "IA_cmd"),
            (self.iac_ib_cmd_key, "IB_cmd"),
            (self.iac_ic_cmd_key, "IC_cmd"),
        ]:
            v = input_dict.get(key)
            if v is not None:
                self.dsl_signal.SetAttribute(attr, float(v) * self.iac_current_scale)

    def _resolve_single_object(self, name: str, class_name: str, label: str):
        objects = self.app.GetCalcRelevantObjects(f"*.{class_name}") or []
        matches = [obj for obj in objects if obj.loc_name == name]
        if not matches:
            available = sorted({str(obj.loc_name) for obj in objects if obj.loc_name is not None})
            raise RuntimeError(
                f"{label} not found: name='{name}', class='{class_name}'. Available: {available}",
            )
        if len(matches) > 1:
            self.logger.warning("Multiple %s with loc_name '%s' in %s, using first", label, name, class_name)
        return matches[0]

    def _resolve_line_current_side_for_terminal(self, line_obj, line_label: str) -> str:
        """Resolve whether bus1 or bus2 corresponds to the configured terminal for a line."""
        def matches(side: str) -> bool:
            side_obj = getattr(line_obj, side)
            if side_obj is None:
                return False
            cterm = side_obj.cterm
            return cterm is self.terminal or (cterm is not None and cterm.loc_name == self.terminal_name)

        match_bus1 = matches("bus1")
        match_bus2 = matches("bus2")
        if match_bus1 and not match_bus2:
            return "bus1"
        if match_bus2 and not match_bus1:
            return "bus2"
        raise RuntimeError(
            f"Could not uniquely resolve bus side for {line_label} at terminal '{self.terminal_name}'. "
            f"match_bus1={match_bus1}, match_bus2={match_bus2}",
        )

    def _check_load_step(self) -> None:
        """Apply timed load halving when simulation time reaches load_change_time_s."""
        if self.load_change_time_s < 0 or self._load_changed or not self.loads:
            return
        if self.current_time >= self.load_change_time_s:
            self.logger.info(
                "Timed load change at step %d (t=%.6f s >= %.6f s)",
                self.current_step, self.current_time, self.load_change_time_s,
            )
            self._apply_runtime_load_change()

    def _apply_runtime_load_change(self) -> None:
        """Halve the current load setpoints directly between ComSim.Execute() calls."""
        new_p = (self._current_load_p_mw * 0.5) if self._current_load_p_mw is not None else None
        new_q = (self._current_load_q_mvar * 0.5) if self._current_load_q_mvar is not None else None

        self.logger.info(
            "Halving load at step %d (t=%.6f s): P=%.4f→%.4f MW, Q=%.4f→%.4f Mvar",
            self.current_step, self.current_time,
            self._current_load_p_mw if self._current_load_p_mw is not None else float("nan"),
            new_p if new_p is not None else float("nan"),
            self._current_load_q_mvar if self._current_load_q_mvar is not None else float("nan"),
            new_q if new_q is not None else float("nan"),
        )
        for name, load_obj in zip(self.load_names, self.loads):
            if new_p is not None:
                load_obj.SetAttribute("plini", new_p)
            if new_q is not None:
                load_obj.SetAttribute("qlini", new_q)

        self._current_load_p_mw = new_p
        self._current_load_q_mvar = new_q
        self._load_changed = True
        self._load_changed_at_step = self.current_step

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

    def _read_measurements(
        self,
    ) -> tuple[float, float, float, dict[str, dict[str, float]], float, float, float, float, float, float, float, float, float, float]:
        """Read voltages (kV→V), per-line currents (kA→A), active power (MW), and ElmIac currents (A)."""
        va = self._read_required_attribute(self.terminal, "m:U:A") * 1e3
        vb = self._read_required_attribute(self.terminal, "m:U:B") * 1e3
        vc = self._read_required_attribute(self.terminal, "m:U:C") * 1e3

        per_line: dict[str, dict[str, float]] = {}
        ia_total_ka = 0.0
        ib_total_ka = 0.0
        ic_total_ka = 0.0
        p_pf = 0.0
        pa_pf = 0.0
        pb_pf = 0.0
        pc_pf = 0.0

        for name, line_obj in zip(self.line_names, self.lines):
            side = self.line_sides[name]
            ia_ka = self._read_required_attribute(line_obj, f"m:I:{side}:A")
            ib_ka = self._read_required_attribute(line_obj, f"m:I:{side}:B")
            ic_ka = self._read_required_attribute(line_obj, f"m:I:{side}:C")
            p_mw = self._read_required_attribute(line_obj, f"m:Psum:{side}")
            pa_mw = self._read_required_attribute(line_obj, f"m:P:{side}:A")
            pb_mw = self._read_required_attribute(line_obj, f"m:P:{side}:B")
            pc_mw = self._read_required_attribute(line_obj, f"m:P:{side}:C")
            per_line[name] = {
                "ia_ka": ia_ka, "ib_ka": ib_ka, "ic_ka": ic_ka,
                "p_mw": p_mw, "pa_mw": pa_mw, "pb_mw": pb_mw, "pc_mw": pc_mw,
            }
            ia_total_ka += ia_ka
            ib_total_ka += ib_ka
            ic_total_ka += ic_ka
            p_pf += p_mw
            pa_pf += pa_mw
            pb_pf += pb_mw
            pc_pf += pc_mw

        ia = ia_total_ka * 1e3
        ib = ib_total_ka * 1e3
        ic = ic_total_ka * 1e3

        ia_iac = 0.0
        ib_iac = 0.0
        ic_iac = 0.0
        if self.iac_source is not None:
            ia_iac = self._read_required_attribute(self.iac_source, "m:I:bus1:A") * 1e3
            ib_iac = self._read_required_attribute(self.iac_source, "m:I:bus1:B") * 1e3
            ic_iac = self._read_required_attribute(self.iac_source, "m:I:bus1:C") * 1e3

        return va, vb, vc, per_line, ia, ib, ic, p_pf, pa_pf, pb_pf, pc_pf, ia_iac, ib_iac, ic_iac

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
        pa_pf: float,
        pb_pf: float,
        pc_pf: float,
        ia_iac: float,
        ib_iac: float,
        ic_iac: float,
        step_pf_time_s: float,
        step_total_time_s: float,
    ) -> dict[str, float]:
        result: dict[str, float] = {
            "Va": va,
            "Vb": vb,
            "Vc": vc,
            "Ia_meas": ia,
            "Ib_meas": ib,
            "Ic_meas": ic,
            "Ia_iac": ia_iac,
            "Ib_iac": ib_iac,
            "Ic_iac": ic_iac,
            "P_pf": p_pf,
            "Pa_pf": pa_pf,
            "Pb_pf": pb_pf,
            "Pc_pf": pc_pf,
            "step_pf_time_s": float(step_pf_time_s),
            "step_total_time_s": float(step_total_time_s),
            "time": float(self.current_time),
            "step": int(self.current_step),
            "load_p_mw_setpoint": float(self._current_load_p_mw) if self._current_load_p_mw is not None else float("nan"),
            "load_q_mvar_setpoint": float(self._current_load_q_mvar) if self._current_load_q_mvar is not None else float("nan"),
        }
        _sanitize = str.maketrans(" /-.:", "_____")
        for name, data in per_line.items():
            key = name.translate(_sanitize)
            result[f"Ia_{key}_kA"] = data["ia_ka"]
            result[f"Ib_{key}_kA"] = data["ib_ka"]
            result[f"Ic_{key}_kA"] = data["ic_ka"]
            result[f"P_{key}_MW"] = data["p_mw"]
            result[f"Pa_{key}_MW"] = data["pa_mw"]
            result[f"Pb_{key}_MW"] = data["pb_mw"]
            result[f"Pc_{key}_MW"] = data["pc_mw"]
        return result

    def _read_required_attribute(self, obj, name: str) -> float:
        value = obj.GetAttribute(name)
        if value is None:
            raise RuntimeError(f"Attribute {name} returned None")
        return float(value)


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

    raw_load_names = config.get('powerfactory', 'load_names')
    load_names = [n.strip() for n in raw_load_names.split(',') if n.strip()]

    load_p_mw_str = config.get('powerfactory', 'load_p_mw')
    load_p_mw = float(load_p_mw_str) if load_p_mw_str.strip() else None

    load_q_mvar_str = config.get('powerfactory', 'load_q_mvar')
    load_q_mvar = float(load_q_mvar_str) if load_q_mvar_str.strip() else None

    load_change_time_s = config.getfloat('powerfactory', 'load_change_time_s', fallback=-1.0)

    dsl_signal_name = config.get('powerfactory', 'dsl_signal_name', fallback='')
    iac_ia_cmd_key = config.get('powerfactory', 'iac_ia_cmd_key', fallback='Ia_ka')
    iac_ib_cmd_key = config.get('powerfactory', 'iac_ib_cmd_key', fallback='Ib_ka')
    iac_ic_cmd_key = config.get('powerfactory', 'iac_ic_cmd_key', fallback='Ic_ka')
    iac_source_name = config.get('powerfactory', 'iac_source_name', fallback='')
    iac_current_scale = config.getfloat('powerfactory', 'iac_current_scale', fallback=1e-3)
    iac_injection_start_time_s = config.getfloat('powerfactory', 'iac_injection_start_time_s', fallback=-1.0)

    return {
        'project_name': config.get('powerfactory', 'project_name'),
        'study_case': config.get('powerfactory', 'study_case'),
        'terminal_name': config.get('powerfactory', 'terminal_name'),
        'line_names': line_names,
        'load_names': load_names,
        'load_p_mw': load_p_mw,
        'load_q_mvar': load_q_mvar,
        'load_change_time_s': load_change_time_s,
        'dsl_signal_name': dsl_signal_name,
        'iac_source_name': iac_source_name,
        'iac_ia_cmd_key': iac_ia_cmd_key,
        'iac_ib_cmd_key': iac_ib_cmd_key,
        'iac_ic_cmd_key': iac_ic_cmd_key,
        'iac_current_scale': iac_current_scale,
        'iac_injection_start_time_s': iac_injection_start_time_s,
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

    _log_fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    _log_file = Path(__file__).parent / "pyro_connector.log"
    _fh = logging.FileHandler(_log_file, encoding="utf-8")
    _fh.setFormatter(_log_fmt)
    _sh = logging.StreamHandler(sys.stdout)
    _sh.setFormatter(_log_fmt)
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(_fh)
    logging.root.addHandler(_sh)
    logger = logging.getLogger("pf_pyro_main")
    logger.info("Log file: %s", _log_file)

    logger.info("PowerFactory Pyro5 Server - EMT Mode")
    logger.info("Config: %s", config_path)
    logger.info("Listening on %s:%s", config['pyro_host'], config['pyro_port'])
    logger.info("Timestep: %.1f µs", config['timestep'] * 1e6)
    logger.info("Project: %s", config['project_name'])
    logger.info("Study case: %s", config['study_case'])
    logger.info("Terminal: %s", config['terminal_name'])
    for i, name in enumerate(config['line_names'], start=1):
        logger.info("Line %d: %s", i, name)
    if config['load_names']:
        for i, name in enumerate(config['load_names'], start=1):
            logger.info("Load %d: %s", i, name)
        if config['load_p_mw'] is not None:
            logger.info("  Initial P: %s MW", config['load_p_mw'])
        if config['load_q_mvar'] is not None:
            logger.info("  Initial Q: %s Mvar", config['load_q_mvar'])
        if config['load_change_time_s'] >= 0:
            logger.info("  Timed load halving at t=%.4f s", config['load_change_time_s'])
    if config['dsl_signal_name']:
        logger.info("DSL signal source: '%s'", config['dsl_signal_name'])
        logger.info(
            "  Command keys: %s, %s, %s",
            config['iac_ia_cmd_key'], config['iac_ib_cmd_key'], config['iac_ic_cmd_key'],
        )
    if config['iac_source_name']:
        logger.info("AC current source (ElmIac): '%s'", config['iac_source_name'])

    Pyro5.config.SERVERTYPE = "multiplex"
    pyro_simulator = Sub_server(
        None,
        project_name=config['project_name'],
        study_case=config['study_case'],
        terminal_name=config['terminal_name'],
        line_names=config['line_names'],
        dt=config['timestep'],
        load_names=config['load_names'],
        load_p_mw=config['load_p_mw'],
        load_q_mvar=config['load_q_mvar'],
        load_change_time_s=config['load_change_time_s'],
        dsl_signal_name=config['dsl_signal_name'],
        iac_source_name=config['iac_source_name'],
        iac_ia_cmd_key=config['iac_ia_cmd_key'],
        iac_ib_cmd_key=config['iac_ib_cmd_key'],
        iac_ic_cmd_key=config['iac_ic_cmd_key'],
        iac_current_scale=config['iac_current_scale'],
        iac_injection_start_time_s=config['iac_injection_start_time_s'],
    )
    daemon = Pyro5.server.Daemon(host=config['pyro_host'], port=config['pyro_port'])
    daemon.register(pyro_simulator, config['pyro_object_name'])

    try:
        daemon.requestLoop()
    finally:
        daemon.close()
