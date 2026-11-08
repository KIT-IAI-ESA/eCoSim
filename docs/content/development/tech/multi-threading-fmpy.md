# Multi-threading in fmpy

- see in the section `Example` for code to reproduce the multi-threading issue
- `fmpy` uses `lxml` as a library
  - `lxml` uses `libxml2`
    - `libxml2` states, that a lot of functions are thread-safe, but one must call `xmlInitParser` before using it
      in a multi-threaded environment
      - s. https://gitlab.gnome.org/GNOME/libxml2/-/wikis/Thread-safety
      - `lxml` seems not to expose this function
- `libvirt` (a completly different library) ran also into multi-threading issues
  - s. https://www.mail-archive.com/devel@lists.libvirt.org/msg11035.html
  - they filed a merge request for `libxml2`: https://gitlab.gnome.org/GNOME/libxml2/-/merge_requests/326
      - there seems to be a new build flag `LIBXML_SCHEMAS_ENABLED` -> it is unclear if `fmpy` is using it
  - they also stated calling `xmlSchemaInitTypes` is enough as a workaround
- `xmlSchemaInitTypes` is not exposed by `lxml`
- `fmpy` GitHub repository restricts issue creations
- *WORKAROUND*: we disabled the `validation` when reading the `modelDescription` of the FMU files
  - this will prevent calling `etree.XMLSchema(doc)` in the background (which in turn can lead to a race condition)
  - disabling the validation means, the FMU xml description will not be checked against the built-in FMU schema
    - the consequences of invalid FMU xml descriptions are not clear
    - as a workaround, we will add a functionality to validate the FMU xml description
      - that means, users need to manually check it with this functionality and can then assume, that everything
        regarding `fmpy` should work as expected
  - this is only a best-effort and best-guess solution -> the long-term consequences are unknown
- every model description is read with `ecosim_common_fmpy.tech.read_model_description`
  - it calls `xmlSchemaInitTypes` once per process before the first read, also on the HPC Dask workers
  - it reads without validation, only `--validate-fmu-file-only` validates

## Example

```python
import io
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

from lxml import etree


logger = logging.getLogger("INFO_LOGGER")

logger.info("%-20s: %s", "Python", sys.version_info)
logger.info("%-20s: %s", "lxml.etree", etree.LXML_VERSION)
logger.info("%-20s: %s", "libxml used", etree.LIBXML_VERSION)
logger.info("%-20s: %s", "libxml compiled", etree.LIBXML_COMPILED_VERSION)
logger.info("%-20s: %s", "libxslt used", etree.LIBXSLT_VERSION)
logger.info("%-20s: %s", "libxslt compiled", etree.LIBXSLT_COMPILED_VERSION)

IMPORTED = b"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="urn:imp" elementFormDefault="qualified">
  <xs:complexType name="Sub"><xs:attribute name="v" type="xs:string"/></xs:complexType>
</xs:schema>"""

MAIN = b"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:imp="urn:imp">
  <xs:import namespace="urn:imp" schemaLocation="imported.xsd"/>
  <xs:element name="root">
    <xs:complexType><xs:attribute name="x" type="xs:string"/></xs:complexType>
  </xs:element>
</xs:schema>"""


N = 4
_barrier = threading.Barrier(N)


class RacingResolver(etree.Resolver):
    # forces all N threads to sit inside resolve() simultaneously,
    # maximizing overlap of libxml2 global loader/context mutation
    def resolve(self, url, pubid, context):
        try:
            _barrier.wait(timeout=10)
        except threading.BrokenBarrierError:
            pass
        if url.endswith("imported.xsd"):
            return self.resolve_string(IMPORTED, context)
        return None


def _build(_: int) -> Tuple[str] | Tuple[str, str]:
    parser = etree.XMLParser()
    parser.resolvers.add(RacingResolver())
    doc = etree.parse(io.BytesIO(MAIN), parser)
    try:
        schema = etree.XMLSchema(doc)
    except etree.XMLSchemaParseError as e:
        return ("PARSE_ERR", str(e)[:120])
    return ("OK",) if schema is not None else ("NULL",)

# enabling the following line will fix the issue
# import ctypes
#
# lib = ctypes.CDLL(etree.__file__)
# lib.xmlSchemaInitTypes()


# SINCE IT IS A THREADING ISSUE, YOU NEED TO CALL IT MULTIPLE TIMES TO PROVOKE THE ERROR
# ALSO TRY CHANGING THE NUMBER OF THREADS (N)
def test_xmlschema_build_race() -> None:
    global _barrier
    bad = []
    for _ in range(30):
        _barrier = threading.Barrier(N)
        with ThreadPoolExecutor(max_workers=N) as executor:
            results = list(executor.map(_build, range(N)))
        bad += [r for r in results if r[0] != "OK"]
    assert not bad, f"{len(bad)} failures, sample={bad[0]}"
```
