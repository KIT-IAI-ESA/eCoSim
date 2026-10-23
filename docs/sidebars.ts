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
      items: ['guides/docker', 'guides/hpc-cluster', 'guides/matlab-client', 'guides/pyro5-client'],
    },
    {
      type: 'category',
      label: 'Development',
      items: [
        'development/project-setup',
        'development/architecture',
        'development/developing',
        'development/release-history',
        {
          type: 'category',
          label: 'Technical notes',
          items: [
            'development/tech/hpc-cheat-sheet',
            'development/tech/multi-threading-fmpy',
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
