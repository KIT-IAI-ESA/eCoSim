import type { ReactNode } from "react";
import useBaseUrl from "@docusaurus/useBaseUrl";
import styles from "./styles.module.css";

// easimov footer
const EASIMOV_URL = "https://easimov.cloud.iai.kit.edu";

const LEGAL_PAGES = [
  { slug: "imprint", title: "Imprint" },
  { slug: "privacy", title: "Privacy" },
  { slug: "accessibility", title: "Accessibility" },
  { slug: "acknowledgements", title: "Acknowledgements" },
];

function Divider(): ReactNode {
  return <span aria-hidden className={styles.divider} />;
}

export default function Footer(): ReactNode {
  const asimovO = useBaseUrl("/img/asimov.webp");
  const esaLogo = useBaseUrl("/img/esa.webp");
  const iaiLogo = useBaseUrl("/img/iai.webp");
  const energyLabLogo = useBaseUrl("/img/energy-lab.svg");
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.logos}>
          <a
            href={EASIMOV_URL}
            target="_blank"
            rel="noopener"
            aria-label="eASiMOV website"
            className={styles.easimov}
          >
            <span className="brand-e">e</span>ASiM
            <span className={styles.o}>
              <img src={asimovO} alt="O" />
            </span>
            V
          </a>
          <Divider />
          <a
            href="https://www.iai.kit.edu/english/groups_4104.php"
            target="_blank"
            rel="noopener"
            aria-label="Energy System Analysis research group"
            className={styles.logoLink}
          >
            <img
              src={esaLogo}
              alt=""
              className={`${styles.logo} ${styles.darkInvert}`}
            />
          </a>
          <Divider />
          <a
            href="https://www.iai.kit.edu/english/index.php"
            target="_blank"
            rel="noopener"
            aria-label="Institute for Automation and Applied Informatics"
            className={styles.logoLink}
          >
            <img
              src={iaiLogo}
              alt=""
              className={`${styles.logo} ${styles.darkInvert}`}
            />
          </a>
          <Divider />
          <a
            href="https://www.elab.kit.edu/english/index.php"
            target="_blank"
            rel="noopener"
            aria-label="Energy Lab"
            className={styles.energyLabLink}
          >
            <img
              src={energyLabLogo}
              alt=""
              className={`${styles.energyLab} ${styles.lightInvert}`}
            />
          </a>
        </div>
        <nav aria-label="Footer" className={styles.legal}>
          {LEGAL_PAGES.map((page) => (
            <a
              key={page.slug}
              href={`${EASIMOV_URL}/${page.slug}`}
              target="_blank"
              rel="noopener"
            >
              {page.title}
            </a>
          ))}
        </nav>
        <p className={styles.copyright}>
          © {new Date().getFullYear()} KIT – The University in the Helmholtz
          Association
        </p>
      </div>
    </footer>
  );
}
