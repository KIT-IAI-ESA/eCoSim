import type { ReactNode } from "react";
import Link from "@docusaurus/Link";
import styles from "./styles.module.css";

export default function NavbarLogo(): ReactNode {
  return (
    <Link to="/docs" className={styles.brand}>
      <span className={styles.wordmark}>
        <span className="brand-e">e</span>CoSim
      </span>
      <span aria-hidden className={styles.divider} />
      <span className={styles.docs}>documentation</span>
    </Link>
  );
}
