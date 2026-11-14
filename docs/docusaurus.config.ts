import { themes as prismThemes } from "prism-react-renderer";
import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";

const repository = "https://github.com/KIT-IAI-ESA/eCoSim";

const config: Config = {
  title: "eCoSim",
  tagline: "Co-Simulation Framework for Energy Systems",
  favicon: "img/favicon.ico",

  future: {
    v4: true,
  },

  url: "https://ecosim.easimov.com",
  baseUrl: "/",
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
          routeBasePath: "docs",
          sidebarPath: "./sidebars.ts",
          editUrl: `${repository}/edit/main/docs/`,
          numberPrefixParser: false,
        },
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
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
        {
          href: "https://easimov.cloud.iai.kit.edu",
          label: "eASiMOV",
          position: "right",
        },
        {
          href: "https://www.iai.kit.edu/english/groups_4104.php",
          label: "ESA",
          position: "right",
        },
        {
          href: "https://www.iai.kit.edu/english/index.php",
          label: "IAI",
          position: "right",
        },
        {
          href: "https://www.kit.edu/english/index.php",
          label: "KIT",
          position: "right",
        },
        { href: repository, label: "GitHub", position: "right" },
      ],
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.vsDark,
      additionalLanguages: ["bash", "ini", "toml"],
    },
    mermaid: {
      theme: { light: "base", dark: "dark" },
      options: {
        flowchart: { curve: "basis" },
        themeVariables: {
          fontFamily: "Work Sans, system-ui, sans-serif",
        },
      },
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
