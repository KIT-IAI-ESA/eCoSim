# Performance Machines

The machines the [performance tests](../testing.md#performance-tests) have expected data for, by their machine name
(`ECOSIM_PERFORMANCE_MACHINE`).

| Machine | OS | CPU | RAM | Storage | Comment |
| --- | --- | --- | --- | --- | --- |
| `github_ci_default` | - | -| -| -| [standard GitHub-hosted runner for private repositories](https://docs.github.com/en/actions/reference/runners/github-hosted-runners#standard-github-hosted-runners-for-private-repositories); GitHub does not guarantee the CPU model, so the CI times vary more than the local ones |
| `local_tuxedo_infinity_book_pro_15_gen9_amd` | Linux (Fedora) | AMD Ryzen 7 8845HS (8 cores, 16 threads, max. 5.1 GHz, 24 MB cache) | 64 GB DDR5-5600 (2 × 32 GB SO-DIMM, dual channel, G.Skill `F5-5600S4040A32G`, CL40) | 4 TB Samsung SSD 990 PRO (NVMe, PCIe 4.0 x4) | TUXEDO InfinityBook Pro AMD Gen9 |
