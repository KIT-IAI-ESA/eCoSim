import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const performance = 'development/performance/2026-07-28/2026-07-28_original_hpc_vs_common_abstraction';

const sidebars: SidebarsConfig = {
  docs: [
    'intro',
    {
      type: 'category',
      label: 'Getting started',
      collapsed: false,
      items: ['getting-started/installation', 'getting-started/quick-start'],
    },
    {
      type: 'category',
      label: 'Guides',
      items: ['guides/docker', 'guides/hpc-cluster', 'guides/matlab-client', 'guides/pyro5-client', 'guides/python-client'],
    },
    {
      type: 'category',
      label: 'Reference',
      items: ['reference/command-line', 'reference/configuration-files'],
    },
    {
      type: 'category',
      label: 'Development',
      items: [
        'development/project-setup',
        'development/architecture',
        'development/developing',
        'development/testing',
        'development/dependencies',
        'development/adding-a-subproject',
        'development/coding-guidelines',
        'development/tips',
        'development/release-history',
        {
          type: 'category',
          label: 'Technical notes',
          items: [
            'development/tech/hpc-cheat-sheet',
            'development/tech/multi-threading-fmpy',
            'development/performance/performance-machines',
            {
              type: 'category',
              label: 'Performance 2026-07-28',
              link: {type: 'doc', id: performance},
              items: [`${performance}_tcp`, `${performance}_dask`],
            },
          ],
        },
      ],
    },
  ],
};

export default sidebars;
