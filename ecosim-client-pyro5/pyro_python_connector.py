"""
PowerFactory Pyro5 Server with EMT Incremental Stepping
Exposes PowerFactory API as a remote Pyro5 object for EMT co-simulation.

This represents the Pyro5 server side of the connection, while the client side is implemented in the ecosimpy repository.
"""
import sys
import os
import argparse
from configparser import ConfigParser
from pathlib import Path

PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024 SP7"
PF_PYTHON_PATH = os.path.join(PF_PATH, "Python", "3.12")
sys.path.insert(0, PF_PYTHON_PATH)
os.add_dll_directory(PF_PATH)

from Pyro5.api import expose, behavior  # noqa: E402
import Pyro5.api  # noqa: E402
import Pyro5.server  # noqa: E402
import numpy as np  # noqa: E402

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
        current_source_name: str,
        dt: float,
        bus_name: str,
    ):
        self.daemon = daemon
        self.project_name = project_name
        self.study_case = study_case
        self.terminal_name = terminal_name
        self.current_source_name = current_source_name
        self.dt = dt
        self.bus_name = bus_name

        self.app = None
        self.project = None
        self.current_source = None
        self.terminal = None
        self.inc = None
        self.current_time = 0.0
        self.current_step = 0
        self.output_dict = {}

    @expose
    def ping(self) -> str:
        return "pong"

    @expose
    def initialize(self) -> dict[str, float]:
        global pf
        if pf is None:
            try:
                import powerfactory as pf_module
                pf = pf_module
            except Exception as e:
                raise RuntimeError(f"Failed to import PowerFactory module: {e}")

        try:
            self.app = pf.GetApplicationExt() or pf.GetApplication()
            if not self.app:
                raise RuntimeError("Failed to connect to PowerFactory")
        except Exception as e:
            raise RuntimeError(f"PowerFactory connection failed: {e}")

        err = self.app.ActivateProject(self.project_name)
        if err:
            raise RuntimeError(f"Project activation failed (error {err})")

        self.project = self.app.GetActiveProject()
        study_folder = self.app.GetProjectFolder("study")
        study_cases = study_folder.GetContents(f"{self.study_case}.IntCase")

        if not study_cases:
            raise RuntimeError(f"Study case '{self.study_case}' not found")

        study_cases[0].Activate()

        terminals = self.app.GetCalcRelevantObjects(f"{self.terminal_name}.ElmTerm")
        if not terminals:
            raise RuntimeError(f"Terminal '{self.terminal_name}' not found")

        self.terminal = terminals[0]

        sources = self.app.GetCalcRelevantObjects(f"{self.current_source_name}.ElmIsc*")
        if sources:
            self.current_source = sources[0]
        else:
            self.current_source = None

# Get ComInc command for incremental EMT simulation
        self.inc = self.app.GetFromStudyCase("ComInc")
        if not self.inc:
            raise RuntimeError("ComInc command not found in study case")

        # Set timestep - SetAttribute returns None, don't check return value
        self.inc.SetAttribute("dtemt", self.dt)

        ldf = self.app.GetFromStudyCase("ComLdf")
        if ldf:
            ldf.Execute()

        self.output_dict = self._read_outputs()
        result = {
            "Va": self.output_dict["Va"],
            "Vb": self.output_dict["Vb"],
            "Vc": self.output_dict["Vc"],
        }
        print(f"Initialize: Va={result['Va']:.1f}V, Vb={result['Vb']:.1f}V, Vc={result['Vc']:.1f}V")
        return result

    @expose
    def do_step(self, input_dict: dict[str, float]) -> dict[str, float]:
        self._apply_inputs(input_dict)
        self._step_emt()

        self.current_time += self.dt
        self.current_step += 1

        self.output_dict = self._read_outputs()
        result = {
            "Va": self.output_dict["Va"],
            "Vb": self.output_dict["Vb"],
            "Vc": self.output_dict["Vc"],
        }
        print(f"Step {self.current_step}: Va={result['Va']:.1f}V, Vb={result['Vb']:.1f}V, Vc={result['Vc']:.1f}V")
        return result

    @expose
    def clear(self):
        self.app = None
        self.project = None
        self.current_source = None
        self.terminal = None
        self.inc = None

    def _apply_inputs(self, input_dict):
        if self.current_source is None:
            return

        if "Ia" in input_dict and "Ib" in input_dict and "Ic" in input_dict:
            ia_peak = input_dict["Ia"]
            ib_peak = input_dict["Ib"]
            ic_peak = input_dict["Ic"]

            sqrt2 = np.sqrt(2)
            ia_rms = ia_peak / sqrt2
            ib_rms = ib_peak / sqrt2
            ic_rms = ic_peak / sqrt2

            i_mag = np.mean([abs(ia_rms), abs(ib_rms), abs(ic_rms)])

            try:
                self.current_source.SetAttribute("i_ph", i_mag)
            except Exception:
                try:
                    self.current_source.SetAttribute("ip_ctrl", i_mag)
                except Exception:
                    pass

    def _step_emt(self):
        # EMT incremental simulation
        self.inc.SetAttribute("tstart", self.current_time)
        self.inc.SetAttribute("iopt_save", 1)
        self.inc.SetAttribute("iopt_load", 1 if self.current_step > 0 else 0)
        self.inc.Execute()

    def _read_outputs(self):
        if self.terminal is None:
            return {}

        va = self.terminal.GetAttribute("m:u:A")
        vb = self.terminal.GetAttribute("m:u:B")
        vc = self.terminal.GetAttribute("m:u:C")

        if va is None or vb is None or vc is None:
            raise RuntimeError("Terminal voltages not available")

        v_base_kv = self.terminal.GetAttribute("uknom")
        v_base_v = v_base_kv * 1000 / np.sqrt(3)

        if abs(va) < 10:
            va *= v_base_v
            vb *= v_base_v
            vc *= v_base_v

        ia = ib = ic = freq = p = q = 0.0
        if self.current_source:
            try:
                ia = self.current_source.GetAttribute(f"m:I:{self.bus_name}:A") or 0.0
                ib = self.current_source.GetAttribute(f"m:I:{self.bus_name}:B") or 0.0
                ic = self.current_source.GetAttribute(f"m:I:{self.bus_name}:C") or 0.0
            except Exception:
                pass

        try:
            freq = self.terminal.GetAttribute("m:fe") or 60.0
            p = self.terminal.GetAttribute(f"m:P:{self.bus_name}") or 0.0
            q = self.terminal.GetAttribute(f"m:Q:{self.bus_name}") or 0.0
        except Exception:
            pass

        return {
            "Va": float(va),
            "Vb": float(vb),
            "Vc": float(vc),
            "Ia": float(ia),
            "Ib": float(ib),
            "Ic": float(ic),
            "freq": float(freq),
            "P": float(p),
            "Q": float(q),
            "time": float(self.current_time),
            "step": int(self.current_step),
        }


def load_config(config_file: Path) -> dict:
    """Load configuration from INI file."""
    config = ConfigParser()
    config.read(config_file)

    return {
        'project_name': config.get('powerfactory', 'project_name'),
        'study_case': config.get('powerfactory', 'study_case'),
        'terminal_name': config.get('powerfactory', 'terminal_name'),
        'current_source_name': config.get('powerfactory', 'current_source_name'),
        'timestep': config.getfloat('powerfactory', 'timestep'),
        'bus_name': config.get('powerfactory', 'bus_name'),
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
    print(f"Study case: {config['study_case']}\n")

    try:
        Pyro5.config.SERVERTYPE = "multiplex"
        pyro_simulator = Sub_server(
            None,
            project_name=config['project_name'],
            study_case=config['study_case'],
            terminal_name=config['terminal_name'],
            current_source_name=config['current_source_name'],
            dt=config['timestep'],
            bus_name=config['bus_name'],
        )
        daemon = Pyro5.server.Daemon(host=config['pyro_host'], port=config['pyro_port'])
        uri = daemon.register(pyro_simulator, config['pyro_object_name'])

        daemon.requestLoop()

    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print("\n!!! SERVER ERROR !!!")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
    finally:
        if 'daemon' in locals():
            daemon.close()
