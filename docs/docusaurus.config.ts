import { themes as prismThemes } from "prism-react-renderer";
import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";

const repository = "https://github.com/mekkyz/ecosim-os";

const config: Config = {
  title: "eCoSim",
  tagline: "Co-Simulation Framework for Energy Systems",
  favicon: "img/favicon.ico",

  future: {
    v4: true,
  },

  url: "https://mekkyz.github.io",
  baseUrl: "/ecosim-os/",
  trailingSlash: false,

  onBrokenLinks: "throw",
  markdown: {
    format: "detect",
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: "throw",
    },
  },

  themes: [
    "@docusaurus/theme-mermaid",
    [
      "@easyops-cn/docusaurus-search-local",
      {
        hashed: true,
        indexBlog: false,
        docsDir: "content",
        docsRouteBasePath: "/",
        highlightSearchTermsOnTargetPage: true,
      },
    ],
  ],

  presets: [
    [
      "classic",
      {
        docs: {
          path: "content",
          routeBasePath: "/",
          sidebarPath: "./sidebars.ts",
          editUrl: `${repository}/edit/main/docs/`,
          numberPrefixParser: false,
        },
        blog: false,
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: "eCoSim",
      items: [
        { href: repository, label: "GitHub", position: "right" },
      ],
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.vsDark,
      additionalLanguages: ["bash", "ini", "toml"],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
