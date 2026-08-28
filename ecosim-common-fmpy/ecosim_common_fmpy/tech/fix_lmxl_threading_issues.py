def fix_lmxl_threading_issues() -> None:
    # the following lines try to mitigate multi-threading issues resulting (indirectly) from the fmpy library
    # s. `docs/dev/tech/multi_threading_fmpy.md` for details
    try:
        import ctypes

        from lxml import etree

        lib = ctypes.CDLL(etree.__file__)
        lib.xmlSchemaInitTypes()

    except Exception:
        pass
